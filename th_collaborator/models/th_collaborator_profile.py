# -*- coding: utf-8 -*-
import logging
import re
import secrets

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import email_normalize
from odoo.tools.mimetypes import guess_mimetype

_logger = logging.getLogger(__name__)

TH_CONTRACT_ALLOWED_EXTENSIONS = ('.pdf', '.jpg', '.jpeg', '.png')


class ThCollaboratorProfile(models.Model):
    """Hồ sơ Cộng tác viên (CTV).

    Quản lý thông tin định danh, liên hệ, người phụ trách và cung cấp cổng
    tải lên hợp đồng công khai cho CTV. Một CTV có thể có nhiều hợp đồng.
    """
    _name = 'th.collaborator.profile'
    _description = 'Cộng tác viên'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    def th_default_user_id(self):
        """Mặc định người phụ trách CTV là người tạo bản ghi."""
        return self.env.user

    def th_default_access_token(self):
        """Sinh token ngẫu nhiên cho link upload công khai của CTV."""
        return secrets.token_urlsafe(32)

    name = fields.Char(string='Họ và tên', required=True, tracking=True)
    th_program = fields.Char(string='Chương trình', tracking=True)
    th_birthday = fields.Date(string='Ngày sinh', tracking=True)
    th_email = fields.Char(string='Email', required=True, tracking=True)
    th_phone = fields.Char(string='Số điện thoại', required=True, tracking=True)
    th_phone_normalized = fields.Char(
        string='SĐT chuẩn hoá', compute='th_compute_phone_normalized', store=True, index=True)
    user_id = fields.Many2one(
        'res.users', string='Người phụ trách', tracking=True,
        default=lambda self: self.th_default_user_id())

    # Thông tin định danh & Thuế
    th_identification_id = fields.Char(string='Số CCCD', index=True, tracking=True)
    th_id_issue_date = fields.Date(string='Ngày cấp CCCD', tracking=True)
    th_id_issue_place = fields.Char(string='Nơi cấp CCCD', tracking=True)
    th_tax_code = fields.Char(string='Mã số thuế', tracking=True)

    # Thông tin tài khoản ngân hàng
    th_bank_account_number = fields.Char(string='Số tài khoản ngân hàng', tracking=True)
    th_bank_name = fields.Char(string='Ngân hàng / Chi nhánh', tracking=True)

    th_access_token = fields.Char(
        string='Token upload', copy=False, default=lambda self: self.th_default_access_token())
    th_upload_url = fields.Char(string='Link upload hợp đồng', compute='th_compute_upload_url')

    th_contract_ids = fields.One2many(
        'th.collaborator.contract', 'th_collaborator_id', string='Danh sách hợp đồng')
    th_completed_contract_ids = fields.One2many(
        'th.collaborator.contract', 'th_collaborator_id', string='Hợp đồng đã hoàn tất',
        domain=[('state', '=', 'close')])
    th_contract_count = fields.Integer(
        string='Số lượng hợp đồng', compute='_compute_contract_counts')
    th_running_contract_count = fields.Integer(
        string='Số HĐ đang chạy', compute='_compute_contract_counts')

    # Thống kê email đã gửi
    th_mail_sent_count = fields.Integer(string='Đã gửi', compute='_compute_mail_statistics')
    th_mail_delivered_count = fields.Integer(string='Đã nhận (SL)', compute='_compute_mail_statistics')
    th_mail_failed_count = fields.Integer(string='Lỗi (SL)', compute='_compute_mail_statistics')
    th_mail_delivered_ratio = fields.Integer(string='Đã nhận', compute='_compute_mail_statistics')
    th_mail_failed_ratio = fields.Integer(string='Lỗi', compute='_compute_mail_statistics')

    _sql_constraints = [
        ('th_phone_normalized_uniq', 'unique(th_phone_normalized)',
         'Số điện thoại đã tồn tại ở một CTV khác.'),
        ('th_access_token_uniq', 'unique(th_access_token)', 'Token upload bị trùng.'),
    ]

    @api.depends('th_contract_ids', 'th_contract_ids.state')
    def _compute_contract_counts(self):
        """Đếm tổng số hợp đồng và số lượng hợp đồng đang chạy của CTV."""
        for rec in self:
            contracts = rec.th_contract_ids
            rec.th_contract_count = len(contracts)
            rec.th_running_contract_count = len(contracts.filtered(lambda c: c.state == 'open'))

    @api.model
    def _normalize_phone(self, phone):
        """Chuẩn hoá SĐT về dạng 0xxxxxxxxx để làm khoá map bản ghi."""
        digits = re.sub(r'\D', '', phone or '')
        if digits.startswith('84') and len(digits) >= 11:
            digits = '0' + digits[2:]
        return digits

    @api.model
    def _is_allowed_contract_file(self, file_name, content=None, mimetype=None):
        """Kiểm tra file hợp đồng upload thường chỉ là PDF hoặc ảnh."""
        if not (file_name or '').lower().endswith(TH_CONTRACT_ALLOWED_EXTENSIONS):
            return False
        if content is not None:
            mimetype = guess_mimetype(content)
        return bool(mimetype) and (mimetype == 'application/pdf' or mimetype.startswith('image/'))

    @api.depends('th_phone')
    def th_compute_phone_normalized(self):
        """Tính SĐT chuẩn hoá từ SĐT người dùng nhập."""
        for rec in self:
            rec.th_phone_normalized = self._normalize_phone(rec.th_phone) or False

    @api.depends('th_access_token')
    def th_compute_upload_url(self):
        """Dựng link công khai để CTV tự tải hợp đồng lên."""
        for rec in self:
            rec.th_upload_url = rec.th_access_token and '%s/th_collaborator/upload/%s' % (
                rec.get_base_url(), rec.th_access_token) or False

    @api.constrains('th_email')
    def th_check_email(self):
        """Kiểm tra email CTV đúng định dạng để gửi mail được."""
        for rec in self:
            if rec.th_email and not email_normalize(rec.th_email):
                raise ValidationError(_('Email "%s" không hợp lệ.') % rec.th_email)

    @api.constrains('th_phone')
    def th_check_phone(self):
        """Kiểm tra SĐT đủ độ dài để liên hệ và phục vụ đối soát dữ liệu."""
        for rec in self:
            if rec.th_phone and len(rec.th_phone_normalized or '') < 9:
                raise ValidationError(_('Số điện thoại "%s" không hợp lệ.') % rec.th_phone)

    def th_action_regenerate_token(self):
        """Tạo lại link upload, vô hiệu hoá link cũ đã gửi cho CTV."""
        self.ensure_one()
        self.th_access_token = self.th_default_access_token()
        self.message_post(body=_('Đã tạo lại link upload hợp đồng, link cũ không còn hiệu lực.'))
        return True

    def action_open_collaborator_contracts(self):
        """Mở danh sách hợp đồng của CTV hiện tại cho Smart Button."""
        self.ensure_one()
        return {
            'name': _('Hợp đồng của %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'th.collaborator.contract',
            'view_mode': 'tree,form',
            'domain': [('th_collaborator_id', '=', self.id)],
            'context': {
                'default_th_collaborator_id': self.id,
                'default_user_id': self.user_id.id if self.user_id else False,
            },
        }

    def _compute_mail_statistics(self):
        """Tính toán thống kê toàn bộ email đã gửi cho CTV này."""
        MailSent = self.env['th.collaborator.mail.sent']
        for profile in self:
            mails = MailSent.search([('th_collaborator_id', '=', profile.id)])
            sent_count = len(mails.filtered(lambda m: m.state in ('sent', 'outgoing', 'exception')))
            delivered_count = len(mails.filtered(lambda m: m.state == 'sent'))
            failed_count = len(mails.filtered(lambda m: m.state == 'exception'))

            profile.th_mail_sent_count = sent_count
            profile.th_mail_delivered_count = delivered_count
            profile.th_mail_failed_count = failed_count

            if sent_count > 0:
                profile.th_mail_delivered_ratio = int(100 * delivered_count / sent_count)
                profile.th_mail_failed_ratio = int(100 * failed_count / sent_count)
            else:
                profile.th_mail_delivered_ratio = 0
                profile.th_mail_failed_ratio = 0

    def th_action_view_sent_mails(self):
        """Xem danh sách toàn bộ email đã gửi cho CTV này."""
        self.ensure_one()
        return {
            'name': _('Email đã gửi - CTV %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'th.collaborator.mail.sent',
            'view_mode': 'tree,form',
            'domain': [('th_collaborator_id', '=', self.id)],
            'context': {'create': False, 'edit': False, 'delete': False},
        }

    def th_action_view_delivered_mails(self):
        """Xem danh sách email đã nhận (sent) của CTV này."""
        self.ensure_one()
        return {
            'name': _('Email đã nhận - CTV %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'th.collaborator.mail.sent',
            'view_mode': 'tree,form',
            'domain': [('th_collaborator_id', '=', self.id), ('state', '=', 'sent')],
            'context': {'create': False, 'edit': False, 'delete': False},
        }

    def th_action_view_failed_mails(self):
        """Xem danh sách email bị lỗi của CTV này."""
        self.ensure_one()
        return {
            'name': _('Email lỗi - CTV %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'th.collaborator.mail.sent',
            'view_mode': 'tree,form',
            'domain': [('th_collaborator_id', '=', self.id), ('state', '=', 'exception')],
            'context': {'create': False, 'edit': False, 'delete': False},
        }
