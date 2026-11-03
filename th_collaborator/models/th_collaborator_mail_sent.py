# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _


class MailMail(models.Model):
    """Mở rộng model mail.mail để lưu trữ liên kết tới Hợp đồng và Cộng tác viên."""
    _inherit = 'mail.mail'

    th_contract_id = fields.Many2one(
        'th.collaborator.contract',
        string='Hợp đồng',
        compute='_compute_th_collaborator_info',
        store=True,
        index=True,
        help='Hợp đồng CTV liên kết với email này'
    )
    th_collaborator_id = fields.Many2one(
        'th.collaborator.profile',
        string='Cộng tác viên',
        compute='_compute_th_collaborator_info',
        store=True,
        index=True,
        help='Cộng tác viên nhận email này'
    )

    @api.depends('mail_message_id', 'mail_message_id.model', 'mail_message_id.res_id')
    def _compute_th_collaborator_info(self):
        """Tự động xác định Hợp đồng và Cộng tác viên từ thông điệp mail_message_id."""
        Contract = self.env['th.collaborator.contract']
        for mail in self:
            msg = mail.mail_message_id
            if msg and msg.model == 'th.collaborator.contract' and msg.res_id:
                contract = Contract.browse(msg.res_id).exists()
                mail.th_contract_id = contract.id if contract else False
                mail.th_collaborator_id = contract.th_collaborator_id.id if contract and contract.th_collaborator_id else False
            elif msg and msg.model == 'th.collaborator.profile' and msg.res_id:
                mail.th_contract_id = False
                mail.th_collaborator_id = msg.res_id
            else:
                mail.th_contract_id = False
                mail.th_collaborator_id = False

    def write(self, vals):
        """Tự động đồng bộ trạng thái lỗi gửi email sang Hợp đồng tương ứng."""
        res = super().write(vals)
        new_state = vals.get('state')
        if new_state == 'exception':
            for mail in self:
                contract = mail.th_contract_id
                if contract and contract.state in ('draft', 'open', 'sent'):
                    err_msg = mail.failure_reason or _('Lỗi máy chủ khi gửi thư (SMTP).')
                    # Ghi nhận trạng thái gửi mail lỗi cho hợp đồng
                    contract.write({
                        'state': 'mail_error',
                        'th_mail_error': err_msg,
                    })
                    contract.message_post(body=_('Gửi email hợp đồng thất bại: %s') % err_msg)
        elif new_state == 'sent':
            for mail in self:
                contract = mail.th_contract_id
                if contract and contract.state == 'mail_error':
                    # Email gửi lại thành công, khôi phục trạng thái gửi mail
                    contract.write({
                        'state': 'sent',
                        'th_mail_error': False,
                        'th_mail_sent_date': fields.Datetime.now(),
                    })
                    contract.message_post(body=_('Email hợp đồng đã được gửi thành công đến CTV: %s') % (contract.th_email or ''))
        return res


class ThCollaboratorMailSent(models.Model):
    """Model view SQL để hiển thị danh sách và chi tiết email đã gửi cho Cộng tác viên."""
    _name = 'th.collaborator.mail.sent'
    _description = 'Mail đã gửi cho cộng tác viên'
    _auto = False
    _order = 'date desc, id desc'
    _rec_name = 'name'

    id = fields.Integer('ID', readonly=True)
    th_collaborator_id = fields.Many2one('th.collaborator.profile', string='Cộng tác viên', readonly=True)
    th_collaborator_name = fields.Char('Tên cộng tác viên', readonly=True)
    th_contract_id = fields.Many2one('th.collaborator.contract', string='Hợp đồng', readonly=True)
    th_contract_code = fields.Char('Mã hợp đồng', readonly=True)
    th_contract_name = fields.Char('Tên hợp đồng', readonly=True)
    subject = fields.Char('Tiêu đề', readonly=True)
    email_to = fields.Char('Email đến', readonly=True)
    email_from = fields.Char('Email từ', readonly=True)
    date = fields.Datetime('Ngày gửi', readonly=True)
    state = fields.Selection([
        ('outgoing', 'Đang gửi'),
        ('sent', 'Đã gửi'),
        ('received', 'Đã nhận'),
        ('exception', 'Lỗi'),
        ('cancel', 'Đã hủy'),
    ], string='Trạng thái', readonly=True)
    body_html = fields.Html('Nội dung', readonly=True)
    failure_reason = fields.Text('Lý do thất bại', readonly=True)
    name = fields.Char('Tên hiển thị', readonly=True)

    def init(self):
        """Khởi tạo hoặc cập nhật SQL View th_collaborator_mail_sent."""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW th_collaborator_mail_sent AS (
                SELECT 
                    mm.id,
                    CASE 
                        WHEN msg.model = 'th.collaborator.contract' THEN tc.th_collaborator_id
                        WHEN msg.model = 'th.collaborator.profile' THEN tp_direct.id
                        ELSE NULL 
                    END AS th_collaborator_id,
                    COALESCE(tp_contract.name, tp_direct.name, '') AS th_collaborator_name,
                    CASE 
                        WHEN msg.model = 'th.collaborator.contract' THEN tc.id
                        ELSE NULL 
                    END AS th_contract_id,
                    COALESCE(tc.th_code, '') AS th_contract_code,
                    COALESCE(tc.name, '') AS th_contract_name,
                    msg.subject,
                    mm.email_to,
                    msg.email_from,
                    msg.date,
                    mm.state,
                    COALESCE(mm.body_html, msg.body) AS body_html,
                    mm.failure_reason,
                    CONCAT(
                        COALESCE(tp_contract.name, tp_direct.name, 'CTV'), 
                        ' - ', 
                        COALESCE(msg.subject, 'Email')
                    ) AS name
                FROM mail_mail mm
                INNER JOIN mail_message msg ON mm.mail_message_id = msg.id
                LEFT JOIN th_collaborator_contract tc ON msg.model = 'th.collaborator.contract' AND msg.res_id = tc.id
                LEFT JOIN th_collaborator_profile tp_contract ON tc.th_collaborator_id = tp_contract.id
                LEFT JOIN th_collaborator_profile tp_direct ON msg.model = 'th.collaborator.profile' AND msg.res_id = tp_direct.id
                WHERE (msg.model = 'th.collaborator.contract' AND tc.id IS NOT NULL)
                   OR (msg.model = 'th.collaborator.profile' AND tp_direct.id IS NOT NULL)
                ORDER BY msg.date DESC, mm.id DESC
            )
        """)

