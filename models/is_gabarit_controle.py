# -*- coding: utf-8 -*-
from odoo import models,fields,api,tools,SUPERUSER_ID
from datetime import datetime
from dateutil.relativedelta import relativedelta
#from is_outillage import date_prochain_controle


class is_gabarit_controle(models.Model):
    _name='is.gabarit.controle'
    _description="Gabarit de contrôle"
    _order='code_pg'
    _rec_name='code_pg'
    _sql_constraints = [('code_pg_uniq','UNIQUE(code_pg)', u'Ce code existe déjà')]
    
    @api.depends('controle_ids','periodicite')
    def _compute_date_prochain_controle(self):
        for rec in self:
            v=self.env['is.historique.controle'].date_prochain_controle(rec)
            rec.date_prochain_controle = v

    code_pg                = fields.Char("Code PG"    , required=True)
    designation            = fields.Char("Désignation", required=True)
    fabriquant             = fields.Char("Fabricant")
    date_reception         = fields.Date("Date de réception")
    reference_plan         = fields.Char("Référence plan")
    indice_plan            = fields.Char("Indice plan")
    moule_ids              = fields.Many2many('is.mold'    ,'is_gabarit_mold_rel'    ,'gabarit_id','mold_id'    , string="Moules affectés")
    dossierf_ids           = fields.Many2many('is.dossierf','is_gabarit_dossierf_rel','gabarit_id','dossierf_id', string="Dossiers F affectés")
    client_id              = fields.Many2one("res.partner","Client")
    site_id                = fields.Many2one('is.database', string='Site')
    lieu_stockage          = fields.Char("Lieu de stockage")
    periodicite            = fields.Selection([
                                    ('24','24 mois (standard)'),
                                    ('48','48 mois ( qté annuelle < 10000p)'),
                                ], string="Périodicité ( en mois )")
    type_controle          = fields.Many2one("is.type.controle.gabarit","Type de contrôle")
    date_prochain_controle = fields.Date("Date prochain contrôle", compute='_compute_date_prochain_controle', readonly=True, store=True)
    controle_ids           = fields.One2many('is.historique.controle', 'gabarit_id', string='Historique des contrôles')
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    active                 = fields.Boolean('Active', default=True)

    def write(self, vals):
        res=super().write(vals)
        for obj in self:
            filtre=[('code_pg', '=', obj.code_pg),'|',('active','=',True),('active','=',False)]
            self.env['is.database'].copy_other_database(obj,filtre)
        return res
            
    @api.model_create_multi
    def create(self, vals_list):
        res=super().create(vals_list)
        filtre=[('code_pg', '=', res.code_pg)]
        filtre=[('code_pg', '=', res.code_pg),'|',('active','=',True),('active','=',False)]
        self.env['is.database'].copy_other_database(res,filtre)
        return res

    def get_copy_other_database_vals(self, DB, USERID, USERPASS, sock):
        vals ={
            'code_pg'               : self.code_pg,
            'designation'           : self.designation,
            'fabriquant'            : self.fabriquant,
            'date_reception'        : self.date_reception,
            'reference_plan'        : self.reference_plan,
            'indice_plan'           : self.indice_plan,
            'moule_ids'             : self._get_moule_ids(DB, USERID, USERPASS, sock),
            'dossierf_ids'          : self._get_dossierf_ids(DB, USERID, USERPASS, sock),
            'client_id'             : self._get_client_id(DB, USERID, USERPASS, sock),
            'site_id'               : self._get_site_id(DB, USERID, USERPASS, sock),
            'lieu_stockage'         : self.lieu_stockage,
            'periodicite'           : self.periodicite,
            'type_controle'         : self._get_type_controle(DB, USERID, USERPASS, sock),
            'active'                : self.site_id and self.site_id.database == DB and True or False,
            'is_database_origine_id': self.id,
        }
        return vals


    def _get_moule_ids(self, DB, USERID, USERPASS, sock):
        lst_moule_ids = []
        for moule in self.moule_ids:
            ids = sock.execute(DB, USERID, USERPASS, 'is.mold', 'search', [('is_database_origine_id', '=', moule.id)])
            if ids:
                lst_moule_ids.append(ids[0])
        return [(6,0,lst_moule_ids)]

    def _get_dossierf_ids(self, DB, USERID, USERPASS, sock):
        ids = []
        for obj in self.dossierf_ids:
            res = sock.execute(DB, USERID, USERPASS, 'is.dossierf', 'search', [('is_database_origine_id', '=', obj.id)])
            if res:
                ids.append(res[0])
        return [(6,0,ids)]
   
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

    def _get_fournisseur_id(self, DB, USERID, USERPASS, sock):
        if self.fournisseur_id:
            ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', self.fournisseur_id.id)])
            if ids:
                return ids[0]
        return False
    
        
class is_emplacement_outillage(models.Model):
    _name = "is.emplacement.outillage"
    _description="Emplacement Outillage"
    
    name = fields.Char("Name")
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
            'is_database_origine_id': self.id
        }
        return vals


class is_type_controle_gabarit(models.Model):
    _name = "is.type.controle.gabarit"
    _description="Type contrôle Gabarit"
    
    name = fields.Char("Name")    
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
            'is_database_origine_id': self.id
        }
        return vals
