# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    """Cấu hình thiết lập hệ thống cho phân hệ Hợp đồng CTV."""
    _inherit = 'res.config.settings'

    th_contract_mail_template_id = fields.Many2one(
        'mail.template',
        string='Mẫu email gửi hợp đồng',
        domain="[('model_id.model', '=', 'th.collaborator.contract')]",
        config_parameter='th_collaborator.contract_mail_template_id',
    )
    th_contract_reminder_mail_template_id = fields.Many2one(
        'mail.template',
        string='Mẫu email nhắc nhở hợp đồng',
        domain="[('model_id.model', '=', 'th.collaborator.contract')]",
        config_parameter='th_collaborator.contract_reminder_mail_template_id',
    )

    @api.model
    def get_values(self):
        """Lấy giá trị cấu hình mẫu email và tự động áp dụng mẫu mặc định nếu chưa thiết lập."""
        res = super().get_values()
        icp = self.env['ir.config_parameter'].sudo()

        template_send_id = icp.get_param('th_collaborator.contract_mail_template_id')
        if not template_send_id:
            default_send = self.env.ref(
                'th_collaborator.th_collaborator_profile_send_mail_template', raise_if_not_found=False)
            if default_send:
                res['th_contract_mail_template_id'] = default_send.id

        template_reminder_id = icp.get_param('th_collaborator.contract_reminder_mail_template_id')
        if not template_reminder_id:
            default_reminder = self.env.ref(
                'th_collaborator.th_collaborator_contract_reminder_mail_template', raise_if_not_found=False)
            if default_reminder:
                res['th_contract_reminder_mail_template_id'] = default_reminder.id

        return res

    def action_open_contract_mail_template(self):
        """Mở giao diện chỉnh sửa mẫu email gửi hợp đồng cho CTV."""
        self.ensure_one()
        template = self.th_contract_mail_template_id or self.env.ref(
            'th_collaborator.th_collaborator_profile_send_mail_template', raise_if_not_found=False)
        if not template:
            raise UserError(_('Không tìm thấy mẫu email gửi hợp đồng.'))
        return {
            'name': _('Mẫu email gửi hợp đồng'),
            'type': 'ir.actions.act_window',
            'res_model': 'mail.template',
            'res_id': template.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_contract_reminder_mail_template(self):
        """Mở giao diện chỉnh sửa mẫu email nhắc nhở nộp hợp đồng."""
        self.ensure_one()
        template = self.th_contract_reminder_mail_template_id or self.env.ref(
            'th_collaborator.th_collaborator_contract_reminder_mail_template', raise_if_not_found=False)
        if not template:
            raise UserError(_('Không tìm thấy mẫu email nhắc nhở hợp đồng.'))
        return {
            'name': _('Mẫu email nhắc nhở hợp đồng'),
            'type': 'ir.actions.act_window',
            'res_model': 'mail.template',
            'res_id': template.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_all_collaborator_mail_templates(self):
        """Mở danh sách toàn bộ các mẫu email thuộc phân hệ Hợp đồng CTV."""
        return {
            'name': _('Mẫu email hợp đồng CTV'),
            'type': 'ir.actions.act_window',
            'res_model': 'mail.template',
            'view_mode': 'tree,form',
            'domain': [('model_id.model', '=', 'th.collaborator.contract')],
            'context': {
                'default_model': 'th.collaborator.contract',
            },
            'target': 'current',
        }
