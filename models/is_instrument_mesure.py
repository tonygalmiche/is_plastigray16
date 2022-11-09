# -*- coding: utf-8 -*-

from odoo import models, fields, api,tools,SUPERUSER_ID
from datetime import datetime
from dateutil.relativedelta import relativedelta
#from is_outillage import date_prochain_controle


class is_instrument_mesure(models.Model):
    _name = 'is.instrument.mesure'
    _description="Instrument de mesure"
    _order = 'code_pg'
    _rec_name='code_pg'
    _sql_constraints = [('code_pg_uniq','UNIQUE(code_pg)', u'Ce code existe déjà')]

    @api.depends('famille_id', 'frequence')
    def _compute_periodicite(self):
        for obj in self:
            periodicite=False
            if obj.frequence=='intensive':
                periodicite=obj.famille_id.intensive
            if obj.frequence=='moyenne':
                periodicite=obj.famille_id.moyenne
            if obj.frequence=='faible':
                periodicite=obj.famille_id.faible
            obj.periodicite=periodicite


    @api.depends()
    def _check_base_db(self):
        for obj in self:
            v=False
            user_data = self.env['res.users'].browse(self._uid)
            if user_data and user_data.company_id.is_base_principale:
                v=True
            obj.is_base_check = v


    code_pg            = fields.Char("Code PG", required=True)
    designation        = fields.Char("Désignation",required=True)
    famille_id         = fields.Many2one("is.famille.instrument", "Famille", required=True)
    fabriquant         = fields.Char("Fabricant")
    num_serie          = fields.Char("N° de série")
    date_reception     = fields.Date("Date de réception")
    type               = fields.Char("Type")
    etendue            = fields.Char("Etendue")
    resolution         = fields.Char("Résolution")
    type_boolean       = fields.Boolean('Is Type?', default=False)
    etendue_boolean    = fields.Boolean('Is Etendue?', default=False)
    resolution_boolean = fields.Boolean('Is Résolution?', default=False)
    emt                = fields.Char("EMT")
    site_id            = fields.Many2one("is.database", "Site", required=True)
    lieu_stockage      = fields.Char("Lieu de stockage")
    service_affecte    = fields.Char("Personne/Service auquel est affecté l'instrument")
    frequence = fields.Selection([
        ('intensive', 'utilisation quotidienne'), 
        ('moyenne', 'utilisation plusieurs jours par semaine'),
        ('faible', 'utilisation 1 fois par semaine ou moins')
    ], "Fréquence", required=True)
    periodicite            = fields.Char("Périodicité", store=True, compute='_compute_periodicite')
    date_prochain_controle = fields.Date("Date prochain contrôle", compute='_compute_date_prochain_controle', readonly=True, store=True)
    controle_ids           = fields.One2many('is.historique.controle', 'instrument_id', string='Historique des contrôles')
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    active                 = fields.Boolean('Active', default=True)
    is_base_check          = fields.Boolean(string="Is Base", compute="_check_base_db")

    
    @api.depends('controle_ids','periodicite')
    def _compute_date_prochain_controle(self):
        for rec in self:
            v=self.env['is.historique.controle'].date_prochain_controle(rec)
            rec.date_prochain_controle = v


    @api.onchange('famille_id')
    def onchange_famille_id(self):
        self.type_boolean = self.famille_id.afficher_type
        self.etendue_boolean = self.famille_id.afficher_type
        self.resolution_boolean = self.famille_id.afficher_type
        #self.classe_boolean = self.famille_id.afficher_classe
        

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
            'famille_id'            : self._get_famille_id(DB, USERID, USERPASS, sock),
            'fabriquant'            : self.fabriquant,
            'num_serie'             : self.num_serie,
            'date_reception'        : self.date_reception,
            'type'                  : self.type,
            'etendue'               : self.etendue,
            'resolution'            : self.resolution,
            'type_boolean'          : self.type_boolean,
            'etendue_boolean'       : self.etendue_boolean,
            'resolution_boolean'    : self.resolution_boolean,
            'lieu_stockage'         : self.lieu_stockage,
            'service_affecte'       : self.service_affecte,
            'frequence'             : self.frequence,
            'periodicite'           : self.periodicite,
            'emt'                   : self.emt,
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


    def _get_famille_id(self, DB, USERID, USERPASS, sock):
        if self.famille_id:
            ids = sock.execute(DB, USERID, USERPASS, 'is.famille.instrument', 'search', [('is_database_origine_id', '=', self.famille_id.id)])
            if not ids:
                self.env['is.database'].copy_other_database(self.famille_id)
                ids = sock.execute(DB, USERID, USERPASS, 'is.famille.instrument', 'search', [('is_database_origine_id', '=', self.famille_id.id)])
            if ids:
                return ids[0]
        return False

        
