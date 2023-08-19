# -*- coding: utf-8 -*-
from odoo import models,fields,api
from datetime import datetime, timedelta


class is_resource_calendar_leaves(models.Model):
    _inherit = "resource.calendar.leaves"
    
    partner_id = fields.Many2one('res.partner', 'Partenaire')
    reason     = fields.Selection([
        ('h_summer', "Congés d'été"),
        ('h_winter', "Congés d'hiver"),
        ('h_public', "Jours fériés"),
        ('others'  , "Autres")], 'Raison de la fermeture')


    def dateto5h(self,date):
        "Retourne un datetime à 5H"
        if type(date) == str:
            date = date[0:10]+" 05:00:00"
        else:
            date = date.strftime('%Y-%m-%d 05:00:00')
        return date


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals['date_from']:
                vals.update({'date_from': self.dateto5h(vals['date_from'])})
            if vals['date_to']:
                vals.update({'date_to': self.dateto5h(vals['date_to'])})
        return super().create(vals_list)
