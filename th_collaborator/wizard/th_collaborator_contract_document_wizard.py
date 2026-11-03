# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.fields import Command


class ThCollaboratorContractDocumentWizard(models.TransientModel):
    """Wizard hỗ trợ nhân sự công ty tải lên tệp hợp đồng cho một bản ghi cụ thể."""
    _name = 'th.collaborator.contract.document.wizard'
    _description = 'Wizard tải lên tệp hợp đồng'

    th_contract_id = fields.Many2one(
        'th.collaborator.contract', string='Hợp đồng mục tiêu',
        required=True, ondelete='cascade')
    th_collaborator_id = fields.Many2one(
        'th.collaborator.profile', string='Cộng tác viên',
        related='th_contract_id.th_collaborator_id', readonly=True)

    th_document_type = fields.Selection([
        ('company_signed', 'Bản công ty đã ký số'),
        ('company_raw', 'Bản công ty chưa ký'),
        ('ctv_signed', 'Bản CTV gửi (Ký ảnh / Scan)'),
        ('ctv_digital_signed', 'Bản CTV gửi (Có chữ ký số)'),
        ('final_signed', 'Bản hoàn tất đủ 2 chữ ký'),
    ], string='Phân loại bản ký', required=True, default=False)

    th_file = fields.Binary(string='Tệp đính kèm (PDF, Ảnh)', required=True)
    th_file_name = fields.Char(string='Tên file đính kèm')
    name = fields.Char(
        string='Tên hiển thị tài liệu', compute='_compute_name', store=True, readonly=True)
    th_notes = fields.Text(string='Ghi chú')

    @api.onchange('th_file_name')
    def _onchange_th_file_name(self):
        """Tự động cập nhật tên hiển thị tài liệu ngay trên giao diện khi chọn tệp."""
        if self.th_file_name:
            self.name = self.th_file_name

    @api.depends('th_file_name')
    def _compute_name(self):
        """Tự động cập nhật tên hiển thị tài liệu theo tên tệp đính kèm được chọn."""
        for rec in self:
            rec.name = rec.th_file_name or False

    def action_confirm_upload(self):
        """Xử lý tạo tài liệu hợp đồng và đồng bộ vào hợp đồng mục tiêu."""
        self.ensure_one()
        if not self.th_document_type:
            raise UserError(_('Vui lòng chọn Phân loại bản ký.'))
        if not self.th_file:
            raise UserError(_('Vui lòng chọn tệp hợp đồng cần tải lên.'))
        if self.th_contract_id.th_is_readonly:
            raise UserError(_('Hợp đồng đã ở trạng thái Hoàn tất hoặc đã Hết hạn, không thể tải lên thêm tệp.'))
        if self.th_contract_id.state not in ('draft', 'open', 'sent', 'mail_error'):
            raise UserError(_('Chỉ được phép tải lên tệp hợp đồng khi đang ở trạng thái Dự thảo, Đang thực hiện, Gửi mail hoặc Gửi mail lỗi.'))

        display_name = self.name or self.th_file_name or _('Tài liệu hợp đồng')
        contract = self.th_contract_id

        # Tạo bản ghi tệp hợp đồng mới
        doc_vals = {
            'name': display_name,
            'th_contract_id': contract.id,
            'th_document_type': self.th_document_type,
            'th_file': self.th_file,
            'th_file_name': self.th_file_name,
            'th_uploaded_by': 'company',
            'th_upload_date': fields.Datetime.now(),
            'th_user_id': self.env.user.id,
            'th_notes': self.th_notes,
        }
        new_doc = self.env['th.collaborator.contract.document'].create(doc_vals)

        # Đồng bộ ngược vào các trường attachment truyền thống để giữ tính tương thích
        if new_doc.th_attachment_id:
            if self.th_document_type in ('company_raw', 'company_signed'):
                contract.write({
                    'th_company_attachment_ids': [Command.link(new_doc.th_attachment_id.id)],
                })
            elif self.th_document_type == 'final_signed':
                contract.write({
                    'th_final_attachment_id': new_doc.th_attachment_id.id,
                })

        # Ghi log lịch sử thao tác vào chatter hợp đồng
        doc_type_label = dict(self._fields['th_document_type'].selection).get(self.th_document_type)
        contract.message_post(
            body=_('Nhân sự công ty đã tải lên tệp "%s" (Phân loại: %s).') % (display_name, doc_type_label)
        )

        return {'type': 'ir.actions.act_window_close'}
