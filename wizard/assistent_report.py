# -*- coding: utf-8 -*-
from odoo import models,fields
from datetime import datetime, date


class assistent_report1(models.TransientModel):
    _name = "assistent.report1"
    _description="Rapport de pointage"


    def date_debut_mois(self):
        now = date.today()                                     # Date du jour
        date_debut_mois = datetime( now.year, now.month, 1 )   # Premier jour du mois
        return date_debut_mois


    site= fields.Selection([
            ("1", "Gray"), 
            ("4", "ST-Brice"), 
        ], "Site", required=True)
    version = fields.Selection([
            ("1", "1"),
            ("2", "2"),
            ("3", "3"),
        ], "Version du rapport", required=True, default="2")
    type_rapport= fields.Selection([
            ("rapport_mois", "Liste mensuelle"), 
            ("rapport_date_a_date", "Liste de date à date"),  
            ("rapport_a_date", "Liste à date")             
        ], "Modèle de rapport", required=True, default="rapport_mois")
    date_jour   = fields.Date("Date"             , required=False, default=lambda *a: fields.datetime.now())
    date_mois   = fields.Date("Date dans le mois", required=False, default=lambda self: self.date_debut_mois())
    date_debut  = fields.Date("Date de début"    , required=False, default=lambda self: self.date_debut_mois())
    date_fin    = fields.Date("Date de fin"      , required=False, default=lambda *a: fields.datetime.now())
    employee    = fields.Many2one('hr.employee', 'Employé', required=False, ondelete='set null', help="Sélectionnez un employé")
    interimaire = fields.Boolean('Intérimaire',  help="Cocher pour sélectionner uniquement les intérimaires")
    saut_page   = fields.Boolean('Saut de page',  help="Cocher pour avoir un saut de page pour chaque employé")
    detail      = fields.Boolean("Vue détaillée")


    def assistent_report1(self):
        report_link = "http://odoo16/odoo-rh/rapport"+ str(self.version)+".php"
        url = "%s?&type_rapport=%s&site=%s&date_jour=%s&date_mois=%s&detail=%s&employee=%s&interimaire=%s&saut_page=%s&date_debut=%s&date_fin=%s"%(
            report_link,
            self.type_rapport,
            self.site,
            self.date_jour,
            self.date_mois,
            self.detail,
            self.employee.id,
            self.interimaire,
            self.saut_page,
            self.date_debut,
            self.date_fin,
        )
        return {
            'type'     : 'ir.actions.act_url',
            'target'   : 'new',
            'url'      : url
        }
