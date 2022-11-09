# -*- coding: utf-8 -*-
from odoo import models,fields,api,tools,SUPERUSER_ID
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta


class is_piece_montabilite(models.Model):
    _name='is.piece.montabilite'
    _description="Pièce de montabilité"
    _rec_name = 'code_pg'
    _sql_constraints = [('code_pg_uniq','UNIQUE(code_pg)', u'Ce code existe déjà')]
    
    @api.depends('moule_ids')
    def compute_client_id(self):
        for rec in self:
            client_id = False
            for moule in rec.moule_ids:
                if moule.client_id:
                    client_id = moule.client_id.id
                    break;
            rec.client_id = client_id
    
    @api.depends('controle_ids','periodicite')
    def _compute_date_prochain_controle(self):
        for rec in self:
            v=self.env['is.historique.controle'].date_prochain_controle(rec)
            rec.date_prochain_controle = v

    code_pg                = fields.Char("Code PG", required=True)
    designation            = fields.Char("Désignation")
    fabriquant             = fields.Selection([('client','Client'),
                                   ('plastigray','Plastigray'),
                                   ('autre','Autre')
                                   ], string="Fabricant")
    fabricant_client_id    = fields.Many2one('res.partner', string='Fabricant (Client)', domain=[('supplier','=',True),('is_company','=',True)])
    fabriquant_mold_id     = fields.Many2one('is.mold', string='Fabricant (Moule)')
    fabriquant_autre       = fields.Char("Fabricant (Autre)")
    date_reception         = fields.Date("Date de réception")
    moule_ids              = fields.Many2many('is.mold','is_piece_montabilite_id', 'is_mold_id_piece_mont', string='Moules affectés')
    client_id              = fields.Many2one('res.partner', string='Client', compute="compute_client_id", store=True)
    site_id                = fields.Many2one('is.database', string='Site')
    lieu_stockage          = fields.Char("Lieu de stockage")
    periodicite            = fields.Selection([
                                    ('24','24 mois (standard)'),
                                    ('48','48 mois ( qté annuelle < 10000p)'),
                                ], string="Périodicité ( en mois )")

    type_controle          = fields.Many2one('is.type.controle.gabarit', string='Type de contrôle')
    date_prochain_controle = fields.Date("Date prochain contrôle", compute='_compute_date_prochain_controle', readonly=True, store=True)
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    active                 = fields.Boolean('Active', default=True)
    controle_ids           = fields.One2many('is.historique.controle', 'piece_id', string='Historique des contrôles')

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
            'fabricant_client_id'   : self._get_fabricant_client_id(DB, USERID, USERPASS, sock),
            'fabriquant_mold_id'    : self._get_fabriquant_mold_id(DB, USERID, USERPASS, sock),
            'fabriquant_autre'      : self.fabriquant_autre,
            'date_reception'        : self.date_reception,
            'moule_ids'             : self._get_moule_ids(DB, USERID, USERPASS, sock),
            'client_id'             : self._get_client_id(DB, USERID, USERPASS, sock),
            'site_id'               : self._get_site_id(DB, USERID, USERPASS, sock),
            'lieu_stockage'         : self.lieu_stockage,
            'periodicite'           : self.periodicite,
            'type_controle'         : self._get_type_controle(DB, USERID, USERPASS, sock),
            'active'                : self.site_id and self.site_id.database == DB and True or False,
            'is_database_origine_id': self.id,
        }
        return vals

    def _get_fabricant_client_id(self, DB, USERID, USERPASS, sock):
        if self.fabricant_client_id:
            ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', self.fabricant_client_id.id)])
            if ids:
                return ids[0]
        return False
    
    def _get_fabriquant_mold_id(self, DB, USERID, USERPASS, sock):
        if self.fabriquant_mold_id:
            ids = sock.execute(DB, USERID, USERPASS, 'is.mold', 'search', [('is_database_origine_id', '=', self.fabriquant_mold_id.id)])
            if not ids:
                self.env['is.database'].copy_other_database(self.fabriquant_mold_id)
                ids = sock.execute(DB, USERID, USERPASS, 'is.mold', 'search', [('is_database_origine_id', '=', self.fabriquant_mold_id.id)])
            if ids:
                return ids[0]
        return False
    
    def _get_moule_ids(self, DB, USERID, USERPASS, sock):
        lst_moule_ids = []
        for moule in self.moule_ids:
            ids = sock.execute(DB, USERID, USERPASS, 'is.mold', 'search', [('is_database_origine_id', '=', moule.id)])
            if ids:
                lst_moule_ids.append(ids[0])
        return [(6,0,lst_moule_ids)]
   
    def _get_client_id(self, DB, USERID, USERPASS, sock):
        if self.client_id:
            ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', self.client_id.id)])
            if ids:
                return ids[0]
        return False

    def _get_site_id(self,  DB, USERID, USERPASS, sock):
        if self.site_id:
            ids = sock.execute(DB, USERID, USERPASS, 'is.database', 'search', [('is_database_origine_id', '=', self.site_id.id)])
            if ids:
                return ids[0]
        return False

    def _get_type_controle(self,  DB, USERID, USERPASS, sock):
        if self.type_controle:
            ids = sock.execute(DB, USERID, USERPASS, 'is.type.controle.gabarit', 'search', [('is_database_origine_id', '=', self.type_controle.id)])
            if not ids:
                self.env['is.database'].copy_other_database(self.type_controle)
                ids = sock.execute(DB, USERID, USERPASS, 'is.type.controle.gabarit', 'search', [('is_database_origine_id', '=', self.type_controle.id)])
            if ids:
                return ids[0]
        return False



