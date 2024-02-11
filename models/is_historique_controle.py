# -*- coding: utf-8 -*-
from odoo import models,fields,api
from datetime import datetime
from dateutil.relativedelta import relativedelta


class is_historique_controle(models.Model):
    _name='is.historique.controle'
    _description="Historique des contrôles"
    _order='date_controle desc'
    _rec_name='date_controle'


    @api.depends('instrument_id.famille_id')
    def _compute(self):
        for obj in self:
            obj.classe_boolean = obj.instrument_id.famille_id.afficher_classe


    @api.depends('operation_controle_id')
    def _compute_operation_controle_code(self):
        for obj in self:
            obj.operation_controle_code = obj.operation_controle_id.code


    @api.depends('rapport_controle_ids')
    def _compute_rapport_controle_name(self):
        for obj in self:
            names=[]
            for line in obj.rapport_controle_ids:
                names.append(line.name)
            obj.rapport_controle_name = '\n'.join(names)


    plaquette_id  = fields.Many2one('is.plaquette.etalon' , string='Plaquette étalon')
    instrument_id = fields.Many2one('is.instrument.mesure', string='Instruments de mesure')
    gabarit_id    = fields.Many2one('is.gabarit.controle' , string='Gabarit de contrôle')
    piece_id      = fields.Many2one('is.piece.montabilite', string='Piece Montabilite')
    operation_controle_id   = fields.Many2one('is.operation.controle', 'Opération de contrôle', required=True)
    operation_controle_code = fields.Char("Code de l'Opération de contrôle", compute=_compute_operation_controle_code, store=False)
    cause_arret             = fields.Char("Cause arrêt")
    cause_visuel            = fields.Char("Cause visuel")
    date_controle           = fields.Date(string='Date du contrôle', default=fields.Date.context_today, copy=False, required=True)
    organisme_controleur    = fields.Selection([('interne', 'Interne'), ('externe', 'Externe')], "Organisme contrôleur", required=True)
    fournisseur_id          = fields.Many2one('res.partner', 'Fournisseur')
    classe                  = fields.Selection([('0', '0'), ('1', '1'), ('2', '2'), ('3', '3'), ('na', '/NA')], "Classe")
    classe_boolean          = fields.Boolean('Is Classe?', compute=_compute, store=False)
    resultat                = fields.Char(string='Résultat/Erreur maxi')
    etat_conformite         = fields.Selection([('conforme', 'Conforme'), ('non_conforme', 'Non Conforme')], string="Etat de la conformité", required=True)
    rapport_controle_ids    = fields.Many2many('ir.attachment', 'rapport_controle_attachment_rel', 'rapport_controle_id', 'attachment_id', u'Pièces jointes')
    rapport_controle_name   = fields.Text("Pièce jointe", compute="_compute_rapport_controle_name")


    def date_prochain_controle(self,rec):
        date_prochain_controle=False
        if rec.controle_ids:
            date_prochain_controle=False
            lines={}
            for row in rec.controle_ids:
                key=row.date_controle
                lines[key]=row
            lines = dict(sorted(lines.items(), reverse=True))
            for key in lines:
                row=lines[key]
                if row.operation_controle_id.code=='arret':
                    date_prochain_controle=False
                    break
                if row.operation_controle_id.code!='maintenance':
                    date_controle=row.date_controle
                    if date_controle:
                        #date_controle = datetime.strptime(date_controle, "%Y-%m-%d")
                        periodicite=0
                        if rec.periodicite:
                            try:
                                periodicite = int(rec.periodicite)
                            except ValueError:
                                continue
                        date_prochain_controle = date_controle + relativedelta(months=periodicite)
                        #date_prochain_controle = date_prochain_controle.strftime('%Y-%m-%d')
                        break
        return date_prochain_controle
        #rec.date_prochain_controle = date_prochain_controle









class is_operation_controle(models.Model):
    _name='is.operation.controle'
    _description="Opérations des contrôles"
    _order='name'

    name       = fields.Char(string='Opération de contrôle'          , required=True)
    code       = fields.Char(string="Code de l'Opération de contrôle", required=True)
    plaquette  = fields.Boolean('Plaquette étalon')
    instrument = fields.Boolean('Instruments de mesure')
    gabarit    = fields.Boolean('Gabarit de contrôle')
    piece      = fields.Boolean('Piece Montabilite')
    active     = fields.Boolean('Active', default=True)

