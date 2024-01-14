# -*- coding: utf-8 -*-
from odoo import models,fields,api

class AuditlogRule(models.Model):
    _inherit = 'auditlog.rule'

    is_duree_conservation = fields.Integer(string='Durée de conservation des journaux (en mois)')


