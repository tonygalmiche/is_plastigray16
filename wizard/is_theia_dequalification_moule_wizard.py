# -*- coding: utf-8 -*-
from odoo import api, fields, models


class IsTheiaDequalificationMouleWizard(models.TransientModel):
    _name = 'is.theia.dequalification.moule.wizard'
    _description = "Assistant de déqualification moule"

    moule_id          = fields.Many2one('is.mold', string="Moule", required=True, readonly=True)
    dequalification_id = fields.Many2one(
        'is.theia.type.dequalification',
        string="Type de déqualification",
        required=True,
    )

    def action_confirmer(self):
        for obj in self:
            return obj.moule_id.dequalification_moule_action(dequalification_id=obj.dequalification_id.id)