class is_famille_instrument(models.Model):
    _name = 'is.famille.instrument'
    _description="Famille d'instrument"
    
    name = fields.Char("Nom de la famille", required=True)
    intensive = fields.Char("INTENSIVE (fréquence f >= 1 fois / jour) en mois ou méthode OPPERET")
    moyenne = fields.Char("MOYENNE ( 1fois / 5 jours < f < 1fois / jour ) en mois ou méthode OPPERET")
    faible = fields.Char("FAIBLE (f <=1fois / 5 jours) en mois ou méthode OPPERET")
    tolerance = fields.Char("Tolérance")
    afficher_classe = fields.Boolean("Afficher le champ Classe", default=False)
    afficher_type = fields.Boolean("Afficher les champs Type, Etendue et Résolution", default=False)
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    

    # def write(self, vals):
    #     try:
    #         res=super(is_famille_instrument, self).write(vals)
    #         for obj in self:
    #             obj.copy_other_database_famille_instrument()
    #         return res
    #     except Exception as e:
    #         raise osv.except_osv(_('Instrument!'),
    #                          _('(%s).') % str(e).decode('utf-8'))


    # def create(self, vals):
    #     try:
    #         obj=super(is_famille_instrument, self).create(vals)
    #         obj.copy_other_database_famille_instrument()
    #         return obj
    #     except Exception as e:
    #         raise osv.except_osv(_('Instrument!'),
    #                          _('(%s).') % str(e).decode('utf-8'))
            

    def copy_other_database_famille_instrument(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for instrument in self:
            for database in database_lines:
                if not database.ip_server or not database.database or not database.port_server or not database.login or not database.password:
                    continue
                DB = database.database
                USERID = SUPERUSER_ID
                DBLOGIN = database.login
                USERPASS = database.password
                DB_SERVER = database.ip_server
                DB_PORT = database.port_server
                sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object' % (DB_SERVER, DB_PORT))
                famille_instrument_vals = self.get_famille_instrument_vals(instrument, DB, USERID, USERPASS, sock)
                dest_famille_instrument_ids = sock.execute(DB, USERID, USERPASS, 'is.famille.instrument', 'search', [('is_database_origine_id', '=', instrument.id)], {})
                if not dest_famille_instrument_ids:
                    dest_famille_instrument_ids = sock.execute(DB, USERID, USERPASS, 'is.famille.instrument', 'search', [('name', '=', instrument.name)], {})
                if dest_famille_instrument_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.famille.instrument', 'write', dest_famille_instrument_ids, famille_instrument_vals, {})
                    famille_instrument_created_id = dest_famille_instrument_ids[0]
                else:
                    famille_instrument_created_id = sock.execute(DB, USERID, USERPASS, 'is.famille.instrument', 'create', famille_instrument_vals, {})
        return True


    def get_famille_instrument_vals(self, instrument, DB, USERID, USERPASS, sock):
        famille_instrument_vals ={
                     'name' : tools.ustr(instrument.name or ''),
                     'intensive': tools.ustr(instrument.intensive or ''),
                     'moyenne': tools.ustr(instrument.moyenne or ''),
                     'faible': tools.ustr(instrument.faible or ''),
                     'tolerance': tools.ustr(instrument.tolerance or ''),
                     'afficher_classe':instrument.afficher_classe,
                     'afficher_type':instrument.afficher_type,
                     'is_database_origine_id':instrument.id,
                     }
        return famille_instrument_vals
    