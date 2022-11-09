# -*- coding: utf-8 -*-
from odoo import models,fields,api,tools,SUPERUSER_ID
from datetime import datetime
from dateutil.relativedelta import relativedelta
#from is_outillage import date_prochain_controle


class is_plaquette_etalon(models.Model):
    _name='is.plaquette.etalon'
    _description="Plaquette étalon"
    _order='code_pg'
    _rec_name='code_pg'
    _sql_constraints = [('code_pg_uniq','UNIQUE(code_pg)', u'Ce code existe déjà')]

    code_pg                = fields.Char("Code PG", required=True)
    designation            = fields.Char("Désignation", required=True)
    fabriquant             = fields.Char("Fabricant")
    date_reception         = fields.Date("Date de réception")
    site_id                = fields.Many2one("is.database", "Site")
    lieu_stockage          = fields.Char("Lieu de stockage")
    periodicite            = fields.Integer("Périodicité (en mois)")
    type_controle          = fields.Selection([('colorimetre','colorimètre'),('visuel','visuel')],string="Type de contrôle")
    date_prochain_controle = fields.Date("Date prochain contrôle", compute='_compute_date_prochain_controle', readonly=True, store=True)
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    active                 = fields.Boolean('Active', default=True)
    controle_ids           = fields.One2many('is.historique.controle', 'plaquette_id', string='Historique des contrôles')


    @api.depends('controle_ids','periodicite')
    def _compute_date_prochain_controle(self):
        for rec in self:
            v=self.env['is.historique.controle'].date_prochain_controle(rec)
            rec.date_prochain_controle = v

    def write(self, vals):
        res=super().write(vals)
        for obj in self:
            filtre=[('code_pg', '=', obj.code_pg),'|',('active','=',True),('active','=',False)]
            self.env['is.database'].copy_other_database(obj,filtre)
        return res
            
    @api.model_create_multi
    def create(self, vals_list):
        res=super().create(vals_list)
        filtre=[('code_pg', '=', res.code_pg),'|',('active','=',True),('active','=',False)]
        self.env['is.database'].copy_other_database(res,filtre)
        return res

    def get_copy_other_database_vals(self, DB, USERID, USERPASS, sock):
        vals ={
            'code_pg'               : self.code_pg,
            'designation'           : self.designation,
            'fabriquant'            : self.fabriquant,
            'date_reception'        : self.date_reception,
            'lieu_stockage'         : self.lieu_stockage,
            'periodicite'           : self.periodicite,
            'type_controle'         : self.type_controle,
            'site_id'               : self._get_site_id(DB, USERID, USERPASS, sock),
            'active'                : self.site_id and self.site_id.database == DB and True or False,
            'is_database_origine_id': self.id,
        }
        return vals

    def _get_site_id(self, DB, USERID, USERPASS, sock):
        if self.site_id:
            ids = sock.execute(DB, USERID, USERPASS, 'is.database', 'search', [('is_database_origine_id', '=', self.site_id.id)])
            if ids:
                return ids[0]
        return False
