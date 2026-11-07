# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.fields import Command


class ThCollaboratorContractDocumentWizard(models.TransientModel):
    """Hỗ trợ nhân viên tải lên tệp hợp đồng cho một bản ghi hợp đồng cụ thể."""
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
        """Tự động kiểm tra tính hợp lệ của tên tệp tải lên so với hợp đồng mục tiêu."""
        if self.th_file_name:
            self.name = self.th_file_name
            phone, code, _custom = self.env['th.collaborator.contract'].th_extract_file_info(self.th_file_name)
            contract = self.th_contract_id
            if contract:
                contract_code = (contract.th_code or '').strip()
                Profile = self.env['th.collaborator.profile']
                contract_phone = Profile._normalize_phone(contract.th_phone or contract.th_collaborator_id.th_phone or '')

                if not phone or not code:
                    return {
                        'warning': {
                            'title': _('Tên tệp không đúng quy chuẩn!'),
                            'message': _('Tên tệp bắt buộc phải chứa cả Mã HĐ và SĐT CTV theo quy chuẩn [Mã HĐ]-[SĐT]-[Tên CTV] (Ví dụ: %s-%s-Nguyen Van A.pdf).') % (
                                contract_code or _('MãHĐ'), contract_phone or _('SĐT')
                            )
                        }
                    }
                if code.lower() != contract_code.lower() or phone != contract_phone:
                    return {
                        'warning': {
                            'title': _('Cảnh báo không khớp thông tin hợp đồng!'),
                            'message': _('Tệp vừa chọn có Mã HĐ "%s" và SĐT "%s", KHÔNG KHỚP với Hợp đồng đang mở (Mã HĐ: "%s" - SĐT: "%s" - CTV: %s). Vui lòng kiểm tra lại để tránh nạp nhầm!') % (
                                code, phone, contract_code, contract_phone, contract.th_collaborator_id.name
                            )
                        }
                    }

    @api.depends('th_file_name')
    def _compute_name(self):
        """Tự động đồng bộ tên hiển thị tài liệu theo tên tệp đính kèm được chọn."""
        for rec in self:
            rec.name = rec.th_file_name or False

    def action_confirm_upload(self):
        """Xử lý khởi tạo tài liệu hợp đồng và liên kết vào hợp đồng mục tiêu thông qua hàm base dùng chung."""
        self.ensure_one()
        if not self.th_document_type:
            raise UserError(_('Vui lòng chọn Phân loại bản ký.'))
        if not self.th_file:
            raise UserError(_('Vui lòng chọn tệp hợp đồng cần tải lên.'))
        if not self.th_file_name:
            raise UserError(_('Không xác định được tên tệp hợp đồng tải lên.'))

        contract = self.th_contract_id
        if contract.th_is_readonly or contract.state in ('close', 'cancel'):
            raise UserError(_('Hợp đồng "%s" đã ở trạng thái Hoàn tất hoặc Đã hủy, không thể tải lên thêm tệp.') % contract.name)

        # Chỉ cho phép nạp tệp hợp đồng công ty khi hợp đồng đang ở trạng thái Dự thảo hoặc Chờ pháp chế duyệt
        if self.th_document_type in ('company_raw', 'company_signed') and contract.state not in ('draft', 'legal_review'):
            state_label = dict(contract._fields['state'].selection).get(contract.state, contract.state)
            raise UserError(_('Hợp đồng "%s" đang ở trạng thái "%s". Chỉ được upload tệp hợp đồng khi hợp đồng ở trạng thái Dự thảo hoặc Chờ pháp chế duyệt!') % (
                contract.name, state_label
            ))

        # Bắt buộc tên tệp phải chứa đầy đủ cả Mã HĐ và SĐT CTV theo quy chuẩn [Mã HĐ]-[SĐT]-[Tên CTV]
        phone, code, _custom = self.env['th.collaborator.contract'].th_extract_file_info(self.th_file_name)
        contract_code = (contract.th_code or '').strip()
        Profile = self.env['th.collaborator.profile']
        contract_phone = Profile._normalize_phone(contract.th_phone or contract.th_collaborator_id.th_phone or '')

        if not phone or not code:
            raise UserError(_('Tên tệp tải lên bắt buộc phải chứa đầy đủ cả Mã HĐ và Số điện thoại CTV theo quy chuẩn [Mã HĐ]-[SĐT]-[Tên CTV] (Ví dụ: %s-%s-Nguyen Van A.pdf). Tên tệp hiện tại: "%s"') % (
                contract_code or _('MãHĐ'), contract_phone or _('SĐT'), self.th_file_name
            ))

        if code.lower() != contract_code.lower():
            raise UserError(_('Mã HĐ trong tên tệp ("%s") không khớp với Mã của hợp đồng đang mở ("%s" - HĐ: %s). Vui lòng kiểm tra lại để tránh nạp nhầm hợp đồng!') % (
                code, contract_code, contract.name
            ))

        if phone != contract_phone:
            raise UserError(_('Số điện thoại trong tên tệp ("%s") không khớp với Số điện thoại của CTV trong hợp đồng này ("%s" - CTV: %s). Vui lòng kiểm tra lại để tránh nạp nhầm CTV!') % (
                phone, contract_phone, contract.th_collaborator_id.name
            ))

        display_name = self.name or self.th_file_name or _('Tài liệu hợp đồng')

        # Sử dụng hàm base dùng chung trên contract để tạo document, gắn attachment và log Chatter
        contract.th_attach_document_file(
            (display_name, self.th_file),
            document_type=self.th_document_type,
            notes=self.th_notes
        )

        return {'type': 'ir.actions.act_window_close'}
