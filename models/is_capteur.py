# -*- coding: utf-8 -*-
from odoo import models,fields,api

class is_capteur(models.Model):
    _name = 'is.capteur'
    _description = "Capteurs pour usine 4.0"
    _order='date_heure desc'

    name       = fields.Char('Nom du capteur', index=True, required=True)
    date_heure = fields.Datetime('Date Heure', index=True, required=True)
    mesure     = fields.Float('Mesure', digits=(12,4))
    unite      = fields.Char('Unité')

