# -*- coding: utf-8 -*-
from odoo import models,fields,api

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
            'designation'           : self.designation,
            'project'               : self._get_project(DB, USERID, USERPASS, sock),
            'mold_ids'              : self._get_mold_ids(DB, USERID, USERPASS, sock),
            'is_database_id'        : self._get_is_database_id(DB, USERID, USERPASS, sock),
            'is_database_origine_id': self.id,
        }
        return vals
    
    def _get_project(self, DB, USERID, USERPASS, sock):
        if self.project:
            ids = sock.execute(DB, USERID, USERPASS, 'is.mold.project', 'search', [('is_database_origine_id', '=', self.project.id)])
            if not ids:
                self.project.copy_other_database_project()
                ids = sock.execute(DB, USERID, USERPASS, 'is.mold.project', 'search', [('is_database_origine_id', '=', self.project.id)])
            if ids:
                return ids[0]
        return False
    
    def _get_mold_ids(self, DB, USERID, USERPASS, sock):
        mold_ids =[]
        for mold in self.mold_ids:
            ids = sock.execute(DB, USERID, USERPASS, 'is.mold', 'search', [('is_database_origine_id', '=', mold.id)])
            if ids:
                mold_ids.append(ids[0])
        return [(6, 0, mold_ids)]

    def _get_is_database_id(self, DB, USERID, USERPASS, sock):
        if self.is_database_id:
            ids = sock.execute(DB, USERID, USERPASS, 'is.database', 'search', [('is_database_origine_id', '=', self.is_database_id.id)])
            if ids:
                return ids[0]
        return False

    @api.depends('project','project.client_id','project.chef_projet_id')
    def _compute(self):
        for obj in self:
            if obj.project:
                obj.client_id      = obj.project.client_id
                obj.chef_projet_id = obj.project.chef_projet_id

    def copy(self, default=None):
        if not default:
            default={}
        default["name"] = '%s (copy)'%(self.name)
        return super(is_dossierf, self).copy(default=default)

    def action_acceder_dossierf(self):
        for obj in self:
            return {
                'name': "Dossier F",
                'view_mode': 'form',
                'res_model': 'is.dossierf',
                'type': 'ir.actions.act_window',
                'res_id': obj.id,
                'domain': '[]',
            }

