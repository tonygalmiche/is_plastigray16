# -*- coding: utf-8 -*-
from odoo import models,fields,api
from datetime import datetime, timedelta


class is_resource_calendar_leaves(models.Model):
    _inherit = "resource.calendar.leaves"
    
    partner_id = fields.Many2one('res.partner', 'Partenaire')
    reason     = fields.Selection([
        ('h_summer', 'Summer holiday'),
        ('h_winter', 'Winter holiday'),
        ('h_public', 'Public holiday'),
        ('others', 'Others')], 'Raison de la fermeture')


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals['date_from']:
                #date = datetime.strptime(vals['date_from'], '%Y-%m-%d %H:%M:%S')
                date = vals['date_from']
                date_from = date.strftime('%Y-%m-%d 05:00:00')
                vals.update({'date_from': date_from})
            if vals['date_to']:
                #date = datetime.strptime(vals['date_to'], '%Y-%m-%d %H:%M:%S')
                date = vals['date_to']
                date_to = date.strftime('%Y-%m-%d 05:00:00')
                vals.update({'date_to': date_to})
        return super().create(vals_list)