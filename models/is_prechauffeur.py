# -*- coding: utf-8 -*-

from odoo import models,fields,api


class is_prechauffeur(models.Model):
    _name='is.prechauffeur'
    _description="Préchauffeur"
    _sql_constraints = [('name_uniq','UNIQUE(name)', u'Ce code existe déjà')]

    name              = fields.Char(string='N° du préchauffeur')
    site_id           = fields.Many2one('is.database', string='Site')
    presse_id         = fields.Many2one('is.presse', string='Affectation sur le site')
    moule_ids         = fields.Many2many('is.mold','is_prechauffeur_mold_rel','prechauffeur_id','mold_id', string="Moules affectés")
    constructeur      = fields.Char(string='Constructeur')
    marque            = fields.Char(string='Marque')
    type_prechauffeur = fields.Char(string='Type')
    num_serie         = fields.Char(string='N° de série')
    date_fabrication  = fields.Date(string='Date de fabrication')
    poids             = fields.Integer(string='Poids (Kg)')
    longueur          = fields.Integer(string='Longueur en mm')
    largeur           = fields.Integer(string='Largeur en mm')
    hauteur           = fields.Integer(string='Hauteur en mm')
    type_fluide       = fields.Selection([
        ('eau','Eau'),
        ('huile','Huile')], string='Type de fluide')
    temperature_maxi          = fields.Integer(string='Température maximum (°C)')
    puissance_installee       = fields.Integer(string='Puissance installée (KW)')
    puissance_chauffe         = fields.Integer(string='Puissance de chauffe (KW)')
    puissance_refroidissement = fields.Integer(string='Puissance de refroidissement (KW)')
    debit_maximum             = fields.Integer(string='Débit maximum (L/min)')
    pression_maximum          = fields.Integer(string='Pression maximum (BARS)')
    commande_deportee         = fields.Selection([
        ('oui','Oui'),
        ('non','Non'),
    ], string='Commande déportée sur presse')
    option_depression = fields.Selection([
        ('oui','Oui'),
        ('non','Non'),
    ], string='Option déprésssion')
    mesure_debit = fields.Selection([
        ('oui','Oui'),
        ('non','Non'),
    ], string='Mesure débit')    
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    active = fields.Boolean('Active', default=True)
    

    # def write(self, vals):
    #     try:
    #         res=super(is_prechauffeur, self).write(vals)
    #         for obj in self:
    #             obj.copy_other_database_is_prechauffeur()
    #         return res
    #     except Exception as e:
    #         raise osv.except_osv(_('Prechauffeur!'),
    #                          _('(%s).') % str(e).decode('utf-8'))


    # @api.model
    # def create(self, vals):
    #     try:
    #         obj=super(is_prechauffeur, self).create(vals)
    #         obj.copy_other_database_is_prechauffeur()
    #         return obj
    #     except Exception as e:
    #         raise osv.except_osv(_('Prechauffeur!'),
    #                          _('(%s).') % str(e).decode('utf-8'))
            
    def copy_other_database_is_prechauffeur(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for prechauffeur in self:
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
                is_prechauffeur_vals = self.get_is_prechauffeur_vals(prechauffeur, DB, USERID, USERPASS, sock)
                dest_is_prechauffeur_ids = sock.execute(DB, USERID, USERPASS, 'is.prechauffeur', 'search', [('is_database_origine_id', '=', prechauffeur.id),
                                                                                                '|',('active','=',True),('active','=',False)], {})
                if dest_is_prechauffeur_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.prechauffeur', 'write', dest_is_prechauffeur_ids, is_prechauffeur_vals, {})
                    is_prechauffeur_created_id = dest_is_prechauffeur_ids[0]
                else:
                    is_prechauffeur_created_id = sock.execute(DB, USERID, USERPASS, 'is.prechauffeur', 'create', is_prechauffeur_vals, {})
        return True

    def get_is_prechauffeur_vals(self, prechauffeur, DB, USERID, USERPASS, sock):
        is_prechauffeur_vals ={
            'name' : tools.ustr(prechauffeur.name or ''),
            'presse_id':self._get_presse_id(prechauffeur, DB, USERID, USERPASS, sock), 
            'constructeur':tools.ustr(prechauffeur.constructeur or ''),
            'marque':tools.ustr(prechauffeur.marque or ''),
            'type_prechauffeur':tools.ustr(prechauffeur.type_prechauffeur or ''),
            'num_serie':tools.ustr(prechauffeur.num_serie or ''),
            'date_fabrication':prechauffeur.date_fabrication,
            'poids':prechauffeur.poids,
            'longueur':prechauffeur.longueur,
            'largeur': prechauffeur.largeur ,
            'hauteur':prechauffeur.hauteur,
            'type_fluide': prechauffeur.type_fluide ,
            'temperature_maxi': prechauffeur.temperature_maxi ,
            'puissance_installee': prechauffeur.puissance_installee ,
            'puissance_chauffe': prechauffeur.puissance_chauffe ,
            'puissance_refroidissement': prechauffeur.puissance_refroidissement ,
            'debit_maximum': prechauffeur.debit_maximum ,
            'pression_maximum':prechauffeur.pression_maximum,
            'commande_deportee': prechauffeur.commande_deportee ,
            'option_depression': prechauffeur.option_depression ,
            'mesure_debit': prechauffeur.mesure_debit ,
            'site_id':self._get_site_id(prechauffeur, DB, USERID, USERPASS, sock),
            'moule_ids':self._get_moule_ids(prechauffeur, DB, USERID, USERPASS, sock), 
            'active':prechauffeur.site_id and prechauffeur.site_id.database == DB and True or False,
            'is_database_origine_id':prechauffeur.id,
        }
        return is_prechauffeur_vals
    
    
    def _get_moule_ids(self, prechauffeur , DB, USERID, USERPASS, sock):
        ids = []
        for moule in prechauffeur.moule_ids:
            res = sock.execute(DB, USERID, USERPASS, 'is.mold', 'search', [('is_database_origine_id', '=', moule.id)], {})
            if res:
                ids.append(res[0])
        return [(6,0,ids)]


    def _get_presse_id(self, prechauffeur, DB, USERID, USERPASS, sock):
        if prechauffeur.presse_id:
            ids = sock.execute(DB, USERID, USERPASS, 'is.presse', 'search', [('is_database_origine_id', '=', prechauffeur.presse_id.id)], {})
            if ids:
                return ids[0]
        return False


    def _get_site_id(self, prechauffeur, DB, USERID, USERPASS, sock):
        if prechauffeur.site_id:
            ids = sock.execute(DB, USERID, USERPASS, 'is.database', 'search', [('is_database_origine_id', '=', prechauffeur.site_id.id)], {})
            if ids:
                return ids[0]
        return False

    
    def _get_mold_id(self, prechauffeur, DB, USERID, USERPASS, sock):
        if prechauffeur.mold_id:
            is_mold_ids = sock.execute(DB, USERID, USERPASS, 'is.mold', 'search', [('is_database_origine_id', '=', prechauffeur.mold_id.id)], {})
            if not is_mold_ids:
                prechauffeur.mold_id.copy_other_database_mold()
                is_mold_ids = sock.execute(DB, USERID, USERPASS, 'is.mold', 'search', [('is_database_origine_id', '=', prechauffeur.mold_id.id)], {})
            if is_mold_ids:
                return is_mold_ids[0]
        return False
    
 
