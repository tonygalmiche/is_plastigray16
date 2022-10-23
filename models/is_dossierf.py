# -*- coding: utf-8 -*-
from odoo import models,fields,api
#from odoo.tools.translate import _


class is_dossierf(models.Model):
    _name='is.dossierf'
    _description = "Dossier F"
    _order='name'
    _sql_constraints = [('name_uniq','UNIQUE(name)', u'Ce Dossier F existe déjà !')] 

    name            = fields.Char("N°Dossier",size=40,required=True, index=True)
    designation     = fields.Char("Désignation")
    project         = fields.Many2one('is.mold.project', 'Projet')
    client_id       = fields.Many2one('res.partner', 'Client'        , store=True, compute='_compute')
    chef_projet_id  = fields.Many2one('res.users'  , 'Chef de projet', store=True, compute='_compute')
    mold_ids        = fields.One2many('is.mold', 'dossierf_id', u"Moules")
    is_database_id         = fields.Many2one('is.database', "Site")
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)


#     def write(self, vals):
#         res=super(is_dossierf, self).write(vals)
#         for obj in self:
#             obj.copy_other_database_dossierf()
#         return res

#     def create(self, vals):
#         obj=super(is_dossierf, self).create(vals)
#         obj.copy_other_database_dossierf()
#         return obj
    
#     def copy_other_database_dossierf(self):
#         cr , uid, context = self.env.args
#         context = dict(context)
#         database_obj = self.env['is.database']
#         database_lines = database_obj.search([])
#         for dossierf in self:
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
#                 dossierf_vals = self.get_dossierf_vals(dossierf, DB, USERID, USERPASS, sock)
#                 ids = sock.execute(DB, USERID, USERPASS, 'is.dossierf', 'search', [('is_database_origine_id', '=', dossierf.id)], {})
#                 if not ids:
#                     ids = sock.execute(DB, USERID, USERPASS, 'is.dossierf', 'search', [('name', '=', dossierf.name)], {})
#                 if ids:
#                     sock.execute(DB, USERID, USERPASS, 'is.dossierf', 'write', ids, dossierf_vals, {})
#                     created_id = ids[0]
#                 else:
#                     created_id = sock.execute(DB, USERID, USERPASS, 'is.dossierf', 'create', dossierf_vals, {})
#         return True
    
    
#     def get_dossierf_vals(self, dossierf, DB, USERID, USERPASS, sock):
#         dossierf_vals = {
#             'name': dossierf.name,
#             'designation':dossierf.designation,
#             'project':self._get_project(dossierf, DB, USERID, USERPASS, sock),
#             'mold_ids': self._get_mold_ids(dossierf, DB, USERID, USERPASS, sock),
#             'is_database_origine_id':dossierf.id,
#             'is_database_id':self._get_is_database_id(dossierf, DB, USERID, USERPASS, sock),
#         }
#         return dossierf_vals
    
#     def _get_project(self, dossierf, DB, USERID, USERPASS, sock):
#         if dossierf.project:
#             project_ids = sock.execute(DB, USERID, USERPASS, 'is.mold.project', 'search', [('is_database_origine_id', '=', dossierf.project.id)], {})
#             if not project_ids:
#                 dossierf.project.copy_other_database_project()
#                 project_ids = sock.execute(DB, USERID, USERPASS, 'is.mold.project', 'search', [('is_database_origine_id', '=', dossierf.project.id)], {})
#             if project_ids:
#                 return project_ids[0]
#         return False
    
#     def _get_mold_ids(self, dossierf, DB, USERID, USERPASS, sock):
#         list_mold_ids =[]
#         for mold in dossierf.mold_ids:
#             dest_mold_ids = sock.execute(DB, USERID, USERPASS, 'is.mold', 'search', [('is_database_origine_id', '=', mold.id)], {})
#             if dest_mold_ids:
#                 list_mold_ids.append(dest_mold_ids[0])
        
#         return [(6, 0, list_mold_ids)]


#     def _get_is_database_id(self, dossierf, DB, USERID, USERPASS, sock):
#         if dossierf.is_database_id:
#             ids = sock.execute(DB, USERID, USERPASS, 'is.database', 'search', [('is_database_origine_id', '=', dossierf.is_database_id.id)], {})
#             if ids:
#                 return ids[0]
#         return False




    @api.depends('project','project.client_id','project.chef_projet_id')
    def _compute(self):
        for obj in self:
            if obj.project:
                obj.client_id      = obj.project.client_id
                obj.chef_projet_id = obj.project.chef_projet_id


    def copy(self, cr, uid, id, default=None, context=None):
        if not context:
            context = {}
        mold = self.read(cr, uid, id, ['name'], context=context)
        default.update({
            'name': mold['name'] + _(' (copy)'),
        })
        return super(is_dossierf, self).copy(cr, uid, id, default=default, context=context)


    def action_acceder_dossierf(self):
        for obj in self:
            return {
                'name': "Dossier F",
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'is.dossierf',
                'type': 'ir.actions.act_window',
                'res_id': obj.id,
                'domain': '[]',
            }

