# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ThCollaboratorContractDocument(models.Model):
    """Quản lý các tệp tài liệu hợp đồng CTV theo từng giai đoạn ký."""
    _name = 'th.collaborator.contract.document'
    _description = 'Tệp tài liệu hợp đồng CTV'
    _order = 'th_upload_date desc, id desc'

    name = fields.Char(string='Tên tệp', required=True)
    th_contract_id = fields.Many2one(
        'th.collaborator.contract', string='Hợp đồng',
        ondelete='cascade', index=True, required=True)

    th_document_type = fields.Selection([
        ('company_raw', 'Bản công ty chưa ký'),
        ('company_signed', 'Bản công ty đã ký số'),
        ('ctv_signed', 'Bản CTV gửi (Ký ảnh / Scan)'),
        ('ctv_digital_signed', 'Bản CTV gửi (Có chữ ký số)'),
        ('final_signed', 'Bản hoàn tất đủ 2 chữ ký'),
    ], string='Phân loại bản ký', required=True, default='company_signed')

    th_file = fields.Binary(string='Tệp đính kèm', attachment=True, required=True)
    th_file_name = fields.Char(string='Tên file đính kèm')

    th_attachment_id = fields.Many2one(
        'ir.attachment', string='Tệp hệ thống (ir.attachment)', ondelete='set null')

    th_uploaded_by = fields.Selection([
        ('company', 'Công ty'),
        ('ctv', 'Cộng tác viên'),
    ], string='Nguồn tải lên', default='company', required=True)

    th_upload_date = fields.Datetime(
        string='Ngày tải lên', default=fields.Datetime.now, readonly=True)
    th_user_id = fields.Many2one(
        'res.users', string='Người tải lên', default=lambda self: self.env.user, readonly=True)
    th_notes = fields.Char(string='Ghi chú')

    @api.model_create_multi
    def create(self, vals_list):
        """Tạo bản ghi tài liệu hợp đồng và tự động sinh bản ghi ir.attachment tương ứng."""
        for vals in vals_list:
            if not vals.get('name') and vals.get('th_file_name'):
                vals['name'] = vals['th_file_name']
        records = super().create(vals_list)
        for rec in records:
            if not rec.th_attachment_id and rec.th_file:
                att = self.env['ir.attachment'].sudo().create({
                    'name': rec.name or rec.th_file_name or 'contract_document.pdf',
                    'datas': rec.th_file,
                    'res_model': 'th.collaborator.contract',
                    'res_id': rec.th_contract_id.id,
                })
                rec.th_attachment_id = att.id
        return records

    def write(self, vals):
        """Cập nhật thông tin tài liệu và đồng bộ tên, dữ liệu sang ir.attachment."""
        res = super().write(vals)
        if any(f in vals for f in ('name', 'th_file', 'th_file_name')):
            for rec in self:
                if rec.th_attachment_id:
                    att_vals = {}
                    if 'th_file' in vals:
                        att_vals['datas'] = rec.th_file
                    if 'name' in vals or 'th_file_name' in vals:
                        att_vals['name'] = rec.name or rec.th_file_name or 'contract_document.pdf'
                    if att_vals:
                        rec.th_attachment_id.sudo().write(att_vals)
        return res

    def action_download_file(self):
        """Tải trực tiếp tệp tài liệu này về máy người dùng."""
        self.ensure_one()
        if self.th_attachment_id:
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{self.th_attachment_id.id}?download=true',
                'target': 'self',
            }
        elif self.th_file:
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content?model=th.collaborator.contract.document&id={self.id}&field=th_file&filename={self.name or "document"}&download=true',
                'target': 'self',
            }
        raise UserError(_('Không tìm thấy tệp đính kèm để tải về.'))
