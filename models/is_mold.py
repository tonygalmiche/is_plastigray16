# -*- coding: utf-8 -*-

from odoo import models,fields,api
from odoo.tools.translate import _
import datetime


class is_mold_dateur(models.Model):
    _name='is.mold.dateur'
    _description = "Dateur Moule"
    _order='mold_id,type_dateur'

    mold_id = fields.Many2one('is.mold', 'Moule', required=True, ondelete='cascade', readonly=True)
    type_dateur = fields.Selection([
            ('dateur_grille'    , u'dateur à grille'),
            ('dateur_laiton'    , u'dateur laiton'),
            ('dateur_fleche'    , u'dateur à fleche'),
            ('dateur_specifique', u'dateur spécifique'),
            ('pas_de_dateur'    , u'pas de dateur'),
        ], "Type de dateur",required=True)
    qt_dans_moule   = fields.Integer("Quantité dans le moule",required=True)
    diametre_dateur = fields.Selection([
            ('d3' , u'Ø3'),
            ('d4' , u'Ø4'),
            ('d5' , u'Ø5'),
            ('d6' , u'Ø6'),
            ('d8' , u'Ø8'),
            ('d10', u'Ø10'),
            ('d12', u'Ø12'),
            ('d14', u'Ø14'),
            ('d16', u'Ø16'),
            ('d18', u'Ø18'),
            ('d20', u'Ø20'),
        ], "Diamètre dateur")
    date_peremption = fields.Date("Date de péremption")
    commentaire     = fields.Char("Commentaire")


class is_mold(models.Model):
    _name='is.mold'
    _description = "Moule"
    _order='name'
    _sql_constraints = [('name_uniq','UNIQUE(name)', 'Ce moule existe deja')]

    name             = fields.Char("N°Moule",size=40,required=True, index=True)
    designation      = fields.Char("Désignation")
    project          = fields.Many2one('is.mold.project', 'Projet')
    client_id        = fields.Many2one('res.partner', 'Client'        , store=True, compute='_compute_chef_projet_id')
    chef_projet_id   = fields.Many2one('res.users'  , 'Chef de projet', store=True, compute='_compute_chef_projet_id')
    dossierf_id      = fields.Many2one('is.dossierf', 'Dossier F')
    dossierf_ids     = fields.Many2many("is.dossierf", "is_mold_dossierf_rel", "mold_id", "dossierf_id", u"Dossiers F")
    nb_empreintes    = fields.Char("Nb empreintes", help="Nombre d'empreintes du moule (Exemple : 1+1)")
    moule_a_version  = fields.Selection([('oui', u'Oui'),('non', u'Non')], "Moule à version")
    lieu_changement  = fields.Selection([('sur_presse', u'sur presse'),('en_mecanique', u'en mécanique')], "Lieu de changement")
    temps_changement = fields.Float("Temps de changement de la version (H)")
    nettoyer         = fields.Boolean('Nettoyage moule avant production')
    nettoyer_vis     = fields.Boolean('Nettoyage vis avant production')
    date_creation    = fields.Date("Date de création")
    date_fin         = fields.Date("Date de fin")
    mouliste_id      = fields.Many2one('res.partner', 'Mouliste')
    carcasse         = fields.Char("Carcasse")
    emplacement      = fields.Char("Emplacement")
    type_dateur      = fields.Selection([
            ('dateur_grille'    , u'dateur à grille'),
            ('dateur_laiton'    , u'dateur laiton'),
            ('dateur_fleche'    , u'dateur à fleche'),
            ('dateur_specifique', u'dateur spécifique'),
            ('pas_de_dateur'    , u'pas de dateur'),
        ], "Type de dateur")
    dateur_specifique = fields.Char("Commentaire sur dateur spécifique")
    date_peremption   = fields.Date("Date de péremption")
    qt_dans_moule     = fields.Integer("Quantité dans le moule")
    diametre_laiton   = fields.Selection([
            ('d3' , u'Ø3'),
            ('d4' , u'Ø4'),
            ('d5' , u'Ø5'),
            ('d6' , u'Ø6'),
            ('d8' , u'Ø8'),
            ('d10', u'Ø10'),
            ('d12', u'Ø12'),
        ], "Diamètre dateur laiton")
    diametre_fleche  = fields.Selection([
            ('d4' , u'Ø4'),
            ('d5' , u'Ø5'),
            ('d6' , u'Ø6'),
            ('d8' , u'Ø8'),
            ('d10', u'Ø10'),
            ('d12', u'Ø12'),
            ('d14', u'Ø14'),
            ('d16', u'Ø16'),
            ('d18', u'Ø18'),
            ('d20', u'Ø20'),
        ], "Diamètre dateur fleche")
    dateur_ids     = fields.One2many('is.mold.dateur', 'mold_id', u"Dateurs")
    dateur_ids_vsb = fields.Boolean('Dateurs vsb', store=False, compute='_compute_dateur_ids_vsb')


    _defaults = {
        'date_creation': lambda *a: fields.datetime.now(),
    }


    @api.depends('project','project.client_id','project.chef_projet_id')
    def _compute_chef_projet_id(self):
        for obj in self:
            if obj.project:
                obj.client_id      = obj.project.client_id
                obj.chef_projet_id = obj.project.chef_projet_id


    @api.depends('name')
    def _compute_dateur_ids_vsb(self):
        for obj in self:
            uid=self._uid
            user=self.env['res.users'].browse(uid)
            company=user.company_id
            vsb=False
            # if company.is_base_principale:
            #     vsb=True
            obj.dateur_ids_vsb=vsb


    def copy(self, default=None):
        if not default:
            default={}
        default["name"] = '%s (copy)'%(self.name)
        return super(is_mold, self).copy(default=default)


    def actualiser_chef_de_projet_action(self):
        for obj in self:
            if obj.project:
                if not obj.client_id:
                    obj.client_id = obj.project.client_id.id
                if not obj.chef_projet_id:
                    obj.chef_projet_id = obj.project.chef_projet_id.id


    def action_acceder_moule(self):
        for obj in self:
            return {
                'name': "Moule",
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'is.mold',
                'type': 'ir.actions.act_window',
                'res_id': obj.id,
                'domain': '[]',
            }


