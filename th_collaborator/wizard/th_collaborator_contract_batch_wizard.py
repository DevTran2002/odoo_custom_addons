# -*- coding: utf-8 -*-
import io
import logging
import os
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command

_logger = logging.getLogger(__name__)


class ThCollaboratorContractBatchWizard(models.TransientModel):
    """Wizard hỗ trợ tải về hoặc nạp tệp lên hàng loạt cho các hợp đồng đã chọn."""
    _name = 'th.collaborator.contract.batch.wizard'
    _description = 'Thao tác hợp đồng hàng loạt'

    th_contract_type = fields.Selection([
        ('company', 'Hợp đồng công ty cung cấp'),
        ('self', 'Hợp đồng CTV nộp'),
        ('final', 'Hợp đồng hoàn tất đủ 2 chữ ký'),
    ], string='Phân loại hợp đồng', default='company', required=True)

    th_action_type = fields.Selection([
        ('download', 'Tải về hàng loạt (ZIP)'),
        ('upload', 'Nạp tệp lên hàng loạt'),
    ], string='Thao tác thực hiện', default='download', required=True)

    th_contract_ids = fields.Many2many(
        'th.collaborator.contract',
        'th_collaborator_contract_batch_wizard_contract_rel',
        'th_wizard_id', 'th_contract_id',
        string='Hợp đồng đã chọn')

    th_total_selected = fields.Integer(
        string='Số HĐ đã chọn', compute='_compute_contract_counts')
    th_total_has_file = fields.Integer(
        string='Số HĐ đã có tệp', compute='_compute_contract_counts')

    th_attachment_ids = fields.Many2many(
        'ir.attachment',
        'th_collaborator_contract_batch_wizard_attachment_rel',
        'th_wizard_id', 'th_attachment_id',
        string='Các tệp tải lên')

    th_result_note = fields.Text(string='Kết quả xử lý')
    th_is_done = fields.Boolean(string='Đã xử lý xong', default=False)

    @api.model
    def default_get(self, fields_list):
        """Khởi tạo danh sách hợp đồng mục tiêu từ các bản ghi được chọn."""
        res = super().default_get(fields_list)
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids')
        if active_model == 'th.collaborator.contract' and active_ids:
            res['th_contract_ids'] = [Command.set(active_ids)]
        return res

    @api.depends('th_contract_ids', 'th_contract_type')
    def _compute_contract_counts(self):
        """Tính toán tổng số hợp đồng đã chọn và số lượng hợp đồng đã có file sẵn sàng tải."""
        for rec in self:
            rec.th_total_selected = len(rec.th_contract_ids)
            has_file_count = 0
            for contract in rec.th_contract_ids:
                if rec.th_contract_type == 'company':
                    if contract._get_company_mail_attachments():
                        has_file_count += 1
                elif rec.th_contract_type == 'self':
                    if contract.th_self_attachment_ids:
                        has_file_count += 1
                elif rec.th_contract_type == 'final':
                    if contract.th_final_attachment_id:
                        has_file_count += 1
            rec.th_total_has_file = has_file_count

    @api.onchange('th_action_type')
    def _onchange_th_action_type(self):
        """Kích hoạt onchange khi chuyển đổi thao tác thực hiện để đảm bảo giao diện phản hồi tức thì."""
        pass

    @api.onchange('th_contract_type')
    def _onchange_th_contract_type(self):
        """Cập nhật lại số lượng tệp sẵn sàng khi đổi phân loại hợp đồng."""
        self._compute_contract_counts()

    def action_clear_contracts(self):
        """Xóa toàn bộ hợp đồng khỏi danh sách đang chọn trong wizard."""
        self.ensure_one()
        self.write({'th_contract_ids': [Command.clear()]})
        return {
            'name': _('Thao tác hợp đồng hàng loạt'),
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def th_action_download_zip(self):
        """Khởi tạo đường dẫn tải xuống gói tệp ZIP chứa toàn bộ tài liệu của các hợp đồng đã chọn."""
        self.ensure_one()
        if not self.th_contract_ids:
            raise UserError(_('Vui lòng chọn ít nhất 1 hợp đồng.'))

        # Kiểm tra xem có bất kỳ hợp đồng nào có file không
        has_file = False
        for contract in self.th_contract_ids:
            if self.th_contract_type == 'company' and contract._get_company_mail_attachments():
                has_file = True
                break
            elif self.th_contract_type == 'self' and contract.th_self_attachment_ids:
                has_file = True
                break
            elif self.th_contract_type == 'final' and contract.th_final_attachment_id:
                has_file = True
                break

        if not has_file:
            raise UserError(_('Không có hợp đồng nào trong các hợp đồng đã chọn có tệp đính kèm để tải về.'))

        contract_ids_param = ','.join(str(cid) for cid in self.th_contract_ids.ids)
        return {
            'type': 'ir.actions.act_url',
            'url': f'/th_collaborator/download_batch?contract_ids={contract_ids_param}&contract_type={self.th_contract_type}',
            'target': 'new',
        }

    def _match_contract_for_file(self, file_name, target_contracts):
        """Đối chiếu tên tệp với danh sách hợp đồng đã chọn theo Mã hợp đồng hoặc Số điện thoại."""
        base_name = os.path.splitext(os.path.basename(file_name))[0].strip()
        tokens = [t.strip() for t in re.split(r'[_\\-\\s.]', base_name) if t.strip()]

        Profile = self.env['th.collaborator.profile']

        # 1. Ưu tiên đối chiếu chính xác theo Mã hợp đồng (th_code)
        for contract in target_contracts:
            if contract.th_code:
                code_lower = contract.th_code.strip().lower()
                for token in tokens:
                    if token.lower() == code_lower:
                        return contract
                if code_lower in base_name.lower() and len(code_lower) >= 3:
                    return contract

        # 2. Đối chiếu theo Số điện thoại của CTV nếu tên file có chứa SĐT
        for token in tokens:
            normalized = Profile._normalize_phone(token)
            if len(normalized) >= 9:
                matched_contracts = target_contracts.filtered(
                    lambda c: c.th_collaborator_id.th_phone_normalized == normalized)
                if len(matched_contracts) == 1:
                    return matched_contracts[0]

        # 3. Đối chiếu theo Số thứ tự CTV nếu tên file theo quy ước [stt].AUM-HĐDVTT.[Tên CTV]
        first_token = tokens[0] if tokens else ''
        if first_token.isdigit():
            stt_num = int(first_token)
            matched_contracts = target_contracts.filtered(
                lambda c: c.th_collaborator_id.th_sequence == stt_num)
            if len(matched_contracts) == 1:
                return matched_contracts[0]

        # 4. Đối chiếu theo Tên CTV nếu trong tên file có chứa tên CTV
        for contract in target_contracts:
            ctv_name = (contract.th_collaborator_id.name or '').strip().lower()
            if ctv_name and ctv_name in base_name.lower():
                return contract

        return False

    def th_action_upload_files(self):
        """Thực hiện gắn hàng loạt tệp tải lên vào đúng các hợp đồng đã chọn."""
        self.ensure_one()
        if not self.th_attachment_ids:
            raise UserError(_('Vui lòng chọn ít nhất 1 tệp hợp đồng cần nạp lên.'))
        if not self.th_contract_ids:
            raise UserError(_('Không có hợp đồng mục tiêu nào được chọn.'))

        Profile = self.env['th.collaborator.profile']
        invalid_files = self.th_attachment_ids.filtered(
            lambda att: not Profile._is_allowed_contract_file(att.name, mimetype=att.mimetype))
        if invalid_files:
            raise UserError(_('Chỉ chấp nhận tệp định dạng PDF hoặc hình ảnh (.jpg, .jpeg, .png). Các tệp sau không hợp lệ:\n%s')
                            % '\n'.join(invalid_files.mapped('name')))

        target_contracts = self.th_contract_ids
        updated_contracts = self.env['th.collaborator.contract']
        unmatched_errors = []

        for att in self.th_attachment_ids:
            contract = self._match_contract_for_file(att.name, target_contracts)
            if not contract:
                unmatched_errors.append(
                    _('%s: Không tìm thấy Mã HĐ hoặc SĐT tương ứng trong danh sách các hợp đồng đang được chọn.') % att.name
                )
                continue

            if contract.th_is_readonly or contract.state in ('close', 'cancel'):
                unmatched_errors.append(
                    _('%s: Hợp đồng "%s" (Mã: %s) đã đóng hoặc hết hạn, không thể cập nhật thêm tệp.') % (
                        att.name, contract.name, contract.th_code or _('Chưa có mã'))
                )
                continue

            att.write({
                'res_model': contract._name,
                'res_id': contract.id,
            })

            if self.th_contract_type == 'company':
                # Cập nhật tệp hợp đồng phía công ty cung cấp
                contract.write({
                    'th_company_attachment_ids': [Command.set([att.id])],
                })
                # sudo: Ghi nhận văn bản lịch sử tài liệu hợp đồng nội bộ
                self.env['th.collaborator.contract.document'].sudo().create({
                    'name': att.name,
                    'th_contract_id': contract.id,
                    'th_document_type': 'company_signed',
                    'th_file': att.datas,
                    'th_file_name': att.name,
                    'th_attachment_id': att.id,
                    'th_uploaded_by': 'company',
                    'th_upload_date': fields.Datetime.now(),
                    'th_user_id': self.env.user.id,
                    'th_notes': _('Nạp từ thao tác hàng loạt trên danh sách'),
                })
                contract.message_post(
                    body=_('Đã nạp tệp HĐ công ty mới [%s] qua thao tác hàng loạt.') % att.name
                )
                updated_contracts |= contract

            elif self.th_contract_type == 'self':
                # Cập nhật tệp hợp đồng phía CTV nộp
                contract.write({
                    'th_self_attachment_ids': [Command.set([att.id])],
                })
                is_raw = bool(contract.th_contract_flow == 'raw_template')
                doc_type = 'ctv_signed' if is_raw else 'ctv_digital_signed'
                # sudo: Ghi nhận văn bản lịch sử tài liệu hợp đồng nội bộ
                self.env['th.collaborator.contract.document'].sudo().create({
                    'name': att.name,
                    'th_contract_id': contract.id,
                    'th_document_type': doc_type,
                    'th_file': att.datas,
                    'th_file_name': att.name,
                    'th_attachment_id': att.id,
                    'th_uploaded_by': 'ctv',
                    'th_upload_date': fields.Datetime.now(),
                    'th_user_id': self.env.user.id,
                    'th_notes': _('Nạp tệp CTV nộp qua thao tác hàng loạt trên danh sách'),
                })
                update_vals = {
                    'th_last_upload_date': fields.Datetime.now(),
                }
                if contract.state in ('draft', 'open', 'sent'):
                    update_vals['state'] = 'pending_sign' if is_raw else 'submitted'
                contract.write(update_vals)
                contract.message_post(
                    body=_('Đã nạp tệp CTV nộp [%s] qua thao tác hàng loạt.') % att.name
                )
                updated_contracts |= contract

            elif self.th_contract_type == 'final':
                # Cập nhật tệp hợp đồng hoàn tất đủ 2 chữ ký
                contract.write({
                    'th_final_attachment_id': att.id,
                })
                # sudo: Ghi nhận văn bản lịch sử tài liệu hợp đồng nội bộ
                self.env['th.collaborator.contract.document'].sudo().create({
                    'name': att.name,
                    'th_contract_id': contract.id,
                    'th_document_type': 'final_signed',
                    'th_file': att.datas,
                    'th_file_name': att.name,
                    'th_attachment_id': att.id,
                    'th_uploaded_by': 'company',
                    'th_upload_date': fields.Datetime.now(),
                    'th_user_id': self.env.user.id,
                    'th_notes': _('Nạp bản hoàn tất 2 chữ ký qua thao tác hàng loạt trên danh sách'),
                })
                contract.message_post(
                    body=_('Đã nạp bản HĐ đủ 2 chữ ký [%s] qua thao tác hàng loạt.') % att.name
                )
                updated_contracts |= contract

        # Dọn dẹp các tệp đính kèm tạm thời liên kết với wizard
        self.th_attachment_ids.filtered(lambda a: a.res_model == self._name).unlink()

        result_lines = [
            _('Cập nhật tệp thành công cho %s hợp đồng.') % len(updated_contracts)
        ]
        if unmatched_errors:
            result_lines.append(_('\nDanh sách tệp xử lý thất bại (%s tệp):') % len(unmatched_errors))
            for err in unmatched_errors:
                result_lines.append(f'  - {err}')

        self.write({
            'th_result_note': '\n'.join(result_lines),
            'th_is_done': True,
        })

        return {
            'name': _('Kết quả thao tác hợp đồng'),
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

