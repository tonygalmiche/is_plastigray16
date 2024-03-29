# -*- coding: utf-8 -*-
from odoo import api,fields,models,tools,SUPERUSER_ID
from xmlrpc import client as xmlrpclib
import logging
_logger = logging.getLogger(__name__)


class is_database(models.Model):
    _name = 'is.database'
    _description = "Database"
    _order='name'

    name                   = fields.Char('Site'           , required=True)
    ip_server              = fields.Char('Adresse IP'     , required=False)
    port_server            = fields.Integer('Port'        , required=False)
    database               = fields.Char('Base de données', required=False)
    login                  = fields.Char('Login'          , required=False)
    password               = fields.Char('Mot de passe'   , required=False)
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    preventif_equipement_user_ids = fields.Many2many('res.users', 'is_database_preventif_equipement_user_ids_rel', 'database_id','user_id', string=u"Destinataires mails préventif équipement")


    def copy_other_database(self, obj, filtre=False):
        if not filtre:
            if hasattr(obj, 'name'):
                filtre=[('name', '=', obj.name)]
            else:
                filtre=[('id', '=', 0)] #Filtre qui ne retourne rien si pas de name
        databases = self.env['is.database'].search([])
        for database in databases:
            if obj and database.ip_server and database.database and database.port_server and database.login and database.password:
                model     = obj._name
                DB        = database.database
                USERID    = 2
                DBLOGIN   = database.login
                USERPASS  = database.password
                DB_SERVER = database.ip_server
                DB_PORT   = database.port_server
                _logger.info("copy_other_database : DB=%s : DB_SERVER=%s : DB_PORT=%s : model=%s"%(DB,DB_SERVER,DB_PORT,model))
                sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object' % (DB_SERVER, DB_PORT))
                vals = obj.get_copy_other_database_vals(DB, USERID, USERPASS, sock)
                try:
                    getattr(obj, 'active')
                    filtre_origine_id=[('is_database_origine_id', '=', obj.id),'|',('active','=',True),('active','=',False)]
                except AttributeError as e:
                    filtre_origine_id=[('is_database_origine_id', '=', obj.id)]
                ids = sock.execute(DB, USERID, USERPASS, model, 'search', filtre_origine_id)
                if not ids:
                    ids = sock.execute(DB, USERID, USERPASS, model, 'search', filtre)
                if ids:
                    res=sock.execute(DB, USERID, USERPASS, model, 'write', ids, vals)
                    _logger.info("write : database=%s : model=%s : ids=%s : vals=%s : res=%s"%(DB,model,ids,vals,res))
                else:
                    res=sock.execute(DB, USERID, USERPASS, model, 'create', vals)
                    _logger.info("create : database=%s : model=%s : vals=%s : id=%s"%(DB,model,vals,res))
        return True


    def unlink_other_database(self, objs):
        for obj in objs:
            databases = self.env['is.database'].search([])
            for database in databases:
                if obj and database.ip_server and database.database and database.port_server and database.login and database.password:
                    model     = obj._name
                    DB        = database.database
                    USERID    = SUPERUSER_ID
                    DBLOGIN   = database.login
                    USERPASS  = database.password
                    DB_SERVER = database.ip_server
                    DB_PORT   = database.port_server
                    sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object' % (DB_SERVER, DB_PORT))
                    ids = sock.execute(DB, USERID, USERPASS, model, 'search', [('is_database_origine_id', '=', obj.id)])
                    if ids:
                        for id in ids:
                            res=sock.execute(DB, USERID, USERPASS, model, 'unlink', id)
                            _logger.info("unlink : database=%s : model=%s : id=%s : res=%s"%(DB,model,id,res))


    # def write(self, vals):
    #     res=super().write(vals)
    #     for obj in self:
    #         self.env['is.database'].copy_other_database(obj)
    #     return res
            
    # @api.model_create_multi
    # def create(self, vals_list):
    #     res=super().create(vals_list)
    #     self.env['is.database'].copy_other_database(res)
    #     return res

    # def get_copy_other_database_vals(self, DB, USERID, USERPASS, sock):
    #     vals ={
    #         'name'                  : self.name,
    #         'is_database_origine_id': self.id
    #     }
    #     return vals



