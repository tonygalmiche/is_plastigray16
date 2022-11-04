# -*- coding: utf-8 -*-
from odoo import models,fields,api, SUPERUSER_ID


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


    # def _login(self, db, login, password):
    #     """Permet d'ajouter l'adresse IP de la personne qui se connecte
    #     cela est utilise par les programmes externes"""
    #     user_id = super(res_users, self)._login(db, login, password)
    #     if request:
    #         ip=request.httprequest.environ.get('REMOTE_ADDR',False)
    #         if ip:
    #             cr = self.pool.cursor()
    #             cr.autocommit(True)
    #             if user_id and ip:
    #                 SQL="""
    #                     INSERT INTO is_res_users (user_id, heure_connexion, adresse_ip)
    #                     VALUES ("""+str(user_id)+""", now() at time zone 'UTC', '"""+str(ip)+"""')
    #                 """
    #                 res=cr.execute(SQL)
    #                 #res=cr.execute("UPDATE res_users SET is_adresse_ip='"+str(ip)+"' WHERE id="+str(user_id))
    #                 cr.close()
    #     return user_id


    # def get_site_ids(self):
    #     ids=[]
    #     for site in self.is_site_ids:
    #         ids.append(site.id)
    #     return ids


class res_groups(models.Model):
    _inherit = "res.groups"
    _order='category_id,name'

    active = fields.Boolean('Actif', default=True)
