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

    th_company_sign_type = fields.Selection([
        ('signed', 'Bản có chữ ký số'),
        ('raw', 'Bản chưa có ký số'),
    ], string='Phân loại chữ ký số', default='signed', required=True)

    th_action_type = fields.Selection([
        ('download', 'Tải về hàng loạt (ZIP)'),
        ('upload', 'Nạp tệp lên hàng loạt'),
        ('replace', 'Thay thế tệp hàng loạt'),
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

    @api.depends('th_contract_ids', 'th_contract_type', 'th_action_type', 'th_company_sign_type')
    def _compute_contract_counts(self):
        """Tính toán tổng số hợp đồng đã chọn và số lượng hợp đồng đã có file sẵn sàng thao tác."""
        for rec in self:
            rec.th_total_selected = len(rec.th_contract_ids)
            has_file_count = 0
            for contract in rec.th_contract_ids:
                if rec.th_contract_type == 'company':
                    if rec.th_action_type == 'download':
                        # Khi tải ZIP, lấy tất cả tệp do công ty cung cấp
                        if contract._get_company_mail_attachments():
                            has_file_count += 1
                    else:
                        # Khi nạp hoặc thay thế, kiểm tra theo loại chữ ký số được chọn
                        if rec.th_company_sign_type == 'signed':
                            docs = contract.th_document_ids.filtered(lambda d: d.th_document_type == 'company_signed')
                            if docs or contract.th_company_attachment_ids:
                                has_file_count += 1
                        else:
                            docs = contract.th_document_ids.filtered(lambda d: d.th_document_type == 'company_raw')
                            if docs:
                                has_file_count += 1
                elif rec.th_contract_type == 'self':
                    if contract.th_self_attachment_ids or contract.th_document_ids.filtered(lambda d: d.th_document_type in ('ctv_signed', 'ctv_digital_signed')):
                        has_file_count += 1
                elif rec.th_contract_type == 'final':
                    if contract.th_final_attachment_id or contract.th_document_ids.filtered(lambda d: d.th_document_type == 'final_signed'):
                        has_file_count += 1
            rec.th_total_has_file = has_file_count

    @api.onchange('th_action_type')
    def _onchange_th_action_type(self):
        """Kích hoạt onchange khi chuyển đổi thao tác thực hiện để đảm bảo giao diện phản hồi tức thì."""
        self._compute_contract_counts()

    @api.onchange('th_contract_type')
    def _onchange_th_contract_type(self):
        """Cập nhật lại số lượng tệp sẵn sàng khi đổi phân loại hợp đồng."""
        self._compute_contract_counts()

    @api.onchange('th_company_sign_type')
    def _onchange_th_company_sign_type(self):
        """Cập nhật lại số lượng tệp sẵn sàng khi đổi loại chữ ký số công ty."""
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

        # Kiểm tra xem có bất kỳ hợp đồng nào có file theo đúng phân loại không
        has_file = False
        for contract in self.th_contract_ids:
            if self.th_contract_type == 'company':
                if contract._get_company_mail_attachments():
                    has_file = True
                    break
            elif self.th_contract_type == 'self':
                if contract.th_self_attachment_ids or contract.th_document_ids.filtered(lambda d: d.th_document_type in ('ctv_signed', 'ctv_digital_signed')):
                    has_file = True
                    break
            elif self.th_contract_type == 'final':
                if contract.th_final_attachment_id or contract.th_document_ids.filtered(lambda d: d.th_document_type == 'final_signed'):
                    has_file = True
                    break

        if not has_file:
            label = dict(self._fields['th_contract_type'].selection).get(self.th_contract_type)
            raise UserError(_('Không có hợp đồng nào trong các hợp đồng đã chọn có tệp đính kèm (%s) để tải về.') % label)

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

        if self.th_action_type not in ('upload', 'replace'):
            raise UserError(_('Thao tác không hợp lệ.'))

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
                target_doc_type = 'company_signed' if self.th_company_sign_type == 'signed' else 'company_raw'
                doc_type_label = _('HĐ công ty có chữ ký số') if self.th_company_sign_type == 'signed' else _('HĐ công ty chưa có ký số')
                type_docs = contract.th_document_ids.filtered(lambda d: d.th_document_type == target_doc_type)

                if self.th_action_type == 'upload':
                    # Chế độ nạp mới: Không phân biệt có hay chưa, luôn cho phép nạp thêm tệp vào hợp đồng
                    self.env['th.collaborator.contract.document'].sudo().create({
                        'name': att.name,
                        'th_contract_id': contract.id,
                        'th_document_type': target_doc_type,
                        'th_file': att.datas,
                        'th_file_name': att.name,
                        'th_attachment_id': att.id,
                        'th_uploaded_by': 'company',
                        'th_upload_date': fields.Datetime.now(),
                        'th_user_id': self.env.user.id,
                        'th_notes': _('Nạp tệp %s qua thao tác hàng loạt') % doc_type_label,
                    })
                    if target_doc_type == 'company_signed':
                        contract.write({'th_company_attachment_ids': [Command.link(att.id)]})
                    contract.message_post(body=_('Đã nạp tệp [%s] (%s) qua thao tác hàng loạt.') % (att.name, doc_type_label))
                    updated_contracts |= contract

                else:
                    # Chế độ thay thế: Bắt buộc hợp đồng phải có tệp sẵn thì mới thay thế được
                    if not type_docs:
                        unmatched_errors.append(
                            _('%s: Hợp đồng "%s" chưa có %s để thay thế. Vui lòng chọn thao tác "Nạp tệp lên hàng loạt".') % (
                                att.name, contract.name, doc_type_label
                            )
                        )
                        continue

                    # 1. Tìm tài liệu có cùng tên file để thay thế chính xác tệp đó
                    same_name_docs = type_docs.filtered(
                        lambda d: d.name == att.name or d.th_file_name == att.name
                    )
                    if same_name_docs:
                        main_doc = same_name_docs[0]
                        old_att = main_doc.th_attachment_id
                        # sudo: Ghi đè thông tin tài liệu hợp đồng nội bộ
                        main_doc.sudo().write({
                            'name': att.name,
                            'th_document_type': target_doc_type,
                            'th_file': att.datas,
                            'th_file_name': att.name,
                            'th_attachment_id': att.id,
                            'th_uploaded_by': 'company',
                            'th_upload_date': fields.Datetime.now(),
                            'th_user_id': self.env.user.id,
                            'th_notes': _('Thay thế tệp %s qua thao tác hàng loạt') % doc_type_label,
                        })
                        if old_att and old_att.id != att.id:
                            # sudo: Dọn dẹp tệp attachment cũ không còn sử dụng
                            old_att.sudo().unlink()
                        # Chỉ dọn dẹp các bản ghi trùng đúng tên đó do lần trước tạo lặp
                        if len(same_name_docs) > 1:
                            same_name_docs[1:].sudo().unlink()
                    else:
                        # Nếu không có tệp trùng tên:
                        # Nếu hợp đồng chỉ có duy nhất 1 tệp thuộc phân loại này thì thay thế tệp đó
                        if len(type_docs) == 1:
                            main_doc = type_docs[0]
                            old_att = main_doc.th_attachment_id
                            # sudo: Ghi đè thông tin tài liệu hợp đồng nội bộ
                            main_doc.sudo().write({
                                'name': att.name,
                                'th_document_type': target_doc_type,
                                'th_file': att.datas,
                                'th_file_name': att.name,
                                'th_attachment_id': att.id,
                                'th_uploaded_by': 'company',
                                'th_upload_date': fields.Datetime.now(),
                                'th_user_id': self.env.user.id,
                                'th_notes': _('Thay thế tệp %s qua thao tác hàng loạt') % doc_type_label,
                            })
                            if old_att and old_att.id != att.id:
                                # sudo: Dọn dẹp tệp attachment cũ không còn sử dụng
                                old_att.sudo().unlink()
                        else:
                            unmatched_errors.append(
                                _('%s: Hợp đồng "%s" có nhiều tệp %s khác nhau. Không tìm thấy tệp trùng tên để thay thế.') % (
                                    att.name, contract.name, doc_type_label
                                )
                            )
                            continue

                    # Cập nhật th_company_attachment_ids an toàn: giữ nguyên các tệp khác, chỉ thay tệp cùng tên
                    if target_doc_type == 'company_signed':
                        old_same_name_atts = contract.th_company_attachment_ids.filtered(lambda a: a.name == att.name)
                        commands = [Command.link(att.id)]
                        for old_a in old_same_name_atts:
                            if old_a.id != att.id:
                                commands.append(Command.unlink(old_a.id))
                        contract.write({'th_company_attachment_ids': commands})

                    contract.message_post(body=_('Đã thay thế tệp [%s] (%s) qua thao tác hàng loạt.') % (att.name, doc_type_label))
                    updated_contracts |= contract

            elif self.th_contract_type == 'self':
                is_raw = bool(contract.th_contract_flow == 'raw_template')
                doc_type = 'ctv_signed' if is_raw else 'ctv_digital_signed'
                doc_type_label = _('HĐ CTV nộp')
                existing_docs = contract.th_document_ids.filtered(lambda d: d.th_document_type in ('ctv_signed', 'ctv_digital_signed'))

                if self.th_action_type == 'upload':
                    # Chế độ nạp mới: Không phân biệt có hay chưa, luôn cho phép nạp thêm tệp CTV nộp
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
                        'th_notes': _('Nạp tệp CTV nộp qua thao tác hàng loạt'),
                    })
                    contract.write({'th_self_attachment_ids': [Command.link(att.id)]})
                    update_vals = {'th_last_upload_date': fields.Datetime.now()}
                    if contract.state in ('draft', 'open', 'sent'):
                        update_vals['state'] = 'pending_sign' if is_raw else 'submitted'
                    contract.write(update_vals)
                    contract.message_post(body=_('Đã nạp tệp CTV nộp [%s] qua thao tác hàng loạt.') % att.name)
                    updated_contracts |= contract

                else:
                    # Chế độ thay thế: Bắt buộc hợp đồng phải có tệp CTV nộp sẵn thì mới thay thế được
                    if not existing_docs:
                        unmatched_errors.append(
                            _('%s: Hợp đồng "%s" chưa có tệp CTV nộp để thay thế. Vui lòng chọn thao tác "Nạp tệp lên hàng loạt".') % (
                                att.name, contract.name
                            )
                        )
                        continue

                    same_name_docs = existing_docs.filtered(
                        lambda d: d.name == att.name or d.th_file_name == att.name
                    )
                    if same_name_docs:
                        main_doc = same_name_docs[0]
                        old_att = main_doc.th_attachment_id
                        # sudo: Ghi đè thông tin tài liệu CTV nộp
                        main_doc.sudo().write({
                            'name': att.name,
                            'th_document_type': doc_type,
                            'th_file': att.datas,
                            'th_file_name': att.name,
                            'th_attachment_id': att.id,
                            'th_uploaded_by': 'ctv',
                            'th_upload_date': fields.Datetime.now(),
                            'th_user_id': self.env.user.id,
                            'th_notes': _('Thay thế tệp CTV nộp qua thao tác hàng loạt'),
                        })
                        if old_att and old_att.id != att.id:
                            # sudo: Dọn dẹp tệp attachment cũ không còn sử dụng
                            old_att.sudo().unlink()
                        if len(same_name_docs) > 1:
                            # sudo: Dọn dẹp các bản ghi tài liệu thừa bị nhân bản cùng tên
                            same_name_docs[1:].sudo().unlink()
                    else:
                        if len(existing_docs) == 1:
                            main_doc = existing_docs[0]
                            old_att = main_doc.th_attachment_id
                            # sudo: Ghi đè thông tin tài liệu CTV nộp
                            main_doc.sudo().write({
                                'name': att.name,
                                'th_document_type': doc_type,
                                'th_file': att.datas,
                                'th_file_name': att.name,
                                'th_attachment_id': att.id,
                                'th_uploaded_by': 'ctv',
                                'th_upload_date': fields.Datetime.now(),
                                'th_user_id': self.env.user.id,
                                'th_notes': _('Thay thế tệp CTV nộp qua thao tác hàng loạt'),
                            })
                            if old_att and old_att.id != att.id:
                                # sudo: Dọn dẹp tệp attachment cũ không còn sử dụng
                                old_att.sudo().unlink()
                        else:
                            unmatched_errors.append(
                                _('%s: Hợp đồng "%s" có nhiều tệp CTV nộp khác nhau. Không tìm thấy tệp trùng tên để thay thế.') % (
                                    att.name, contract.name
                                )
                            )
                            continue

                    # Cập nhật Many2many an toàn: giữ nguyên tệp khác, chỉ gỡ tệp cùng tên
                    old_same_name_atts = contract.th_self_attachment_ids.filtered(lambda a: a.name == att.name)
                    commands = [Command.link(att.id)]
                    for old_a in old_same_name_atts:
                        if old_a.id != att.id:
                            commands.append(Command.unlink(old_a.id))
                    contract.write({'th_self_attachment_ids': commands})

                    update_vals = {'th_last_upload_date': fields.Datetime.now()}
                    if contract.state in ('draft', 'open', 'sent'):
                        update_vals['state'] = 'pending_sign' if is_raw else 'submitted'
                    contract.write(update_vals)
                    contract.message_post(body=_('Đã thay thế tệp CTV nộp [%s] qua thao tác hàng loạt.') % att.name)
                    updated_contracts |= contract

            elif self.th_contract_type == 'final':
                doc_type_label = _('HĐ đủ 2 chữ ký')
                existing_docs = contract.th_document_ids.filtered(lambda d: d.th_document_type == 'final_signed')

                if self.th_action_type == 'upload':
                    # Chế độ nạp mới: Luôn cho phép nạp bản hợp đồng 2 chữ ký
                    contract.write({'th_final_attachment_id': att.id})
                    # sudo: Tạo bản ghi tài liệu hoàn tất 2 chữ ký
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
                        'th_notes': _('Nạp bản HĐ đủ 2 chữ ký qua thao tác hàng loạt'),
                    })
                    contract.message_post(body=_('Đã nạp bản HĐ đủ 2 chữ ký [%s] qua thao tác hàng loạt.') % att.name)
                    updated_contracts |= contract

                else:
                    # Chế độ thay thế: Bắt buộc phải có tệp sẵn thì mới thay thế được
                    if not existing_docs and not contract.th_final_attachment_id:
                        unmatched_errors.append(
                            _('%s: Hợp đồng "%s" chưa có bản HĐ đủ 2 chữ ký để thay thế. Vui lòng chọn thao tác "Nạp tệp lên hàng loạt".') % (
                                att.name, contract.name
                            )
                        )
                        continue

                    contract.write({'th_final_attachment_id': att.id})
                    if existing_docs:
                        main_doc = existing_docs[0]
                        old_att = main_doc.th_attachment_id
                        # sudo: Ghi đè thông tin tài liệu hoàn tất 2 chữ ký
                        main_doc.sudo().write({
                            'name': att.name,
                            'th_document_type': 'final_signed',
                            'th_file': att.datas,
                            'th_file_name': att.name,
                            'th_attachment_id': att.id,
                            'th_uploaded_by': 'company',
                            'th_upload_date': fields.Datetime.now(),
                            'th_user_id': self.env.user.id,
                            'th_notes': _('Thay thế bản HĐ đủ 2 chữ ký qua thao tác hàng loạt'),
                        })
                        if old_att and old_att.id != att.id:
                            # sudo: Dọn dẹp tệp attachment cũ không còn sử dụng
                            old_att.sudo().unlink()
                        if len(existing_docs) > 1:
                            # sudo: Dọn dẹp các bản ghi tài liệu thừa bị nhân bản cùng loại
                            existing_docs[1:].sudo().unlink()
                    else:
                        # sudo: Tạo bản ghi tài liệu hoàn tất 2 chữ ký
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
                            'th_notes': _('Thay thế bản HĐ đủ 2 chữ ký qua thao tác hàng loạt'),
                        })
                    contract.message_post(body=_('Đã thay thế bản HĐ đủ 2 chữ ký [%s] qua thao tác hàng loạt.') % att.name)
                    updated_contracts |= contract

        # Dọn dẹp các tệp đính kèm tạm thời liên kết với wizard
        self.th_attachment_ids.filtered(lambda a: a.res_model == self._name).unlink()

        action_verb = _('Thay thế') if self.th_action_type == 'replace' else _('Nạp')
        result_lines = [
            _('%s tệp thành công cho %s hợp đồng.') % (action_verb, len(updated_contracts))
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

