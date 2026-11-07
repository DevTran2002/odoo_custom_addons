# -*- coding: utf-8 -*-
import logging
import os

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command

_logger = logging.getLogger(__name__)


class ThCollaboratorUploadWizard(models.TransientModel):
    """Wizard hỗ trợ nạp hàng loạt file hợp đồng công ty từ máy tính."""
    _name = 'th.collaborator.upload.wizard'
    _description = 'Nạp hợp đồng CTV hàng loạt'

    th_mode = fields.Selection([
        ('add', 'Bổ sung hợp đồng mới'),
        ('replace', 'Thay thế hợp đồng cũ'),
    ], string='Chế độ xử lý', default='add', required=True)

    th_company_sign_type = fields.Selection([
        ('signed', 'Bản có chữ ký số'),
        ('raw', 'Bản chưa có ký số'),
    ], string='Phân loại chữ ký số', default='signed', required=True)

    th_contract_type_ids = fields.Many2many(
        'th.collaborator.contract.type', 'th_collaborator_upload_wizard_contract_type_rel',
        'th_wizard_id', 'th_contract_type_id', string='Loại hợp đồng')

    th_batch_date = fields.Date(
        string='Ngày đẩy hợp đồng', default=fields.Date.context_today)
    date_start = fields.Date(
        string='Ngày bắt đầu', default=fields.Date.context_today)
    date_end = fields.Date(
        string='Ngày kết thúc')

    th_attachment_ids = fields.Many2many(
        'ir.attachment', 'th_collaborator_upload_wizard_attachment_rel',
        'th_wizard_id', 'th_attachment_id', string='Các file hợp đồng')

    th_target_contract_ids = fields.Many2many(
        'th.collaborator.contract', 'th_collaborator_upload_wizard_target_contract_rel',
        'th_wizard_id', 'th_contract_id', string='Hợp đồng cần thay thế')

    th_result_note = fields.Text(string='Kết quả xử lý')
    th_is_done = fields.Boolean(string='Đã xử lý', default=False)

    @api.model
    def default_get(self, fields_list):
        """Khởi tạo giá trị mặc định và tự động điền danh sách hợp đồng mục tiêu nếu mở từ danh sách."""
        res = super().default_get(fields_list)
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids')
        if active_model == 'th.collaborator.contract' and active_ids:
            res['th_mode'] = 'replace'
            res['th_target_contract_ids'] = [Command.set(active_ids)]
        return res

    def th_action_import_contracts(self):
        """Thực hiện xử lý nạp hàng loạt tệp hợp đồng theo chế độ bổ sung mới hoặc thay thế."""
        self.ensure_one()
        if not self.th_attachment_ids:
            raise UserError(_('Vui lòng chọn ít nhất 1 file hợp đồng cần tải lên.'))

        Profile = self.env['th.collaborator.profile']
        Contract = self.env['th.collaborator.contract']

        invalid_files = self.th_attachment_ids.filtered(
            lambda att: not Profile._is_allowed_contract_file(att.name, mimetype=att.mimetype))
        if invalid_files:
            raise UserError(_('Chỉ chấp nhận file PDF hoặc hình ảnh (.jpg, .jpeg, .png). Các file sau không hợp lệ:\n%s')
                            % '\n'.join(invalid_files.mapped('name')))

        if self.th_mode == 'add':
            if not self.th_contract_type_ids:
                raise UserError(_('Vui lòng chọn Loại hợp đồng cho đợt hợp đồng mới.'))
            if not self.date_start:
                raise UserError(_('Vui lòng nhập Ngày bắt đầu cho đợt hợp đồng mới.'))
            if not self.date_end:
                raise UserError(_('Vui lòng nhập Ngày kết thúc cho đợt hợp đồng mới.'))
            if self.date_end < self.date_start:
                raise UserError(_('Ngày kết thúc không được nhỏ hơn ngày bắt đầu.'))

        created_contracts = self.env['th.collaborator.contract']
        updated_contracts = self.env['th.collaborator.contract']
        unmatched_errors = []

        target_doc_type = 'company_signed' if self.th_company_sign_type == 'signed' else 'company_raw'

        for att in self.th_attachment_ids:
            # Sử dụng phương thức base đối soát tệp tin dùng chung từ th.collaborator.contract
            existing_contract, phone, code, collaborator_name, err_msg = Contract.th_match_contract_for_file(att.name)
            if err_msg:
                unmatched_errors.append(err_msg)
                continue

            profile = Profile.search([('th_phone_normalized', '=', phone)], limit=1)
            if not profile:
                unmatched_errors.append(
                    _('%s: Không tìm thấy CTV có số điện thoại %s.') % (att.name, phone)
                )
                continue

            # Bắt buộc: Mã HĐ và SĐT phải thuộc về cùng một CTV để tránh nạp nhầm hợp đồng
            if existing_contract and existing_contract.th_collaborator_id.id != profile.id:
                unmatched_errors.append(
                    _('%s: Mã HĐ "%s" thuộc về CTV khác (%s), không khớp với CTV có SĐT %s (%s).') % (
                        att.name, code, existing_contract.th_collaborator_id.name, phone, profile.name
                    )
                )
                continue

            if self.th_mode == 'add':
                if existing_contract:
                    # Kiểm tra trạng thái: Tuyệt đối không cho phép nạp thêm tệp khi hợp đồng đã Hoàn tất hoặc Đã hủy
                    if existing_contract.state in ('close', 'cancel') or existing_contract.th_is_readonly:
                        unmatched_errors.append(
                            _('%s: Hợp đồng "%s" (Mã: %s) đã ở trạng thái Hoàn tất hoặc Đã hủy, không thể nạp thêm tệp.') % (
                                att.name, existing_contract.name, code
                            )
                        )
                        continue

                    # Chỉ cho phép nạp bổ sung tệp vào hợp đồng đã có khi hợp đồng đang ở trạng thái Dự thảo hoặc Chờ pháp chế duyệt
                    if existing_contract.state not in ('draft', 'legal_review'):
                        state_label = dict(existing_contract._fields['state'].selection).get(existing_contract.state, existing_contract.state)
                        unmatched_errors.append(
                            _('%s: Hợp đồng "%s" (Mã: %s) đang ở trạng thái "%s". Chỉ được upload bổ sung khi ở trạng thái Dự thảo hoặc Chờ pháp chế duyệt.') % (
                                att.name, existing_contract.name, code, state_label
                            )
                        )
                        continue

                    # Nạp bổ sung tệp bằng phương thức base dùng chung
                    existing_contract.th_attach_document_file(
                        att, document_type=target_doc_type, notes=_('Bổ sung tệp qua wizard nạp hợp đồng')
                    )
                    updated_contracts |= existing_contract
                    continue

                # Tạo mới hợp đồng
                contract_name = f"Hợp đồng {code} - {collaborator_name or profile.name}"
                new_contract = Contract.create({
                    'name': contract_name,
                    'th_code': code,
                    'th_collaborator_id': profile.id,
                    'user_id': profile.user_id.id if profile.user_id else self.env.user.id,
                    'th_batch_date': self.th_batch_date or fields.Date.context_today(self),
                    'th_contract_type_ids': [Command.set(self.th_contract_type_ids.ids)] if self.th_contract_type_ids else False,
                    'date_start': self.date_start or fields.Date.context_today(self),
                    'date_end': self.date_end,
                    'state': 'draft',
                })
                # Gắn tệp bằng phương thức base dùng chung
                new_contract.th_attach_document_file(
                    att, document_type=target_doc_type, notes=_('Nạp từ wizard tải hàng loạt')
                )
                created_contracts |= new_contract

            else:
                # Chế độ Thay thế: Bắt buộc phải tìm thấy đúng hợp đồng có mã `code` của đúng CTV `profile`
                target_contract = existing_contract
                if not target_contract:
                    unmatched_errors.append(
                        _('%s: Không tìm thấy hợp đồng có mã "%s" của CTV %s (SĐT: %s) để thay thế.') % (
                            att.name, code, profile.name, phone
                        )
                    )
                    continue

                # Kiểm tra trạng thái: Tuyệt đối không cho phép thay thế tệp khi hợp đồng đã Hoàn tất hoặc Đã hủy
                if target_contract.state in ('close', 'cancel') or target_contract.th_is_readonly:
                    unmatched_errors.append(
                        _('%s: Hợp đồng "%s" (Mã: %s) đã ở trạng thái Hoàn tất hoặc Đã hủy, không thể thay thế tệp.') % (
                            att.name, target_contract.name, code
                        )
                    )
                    continue

                # Chỉ cho phép thay thế tệp công ty khi hợp đồng đang ở trạng thái Dự thảo hoặc Chờ pháp chế duyệt
                if target_contract.state not in ('draft', 'legal_review'):
                    state_label = dict(target_contract._fields['state'].selection).get(target_contract.state, target_contract.state)
                    unmatched_errors.append(
                        _('%s: Hợp đồng "%s" (Mã: %s) đang ở trạng thái "%s". Chỉ được thay thế tệp khi ở trạng thái Dự thảo hoặc Chờ pháp chế duyệt.') % (
                            att.name, target_contract.name, code, state_label
                        )
                    )
                    continue

                # Thay thế tệp bằng phương thức base dùng chung
                target_contract.th_replace_document_file(
                    att, document_type=target_doc_type, notes=_('Thay thế file qua nạp hàng loạt')
                )
                updated_contracts |= target_contract

        self.th_attachment_ids.filtered(lambda a: a.res_model == self._name).unlink()

        result_lines = []
        if self.th_mode == 'add':
            if created_contracts:
                result_lines.append(_('Tạo mới thành công %s hợp đồng.') % len(created_contracts))
            if updated_contracts:
                result_lines.append(_('Bổ sung tệp thành công cho %s hợp đồng đã có.') % len(updated_contracts))
            if not created_contracts and not updated_contracts:
                result_lines.append(_('Không có hợp đồng nào được tạo mới hoặc bổ sung tệp.'))
        else:
            result_lines.append(_('Cập nhật/thay thế file thành công cho %s hợp đồng.') % len(updated_contracts))

        if unmatched_errors:
            result_lines.append(_('\nDanh sách file xử lý thất bại (%s file):') % len(unmatched_errors))
            for err in unmatched_errors:
                result_lines.append(f"  - {err}")

        self.write({
            'th_result_note': '\n'.join(result_lines),
            'th_is_done': True,
        })
        _logger.info('Upload wizard: created %s, updated %s, failed %s',
                     len(created_contracts), len(updated_contracts), len(unmatched_errors))

        return {
            'name': _('Kết quả nạp hợp đồng'),
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
