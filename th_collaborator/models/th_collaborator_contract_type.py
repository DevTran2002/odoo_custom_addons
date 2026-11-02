# -*- coding: utf-8 -*-
from random import randint

from odoo import fields, models


class ThCollaboratorContractType(models.Model):
    _name = 'th.collaborator.contract.type'
    _description = 'Loại hợp đồng CTV'
    _order = 'sequence, name'

    def th_default_color(self):
        """Gán màu ngẫu nhiên để các tag dễ phân biệt."""
        return randint(1, 11)

    name = fields.Char(string='Tên loại hợp đồng', translate=True)
    sequence = fields.Integer(string='Thứ tự', default=10)
    th_color = fields.Integer(string='Màu', default=lambda self: self.th_default_color())
    active = fields.Boolean(string='Đang sử dụng', default=True)

    _sql_constraints = [
        ('th_name_uniq', 'unique(name)', 'Loại hợp đồng đã tồn tại.'),
    ]
