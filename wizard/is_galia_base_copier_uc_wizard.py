# -*- coding: utf-8 -*-
from odoo import api, fields, models


class IsGaliaBaseCopierUcWizard(models.TransientModel):
    _name = 'is.galia.base.copier.uc.wizard'
    _description = "Assistant de copie des étiquettes dans les UC de la base d'un site"

    galia_ids           = fields.Many2many('is.galia.base', string="Etiquettes", readonly=True)
    nb_etiquettes       = fields.Integer("Nombre d'étiquettes", compute='_compute_inter_site')
    database_origine_id = fields.Many2one('is.database', "Site des étiquettes", readonly=True)
    database_id         = fields.Many2one('is.database', "Site de destination", required=True,
        domain=[('database','!=',False),('port_server','!=',0)])
    inter_site          = fields.Boolean("Copie inter-site", compute='_compute_inter_site')


    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('active_model')=='is.galia.base':
            etiquettes = self.env['is.galia.base'].browse(self.env.context.get('active_ids') or [])
            database = etiquettes._get_database_origine()
            res['galia_ids']           = [(6,0,etiquettes.ids)]
            res['database_origine_id'] = database.id
            res['database_id']         = database.id
        return res


    @api.depends('galia_ids','database_origine_id','database_id')
    def _compute_inter_site(self):
        for obj in self:
            obj.nb_etiquettes = len(obj.galia_ids)
            obj.inter_site    = obj.database_id and obj.database_id!=obj.database_origine_id


    def action_copier(self):
        self.ensure_one()
        return self.galia_ids.copier_uc_vers_site_action(self.database_id)
