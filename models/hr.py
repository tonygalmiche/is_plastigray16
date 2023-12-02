# -*- coding: utf-8 -*-

from odoo import models,fields,api


class hr_employee(models.Model):
    _name = "hr.employee"
    _inherit = "hr.employee"

    def _badge_count(self):
        badge_obj = self.env['is.badge']
        for obj in self:
            nb = len(badge_obj.search([('employee', '=', obj.id)]))
            obj.is_badge_count=nb


    def _pointage_count(self):
        pointage_obj = self.env['is.pointage']
        for obj in self:
            nb = len(pointage_obj.search([('employee', '=', obj.id)]))
            obj.is_pointage_count=nb


    def action_view_badge(self, cr, uid, ids, context=None):
        res = {}
        res['context'] = "{'employee': " + str(ids[0]) + "}"
        return res

    is_site=fields.Selection([
            ("1", "Gray"), 
            ("4", "ST-Brice"), 
        ], "Site", required=False)
    is_matricule=fields.Char('Matricule', help='N° de matricule du logiciel de paye', required=False)
    is_categorie=fields.Selection([
            ("2x8" , "Équipe en 2x8"), 
            ("2x8r", "Équipe en 2x8 avec recouvrement"), 
            ("nuit", "Équipe de nuit"),
            ("3x8" , "en 3x8"),
            ("jour", "Personnel de journée"),
        ], "Catégorie de personnel", required=False)
    is_interimaire    = fields.Boolean('Intérimaire',  help="Cocher pour indiquer que c'est un intérimaire")
    is_pointage       = fields.Boolean('Pointage',  help="Cocher pour indiquer que l'employé pointe", default=False)
    is_badge_count    = fields.Integer('# Badges'      , compute='_badge_count'   , readonly=True, store=False)
    is_pointage_count = fields.Integer('# Pointages', compute='_pointage_count', readonly=True, store=False)
    is_jour1=fields.Float('Lundi')
    is_jour2=fields.Float('Mardi')
    is_jour3=fields.Float('Mercredi')
    is_jour4=fields.Float('Jeudi')
    is_jour5=fields.Float('Vendredi')
    is_jour6=fields.Float('Samedi')
    is_jour7=fields.Float('Dimanche')

    is_employe_horaire_ids = fields.One2many('is.employe.horaire', 'employe_id', u"Horaires")
    is_employe_absence_ids = fields.One2many('is.employe.absence', 'employe_id', u"Absences")

    is_valideur_n1      = fields.Many2one('res.users', string=u'Valideur Niveau 1')
    is_valideur_n2      = fields.Many2one('res.users', string=u'Valideur Niveau 2')
    is_droit_conges_ids = fields.One2many('is.droit.conges', 'employe_id', u"Droit aux congés")

    is_mode_communication = fields.Selection([
                                        ('courriel'    , u'Courriel'),
                                        ('sms'         , u'SMS'),
                                        ('courriel+sms','Courriel + SMS'),
                                        ], string='Mode de communication')
    is_mobile   = fields.Char(u"Mobile"  , help="Téléphone utilisé pour l'envoi des SMS pour les demandes de congés")
    is_courriel = fields.Char(u"Courriel", help="Courriel utilisé pour l'envoi des informations pour les demandes de congés")

    message_main_attachment_id = fields.Many2one(groups="base.group_user") # Etait : groups="hr.group_hr_user"
    is_editable = fields.Boolean('Champs éditables', compute='_compute_is_editable', readonly=True, store=False)



    def _compute_is_editable(self):
        test=False
        if self.env['res.users'].has_group('hr.group_hr_manager'):
            test=True
        for obj in self:
            print(obj,test)
            obj.is_editable = test
            

    def name_get(self):
        res = []
        for obj in self:
            name = "%s (%s)"%(obj.name,(obj.is_matricule or ''))
            res.append((obj.id,name))
        return res

    def _name_search(self, name='', args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if name:
            ids = list(self._search(['|',('name','ilike', name),('is_matricule','ilike', name)], limit=limit))
        else:
            ids = self._search(args, limit=limit)
        return ids


class is_employe_horaire(models.Model):
    _name='is.employe.horaire'
    _description="is_employe_horaire"
    _order='date_debut desc'

    employe_id = fields.Many2one('hr.employee', 'Employé', required=True, ondelete='cascade', readonly=True)
    date_debut = fields.Date('Date de début', required=True)
    date_fin   = fields.Date('Date de fin'  , required=True)
    semaine=fields.Selection([
            ("P" , "Paire"), 
            ("I" , "Impaire"), 
            ("PI", "Paire+Impaire"), 
        ], "Semaine", required=True)
    jour1 = fields.Float('Lundi')
    jour2 = fields.Float('Mardi')
    jour3 = fields.Float('Mercredi')
    jour4 = fields.Float('Jeudi')
    jour5 = fields.Float('Vendredi')
    jour6 = fields.Float('Samedi')
    jour7 = fields.Float('Dimanche')


class is_employe_absence(models.Model):
    _name='is.employe.absence'
    _description="is_employe_absence"
    _order='date_debut desc'

    employe_id  = fields.Many2one('hr.employee', 'Employé', required=True, ondelete='cascade', readonly=True)
    date_debut  = fields.Date('Date de début', required=True)
    date_fin    = fields.Date('Date de fin'  , required=True)
    nb_heures   = fields.Float("Nombre d'heures d'absence par jour", required=True)
    commentaire = fields.Char("Commentaire")

