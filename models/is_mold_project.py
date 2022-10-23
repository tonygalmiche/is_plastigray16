# -*- coding: utf-8 -*-
from odoo import models,fields,api
from odoo.tools.translate import _


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


#     def write(self, vals):
#         try:
#             res=super(is_mold_project, self).write(vals)
#             for obj in self:
#                 obj.copy_other_database_project()
#             return res
#         except Exception as e:
#             raise osv.except_osv(_('Project!'),
#                              _('(%s).') % str(e).decode('utf-8'))

#     def create(self, vals):
#         try:
#             obj=super(is_mold_project, self).create(vals)
#             obj.copy_other_database_project()
#             return obj
#         except Exception as e:
#             raise osv.except_osv(_('Project!'),
#                              _('(%s).') % str(e).decode('utf-8'))
    
#     def copy_other_database_project(self):
#         cr , uid, context = self.env.args
#         context = dict(context)
#         project_obj = self.env['is.mold.project']
#         database_obj = self.env['is.database']
#         database_lines = database_obj.search([])
#         for project in self:
#             for database in database_lines:
#                 if not database.ip_server or not database.database or not database.port_server or not database.login or not database.password:
#                     continue
#                 DB = database.database
#                 USERID = SUPERUSER_ID
#                 DBLOGIN = database.login
#                 USERPASS = database.password
#                 DB_SERVER = database.ip_server
#                 DB_PORT = database.port_server
#                 sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object' % (DB_SERVER, DB_PORT))
#                 project_vals = self.get_project_vals(project, DB, USERID, USERPASS, sock)
#                 ids = sock.execute(DB, USERID, USERPASS, 'is.mold.project', 'search', [('is_database_origine_id', '=', project.id)], {})
#                 if not ids:
#                     ids = sock.execute(DB, USERID, USERPASS, 'is.mold.project', 'search', [('name', '=', project.name)], {})
#                 if ids:
#                     sock.execute(DB, USERID, USERPASS, 'is.mold.project', 'write', ids, project_vals, {})
#                     created_id = ids[0]
#                 else:
#                     created_id = sock.execute(DB, USERID, USERPASS, 'is.mold.project', 'create', project_vals, {})
#         return True


#     def get_project_vals(self, project, DB, USERID, USERPASS, sock):
#         project_vals = {
#             'name': project.name,
#             'client_id'             : self._get_client_id(project, DB, USERID, USERPASS, sock),
#             'chef_projet_id'        : self._get_chef_projet_id(project, DB, USERID, USERPASS, sock),
#             'choix_modele'          : project.choix_modele,
#             'mold_ids'              : self._get_mold_ids(project, DB, USERID, USERPASS, sock),
#             'is_database_origine_id': project.id,
#             'commentaire'           : project.commentaire,
#         }
#         return project_vals

#     def _get_client_id(self, project, DB, USERID, USERPASS, sock):
#         if project.client_id:
#             client_ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', project.client_id.id),'|',('active','=',True),('active','=',False)], {})
#             if client_ids:
#                 return client_ids[0]
#         return False
        
#     def _get_chef_projet_id(self, project, DB, USERID, USERPASS, sock):
#         if project.chef_projet_id:
#             chef_projet_ids = sock.execute(DB, USERID, USERPASS, 'res.users', 'search', [('login', '=', project.chef_projet_id.login)], {})
#             if chef_projet_ids:
#                 return chef_projet_ids[0]
#         return False
    
#     def _get_mold_ids(self, project, DB, USERID, USERPASS, sock):
#         list_mold_ids =[]
#         for mold in project.mold_ids:
#             dest_mold_ids = sock.execute(DB, USERID, USERPASS, 'is.mold', 'search', [('is_database_origine_id', '=', mold.id)], {})
#             if dest_mold_ids:
#                 list_mold_ids.append(dest_mold_ids[0])
        
#         return [(6, 0, list_mold_ids)]
        


    @api.model
    def _get_group_chef_de_projet(self):
        ids = self.env.ref('is_plastigray.is_chef_projet_group').ids
        return [('groups_id','in',ids)]


    def copy(self, default=None):
        if not default:
            default={}
        default["name"] = '%s (copy)'%(self.name)
        return super(is_mold_project, self).copy(default=default)





