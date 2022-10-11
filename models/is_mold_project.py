# -*- coding: utf-8 -*-
from odoo import models,fields,api
from odoo.tools.translate import _


class is_mold_project(models.Model):
    _name='is.mold.project'
    _description = "Projet"
    _order='name'    #Ordre de tri par defaut des listes
    _sql_constraints = [('name_uniq','UNIQUE(name)', 'Ce projet existe déjà')]


    @api.model
    def _get_group_chef_de_projet(self):
        ids = self.env.ref('is_plastigray.is_chef_projet_group').ids
        return [('groups_id','in',ids)]


    name           = fields.Char("Nom du projet",size=40,required=True, index=True)
    client_id      = fields.Many2one('res.partner', 'Client')
    chef_projet_id = fields.Many2one('res.users', 'Chef de projet',required=True)
    choix_modele   = fields.Selection([
            ('1', u'1 - Moule par défaut hors automobile'),
            ('2', u'2 - Moule par défaut automobile'),
        ], u"Choix du modèle",required=True)
    commentaire  = fields.Char("Commentaire")
    mold_ids     = fields.One2many('is.mold'    , 'project', u"Moules")
    dossierf_ids = fields.One2many('is.dossierf', 'project', u"Dossiers F")


    def copy(self, default=None):
        if not default:
            default={}
        default["name"] = '%s (copy)'%(self.name)
        return super(is_mold_project, self).copy(default=default)





