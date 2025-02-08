# -*- coding: utf-8 -*-
from odoo import models,fields,api               # type: ignore
from odoo.exceptions import ValidationError      # type: ignore


class is_gestion_portail(models.Model):
    _name='is.gestion.portail'
    _description="Gestion du portail"
    _order='ordre'

    name       = fields.Char("Description de l’horaire", help="ex : Le matin du lundi au vendredi", required=True)
    ordre      = fields.Integer("Ordre", default=0, help="Ordre de prise en compte. Le premier est pris en compte")
    date_debut = fields.Date("Date de début")
    date_fin   = fields.Date("Date de fin")
    date_ids   = fields.One2many('is.gestion.portail.date', 'gestion_id', "Dates ")
    dates      = fields.Text("Dates", store=True, compute='_compute_dates')
    jour_1     = fields.Boolean("Lundi"   , default=False)
    jour_2     = fields.Boolean("Mardi"   , default=False)
    jour_3     = fields.Boolean("Mercredi", default=False)
    jour_4     = fields.Boolean("Jeudi"   , default=False)
    jour_5     = fields.Boolean("Vendredi", default=False)
    jour_6     = fields.Boolean("Samedi"  , default=False)
    jour_7     = fields.Boolean("Dimanche", default=False)
    heure_ouverture = fields.Float("Heure d’ouverture" , required=True)
    heure_fermeture = fields.Float("Heure de fermeture", required=True)


    @api.depends('date_ids','date_ids.name')
    def _compute_dates(self):
        for obj in self:
            dates=[]
            for line in obj.date_ids:
                if line.name:
                    dates.append(line.name.strftime('%d/%m/%Y'))
            dates = ', '.join(dates)
            obj.dates = dates
          

class is_gestion_portail_date(models.Model):
    _name='is.gestion.portail.date'
    _description="Gestion du portail - Dates"
    _order='name'

    gestion_id = fields.Many2one('is.gestion.portail', 'Gestion portail', required=True, ondelete="cascade")
    name       = fields.Date("Date")


class is_gestion_portail_calendar(models.Model):
    _name='is.gestion.portail.calendar'
    _description="Gestion du portail - Calendar"
    _order='date_debut'
    _rec_name = 'gestion_id'

    gestion_id = fields.Many2one('is.gestion.portail', 'Gestion portail', required=True)
    date_debut = fields.Datetime("Date de début", required=True)
    date_fin   = fields.Datetime("Date de fin", required=True)
