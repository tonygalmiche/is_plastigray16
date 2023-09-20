# -*- coding: utf-8 -*-
from odoo import models,fields,api, SUPERUSER_ID
from odoo.http import request
from datetime import datetime


class is_res_users(models.Model):
    _name = 'is.res.users'
    _description="is_res_users"
    _order= 'heure_connexion desc'

    user_id         = fields.Many2one('res.users', 'Utilisateur', index=True)
    heure_connexion = fields.Datetime('Heure de connexion'      , index=True)
    adresse_ip      = fields.Char('Adresse IP'                  , index=True)


class is_service(models.Model):
    _name = 'is.service'
    _description = "Service"
    
    name        = fields.Char('Service', required=True)


class res_users(models.Model):
    _inherit = "res.users"

    is_site_id    = fields.Many2one("is.database", "Site de production", help=u"Ce champ est utilisé en particulier pour la gestion des OT dans odoo0")
    is_site_ids   = fields.Many2many('is.database','res_users_site_rel','user_id','site_id', string=u"Sites autorisés")
    is_service_id = fields.Many2one('is.service', 'Service')
    is_adresse_ip = fields.Char('Adresse IP', help='Adresse IP de cet utilisateur pour lui donner des accès spcécifiques dans THEIA')
    is_signature  = fields.Binary("Signature", help="Utilisé pour imprimer les certificats matière fournisseur")


    def update_group(self):
        for data in self:
            principale_grp_id = self.env.ref('is_plastigray16.is_base_principale_grp')
            secondaire_grp_id = self.env.ref('is_plastigray16.is_base_secondaire_grp')
            if data.company_id.is_base_principale:
                principale_grp_id.write({'users': [(4, data.id)]})
                secondaire_grp_id.write({'users': [(5, data.id)]})
            else:
                secondaire_grp_id.write({'users': [(4, data.id)]})
                principale_grp_id.write({'users': [(5, data.id)]})
        return True


    @api.model_create_multi
    def create(self, vals_list):
        res=super().create(vals_list)
        res.update_group()
        return res


    @classmethod
    def _login(cls, db, login, password, user_agent_env):
        "Permet d'ajouter l'adresse IP de la personne qui se connecte cela est utilise par les programmes externes"
        user_id = super()._login(db, login, password, user_agent_env)
        try:
            ip = request.httprequest.environ['REMOTE_ADDR']
        except:
            ip = False
        with cls.pool.cursor() as cr:
            self = api.Environment(cr, SUPERUSER_ID, {})[cls._name]
            vals={
                'user_id'        : user_id,
                'heure_connexion': datetime.now(),
                'adresse_ip'     : ip,
            }
            res=self.env['is.res.users'].create(vals)
        return user_id


    def get_site_ids(self):
        ids=[]
        for site in self.is_site_ids:
            ids.append(site.id)
        return ids


class res_groups(models.Model):
    _inherit = "res.groups"
    _order='category_id,name'

    active = fields.Boolean('Actif', default=True)
