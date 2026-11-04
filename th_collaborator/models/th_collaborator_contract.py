# -*- coding: utf-8 -*-
import base64
import logging
import os
import re
import secrets

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command

_logger = logging.getLogger(__name__)

TH_CONTRACT_ALLOWED_EXTENSIONS = ('.pdf', '.jpg', '.jpeg', '.png')


class ThCollaboratorContract(models.Model):
    """Quản lý hợp đồng và tài liệu đính kèm của Cộng tác viên."""
    _name = 'th.collaborator.contract'
    _description = 'Hợp đồng cộng tác viên'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    @api.model
    def _default_user_id(self):
        """Mặc định người phụ trách hợp đồng là người dùng hiện tại."""
        return self.env.user

    def th_default_access_token(self):
        """Sinh token ngẫu nhiên cho link upload công khai của Hợp đồng."""
        return secrets.token_urlsafe(32)

    name = fields.Char(string='Tên hợp đồng', required=True, tracking=True)
    th_code = fields.Char(string='Mã hợp đồng', required=True, index=True, copy=False, tracking=True)
    th_access_token = fields.Char(
        string='Token upload', copy=False, default=lambda self: self.th_default_access_token())
    th_upload_url = fields.Char(
        string='Link upload hợp đồng', compute='_compute_upload_url')
    th_collaborator_id = fields.Many2one(
        'th.collaborator.profile', string='Cộng tác viên',
        required=True, index=True, ondelete='restrict', tracking=True)
    th_collaborator_sequence = fields.Integer(
        string='Số thứ tự CTV', related='th_collaborator_id.th_sequence',
        store=True, readonly=True, index=True)
    user_id = fields.Many2one(
        'res.users', string='Người phụ trách', required=True, tracking=True,
        default=lambda self: self._default_user_id())
    th_phone = fields.Char(
        string='Số điện thoại', related='th_collaborator_id.th_phone', store=True, readonly=True)
    th_email = fields.Char(
        string='Email', related='th_collaborator_id.th_email', store=True, readonly=True)
    th_batch_date = fields.Date(
        string='Ngày đẩy hợp đồng', required=True, default=fields.Date.context_today, index=True, tracking=True)
    th_contract_type_ids = fields.Many2many(
        'th.collaborator.contract.type', 'th_collaborator_contract_type_rel',
        'th_contract_id', 'th_contract_type_id', string='Loại hợp đồng', required=True)
    date_start = fields.Date(
        string='Ngày bắt đầu', required=True, default=fields.Date.context_today, tracking=True)
    date_end = fields.Date(
        string='Ngày kết thúc', required=True, tracking=True)
    th_is_expired = fields.Boolean(
        string='Đã hết hạn', compute='_compute_expiration_status', store=True, index=True, tracking=True)
    th_expiration_status = fields.Selection([
        ('valid', 'Đang chạy'),
        ('expired', 'Đã hết hạn'),
    ], string='Thời hạn hợp đồng', compute='_compute_expiration_status', store=True, index=True)
    state = fields.Selection([
        ('draft', 'Dự thảo'),
        ('open', 'Đang thực hiện'),
        ('sent', 'Gửi mail'),
        ('submitted', 'Chờ duyệt'),
        ('pending_sign', 'Chờ ký'),
        ('valid', 'Đã duyệt hợp lệ'),
        ('close', 'Hoàn tất'),
        ('mail_error', 'Gửi mail lỗi'),
        ('cancel', 'Đã hủy'),
    ], string='Trạng thái', default='draft', tracking=True)

    th_contract_flow = fields.Selection([
        ('signed_template', 'Mẫu đã ký số'),
        ('raw_template', 'Mẫu chưa ký số'),
    ], string='Luồng ký hợp đồng', compute='_compute_contract_flow', store=True, readonly=False, copy=False, tracking=True)

    th_is_signed = fields.Boolean(
        string='Đã ký/nộp', compute='_compute_is_signed', store=True, tracking=True)
    th_mail_error = fields.Text(string='Lỗi gửi mail', copy=False, tracking=True)

    th_mail_sent_count = fields.Integer(string='Đã gửi', compute='_compute_mail_statistics')
    th_mail_delivered_count = fields.Integer(string='Đã nhận (SL)', compute='_compute_mail_statistics')
    th_mail_failed_count = fields.Integer(string='Lỗi (SL)', compute='_compute_mail_statistics')
    th_mail_delivered_ratio = fields.Integer(string='Đã nhận', compute='_compute_mail_statistics')
    th_mail_failed_ratio = fields.Integer(string='Lỗi', compute='_compute_mail_statistics')

    th_document_ids = fields.One2many(
        'th.collaborator.contract.document', 'th_contract_id',
        string='Danh sách tệp hợp đồng')
    th_company_attachment_ids = fields.Many2many(
        'ir.attachment', 'th_collaborator_contract_company_attachment_rel',
        'th_contract_id', 'th_attachment_id', string='Hợp đồng công ty')
    th_self_attachment_ids = fields.Many2many(
        'ir.attachment', 'th_collaborator_contract_self_attachment_rel',
        'th_contract_id', 'th_attachment_id', string='Hợp đồng CTV tải lên')
    th_final_attachment_id = fields.Many2one(
        'ir.attachment', string='Hợp đồng hoàn tất đủ 2 chữ ký', copy=False)
    th_mail_sent_date = fields.Datetime(string='Ngày gửi mail', copy=False)
    th_last_upload_date = fields.Datetime(string='Ngày CTV tải lên', copy=False)

    th_company_file_name = fields.Char(
        string='HĐ công ty cung cấp', compute='_compute_contract_file_info', store=True)
    th_company_signed_file_name = fields.Char(
        string='HĐ công ty có chữ ký số', compute='_compute_contract_file_info', store=True)
    th_company_raw_file_name = fields.Char(
        string='HĐ công ty chưa ký số', compute='_compute_contract_file_info', store=True)
    th_self_file_name = fields.Char(
        string='HĐ CTV nộp', compute='_compute_contract_file_info', store=True)
    th_final_file_name = fields.Char(
        string='HĐ đủ 2 chữ ký', compute='_compute_contract_file_info', store=True)

    th_is_readonly = fields.Boolean(
        string='Khóa chỉnh sửa', compute='_compute_is_readonly')

    _sql_constraints = [
        ('th_code_uniq', 'unique(th_code)', 'Mã hợp đồng đã tồn tại trong hệ thống. Vui lòng chọn mã khác.'),
        ('th_contract_access_token_uniq', 'unique(th_access_token)', 'Token upload của hợp đồng bị trùng.'),
    ]

    @api.depends('state', 'th_is_expired')
    def _compute_is_readonly(self):
        """Khóa chỉnh sửa khi hợp đồng ở trạng thái Hoàn tất, Đã hủy hoặc đã Hết hạn."""
        for rec in self:
            rec.th_is_readonly = bool(rec.state in ('close', 'cancel') or rec.th_is_expired)

    def _add_sql_constraints(self):
        """Khởi tạo token upload ngẫu nhiên duy nhất cho các bản ghi cũ trước khi gán ràng buộc unique."""
        self.env.cr.execute("""
            SELECT id FROM th_collaborator_contract 
            WHERE th_access_token IS NULL OR th_access_token IN (
                SELECT th_access_token FROM th_collaborator_contract GROUP BY th_access_token HAVING count(*) > 1
            )
        """)
        dup_ids = [r[0] for r in self.env.cr.fetchall()]
        for rec_id in dup_ids:
            new_token = secrets.token_urlsafe(32)
            self.env.cr.execute(
                "UPDATE th_collaborator_contract SET th_access_token = %s WHERE id = %s",
                (new_token, rec_id)
            )
        super()._add_sql_constraints()

    @api.constrains('date_start', 'date_end')
    def _check_contract_dates(self):
        """Kiểm tra ngày kết thúc hợp đồng không được nhỏ hơn ngày bắt đầu."""
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_end < rec.date_start:
                raise ValidationError(
                    _('Ngày kết thúc hợp đồng (%s) không được nhỏ hơn ngày bắt đầu (%s).')
                    % (rec.date_end, rec.date_start)
                )

    @api.depends('date_start', 'date_end')
    def _compute_expiration_status(self):
        """Xác định trạng thái hết hạn hiệu lực của hợp đồng dựa vào ngày kết thúc."""
        today = fields.Date.context_today(self)
        for rec in self:
            is_expired = bool(rec.date_end and rec.date_end < today)
            rec.th_is_expired = is_expired
            rec.th_expiration_status = 'expired' if is_expired else 'valid'

    @api.depends('th_self_attachment_ids', 'th_final_attachment_id', 'th_document_ids.th_document_type', 'state')
    def _compute_is_signed(self):
        """Xác định trạng thái đã nộp hoặc hoàn tất ký kết của hợp đồng."""
        for rec in self:
            has_signed_doc = bool(rec.th_document_ids.filtered(lambda d: d.th_document_type in ('ctv_signed', 'ctv_digital_signed', 'final_signed')))
            rec.th_is_signed = bool(
                rec.th_self_attachment_ids or rec.th_final_attachment_id or has_signed_doc or rec.state in ('submitted', 'pending_sign', 'valid', 'close')
            )

    @api.depends('state', 'th_document_ids.th_document_type')
    def _compute_contract_flow(self):
        """Tự động xác định luồng ký hợp đồng theo trạng thái hoặc tài liệu nộp."""
        for rec in self:
            if rec.state == 'pending_sign':
                rec.th_contract_flow = 'raw_template'
            elif rec.state == 'submitted':
                rec.th_contract_flow = 'signed_template'
            elif not rec.th_contract_flow:
                has_raw = any(d.th_document_type == 'ctv_signed' for d in rec.th_document_ids)
                has_signed = any(d.th_document_type == 'ctv_digital_signed' for d in rec.th_document_ids)
                if has_raw:
                    rec.th_contract_flow = 'raw_template'
                elif has_signed:
                    rec.th_contract_flow = 'signed_template'
                else:
                    rec.th_contract_flow = False

    @api.depends('th_company_attachment_ids', 'th_self_attachment_ids', 'th_final_attachment_id', 'th_document_ids', 'th_document_ids.th_document_type', 'th_document_ids.name')
    def _compute_contract_file_info(self):
        """Tính toán tên hiển thị phân biệt rõ 3 loại tệp hợp đồng trên tree view."""
        for rec in self:
            company_docs = rec.th_document_ids.filtered(lambda d: d.th_document_type in ('company_raw', 'company_signed'))
            company_files = company_docs.mapped('name') or rec.th_company_attachment_ids.mapped('name')
            if company_files:
                rec.th_company_file_name = company_files[0] if len(company_files) == 1 else f"{company_files[0]} (+{len(company_files) - 1})"
            else:
                rec.th_company_file_name = _('Chưa có file')

            signed_docs = rec.th_document_ids.filtered(lambda d: d.th_document_type == 'company_signed')
            signed_files = signed_docs.mapped('name') or (rec.th_company_attachment_ids.mapped('name') if not company_docs else [])
            rec.th_company_signed_file_name = signed_files[0] if signed_files else _('Chưa có')

            raw_docs = rec.th_document_ids.filtered(lambda d: d.th_document_type == 'company_raw')
            raw_files = raw_docs.mapped('name')
            rec.th_company_raw_file_name = raw_files[0] if raw_files else _('Chưa có')

            self_docs = rec.th_document_ids.filtered(lambda d: d.th_document_type in ('ctv_signed', 'ctv_digital_signed'))
            self_files = self_docs.mapped('name') or rec.th_self_attachment_ids.mapped('name')
            if self_files:
                rec.th_self_file_name = self_files[0] if len(self_files) == 1 else f"{self_files[0]} (+{len(self_files) - 1})"
            else:
                rec.th_self_file_name = _('Chưa nộp')

            final_doc = rec.th_document_ids.filtered(lambda d: d.th_document_type == 'final_signed')[:1]
            if final_doc:
                rec.th_final_file_name = final_doc.name or _('Đã có bản hoàn tất')
            elif rec.th_final_attachment_id:
                rec.th_final_file_name = rec.th_final_attachment_id.name or _('Đã có bản hoàn tất')
            else:
                rec.th_final_file_name = _('Chưa có')

    @api.onchange('th_collaborator_id')
    def _onchange_th_collaborator_id(self):
        """Tự động đồng bộ người phụ trách từ hồ sơ CTV khi được chọn."""
        if self.th_collaborator_id and self.th_collaborator_id.user_id:
            self.user_id = self.th_collaborator_id.user_id

    @api.model_create_multi
    def create(self, vals_list):
        """Tạo hợp đồng mới, tự động khởi tạo token upload và gắn file đính kèm."""
        for vals in vals_list:
            if not vals.get('th_access_token'):
                vals['th_access_token'] = self.th_default_access_token()
        records = super().create(vals_list)
        records._link_contract_attachments()
        return records

    def write(self, vals):
        """Cập nhật hợp đồng và kiểm soát các ràng buộc điều kiện khi chuyển trạng thái."""
        business_fields = {
            'name', 'th_code', 'th_collaborator_id', 'user_id',
            'th_batch_date', 'th_contract_type_ids', 'date_start', 'date_end',
        }
        if any(f in vals for f in business_fields):
            for rec in self:
                if rec.th_is_readonly:
                    raise UserError(
                        _('Hợp đồng "%s" đã ở trạng thái Hoàn tất hoặc đã Hết hạn, thông tin đã bị khóa không thể chỉnh sửa.')
                        % rec.name
                    )

        new_state = vals.get('state')
        if new_state:
            for rec in self:
                current_state = rec.state
                if new_state == current_state:
                    continue

                if current_state == 'close':
                    raise UserError(
                        _('Hợp đồng "%s" đã ở trạng thái Hoàn tất, không thể thay đổi trạng thái.')
                        % rec.name
                    )
                if rec.th_is_expired and new_state != current_state:
                    raise UserError(
                        _('Hợp đồng "%s" đã hết hạn hiệu lực, không thể chuyển đổi trạng thái.')
                        % rec.name
                    )

                if new_state == 'open':
                    has_company_file = bool(
                        rec.th_company_attachment_ids or
                        rec.th_document_ids.filtered(lambda d: d.th_document_type in ('company_raw', 'company_signed'))
                    )
                    if not has_company_file:
                        raise UserError(
                            _('Không thể chuyển sang trạng thái "Đang thực hiện": Hợp đồng "%s" chưa có tệp hợp đồng do công ty tải lên.')
                            % rec.name
                        )

                elif new_state == 'sent':
                    has_company_file = bool(
                        rec.th_company_attachment_ids or
                        rec.th_document_ids.filtered(lambda d: d.th_document_type in ('company_raw', 'company_signed'))
                    )
                    if not has_company_file:
                        raise UserError(
                            _('Không thể chuyển sang trạng thái "Gửi mail": Hợp đồng "%s" chưa có tệp hợp đồng do công ty tải lên.')
                            % rec.name
                        )
                    if not rec.th_email:
                        raise UserError(
                            _('Không thể chuyển sang trạng thái "Gửi mail": CTV chưa có địa chỉ email.')
                        )
                    if not rec.user_id.email:
                        raise UserError(
                            _('Không thể chuyển sang trạng thái "Gửi mail": Người phụ trách chưa có địa chỉ email.')
                        )

                elif new_state == 'submitted':
                    if current_state not in ('sent', 'submitted'):
                        raise UserError(
                            _('Hợp đồng "%s" phải ở trạng thái "Gửi mail" trước khi chuyển sang "Chờ duyệt".')
                            % rec.name
                        )
                    has_ctv_file = bool(
                        rec.th_self_attachment_ids or
                        rec.th_document_ids.filtered(lambda d: d.th_document_type in ('ctv_signed', 'ctv_digital_signed'))
                    )
                    if not has_ctv_file:
                        raise UserError(
                            _('Không thể chuyển sang trạng thái "Chờ duyệt": Hợp đồng "%s" chưa có tệp bản ký do CTV nộp.')
                            % rec.name
                        )

                elif new_state == 'pending_sign':
                    if current_state not in ('sent', 'submitted', 'pending_sign'):
                        raise UserError(
                            _('Hợp đồng "%s" phải ở trạng thái "Gửi mail" hoặc "Chờ duyệt" trước khi chuyển sang "Chờ ký".')
                            % rec.name
                        )
                    has_ctv_file = bool(
                        rec.th_self_attachment_ids or
                        rec.th_document_ids.filtered(lambda d: d.th_document_type in ('ctv_signed', 'ctv_digital_signed'))
                    )
                    if not has_ctv_file:
                        raise UserError(
                            _('Không thể chuyển sang trạng thái "Chờ ký": Hợp đồng "%s" chưa có tệp bản ký do CTV nộp.')
                            % rec.name
                        )

                elif new_state == 'valid':
                    if current_state not in ('submitted', 'pending_sign', 'valid'):
                        raise UserError(
                            _('Hợp đồng "%s" phải ở trạng thái "Chờ duyệt" hoặc "Chờ ký" trước khi chuyển sang "Đã duyệt hợp lệ".')
                            % rec.name
                        )
                    has_ctv_file = bool(
                        vals.get('th_self_attachment_ids') or
                        rec.th_self_attachment_ids or
                        rec.th_document_ids.filtered(lambda d: d.th_document_type in ('ctv_signed', 'ctv_digital_signed'))
                    )
                    if not has_ctv_file:
                        raise UserError(
                            _('Không thể chuyển sang trạng thái "Đã duyệt hợp lệ": Hợp đồng "%s" chưa có tệp do CTV nộp.')
                            % rec.name
                        )
                    has_final_file = bool(
                        vals.get('th_final_attachment_id') or
                        rec.th_final_attachment_id or
                        rec.th_document_ids.filtered(lambda d: d.th_document_type == 'final_signed')
                    )
                    is_pre_signed_completed = bool(
                        rec.th_contract_flow == 'signed_template' and
                        rec.th_document_ids.filtered(lambda d: d.th_document_type == 'company_signed') and
                        rec.th_document_ids.filtered(lambda d: d.th_document_type in ('ctv_signed', 'ctv_digital_signed'))
                    )
                    if not has_final_file and not is_pre_signed_completed:
                        raise UserError(
                            _('Không thể chuyển sang trạng thái "Đã duyệt hợp lệ": Hợp đồng "%s" chưa có bản hợp đồng đầy đủ cả 2 chữ ký. Vui lòng ký số và tải lên tệp hợp đồng hoàn tất đủ 2 chữ ký trước khi duyệt.')
                            % rec.name
                        )

                elif new_state == 'close':
                    has_final_file = bool(
                        vals.get('th_final_attachment_id') or
                        rec.th_final_attachment_id or
                        rec.th_document_ids.filtered(lambda d: d.th_document_type == 'final_signed')
                    )
                    if not has_final_file:
                        raise UserError(
                            _('Không thể chuyển sang trạng thái "Hoàn tất": Hợp đồng "%s" chưa có bản hợp đồng đánh dấu đủ 2 chữ ký.')
                            % rec.name
                        )
                    if not rec.th_final_attachment_id and not vals.get('th_final_attachment_id'):
                        final_doc = rec.th_document_ids.filtered(lambda d: d.th_document_type == 'final_signed')[:1]
                        if final_doc and final_doc.th_attachment_id:
                            vals['th_final_attachment_id'] = final_doc.th_attachment_id.id

        old_states = {rec.id: rec.state for rec in self} if 'state' in vals else {}
        res = super().write(vals)

        if vals.get('state') == 'valid':
            for rec in self:
                if old_states.get(rec.id) != 'valid':
                    rec.message_post(
                        body=_('Nhân sự %s đã kiểm tra và chuyển trạng thái hợp đồng sang Đã duyệt hợp lệ.')
                        % self.env.user.name
                    )

        if vals.get('state') == 'sent':
            for rec in self:
                if old_states.get(rec.id) != 'sent':
                    if not rec.th_mail_sent_date:
                        rec.message_post(
                            body=_('Nhân sự %s đã xác nhận chuyển trạng thái sang "Gửi mail" thủ công (Hợp đồng chưa phát hành email qua hệ thống).')
                            % self.env.user.name
                        )
                    if rec.th_mail_error:
                        rec.th_mail_error = False

        if 'th_company_attachment_ids' in vals or 'th_self_attachment_ids' in vals or 'th_final_attachment_id' in vals:
            self._link_contract_attachments()
        return res

    def _link_contract_attachments(self):
        """Gắn liên kết res_model và res_id vào tệp đính kèm để quản lý phân quyền."""
        for rec in self:
            all_attachments = rec.th_company_attachment_ids | rec.th_self_attachment_ids
            if rec.th_final_attachment_id:
                all_attachments |= rec.th_final_attachment_id
            attachments = all_attachments.filtered(
                lambda att: att.res_model != rec._name or att.res_id != rec.id)
            if attachments:
                attachments.write({'res_model': rec._name, 'res_id': rec.id})

    def action_set_draft(self):
        """Chuyển hợp đồng về trạng thái dự thảo."""
        self.write({'state': 'draft'})

    def action_set_sent(self):
        """Chuyển hợp đồng sang trạng thái Gửi mail thủ công."""
        self.write({'state': 'sent'})

    def action_set_close(self):
        """Chuyển hợp đồng sang trạng thái hoàn tất khi đã có đủ bản 2 chữ ký."""
        for rec in self:
            has_final_file = bool(
                rec.th_final_attachment_id or
                rec.th_document_ids.filtered(lambda d: d.th_document_type == 'final_signed')
            )
            if not has_final_file:
                raise UserError(
                    _('Không thể hoàn tất hợp đồng "%s": Chưa có bản hợp đồng đánh dấu đủ 2 chữ ký.')
                    % rec.name
                )
            if not rec.th_final_attachment_id:
                final_doc = rec.th_document_ids.filtered(lambda d: d.th_document_type == 'final_signed')[:1]
                if final_doc and final_doc.th_attachment_id:
                    rec.th_final_attachment_id = final_doc.th_attachment_id.id
        self.write({'state': 'close'})

    def action_set_cancel(self):
        """Hủy hợp đồng."""
        self.write({'state': 'cancel'})

    def _compute_mail_statistics(self):
        """Tính toán thống kê số lượng và tỷ lệ email đã gửi cho hợp đồng này."""
        MailSent = self.env['th.collaborator.mail.sent']
        for contract in self:
            mails = MailSent.search([('th_contract_id', '=', contract.id)])
            sent_count = len(mails.filtered(lambda m: m.state in ('sent', 'outgoing', 'exception')))
            delivered_count = len(mails.filtered(lambda m: m.state == 'sent'))
            failed_count = len(mails.filtered(lambda m: m.state == 'exception'))

            contract.th_mail_sent_count = sent_count
            contract.th_mail_delivered_count = delivered_count
            contract.th_mail_failed_count = failed_count

            if sent_count > 0:
                contract.th_mail_delivered_ratio = int(100 * delivered_count / sent_count)
                contract.th_mail_failed_ratio = int(100 * failed_count / sent_count)
            else:
                contract.th_mail_delivered_ratio = 0
                contract.th_mail_failed_ratio = 0

    def th_action_view_sent_mails(self):
        """Mở danh sách toàn bộ email đã phát hành cho hợp đồng này."""
        self.ensure_one()
        return {
            'name': _('Email đã gửi - Hợp đồng %s') % (self.th_code or self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'th.collaborator.mail.sent',
            'view_mode': 'tree,form',
            'domain': [('th_contract_id', '=', self.id)],
            'context': {'create': False, 'edit': False, 'delete': False},
        }

    def th_action_view_delivered_mails(self):
        """Mở danh sách email đã gửi thành công (sent) cho hợp đồng này."""
        self.ensure_one()
        return {
            'name': _('Email đã nhận - Hợp đồng %s') % (self.th_code or self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'th.collaborator.mail.sent',
            'view_mode': 'tree,form',
            'domain': [('th_contract_id', '=', self.id), ('state', '=', 'sent')],
            'context': {'create': False, 'edit': False, 'delete': False},
        }

    def th_action_view_failed_mails(self):
        """Mở danh sách email gửi thất bại của hợp đồng này."""
        self.ensure_one()
        return {
            'name': _('Email lỗi - Hợp đồng %s') % (self.th_code or self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'th.collaborator.mail.sent',
            'view_mode': 'tree,form',
            'domain': [('th_contract_id', '=', self.id), ('state', '=', 'exception')],
            'context': {'create': False, 'edit': False, 'delete': False},
        }

    @api.depends('th_access_token')
    def _compute_upload_url(self):
        """Dựng đường dẫn trang web công khai để CTV tải lên hợp đồng."""
        for rec in self:
            rec.th_upload_url = rec.th_access_token and '%s/th_collaborator/upload/%s' % (
                rec.get_base_url(), rec.th_access_token) or False

    def th_action_regenerate_token(self):
        """Tạo mới token upload và làm mất hiệu lực đường dẫn upload cũ."""
        self.ensure_one()
        self.th_access_token = self.th_default_access_token()
        self.message_post(body=_('Đã tạo lại link upload cho hợp đồng này, link cũ không còn hiệu lực.'))
        return True

    def action_open_contract_form(self):
        """Mở form xem chi tiết và theo dõi lịch sử thao tác của hợp đồng."""
        self.ensure_one()
        return {
            'name': _('Hợp đồng %s') % (self.th_code or self.name),
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _build_self_contract_file_names(self, original_names):
        """Quy chuẩn hóa tên tệp CTV tải lên theo cú pháp: SĐT_MãHĐ_TênHĐ.đuôi_tệp."""
        self.ensure_one()
        phone = self.th_collaborator_id.th_phone_normalized or ''
        code = self.th_code or ''
        name = self.name or ''
        base_name = re.sub(r'[\\/:*?"<>|]+', '_', f'{phone}_{code}_{name}').strip()
        file_names = []
        for index, original_name in enumerate(original_names, start=1):
            extension = os.path.splitext(original_name or '')[1].lower()
            suffix = f'_{index}' if len(original_names) > 1 else ''
            file_names.append(f'{base_name}{suffix}{extension}')
        return file_names

    def _add_self_contracts(self, files, upload_type='signed_template'):
        """Lưu trữ tệp hợp đồng do CTV gửi lên qua cổng portal trực tuyến."""
        self.ensure_one()
        Attachment = self.env['ir.attachment']
        DocModel = self.env['th.collaborator.contract.document']
        existing_attachments = {att.name: att for att in self.th_self_attachment_ids}
        file_names = self._build_self_contract_file_names([file_name for file_name, dummy in files])

        result_attachments = self.env['ir.attachment']
        commands = []
        is_raw = bool(upload_type == 'raw_template')
        doc_type = 'ctv_signed' if is_raw else 'ctv_digital_signed'
        notes = _('Bản ký từ mẫu chưa có chữ ký số công ty') if is_raw else _('Bản ký từ mẫu đã có chữ ký số công ty')

        for file_name, (dummy, content) in zip(file_names, files):
            raw_b64 = base64.b64encode(content) if isinstance(content, bytes) else content
            if file_name in existing_attachments:
                att = existing_attachments[file_name]
                att.write({'raw': content})
                result_attachments |= att
            else:
                att = Attachment.create({
                    'name': file_name,
                    'raw': content,
                    'res_model': self._name,
                    'res_id': self.id,
                })
                commands.append(Command.link(att.id))
                result_attachments |= att

            existing_doc = self.th_document_ids.filtered(
                lambda d: d.name == file_name and d.th_uploaded_by == 'ctv')[:1]
            if existing_doc:
                existing_doc.write({
                    'th_file': raw_b64,
                    'th_document_type': doc_type,
                    'th_upload_date': fields.Datetime.now(),
                    'th_attachment_id': att.id,
                    'th_notes': notes,
                })
            else:
                DocModel.create({
                    'name': file_name,
                    'th_contract_id': self.id,
                    'th_document_type': doc_type,
                    'th_file': raw_b64,
                    'th_file_name': file_name,
                    'th_attachment_id': att.id,
                    'th_uploaded_by': 'ctv',
                    'th_upload_date': fields.Datetime.now(),
                    'th_notes': notes,
                })

        new_state = 'pending_sign' if is_raw else 'submitted'
        vals = {
            'th_last_upload_date': fields.Datetime.now(),
            'state': new_state,
            'th_contract_flow': upload_type,
        }
        if commands:
            vals['th_self_attachment_ids'] = commands
        self.write(vals)

        if is_raw:
            msg = _('CTV đã nộp %s file hợp đồng từ mẫu chưa có chữ ký số công ty: %s. Trạng thái chuyển sang Chờ ký.') % (
                len(result_attachments), ', '.join(result_attachments.mapped('name')))
        else:
            msg = _('CTV đã nộp %s file hợp đồng từ mẫu đã có chữ ký số công ty: %s. Trạng thái chuyển sang Chờ duyệt.') % (
                len(result_attachments), ', '.join(result_attachments.mapped('name')))
        self.message_post(body=msg, subtype_xmlid='mail.mt_comment')
        _logger.info('Collaborator contract %s: uploaded %s file(s) with state %s', self.id, len(result_attachments), new_state)
        return result_attachments

    @api.model
    def _get_contract_mail_template(self):
        """Lấy mẫu email phát hành hợp đồng theo cấu hình hệ thống hoặc mẫu mặc định."""
        template_id = self.env['ir.config_parameter'].sudo().get_param('th_collaborator.contract_mail_template_id')
        if template_id:
            template = self.env['mail.template'].browse(int(template_id)).exists()
            if template:
                return template
        template = self.env.ref(
            'th_collaborator.th_collaborator_profile_send_mail_template', raise_if_not_found=False)
        if not template:
            template = self.env.ref(
                'th_collaborator.th_collaborator_profile_upload_mail_template', raise_if_not_found=False)
        return template

    @api.model
    def _get_contract_reminder_mail_template(self):
        """Lấy mẫu email nhắc nhở nộp hợp đồng theo cấu hình hệ thống hoặc mẫu mặc định."""
        template_id = self.env['ir.config_parameter'].sudo().get_param('th_collaborator.contract_reminder_mail_template_id')
        if template_id:
            template = self.env['mail.template'].browse(int(template_id)).exists()
            if template:
                return template
        return self.env.ref(
            'th_collaborator.th_collaborator_contract_reminder_mail_template', raise_if_not_found=False)

    def _get_company_mail_attachments(self):
        """Lấy danh sách tệp đính kèm do công ty cung cấp để gửi mail cho CTV."""
        self.ensure_one()
        target_docs = self.th_document_ids.filtered(
            lambda d: d.th_document_type in ('company_raw', 'company_signed')
        )
        attachments = target_docs.mapped('th_attachment_id')
        if not attachments and self.th_company_attachment_ids:
            attachments = self.th_company_attachment_ids
        return attachments

    def th_action_send_contract_mail(self):
        """Phát hành email mời ký hợp đồng đến địa chỉ email của CTV."""
        self.ensure_one()
        error_msg = False
        if not self.th_email:
            error_msg = _('CTV chưa có địa chỉ email để gửi hợp đồng.')
        elif not self.user_id.email:
            error_msg = _('Người phụ trách chưa có địa chỉ email để làm hòm thư phát hành.')

        company_attachments = self._get_company_mail_attachments()
        if not company_attachments and not error_msg:
            error_msg = _('Hợp đồng chưa có tài liệu có trạng thái bản công ty ký số hoặc bản công ty chưa ký số để gửi.')

        default_template = self._get_contract_mail_template()
        if not default_template and not error_msg:
            error_msg = _('Không tìm thấy mẫu email gửi hợp đồng.')

        if error_msg:
            self.write({
                'state': 'mail_error',
                'th_mail_error': error_msg,
            })
            self.message_post(body=_('Gửi email hợp đồng thất bại: %s') % error_msg)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Gửi email hợp đồng thất bại'),
                    'message': error_msg,
                    'type': 'danger',
                    'sticky': True,
                    'next': {'type': 'ir.actions.client', 'tag': 'reload'},
                }
            }

        try:
            mail_id = default_template.send_mail(self.id, force_send=True, email_values={
                'email_from': self.user_id.email_formatted,
                'reply_to': self.user_id.email_formatted,
                'attachment_ids': company_attachments.ids,
            })
            mail = self.env['mail.mail'].browse(mail_id)
            if mail.exists() and mail.state == 'exception':
                err_detail = mail.failure_reason or _('Máy chủ gửi mail (SMTP) báo lỗi khi gửi thư.')
                self.write({
                    'state': 'mail_error',
                    'th_mail_error': err_detail,
                })
                self.message_post(body=_('Gửi email hợp đồng thất bại: %s') % err_detail)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Gửi email hợp đồng thất bại'),
                        'message': err_detail,
                        'type': 'danger',
                        'sticky': True,
                        'next': {'type': 'ir.actions.client', 'tag': 'reload'},
                    }
                }

            vals = {
                'th_mail_sent_date': fields.Datetime.now(),
                'th_mail_error': False,
                'state': 'sent',
            }
            self.write(vals)
            attached_names = ', '.join(company_attachments.mapped('name'))
            self.message_post(
                body=_('Đã phát hành email hợp đồng thành công cho CTV: %s (Đính kèm: %s)') % (self.th_email, attached_names)
            )
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Thành công'),
                    'message': _('Đã phát hành email hợp đồng thành công cho CTV: %s') % self.th_email,
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.client', 'tag': 'reload'},
                }
            }
        except Exception as e:
            err_detail = str(e)
            self.write({
                'state': 'mail_error',
                'th_mail_error': err_detail,
            })
            self.message_post(body=_('Gửi email hợp đồng thất bại: %s') % err_detail)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Gửi email hợp đồng thất bại'),
                    'message': err_detail,
                    'type': 'danger',
                    'sticky': True,
                    'next': {'type': 'ir.actions.client', 'tag': 'reload'},
                }
            }

    def th_action_send_contract_mail_batch(self):
        """Gửi email hợp đồng hàng loạt cho các bản ghi được chọn trên danh sách."""
        if not self:
            raise UserError(_('Vui lòng chọn ít nhất một hợp đồng để gửi mail.'))

        default_template = self._get_contract_mail_template()
        if not default_template:
            raise UserError(_('Không tìm thấy mẫu email gửi hợp đồng.'))

        # Tự động lọc và bảo vệ: Bỏ qua các hợp đồng không hợp lệ (đã hoàn tất, đã hủy, đã nộp hoặc đã gửi mail)
        skipped_records = []
        processable_records = self.env['th.collaborator.contract']

        for rec in self:
            if rec.state in ('close', 'cancel'):
                skipped_records.append((rec, _('Đã hoàn tất hoặc đã hủy')))
            elif rec.th_is_expired:
                skipped_records.append((rec, _('Đã hết hạn hiệu lực')))
            elif rec.state in ('submitted', 'pending_sign', 'valid'):
                skipped_records.append((rec, _('CTV đã nộp bản ký / đang xử lý duyệt')))
            elif rec.state == 'sent':
                skipped_records.append((rec, _('Đã gửi mail trước đó')))
            else:
                processable_records |= rec

        if not processable_records:
            skip_details = '\n'.join([f"- {r.th_code or r.name} ({r.th_collaborator_id.name}): {reason}" for r, reason in skipped_records[:10]])
            if len(skipped_records) > 10:
                skip_details += _('\n- ... và %s hợp đồng khác.') % (len(skipped_records) - 10)
            raise UserError(
                _('Không có hợp đồng nào phù hợp để gửi mail trong các bản ghi đã chọn.\n\nChi tiết các hợp đồng bị bỏ qua:\n%s')
                % skip_details
            )

        success_records = self.env['th.collaborator.contract']
        failed_records = []

        for rec in processable_records:
            company_attachments = rec._get_company_mail_attachments()
            error_msg = False
            if not rec.th_email:
                error_msg = _('CTV chưa có địa chỉ email.')
            elif not company_attachments:
                error_msg = _('Hợp đồng chưa có tài liệu có trạng thái bản công ty ký số hoặc bản công ty chưa ký số.')
            elif not rec.user_id.email:
                error_msg = _('Người phụ trách chưa có địa chỉ email.')

            if error_msg:
                rec.write({
                    'state': 'mail_error',
                    'th_mail_error': error_msg,
                })
                failed_records.append((rec, error_msg))
                continue

            try:
                mail_id = default_template.send_mail(rec.id, force_send=True, email_values={
                    'email_from': rec.user_id.email_formatted,
                    'reply_to': rec.user_id.email_formatted,
                    'attachment_ids': company_attachments.ids,
                })
                mail = self.env['mail.mail'].browse(mail_id)
                if mail.exists() and mail.state == 'exception':
                    err_detail = mail.failure_reason or _('Máy chủ gửi mail (SMTP) báo lỗi khi gửi thư.')
                    rec.write({
                        'state': 'mail_error',
                        'th_mail_error': err_detail,
                    })
                    rec.message_post(body=_('Gửi email hợp đồng thất bại: %s') % err_detail)
                    failed_records.append((rec, err_detail))
                    continue

                vals = {
                    'th_mail_sent_date': fields.Datetime.now(),
                    'th_mail_error': False,
                    'state': 'sent',
                }
                rec.write(vals)
                attached_names = ', '.join(company_attachments.mapped('name'))
                rec.message_post(
                    body=_('Đã phát hành email hợp đồng thành công cho CTV: %s (Đính kèm: %s)') % (rec.th_email, attached_names)
                )
                success_records |= rec
            except Exception as e:
                err_detail = str(e)
                rec.write({
                    'state': 'mail_error',
                    'th_mail_error': err_detail,
                })
                rec.message_post(body=_('Gửi email hợp đồng thất bại: %s') % err_detail)
                failed_records.append((rec, err_detail))

        summary_lines = [
            _('Tổng kết gửi mail: Thành công %s/%s hợp đồng cần gửi.') % (len(success_records), len(processable_records))
        ]
        if skipped_records:
            summary_lines.append(_('Đã bỏ qua %s hợp đồng do đã hoàn tất, đã nộp hoặc đã gửi mail trước đó.') % len(skipped_records))
        if failed_records:
            summary_lines.append(_('\nDanh sách thất bại (%s):') % len(failed_records))
            for contract, reason in failed_records[:10]:
                summary_lines.append(f"- {contract.th_code or contract.name} ({contract.th_collaborator_id.name}): {reason}")
            if len(failed_records) > 10:
                summary_lines.append(_('- ... và %s hợp đồng khác.') % (len(failed_records) - 10))

        message = '\n'.join(summary_lines)
        _logger.info('Batch mail sent: %s success, %s skipped, %s failed', len(success_records), len(skipped_records), len(failed_records))

        notify_type = 'success' if not failed_records else ('warning' if success_records else 'danger')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Kết quả gửi email hợp đồng'),
                'type': notify_type,
                'message': message,
                'sticky': bool(failed_records or skipped_records),
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    def th_action_send_final_contract_mail(self):
        """Gửi trả bản hợp đồng đã hoàn tất đủ 2 chữ ký cho CTV qua email."""
        self.ensure_one()
        if not self.th_final_attachment_id:
            final_doc = self.th_document_ids.filtered(lambda d: d.th_document_type == 'final_signed')[:1]
            if final_doc and final_doc.th_attachment_id:
                self.th_final_attachment_id = final_doc.th_attachment_id.id

        if not self.th_final_attachment_id:
            raise UserError(_('Vui lòng tải lên tệp hợp đồng hoàn tất đã đủ 2 chữ ký trước khi gửi trả CTV.'))
        if not self.th_email:
            raise UserError(_('CTV chưa có địa chỉ email để gửi hợp đồng.'))

        mail_values = {
            'subject': _('[%s] HỢP ĐỒNG HOÀN TẤT ĐỦ CHỮ KÝ - %s') % (self.env.company.name, self.name),
            'body_html': _(
                '<p>Kính gửi Anh/Chị <strong>%s</strong>,</p>'
                '<p>Công ty xin gửi lại Anh/Chị bản hợp đồng <strong>"%s"</strong> (Mã: <strong>%s</strong>) '
                'đã có đầy đủ chữ ký của hai bên trong tệp đính kèm để Anh/Chị lưu trữ.</p>'
                '<p>Trân trọng cảm ơn sự hợp tác của Anh/Chị!</p>'
            ) % (self.th_collaborator_id.name, self.name, self.th_code),
            'email_from': self.user_id.email_formatted or self.env.company.email,
            'reply_to': self.user_id.email_formatted or self.env.company.email,
            'email_to': self.th_email,
            'attachment_ids': [Command.link(self.th_final_attachment_id.id)],
        }
        mail = self.env['mail.mail'].sudo().create(mail_values)
        mail.send()
        self.write({'state': 'close'})
        self.message_post(body=_('Đã gửi trả hợp đồng hoàn tất "%s" cho CTV qua email và chuyển trạng thái sang Hoàn tất.') % self.th_final_attachment_id.name)
        return True

    def action_open_upload_document_wizard(self):
        """Mở cửa sổ wizard cho phép nhân viên tải lên tệp hợp đồng."""
        self.ensure_one()
        if self.th_is_readonly:
            raise UserError(_('Hợp đồng đã ở trạng thái Hoàn tất hoặc đã Hết hạn, không thể tải lên thêm tệp.'))
        if self.state in ('close', 'cancel'):
            raise UserError(_('Hợp đồng đã ở trạng thái Hoàn tất hoặc Đã hủy, không thể tải lên thêm tệp.'))
        default_doc_type = 'final_signed' if self.state in ('submitted', 'pending_sign', 'valid') else False
        return {
            'name': _('Tải lên tệp hợp đồng'),
            'type': 'ir.actions.act_window',
            'res_model': 'th.collaborator.contract.document.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_th_contract_id': self.id,
                'default_th_document_type': default_doc_type,
            },
        }

    def _get_download_contract_action(self, contract_type):
        """Khởi tạo hành động tải tệp hợp đồng về máy người dùng theo phân loại."""
        if not self:
            raise UserError(_('Vui lòng chọn ít nhất 1 hợp đồng.'))
        contract = self[0]
        if contract_type == 'company':
            attachments = contract._get_company_mail_attachments()
        elif contract_type == 'self':
            attachments = contract.th_self_attachment_ids
        else:
            attachments = contract.th_final_attachment_id

        if not attachments:
            raise UserError(_('Hợp đồng "%s" chưa có file để tải về.') % contract.name)

        stt_val = contract.th_collaborator_id.th_sequence or 1
        return {
            'type': 'ir.actions.act_url',
            'url': f'/th_collaborator/download_file?contract_id={contract.id}&contract_type={contract_type}&stt={stt_val}',
            'target': 'self',
        }

    def th_action_download_company_contracts(self):
        """Tải tệp hợp đồng do công ty cung cấp về máy."""
        return self._get_download_contract_action('company')

    def th_action_download_self_contracts(self):
        """Tải tệp hợp đồng do CTV nộp về máy."""
        return self._get_download_contract_action('self')

    def th_action_download_final_contracts(self):
        """Tải tệp hợp đồng hoàn tất đủ chữ ký hai bên về máy."""
        return self._get_download_contract_action('final')

    def action_open_batch_contract_wizard(self):
        """Mở cửa sổ wizard thao tác tải / nạp hàng loạt cho các hợp đồng đã chọn."""
        if not self:
            raise UserError(_('Vui lòng chọn ít nhất 1 hợp đồng.'))
        return {
            'name': _('Thao tác tệp hợp đồng hàng loạt'),
            'type': 'ir.actions.act_window',
            'res_model': 'th.collaborator.contract.batch.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_th_contract_ids': [Command.set(self.ids)],
            },
        }

    def action_open_batch_company_wizard(self):
        """Mở cửa sổ thao tác tải / nạp hàng loạt cho HĐ công ty."""
        if not self:
            raise UserError(_('Vui lòng chọn ít nhất 1 hợp đồng.'))
        return {
            'name': _('HĐ Công ty - Tải / Nạp hàng loạt'),
            'type': 'ir.actions.act_window',
            'res_model': 'th.collaborator.contract.batch.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_th_contract_type': 'company',
                'default_th_contract_ids': [Command.set(self.ids)],
            },
        }

    def action_open_batch_self_wizard(self):
        """Mở cửa sổ thao tác tải / nạp hàng loạt cho HĐ CTV nộp."""
        if not self:
            raise UserError(_('Vui lòng chọn ít nhất 1 hợp đồng.'))
        return {
            'name': _('HĐ CTV nộp - Tải / Nạp hàng loạt'),
            'type': 'ir.actions.act_window',
            'res_model': 'th.collaborator.contract.batch.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_th_contract_type': 'self',
                'default_th_contract_ids': [Command.set(self.ids)],
            },
        }

    def action_open_batch_final_wizard(self):
        """Mở cửa sổ thao tác tải / nạp hàng loạt cho HĐ hoàn tất đủ 2 chữ ký."""
        if not self:
            raise UserError(_('Vui lòng chọn ít nhất 1 hợp đồng.'))
        return {
            'name': _('HĐ Hoàn tất - Tải / Nạp hàng loạt'),
            'type': 'ir.actions.act_window',
            'res_model': 'th.collaborator.contract.batch.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_th_contract_type': 'final',
                'default_th_contract_ids': [Command.set(self.ids)],
            },
        }

    @api.model
    def th_cron_send_contract_reminders(self):
        """Cron job hằng ngày: Cập nhật hạn hợp đồng và gửi email nhắc nhở nộp hợp đồng."""
        today = fields.Date.context_today(self)
        active_contracts = self.search([
            ('date_end', '!=', False),
            ('state', 'not in', ('close', 'cancel')),
        ])
        if active_contracts:
            active_contracts._compute_expiration_status()

        contracts = self.search([
            ('state', '=', 'open'),
            ('th_self_attachment_ids', '=', False),
            ('date_end', '!=', False),
            ('th_email', '!=', False),
        ])
        reminder_template = self._get_contract_reminder_mail_template()
        if not reminder_template:
            _logger.warning('Không tìm thấy mẫu email nhắc nhở hợp đồng.')
            return False

        reminded_count = 0
        for contract in contracts:
            days_diff = (contract.date_end - today).days
            if days_diff <= 3:
                try:
                    email_values = {
                        'email_from': contract.user_id.email_formatted or self.env.company.email,
                        'reply_to': contract.user_id.email_formatted or self.env.company.email,
                        'email_to': contract.th_email,
                        'email_cc': contract.user_id.email if contract.user_id.email else False,
                    }
                    reminder_template.send_mail(contract.id, force_send=True, email_values=email_values)
                    contract.message_post(
                        body=_('Hệ thống đã tự động gửi email nhắc nhở nộp hợp đồng cho CTV (Hạn kết thúc: %s).')
                        % contract.date_end.strftime('%d/%m/%Y')
                    )
                    reminded_count += 1
                except Exception as e:
                    _logger.error('Lỗi khi gửi mail nhắc nhở hợp đồng %s: %s', contract.id, str(e))

        _logger.info('Cron th_cron_send_contract_reminders hoàn thành: %s hợp đồng được nhắc nhở.', reminded_count)
        return True

    def _sync_attachments_to_documents(self):
        """Đồng bộ chuyển đổi các tệp đính kèm cũ sang bảng danh sách tài liệu hợp đồng."""
        DocModel = self.env['th.collaborator.contract.document']
        for rec in self:
            existing_doc_att_ids = rec.th_document_ids.mapped('th_attachment_id.id')
            for att in rec.th_company_attachment_ids:
                if att.id not in existing_doc_att_ids:
                    DocModel.create({
                        'name': att.name or _('Bản công ty'),
                        'th_contract_id': rec.id,
                        'th_document_type': 'company_signed',
                        'th_file': att.datas,
                        'th_file_name': att.name,
                        'th_attachment_id': att.id,
                        'th_uploaded_by': 'company',
                        'th_upload_date': att.create_date or fields.Datetime.now(),
                        'th_user_id': att.create_uid.id if att.create_uid else self.env.user.id,
                        'th_notes': _('Đồng bộ từ tệp hợp đồng công ty cũ'),
                    })
            for att in rec.th_self_attachment_ids:
                if att.id not in existing_doc_att_ids:
                    DocModel.create({
                        'name': att.name or _('Bản CTV nộp'),
                        'th_contract_id': rec.id,
                        'th_document_type': 'ctv_signed',
                        'th_file': att.datas,
                        'th_file_name': att.name,
                        'th_attachment_id': att.id,
                        'th_uploaded_by': 'ctv',
                        'th_upload_date': att.create_date or fields.Datetime.now(),
                        'th_user_id': att.create_uid.id if att.create_uid else self.env.user.id,
                        'th_notes': _('Đồng bộ từ tệp CTV nộp cũ'),
                    })
            if rec.th_final_attachment_id and rec.th_final_attachment_id.id not in existing_doc_att_ids:
                att = rec.th_final_attachment_id
                DocModel.create({
                    'name': att.name or _('Bản hoàn tất đủ 2 chữ ký'),
                    'th_contract_id': rec.id,
                    'th_document_type': 'final_signed',
                    'th_file': att.datas,
                    'th_file_name': att.name,
                    'th_attachment_id': att.id,
                    'th_uploaded_by': 'company',
                    'th_upload_date': att.create_date or fields.Datetime.now(),
                    'th_user_id': att.create_uid.id if att.create_uid else self.env.user.id,
                    'th_notes': _('Đồng bộ từ tệp hoàn tất cũ'),
                })
