# -*- coding: utf-8 -*-
from odoo import models,fields,api
from odoo.exceptions import ValidationError


class is_mold_project(models.Model):
    _name='is.mold.project'
    _description = "Projet"
    _order='name'    #Ordre de tri par defaut des listes
    _sql_constraints = [('name_uniq','UNIQUE(name)', 'Ce projet existe déjà')]

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
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)

    def write(self, vals):
        res=super().write(vals)
        for obj in self:
            self.env['is.database'].copy_other_database(obj)
        return res
            
    @api.model_create_multi
    def create(self, vals_list):
        res=super().create(vals_list)
        self.env['is.database'].copy_other_database(res)
        return res

    def get_copy_other_database_vals(self, DB, USERID, USERPASS, sock):
        vals ={
            'name'                  : self.name,
            'client_id'             : self._get_client_id(DB, USERID, USERPASS, sock),
            'chef_projet_id'        : self._get_chef_projet_id(DB, USERID, USERPASS, sock),
            'choix_modele'          : self.choix_modele,
            'mold_ids'              : self._get_mold_ids(DB, USERID, USERPASS, sock),
            'commentaire'           : self.commentaire,
            'is_database_origine_id': self.id,
        }
        return vals

    def _get_client_id(self, DB, USERID, USERPASS, sock):
        if self.client_id:
            ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', self.client_id.id),'|',('active','=',True),('active','=',False)])
            if ids:
                return ids[0]
        return False
        
    def _get_chef_projet_id(self, DB, USERID, USERPASS, sock):
        if self.chef_projet_id:
            ids = sock.execute(DB, USERID, USERPASS, 'res.users', 'search', [('login', '=', self.chef_projet_id.login)])
            if ids:
                return ids[0]
            else:
                raise ValidationError('Chef de projet non trouvé (login=%s) dans %s !'%(self.chef_projet_id.login,DB))
        return False
    
    def _get_mold_ids(self, DB, USERID, USERPASS, sock):
        list_mold_ids =[]
        for mold in self.mold_ids:
            ids = sock.execute(DB, USERID, USERPASS, 'is.mold', 'search', [('is_database_origine_id', '=', mold.id)])
            if ids:
                list_mold_ids.append(ids[0])
        
        return [(6, 0, list_mold_ids)]
        
    @api.model
    def _get_group_chef_de_projet(self):
        ids = self.env.ref('is_plastigray16.is_chef_projet_group').ids
        return [('groups_id','in',ids)]


    def copy(self, default=None):
        if not default:
            default={}
        default["name"] = '%s (copy)'%(self.name)
        return super(is_mold_project, self).copy(default=default)




