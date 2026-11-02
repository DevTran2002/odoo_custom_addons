# -*- coding: utf-8 -*-
from odoo import models


class ThCollaboratorSignConfig(models.Model):
    """Model chuyển tiếp nhằm duy trì registry cho Odoo khi nâng cấp database cũ.

    Tránh lỗi KeyError trong ir.model.fields.selection.unlink() khi Odoo dọn dẹp các
    bản ghi selection cũ từ phiên bản trước.
    """
    _name = 'th.collaborator.sign.config'
    _description = 'Cấu hình ký số (Chuyển tiếp)'


class ThCollaboratorContractTemplate(models.Model):
    """Model chuyển tiếp nhằm duy trì registry cho Odoo khi nâng cấp database cũ."""
    _name = 'th.collaborator.contract.template'
    _description = 'Mẫu hợp đồng (Chuyển tiếp)'


class ThCollaboratorContractTemplateLine(models.Model):
    """Model chuyển tiếp nhằm duy trì registry cho Odoo khi nâng cấp database cũ."""
    _name = 'th.collaborator.contract.template.line'
    _description = 'Dòng mẫu hợp đồng (Chuyển tiếp)'

