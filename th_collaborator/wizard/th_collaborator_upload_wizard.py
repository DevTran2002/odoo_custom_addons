# -*- coding: utf-8 -*-
import logging
import os
import re

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

    def _extract_phone_and_code(self, file_name):
        """Bóc tách số điện thoại, mã hợp đồng và tên hợp đồng từ tên tệp tin tải lên."""
        Profile = self.env['th.collaborator.profile']
        base_name = os.path.splitext(os.path.basename(file_name))[0]
        tokens = [token.strip() for token in re.split(r'[_\-\s]', base_name) if token.strip()]

        if not tokens:
            return False, False, False

        phone = Profile._normalize_phone(tokens[0])
        if len(phone) < 9:
            return False, False, False

        code = tokens[1] if len(tokens) > 1 else False
        custom_name = ' '.join(tokens[2:]) if len(tokens) > 2 else False
        return phone, code, custom_name

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

        extracted_data = []
        all_phones = set()
        for att in self.th_attachment_ids:
            phone, code, custom_name = self._extract_phone_and_code(att.name)
            if not phone:
                unmatched_errors.append(f"{att.name}: Không tìm thấy số điện thoại hợp lệ ở đầu tên file.")
                continue
            if not code:
                unmatched_errors.append(f"{att.name}: Không tìm thấy Mã hợp đồng (cấu trúc yêu cầu: SĐT_MãHĐ_TênFile).")
                continue
            extracted_data.append((att, phone, code, custom_name))
            all_phones.add(phone)

        profiles = Profile.search([('th_phone_normalized', 'in', list(all_phones))])
        profile_map = {p.th_phone_normalized: p for p in profiles}

        for att, phone, code, custom_name in extracted_data:
            profile = profile_map.get(phone)
            if not profile:
                unmatched_errors.append(f"{att.name}: Không tìm thấy CTV có số điện thoại {phone}.")
                continue

            existing_contract = Contract.search([('th_code', '=', code)], limit=1)

            if self.th_mode == 'add':
                if existing_contract:
                    unmatched_errors.append(
                        f"{att.name}: Mã HĐ '{code}' đã tồn tại trong hệ thống (HĐ: {existing_contract.name} - CTV: {existing_contract.th_collaborator_id.name}). Vui lòng chọn chế độ Thay thế nếu muốn cập nhật file."
                    )
                    continue

                contract_name = custom_name or f"Hợp đồng {code} - {profile.name}"
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
                att.write({
                    'res_model': new_contract._name,
                    'res_id': new_contract.id,
                })
                new_contract.write({
                    'th_company_attachment_ids': [Command.link(att.id)],
                })
                self.env['th.collaborator.contract.document'].sudo().create({
                    'name': att.name,
                    'th_contract_id': new_contract.id,
                    'th_document_type': 'company_signed',
                    'th_file': att.datas,
                    'th_file_name': att.name,
                    'th_attachment_id': att.id,
                    'th_uploaded_by': 'company',
                    'th_upload_date': fields.Datetime.now(),
                    'th_user_id': self.env.user.id,
                    'th_notes': _('Nạp từ wizard tải hàng loạt'),
                })
                new_contract.message_post(body=_('Tạo mới hợp đồng qua nạp file hàng loạt (Tệp nguồn: %s).') % att.name)
                created_contracts |= new_contract

            else:
                target_contract = existing_contract
                if not target_contract:
                    if len(profile.th_contract_ids) == 1:
                        target_contract = profile.th_contract_ids[0]
                    else:
                        running = profile.th_contract_ids.filtered(lambda c: c.state == 'open')
                        if len(running) == 1:
                            target_contract = running[0]

                if not target_contract:
                    unmatched_errors.append(
                        f"{att.name}: Không tìm thấy hợp đồng có mã '{code}' của CTV {profile.name} để thay thế."
                    )
                    continue

                if target_contract.th_collaborator_id.id != profile.id:
                    unmatched_errors.append(
                        f"{att.name}: Mã HĐ '{code}' thuộc về CTV khác ({target_contract.th_collaborator_id.name}), không khớp với SĐT {phone}."
                    )
                    continue

                old_file_names = target_contract.th_company_attachment_ids.mapped('name')
                att.write({
                    'res_model': target_contract._name,
                    'res_id': target_contract.id,
                })
                # Cập nhật danh sách attachment: giữ nguyên các tệp khác, chỉ thay thế tệp cùng tên nếu có
                old_same_name_atts = target_contract.th_company_attachment_ids.filtered(lambda a: a.name == att.name)
                commands = [Command.link(att.id)]
                for old_a in old_same_name_atts:
                    if old_a.id != att.id:
                        commands.append(Command.unlink(old_a.id))
                target_contract.write({'th_company_attachment_ids': commands})

                # Tìm bản ghi tài liệu có cùng tên file để ghi đè đúng tệp đó
                same_name_docs = target_contract.th_document_ids.filtered(
                    lambda d: d.name == att.name or d.th_file_name == att.name
                )
                if same_name_docs:
                    # Ghi đè đúng bản ghi tài liệu cùng tên
                    main_doc = same_name_docs[0]
                    main_doc.sudo().write({
                        'name': att.name,
                        'th_document_type': 'company_signed',
                        'th_file': att.datas,
                        'th_file_name': att.name,
                        'th_attachment_id': att.id,
                        'th_uploaded_by': 'company',
                        'th_upload_date': fields.Datetime.now(),
                        'th_user_id': self.env.user.id,
                        'th_notes': _('Thay thế file qua nạp hàng loạt'),
                    })
                    # Chỉ dọn dẹp nếu có các bản ghi trùng tên do lần trước tạo thừa
                    if len(same_name_docs) > 1:
                        same_name_docs[1:].sudo().unlink()
                else:
                    # Nếu không có tệp nào trùng tên:
                    # Nếu hợp đồng chỉ có duy nhất 1 tệp công ty thì thay thế tệp đó
                    company_docs = target_contract.th_document_ids.filtered(
                        lambda d: d.th_document_type in ('company_signed', 'company_raw')
                    )
                    if len(company_docs) == 1:
                        main_doc = company_docs[0]
                        main_doc.sudo().write({
                            'name': att.name,
                            'th_document_type': 'company_signed',
                            'th_file': att.datas,
                            'th_file_name': att.name,
                            'th_attachment_id': att.id,
                            'th_uploaded_by': 'company',
                            'th_upload_date': fields.Datetime.now(),
                            'th_user_id': self.env.user.id,
                            'th_notes': _('Thay thế file qua nạp hàng loạt'),
                        })
                    else:
                        # Nếu hợp đồng có nhiều tệp khác nhau thì thêm mới tệp này, giữ nguyên vẹn các tệp khác
                        self.env['th.collaborator.contract.document'].sudo().create({
                            'name': att.name,
                            'th_contract_id': target_contract.id,
                            'th_document_type': 'company_signed',
                            'th_file': att.datas,
                            'th_file_name': att.name,
                            'th_attachment_id': att.id,
                            'th_uploaded_by': 'company',
                            'th_upload_date': fields.Datetime.now(),
                            'th_user_id': self.env.user.id,
                            'th_notes': _('Thay thế file qua nạp hàng loạt'),
                        })

                target_contract.message_post(
                    body=_('Đã thay thế file hợp đồng công ty cũ [%s] bằng file mới [%s] qua nạp hàng loạt.') % (
                        ', '.join(old_file_names) if old_file_names else _('Chưa có'), att.name
                    )
                )
                updated_contracts |= target_contract

        self.th_attachment_ids.filtered(lambda a: a.res_model == self._name).unlink()

        result_lines = []
        if self.th_mode == 'add':
            result_lines.append(_('Tạo mới thành công %s hợp đồng.') % len(created_contracts))
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
