# -*- coding: utf-8 -*-
from odoo import models,fields,api
import os
import time
import datetime
import base64

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


# ** Fonctions d'importation EDI ***********************************************
import_function=[
    ('902580'         , '902580'),
    ('902810'         , '902810'),
    ('903410'         , '903410'),
    ('ACTIA'          , 'ACTIA'),
    ('ASTEELFLASH'    , 'ASTEELFLASH'),
    ('DARWIN'         , 'DARWIN'),
    ('eCar'           , 'eCar'),
    ('GXS'            , 'GXS'),
    ('John-Deere'     , 'John-Deere'),
    ('Lacroix'        , 'Lacroix'),
    ('Millipore'      , 'Millipore'),
    ('Mini-Delta-Dore', 'Mini-Delta-Dore'),
    ('Motus'          , 'Motus'),
    ('Odoo'           , 'Odoo'),
    ('Plasti-ka'      , 'Plasti-ka'),
    ('SIMU'           , 'SIMU'),
    ('SIMU-SOMFY'     , 'SIMU-SOMFY'),
    ('THERMOR'        , 'THERMOR'),
    ('Watts'          , 'Watts'),
]
# ******************************************************************************


type_commande_list=[
    ('ouverte'         , 'Commande ouverte'),
    ('ferme'           , 'Commande ferme avec horizon'),
    ('ferme_uniquement', 'Commande ferme uniquement')
]


traitement_edi=[
    ('DESADV', 'DESADV'),
]


class is_segment_achat(models.Model):
    _name = 'is.segment.achat'
    _description = "Segment d'achat"
    
    name        = fields.Char('Code', size=256, required=True)
    description = fields.Text('Commentaire')
    family_line = fields.One2many('is.famille.achat', 'segment_id', 'Familles')
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)


#     def write(self, vals):
#         try:
#             res=super(is_segment_achat, self).write(vals)
#             for obj in self:
#                 obj.copy_other_database_segment_achat()
#             return res
#         except Exception as e:
#             raise osv.except_osv(_('Segment!'),
#                              _('(%s).') % str(e).decode('utf-8'))

#     @api.model
#     def create(self, vals):
#         try:
#             obj=super(is_segment_achat, self).create(vals)
#             obj.copy_other_database_segment_achat()
#             return obj
#         except Exception as e:
#             raise osv.except_osv(_('Segment!'),
#                              _('(%s).') % str(e).decode('utf-8'))

#     def copy_other_database_segment_achat(self):
#         cr , uid, context = self.env.args
#         context = dict(context)
#         database_obj = self.env['is.database']
#         database_lines = database_obj.search([])
#         for segment in self:
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
#                 segment_achat_vals = self.get_segment_achat_vals(segment, DB, USERID, USERPASS, sock)
#                 dest_segment_achat_ids = sock.execute(DB, USERID, USERPASS, 'is.segment.achat', 'search', [('is_database_origine_id', '=', segment.id)], {})
#                 if not dest_segment_achat_ids:
#                     dest_segment_achat_ids = sock.execute(DB, USERID, USERPASS, 'is.segment.achat', 'search', [('name', '=', segment.name)], {})
#                 if dest_segment_achat_ids:
#                     sock.execute(DB, USERID, USERPASS, 'is.segment.achat', 'write', dest_segment_achat_ids, segment_achat_vals, {})
#                     segment_achat_created_id = dest_segment_achat_ids[0]
#                 else:
#                     segment_achat_created_id = sock.execute(DB, USERID, USERPASS, 'is.segment.achat', 'create', segment_achat_vals, {})
#         return True

#     def _get_family_line(self, segment, DB, USERID, USERPASS, sock):
#         lines = []
#         for family_line in segment.family_line:
#             lines.append(((0, 0, {'name':tools.ustr(family_line.name), 'description': family_line.description,})))
#         return lines
    
#     def get_segment_achat_vals(self, segment, DB, USERID, USERPASS, sock):
#         segment_achat_vals ={
#                              'name'       : tools.ustr(segment.name),
#                              'description': tools.ustr(segment.description),
#                              'is_database_origine_id':segment.id,
#                              }
#         return segment_achat_vals
        



class is_famille_achat(models.Model):
    _name = 'is.famille.achat'
    _description = "Famille d'achat"
    
    name        = fields.Char('Code', size=256, required=True)
    segment_id  = fields.Many2one('is.segment.achat', 'Segment', required=True)
    description = fields.Text('Commentaire')  
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
 
#     def write(self, vals):
#         try:
#             res=super(is_famille_achat, self).write(vals)
#             for obj in self:
#                 obj.copy_other_database_famille_achat()
#             return res
#         except Exception as e:
#             raise osv.except_osv(_('Famille!'),
#                              _('(%s).') % str(e).decode('utf-8'))
 
#     @api.model
#     def create(self, vals):
#         try:
#             obj=super(is_famille_achat, self).create(vals)
#             obj.copy_other_database_famille_achat()
#             return obj
#         except Exception as e:
#             raise osv.except_osv(_('Famille!'),
#                              _('(%s).') % str(e).decode('utf-8'))

#     def copy_other_database_famille_achat(self):
#         cr , uid, context = self.env.args
#         context = dict(context)
#         database_obj = self.env['is.database']
#         database_lines = database_obj.search([])
#         for famille in self:
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
#                 famille_achat_vals = self.get_famille_achat_vals(famille, DB, USERID, USERPASS, sock)
#                 dest_famille_achat_ids = sock.execute(DB, USERID, USERPASS, 'is.famille.achat', 'search', [('is_database_origine_id', '=', famille.id)], {})
#                 if not dest_famille_achat_ids:
#                     dest_famille_achat_ids = sock.execute(DB, USERID, USERPASS, 'is.famille.achat', 'search', [('name', '=', famille.name)], {})
#                 if dest_famille_achat_ids:
#                     sock.execute(DB, USERID, USERPASS, 'is.famille.achat', 'write', dest_famille_achat_ids, famille_achat_vals, {})
#                     famille_achat_created_id = dest_famille_achat_ids[0]
#                 else:
#                     famille_achat_created_id = sock.execute(DB, USERID, USERPASS, 'is.famille.achat', 'create', famille_achat_vals, {})
#         return True
 
#     def get_segment_id(self, famille, DB, USERID, USERPASS, sock):
#         if famille.segment_id:
#             segment_ids = sock.execute(DB, USERID, USERPASS, 'is.segment.achat', 'search', [('is_database_origine_id', '=', famille.segment_id.id)], {})
#             if not segment_ids:
#                 famille.segment_id.copy_other_database_segment_achat()
#                 segment_ids = sock.execute(DB, USERID, USERPASS, 'is.segment.achat', 'search', [('is_database_origine_id', '=', famille.segment_id.id)], {})
#             if segment_ids:
#                 return segment_ids[0]
#         return False

#     def get_famille_achat_vals(self, famille, DB, USERID, USERPASS, sock):
#         famille_achat_vals ={
#                              'name'       : tools.ustr(famille.name),
#                              'description': tools.ustr(famille.description),
#                             'segment_id' : self.get_segment_id(famille, DB, USERID, USERPASS, sock),
#                               'is_database_origine_id':famille.id,
#                              }
#         return famille_achat_vals
    
    


class is_site(models.Model):
    _name = 'is.site'
    _description = 'Sites'
    
    name = fields.Char('Site', required=True) 
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)

#     def write(self, vals):
#         try:
#             res=super(is_site, self).write(vals)
#             for obj in self:
#                 obj.copy_other_database_is_site()
#             return res
#         except Exception as e:
#             raise osv.except_osv(_('Site!'),
#                              _('(%s).') % str(e).decode('utf-8'))
            
#     def create(self, vals):
#         try:
#             obj=super(is_site, self).create(vals)
#             obj.copy_other_database_is_site()
#             return obj
#         except Exception as e:
#             raise osv.except_osv(_('Site!'),
#                              _('(%s).') % str(e).decode('utf-8'))
    
    
#     def copy_other_database_is_site(self):
#         cr , uid, context = self.env.args
#         context = dict(context)
#         database_obj = self.env['is.database']
#         database_lines = database_obj.search([])
#         for is_site in self:
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
#                 is_site_vals = self.get_is_site_vals(is_site, DB, USERID, USERPASS, sock)
#                 dest_is_site_ids = sock.execute(DB, USERID, USERPASS, 'is.site', 'search', [('is_database_origine_id', '=', is_site.id)], {})
#                 if not dest_is_site_ids:
#                     dest_is_site_ids = sock.execute(DB, USERID, USERPASS, 'is.site', 'search', [('name', '=', is_site.name)], {})
#                 if dest_is_site_ids:
#                     sock.execute(DB, USERID, USERPASS, 'is.site', 'write', dest_is_site_ids, is_site_vals, {})
#                     is_site_created_id = dest_is_site_ids[0]
#                 else:
#                     is_site_created_id = sock.execute(DB, USERID, USERPASS, 'is.site', 'create', is_site_vals, {})
#         return True

        
#     def get_is_site_vals(self, is_site, DB, USERID, USERPASS, sock):
#         is_site_vals ={
#                      'name' : tools.ustr(is_site.name),
#                      'is_database_origine_id':is_site.id
#                      }
#         return is_site_vals
    



class is_transmission_cde(models.Model):
    _name = 'is.transmission.cde'
    _description = 'Mode de transmission des cmds'
    
    name        = fields.Char('Mode de transmission des commandes', required=True)
    commentaire = fields.Char('Commentaire')
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)


#     def write(self, vals):
#         try:
#             res=super(is_transmission_cde, self).write(vals)
#             for obj in self:
#                 obj.copy_other_database_transmission_cde()
#             return res
#         except Exception as e:
#             raise osv.except_osv(_('Transmission!'),
#                              _('(%s).') % str(e).decode('utf-8'))

#     def create(self, vals):
#         try:
#             obj=super(is_transmission_cde, self).create(vals)
#             obj.copy_other_database_transmission_cde()
#             return obj
#         except Exception as e:
#             raise osv.except_osv(_('Transmission!'),
#                              _('(%s).') % str(e).decode('utf-8'))
    
    
#     def copy_other_database_transmission_cde(self):
#         cr , uid, context = self.env.args
#         context = dict(context)
#         database_obj = self.env['is.database']
#         database_lines = database_obj.search([])
#         for is_transmission in self:
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
#                 is_transmission_vals = self.get_is_transmission_vals(is_transmission, DB, USERID, USERPASS, sock)
#                 dest_is_transmission_ids = sock.execute(DB, USERID, USERPASS, 'is.transmission.cde', 'search', [('is_database_origine_id', '=', is_transmission.id)], {})
#                 if not dest_is_transmission_ids:
#                     dest_is_transmission_ids = sock.execute(DB, USERID, USERPASS, 'is.transmission.cde', 'search', [('name', '=', is_transmission.name)], {})
#                 if dest_is_transmission_ids:
#                     sock.execute(DB, USERID, USERPASS, 'is.transmission.cde', 'write', dest_is_transmission_ids, is_transmission_vals, {})
#                     is_transmission_created_id = dest_is_transmission_ids[0]
#                 else:
#                     is_transmission_created_id = sock.execute(DB, USERID, USERPASS, 'is.transmission.cde', 'create', is_transmission_vals, {})
#         return True

        
#     def get_is_transmission_vals(self, is_transmission, DB, USERID, USERPASS, sock):
#         is_transmission_vals ={
#                      'name' : tools.ustr(is_transmission.name),
#                      'is_database_origine_id':is_transmission.id,
#                      }
#         return is_transmission_vals
    



class is_norme_certificats(models.Model):
    _name = 'is.norme.certificats'
    _description = u'Norme Certificat qualité'
    
    name                   = fields.Char('Nome certificat', required=True)
    notation_fournisseur   = fields.Integer('Coefficient notation fournisseur')
    commentaire            = fields.Char('Commentaire')
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)


    # def write(self, vals):
    #     try:
    #         res=super(is_norme_certificats, self).write(vals)
    #         for obj in self:
    #             obj.copy_other_database_norme_certificats()
    #         return res
    #     except Exception as e:
    #         raise osv.except_osv(_('Norme!'),
    #                          _('(%s).') % str(e).decode('utf-8'))


    # def create(self, vals):
    #     try:
    #         obj=super(is_norme_certificats, self).create(vals)
    #         obj.copy_other_database_norme_certificats()
    #         return obj
    #     except Exception as e:
    #         raise osv.except_osv(_('Norme!'),
    #                          _('(%s).') % str(e).decode('utf-8'))
    
    
    def copy_other_database_norme_certificats(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for norme_certificats in self:
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
                norme_certificats_vals = self.get_is_norme_certificats_vals(norme_certificats, DB, USERID, USERPASS, sock)
                dest_norme_certificats_ids = sock.execute(DB, 1, USERPASS, 'is.norme.certificats', 'search', [('is_database_origine_id', '=', norme_certificats.id)], {})
                if not dest_norme_certificats_ids:
                    dest_norme_certificats_ids = sock.execute(DB, USERID, USERPASS, 'is.norme.certificats', 'search', [('name', '=', norme_certificats.name)], {})
                if dest_norme_certificats_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.norme.certificats', 'write', dest_norme_certificats_ids, norme_certificats_vals, {})
                    norme_certificats_created_id = dest_norme_certificats_ids[0]
                else:
                    norme_certificats_created_id = sock.execute(DB, USERID, USERPASS, 'is.norme.certificats', 'create', norme_certificats_vals, {})
        return True

        
    def get_is_norme_certificats_vals(self, norme_certificats, DB, USERID, USERPASS, sock):
        norme_certificats_vals ={
            'name'                  : tools.ustr(norme_certificats.name),
            'notation_fournisseur'  : norme_certificats.notation_fournisseur,
            'commentaire'           : tools.ustr(norme_certificats.commentaire or ''),
            'is_database_origine_id': norme_certificats.id,
        }
        return norme_certificats_vals
    

class is_certifications_qualite(models.Model):
    _name = 'is.certifications.qualite'
    _description = u'Certifications qualité'
    
    is_norme           = fields.Many2one('is.norme.certificats', u'Norme Certificat qualité', required=True)
    is_date_validation = fields.Date(u'Date de validité du certificat', required=True)
    is_certificat      = fields.Binary('Certificat qualité')
    is_certificat_ids  = fields.Many2many('ir.attachment', 'is_certificat_attachment_rel', 'certificat_id', 'attachment_id', u'Pièces jointes')
    partner_id         = fields.Many2one('res.partner', 'Client/Fournisseur')    
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    

#     def write(self, vals):
#         try:
#             res=super(is_certifications_qualite, self).write(vals)
#             for obj in self:
#                 obj.copy_other_database_certifications_qualite()
#             return res
#         except Exception as e:
#             raise osv.except_osv(_('Qualite!'),
#                              _('(%s).') % str(e).decode('utf-8'))


#     @api.model
#     def create(self, vals):
#         try:
#             obj=super(is_certifications_qualite, self).create(vals)
#             obj.copy_other_database_certifications_qualite()
#             return obj
#         except Exception as e:
#             raise osv.except_osv(_('Qualite!'),
#                              _('(%s).') % str(e).decode('utf-8'))

    
#     def copy_other_database_certifications_qualite(self):
#         cr , uid, context = self.env.args
#         context = dict(context)
#         database_obj = self.env['is.database']
#         database_lines = database_obj.search([])
#         for certifications_qualite in self:
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
#                 certifications_qualite_vals = self.get_is_certifications_qualite_vals(certifications_qualite, DB, USERID, USERPASS, sock)
#                 dest_certifications_qualite_ids = sock.execute(DB, USERID, USERPASS, 'is.certifications.qualite', 'search', [('is_database_origine_id', '=', certifications_qualite.id)], {})
#                 if dest_certifications_qualite_ids:
#                     sock.execute(DB, USERID, USERPASS, 'is.certifications.qualite', 'write', dest_certifications_qualite_ids, certifications_qualite_vals, {})
#                     certifications_qualite_created_id = dest_certifications_qualite_ids[0]
#                 else:
#                     certifications_qualite_created_id = sock.execute(DB, USERID, USERPASS, 'is.certifications.qualite', 'create', certifications_qualite_vals, {})
#         return True


#     @api.model
#     def _get_is_norme(self, certifications_qualite, DB, USERID, USERPASS, sock):
#         if certifications_qualite.is_norme:
#             is_norme_ids = sock.execute(DB, USERID, USERPASS, 'is.norme.certificats', 'search', [('is_database_origine_id', '=', certifications_qualite.is_norme.id)], {})
#             if not is_norme_ids:
#                 certifications_qualite.is_norme.copy_other_database_norme_certificats()
#                 is_norme_ids = sock.execute(DB, USERID, USERPASS, 'is.norme.certificats', 'search', [('is_database_origine_id', '=', certifications_qualite.is_norme.id)], {})
#             if is_norme_ids:
#                 return is_norme_ids[0]
#         return False

#     def _get_certificat_ids(self, certifications_qualite, DB, USERID, USERPASS, sock):
#         certificat_data = []
#         for  certificat in certifications_qualite.is_certificat_ids:
#             certificat_data.append(((0, 0, {'name':tools.ustr(certificat.name), 'datas':certificat.datas, 'res_model':certificat.res_model})))
#         return certificat_data

#     def get_is_certifications_qualite_vals(self, certifications_qualite, DB, USERID, USERPASS, sock):
#         certifications_qualite_vals ={
#                      'is_norme' : self._get_is_norme(certifications_qualite, DB, USERID, USERPASS, sock),
#                      'is_date_validation':certifications_qualite.is_date_validation,
#                      'is_certificat_ids':self._get_certificat_ids(certifications_qualite, DB, USERID, USERPASS, sock),
#                      'is_database_origine_id':certifications_qualite.id,
#                      }
#         return certifications_qualite_vals
    


    def name_get(self):
        res=[]
        for obj in self:
            res.append((obj.id, obj.is_norme.name))
        return res


class is_secteur_activite(models.Model):
    _name='is.secteur.activite'
    _description="Secteur d'activité"
    _order='name'
    _sql_constraints = [('name_uniq','UNIQUE(name)', 'Ce code existe déjà')] 

    name        = fields.Char("Secteur d'activité", required=True)
    commentaire = fields.Char('Commentaire') 
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    
#     def write(self, vals):
#         try:
#             res=super(is_secteur_activite, self).write(vals)
#             for obj in self:
#                 obj.copy_other_database_secteur_activite()
#             return res
#         except Exception as e:
#             raise osv.except_osv(_('Secteur!'),
#                              _('(%s).') % str(e).decode('utf-8'))


#     def create(self, vals):
#         try:
#             obj=super(is_secteur_activite, self).create(vals)
#             obj.copy_other_database_secteur_activite()
#             return obj
#         except Exception as e:
#             raise osv.except_osv(_('Secteur!'),
#                              _('(%s).') % str(e).decode('utf-8'))
    
#     def copy_other_database_secteur_activite(self):
#         cr , uid, context = self.env.args
#         context = dict(context)
#         database_obj = self.env['is.database']
#         database_lines = database_obj.search([])
#         for activite in self:
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
#                 activite_vals = self.get_activite_vals(activite, DB, USERID, USERPASS, sock)
#                 dest_activite_ids = sock.execute(DB, USERID, USERPASS, 'is.secteur.activite', 'search', [('is_database_origine_id', '=', activite.id)], {})
#                 if not dest_activite_ids:
#                     dest_activite_ids = sock.execute(DB, USERID, USERPASS, 'is.secteur.activite', 'search', [('name', '=', activite.name)], {})
#                 if dest_activite_ids:
#                     sock.execute(DB, USERID, USERPASS, 'is.secteur.activite', 'write', dest_activite_ids, activite_vals, {})
#                     activite_created_id = dest_activite_ids[0]
#                 else:
#                     activite_created_id = sock.execute(DB, USERID, USERPASS, 'is.secteur.activite', 'create', activite_vals, {})
#         return True

#     def get_activite_vals(self, activite, DB, USERID, USERPASS, sock):
#         activite_vals ={
#                      'name' : tools.ustr(activite.name),
#                      'is_database_origine_id':activite.id,
#                      }
#         return activite_vals
    




class is_type_contact(models.Model):
    _name='is.type.contact'
    _description="Type de contact"
    _order='name'
    _sql_constraints = [('name_uniq','UNIQUE(name)', 'Ce code existe déjà')] 

    name        = fields.Char("Type de contact", required=True)
    commentaire = fields.Char('Commentaire')
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)


#     def write(self, vals):
#         try:
#             res=super(is_type_contact, self).write(vals)
#             for obj in self:
#                 obj.copy_other_database_type_contact()
#             return res
#         except Exception as e:
#             raise osv.except_osv(_('Contact!'),
#                              _('(%s).') % str(e).decode('utf-8'))


#     def create(self, vals):
#         try:
#             obj=super(is_type_contact, self).create(vals)
#             obj.copy_other_database_type_contact()
#             return obj
#         except Exception as e:
#             raise osv.except_osv(_('Contact!'),
#                              _('(%s).') % str(e).decode('utf-8'))

    
#     def copy_other_database_type_contact(self):
#         cr , uid, context = self.env.args
#         context = dict(context)
#         database_obj = self.env['is.database']
#         database_lines = database_obj.search([])
#         for type_contact in self:
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
#                 type_contact_vals = self.get_type_contact_vals(type_contact, DB, USERID, USERPASS, sock)
#                 dest_type_contact_ids = sock.execute(DB, USERID, USERPASS, 'is.type.contact', 'search', [('is_database_origine_id', '=', type_contact.id)], {})
#                 if not dest_type_contact_ids:
#                     dest_type_contact_ids = sock.execute(DB, USERID, USERPASS, 'is.type.contact', 'search', [('name', '=', type_contact.name)], {})
#                 if dest_type_contact_ids:
#                     sock.execute(DB, USERID, USERPASS, 'is.type.contact', 'write', dest_type_contact_ids, type_contact_vals, {})
#                     type_contact_created_id = dest_type_contact_ids[0]
#                 else:
#                     type_contact_created_id = sock.execute(DB, USERID, USERPASS, 'is.type.contact', 'create', type_contact_vals, {})
#         return True

#     @api.model
#     def get_type_contact_vals(self, type_contact, DB, USERID, USERPASS, sock):
#         type_contact_vals ={
#                      'name' : tools.ustr(type_contact.name),
#                      'is_database_origine_id':type_contact.id,
#                      }
#         return type_contact_vals
    


class is_escompte(models.Model):
    _name='is.escompte'
    _description="Escompte"
    _order='name'

    name = fields.Char("Intitulé", required=True)
    taux = fields.Float("Taux d'escompte", required=True)
    compte = fields.Many2one('account.account', "Compte")
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    
#     def write(self, vals):
#         try:
#             res=super(is_escompte, self).write(vals)
#             for obj in self:
#                 obj.copy_other_database_is_escompte()
#             return res
#         except Exception as e:
#             raise osv.except_osv(_('escompte!'),
#                              _('(%s).') % str(e).decode('utf-8'))

#     @api.model
#     def create(self, vals):
#         try:
#             obj=super(is_escompte, self).create(vals)
#             obj.copy_other_database_is_escompte()
#             return obj
#         except Exception as e:
#             raise osv.except_osv(_('escompte!'),
#                              _('(%s).') % str(e).decode('utf-8'))

    
#     def copy_other_database_is_escompte(self):
#         cr , uid, context = self.env.args
#         context = dict(context)
#         database_obj = self.env['is.database']
#         database_lines = database_obj.search([])
#         for is_escompte in self:
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
#                 is_escompte_vals = self.get_is_escompte_vals(is_escompte, DB, USERID, USERPASS, sock)
#                 dest_is_escompte_ids = sock.execute(DB, USERID, USERPASS, 'is.escompte', 'search', [('is_database_origine_id', '=', is_escompte.id)], {})
#                 if not dest_is_escompte_ids:
#                     dest_is_escompte_ids = sock.execute(DB, USERID, USERPASS, 'is.escompte', 'search', [('name', '=', is_escompte.name)], {})
#                 if dest_is_escompte_ids:
#                     sock.execute(DB, USERID, USERPASS, 'is.escompte', 'write', dest_is_escompte_ids, is_escompte_vals, {})
#                     is_escompte_created_id = dest_is_escompte_ids[0]
#                 else:
#                     is_escompte_created_id = sock.execute(DB, USERID, USERPASS, 'is.escompte', 'create', is_escompte_vals, {})
#         return True

#     def _get_is_escompte_compte(self, is_escompte, DB, USERID, USERPASS, sock):
#         if is_escompte.compte:
#             dest_compte_ids = sock.execute(DB, USERID, USERPASS, 'account.account', 'search', [('code', '=', is_escompte.compte.code)], {})
#             if dest_compte_ids:
#                 return dest_compte_ids[0]
#         return False
            
    
#     def get_is_escompte_vals(self, is_escompte, DB, USERID, USERPASS, sock):
#         is_escompte_vals ={
#                      'name' : tools.ustr(is_escompte.name),
#                      'taux' : is_escompte.taux,
#                      'compte': self._get_is_escompte_compte(is_escompte, DB, USERID, USERPASS, sock),
#                      'is_database_origine_id':is_escompte.id
#                      }
#         return is_escompte_vals

    


class res_partner(models.Model):
    _inherit = 'res.partner'

    def _get_default_location(self):
        company_id = self.env.user.company_id.id
        warehouse_obj = self.env['stock.warehouse']
        warehouse_id = warehouse_obj.search([('company_id','=',company_id)])
        location = warehouse_id.out_type_id and  warehouse_id.out_type_id.default_location_src_id
        return location and location or False

    customer   = fields.Boolean('Client')      # Champ ajouté car n'existe plus dans Odoo 16
    supplier   = fields.Boolean('Fournisseur') # Champ ajouté car n'existe plus dans Odoo 16

    display_name            = fields.Char(string='Nom affiché', compute='_compute_display_name')
    is_transporteur_id      = fields.Many2one('res.partner', 'Transporteur')
    is_delai_transport      = fields.Integer('Delai de transport (jour)')
    is_livre_a_id           = fields.Many2one('res.partner', 'Livrer à', help="Indiquez l'adresse de livraison si celle-ci est différente de celle de la société")
    is_certificat_matiere   = fields.Boolean(u'Certificat matière demandé')
    is_import_function      = fields.Selection(import_function, "Fonction d'importation EDI")
 
    is_traitement_edi                     = fields.Selection(traitement_edi, "Traitement EDI")
    is_numero_bal_recepteur               = fields.Char(string='Numero BAL recepteur')
    is_numero_identification_destinataire = fields.Char(string='Numero Identification Destinataire')
    is_numero_bal_emetteur                = fields.Char(string='Numero BAL Emetteur')
    is_standard_edi                       = fields.Char(string='Standard EDI')
    is_code_acheteur                      = fields.Char(string='Code Acheteur (BY)')
    is_code_expediteur                    = fields.Char(string='Code Expediteur (CZ)')
    is_code_vendeur                       = fields.Char(string='Code Vendeur (SE)')
    is_code_destinataire                  = fields.Char(string='Code Destinataire (CN)')
    is_code_destinataire_agence           = fields.Char(string='Code Destinataire Agence (CN)')


    is_raison_sociale2      = fields.Char('Raison sociale 2')
    is_code                 = fields.Char('Code'        , index=True)
    is_adr_code             = fields.Char('Code adresse', index=True)
    is_rue3                 = fields.Char('Rue 3 ou Boite Postale')
    is_secteur_activite     = fields.Many2one('is.secteur.activite', "Secteur d'activité")
    is_type_contact         = fields.Many2one('is.type.contact', "Type de contact")
    is_adr_facturation      = fields.Many2one('res.partner', 'Adresse de facturation')
    is_adr_groupe           = fields.Char('Code auxiliaire comptable', help="Code auxiliaire comptable de l'adresse groupe pour la comptabilité")
    is_cofor                = fields.Char('N° fournisseur (COFOR)', help="Notre code fourniseur chez le client")
    is_incoterm             = fields.Many2one('account.incoterms', "Incoterm  / Conditions de livraison")
    is_lieu                 = fields.Char("Lieu")
    is_escompte             = fields.Many2one('is.escompte', "Escompte")
    is_type_reglement       = fields.Many2one('account.journal', u'Type règlement', domain=[('type', 'in', ['bank','cash'])])
    is_num_siret            = fields.Char(u'N° de SIRET')
    is_code_client          = fields.Char('Code client', help=u'Notre code client chez le fourniseur')
    is_segment_achat        = fields.Many2one('is.segment.achat', "Segment d'achat")
    is_famille_achat_ids    = fields.Many2many('is.famille.achat', "res_partner_famille_achat_rel", 'partner_id', 'famille_id', string="Famille d'achat")
    is_fournisseur_imp      = fields.Boolean(u'Fournisseur imposé')
    is_fournisseur_da_fg    = fields.Boolean(u'Fournisseur pour DA-FG')
    is_site_livre_ids       = fields.Many2many('is.site', "res_partner_site_livre_rel", 'partner_id', 'site_id', string='sites livrés')
    is_groupage             = fields.Boolean('Groupage')
    is_tolerance_delai      = fields.Boolean('Tolérance sur délai')
    is_nb_jours_tolerance   = fields.Integer('Nb jours tolérance sur délai')
    is_tolerance_quantite   = fields.Boolean('Tolérance sur quantité')
    is_transmission_cde     = fields.Many2one('is.transmission.cde', 'Mode de transmission des commandes')
    is_certifications       = fields.One2many('is.certifications.qualite', 'partner_id', u'Certification qualité')
    is_type_contact         = fields.Many2one('is.type.contact', "Type de contact")
    is_source_location_id   = fields.Many2one('stock.location', 'Source Location', default=_get_default_location) 
    is_rib_id               = fields.Many2one('res.partner.bank', 'RIB') 
    is_adr_liv_sur_facture  = fields.Boolean(u"Afficher l'adresse de livraison sur la facture", default=True)
    is_num_autorisation_tva = fields.Char("N° d'autorisation", help="N° d'autorisation de franchise de taxe")
    is_caracteristique_bl   = fields.Selection([
        ('cde_odoo'   , '1 commande Odoo = 1 BL'),
        ('cde_client' , '1 commande client = 1 BL'),
        ('ref_article', '1 référence client = 1 BL'),
    ], 'Caractéristique des BL')
    is_mode_envoi_facture   = fields.Selection([
        ('courrier'        , 'Envoi par courrier'),
        ('courrier2'       , 'Envoi par courrier en double exemplaire'),
        ('mail'            , 'Envoi par mail (1 mail par facture)'),
        ('mail2'           , 'Envoi par mail (1 mail par facture en double exemplaire)'),
        ('mail_client'     , 'Envoi par mail (1 mail par client)'),
        ('mail_client_bl'  , 'Envoi par mail avec BL (1 mail par client)'),
        ('mail_regroupe_bl', 'Regroupement des BL sur une même facture et envoi par mail'),
    ], "Mode d'envoi des factures")
    is_type_cde_fournisseur = fields.Selection(type_commande_list, "Type commande fourniseur", readonly=True)
    is_horizon_besoins      = fields.Integer(u'Horizon des besoins (jour)', help=u"Champ utilisé pour le mail de l'horizon des besoins (7 jours en général ou 21 jours pendant la période de vacances)")

    is_database_origine_id = fields.Integer("Id d'origine", readonly=True, index=True)
    is_database_line_ids   = fields.Many2many('is.database','partner_database_rel','partner_id','database_id', string="Sites")


    _defaults = {
        'delai_transport'     : 0,
        'is_adr_code'         : 0,
        'is_fournisseur_da_fg': False,
        'is_horizon_besoins'  : 7,
    }

    # _sql_constraints = [
    #     ('code_adr_uniq', 'unique(is_code, is_adr_code, company_id)', u'Le code et le code adresse doivent être uniques par société!'),
    # ]
    

    # # Le champ display_name est un champ standard d'Odoo correspondant au titre de la fiche
    # # Cette fonction appelle la fonction name_get => Elle permet de définir les dépendances de champs
    # @api.one
    # @api.depends('name', 'parent_id.name','is_code', 'is_adr_code')
    # def _compute_display_name(self):
    #     r=self.name_get()
    #     self.display_name = r[0][1]


    # def write(self, vals):
    #     for obj in self:
    #         logger.info(u'write : partner='+str(obj.is_code)+u'/'+str(obj.is_adr_code))
    #         if 'is_adr_facturation' in vals:
    #             if vals['is_adr_facturation']==obj.id:
    #                 vals['is_adr_facturation']=False
    #         else:
    #             if obj.is_adr_facturation.id==obj.id:
    #                 vals['is_adr_facturation']=False
    #     try:
    #         for obj in self:
    #             res=super(res_partner, self).write(vals)
    #             self.env['is.database'].copy_other_database(obj)
    #             return res
    #     except Exception as e:
    #         raise osv.except_osv('Client recursif !','')


    # @api.model
    # def create(self, vals):
    #     try:
    #         obj=super(res_partner, self).create(vals)
    #         self.env['is.database'].copy_other_database(obj)
    #     except Exception as e:
    #         raise osv.except_osv('Client recursif !','')
    #     return obj


    def name_get(self):
        context=self._context
        if not len(self.ids):
            return []
        res = []
        if context is None:
            context = {}
        for record in self:
            name = record.name
            if record.parent_id and not record.is_company:
                name =  "%s, %s" % (record.parent_id.name, name)
            if record.is_company:
                if record.is_code and record.is_adr_code:
                    name =  "%s (%s/%s)" % (name, record.is_code, record.is_adr_code)
                if record.is_code and not record.is_adr_code:
                    name =  "%s (%s)" % (name, record.is_code)
            if context.get('show_address_only'):
                name = self._display_address(record, without_company=True, context=context)
            #Affiche l'adresse complète (ex dans les commandes)
            if context.get('show_address'):
                name = name + "\n" + self._display_address(record, without_company=True, context=context)
            name = name.replace('\n\n','\n')
            name = name.replace('\n\n','\n')
            if context.get('show_email') and record.email:
                name = "%s <%s>" % (name, record.email)
            res.append((record.id, name))
        return res


    def action_view_partner(self):
        #dummy, view_id = self.env['ir.model.data'].get_object_reference('base', 'view_partner_form')


        view_id = self.env.ref('base.view_partner_form').id


        for partner in self:
            return {
            'name':partner.name,
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'res.partner',
            'type': 'ir.actions.act_window',
            'res_id': partner.id,
            'domain': '[]',
        }


    # #TODO : Suite à l'installation du module 'project', j'ai du remettre l'ancienne api sinon plantage
    # def copy(self, cr, uid, partner_id, default=None, context=None):
    #     if default is None:
    #         default = {}
    #     for partner in self.browse(cr, uid, [partner_id], context=context):
    #         default['is_code']                        = partner.is_code + u' (copie)'
    #         default['is_adr_code']                    = partner.is_adr_code + u' (copie)'
    #         default['property_account_position']      = partner.property_account_position
    #         default['property_payment_term']          = partner.property_payment_term
    #         default['property_supplier_payment_term'] = partner.property_supplier_payment_term
    #     res=super(res_partner, self).copy(cr, uid, partner_id, default=default, context=context)
    #     return res


    def onchange_segment_id(self, cr, uid, ids, segment_id, context=None):
        domain = []
        val = {'is_famille_achat': False }
        if segment_id:
            domain.append(('segment_id','=',segment_id))           
        return {'value': val,
                'domain': {'is_famille_achat': domain}}


    def num_closing_days(self, partner):
        """ Retourner les jours de fermetures du partner
        """
        jours_fermes = []
        if partner.close_monday:
            jours_fermes.append(1)
        if partner.close_tuesday:
            jours_fermes.append(2)
        if partner.close_wednesday:
            jours_fermes.append(3)
        if partner.close_thursday:
            jours_fermes.append(4)
        if partner.close_friday:
            jours_fermes.append(5)
        if partner.close_saturday:
            jours_fermes.append(6)
        if partner.close_sunday:
            jours_fermes.append(0)
        return jours_fermes
    

    def get_leave_dates(self, partner, avec_jours_feries=False):
        """ Retourner les jours de congés du partner
        """
        leave_dates = []
        if partner.calendar_line:
            for line in partner.calendar_line:                                                                                                                                                            
                delta = datetime.datetime.strptime(line.date_to, DATETIME_FORMAT) - datetime.datetime.strptime(line.date_from, DATETIME_FORMAT)
                for i in range(delta.days + 1):
                    date = datetime.datetime.strptime(line.date_from, DATETIME_FORMAT) + datetime.timedelta(days=i)
                    leave_dates.append(date.strftime('%Y-%m-%d'))
        if avec_jours_feries:
            jours_feries=self.get_jours_feries(partner)
            for date in jours_feries:
                if date not in leave_dates:
                    leave_dates.append(date)
        return leave_dates
    

    def get_jours_feries(self, partner):
        """ Retourner les jours fériés du pays du partner indiqué 
        """
        jours_feries = []
        for line in partner.country_id.is_jour_ferie_ids:
            jours_feries.append(line.name)
        return jours_feries


    def test_date_dispo(self, date, partner, avec_jours_feries=False):
        """ Test si la date indiquée tombe sur un jour ouvert du partner 
        """
        res=True
        if date:
            num_day = int(time.strftime('%w', time.strptime(date, '%Y-%m-%d'))) #Jour de la semaine (avec dimanche=0)
            if num_day in self.num_closing_days(partner):
                res=False
            if date in self.get_leave_dates(partner, avec_jours_feries):
                res=False
        return res


    def get_day_except_weekend(self, date, num_day):
        """ Calculer la date d'expédition en exceptant les weekends
        """
        if int(num_day) not in [0, 6]:
            return date
        else:
            date = datetime.datetime.strptime(date, '%Y-%m-%d') - datetime.timedelta(days=1)
            date = date.strftime('%Y-%m-%d')
            num_day = time.strftime('%w', time.strptime(date, '%Y-%m-%d'))
            return self.get_day_except_weekend(date, num_day)

        
    def get_working_day(self, date, num_day, jours_fermes, leave_dates):
        """ Déterminer la date d'expédition en fonction des jours de fermeture de l'usine ou des jours de congés de l'usine 
        """
        if int(num_day) not in jours_fermes and date not in leave_dates:
            return date
        else:
            date = datetime.datetime.strptime(date, '%Y-%m-%d') - datetime.timedelta(days=1)
            date = date.strftime('%Y-%m-%d')
            num_day = time.strftime('%w', time.strptime(date, '%Y-%m-%d'))
            return self.get_working_day(date, num_day, jours_fermes, leave_dates)
        

    def get_date_livraison(self, company, partner, date_expedition):
        date_livraison=date_expedition
        if partner:
            res_partner = self.env['res.partner']
            # jours de fermeture de la société
            jours_fermes = res_partner.num_closing_days(company.partner_id)
            # Jours de congé de la société
            leave_dates = res_partner.get_leave_dates(company.partner_id)
            delai_transport = partner.is_delai_transport
            if delai_transport:
                new_date=datetime.datetime.strptime(date_expedition, '%Y-%m-%d')
                nb_jours=delai_transport
                while True:
                    new_date = new_date + datetime.timedelta(days=1)
                    date_txt=new_date.strftime('%Y-%m-%d')
                    num_day = int(time.strftime('%w', time.strptime( date_txt, '%Y-%m-%d')))
                    if not(num_day in jours_fermes or date_txt in leave_dates):
                        nb_jours=nb_jours-1
                    if nb_jours<=0:
                        date_livraison=new_date.strftime('%Y-%m-%d')
                        break
        return date_livraison


    def get_date_dispo(self, partner, date, avec_jours_feries=False):
        """ Retourne la première date disponible dans le passé en tenant compte des jours d'ouverture et des vacances 
        """
        num_closing_days = self.num_closing_days(partner)
        leave_dates      = self.get_leave_dates(partner, avec_jours_feries)
        new_date = datetime.datetime.strptime(date, '%Y-%m-%d')
        while True:
            date_txt=new_date.strftime('%Y-%m-%d')
            num_day = int(time.strftime('%w', time.strptime( date_txt, '%Y-%m-%d')))
            if num_day in num_closing_days or date_txt in leave_dates:
                new_date = new_date - datetime.timedelta(days=1)
            else:
                break
        return new_date.strftime('%Y-%m-%d')


    def get_date_debut(self, partner_id, date_fin, nb_jours):
        """ Calcul la date de début à partir de la date de fin en jours ouvrés 
        """
        if nb_jours<=0:
            return date_fin
        num_closing_days = self.num_closing_days(partner_id)
        leave_dates      = self.get_leave_dates(partner_id)
        new_date = datetime.datetime.strptime(date_fin, '%Y-%m-%d')
        while True:
            new_date = new_date - datetime.timedelta(days=1)
            date_txt=new_date.strftime('%Y-%m-%d')
            num_day = int(time.strftime('%w', time.strptime( date_txt, '%Y-%m-%d')))
            if not(num_day in num_closing_days or date_txt in leave_dates):
                nb_jours=nb_jours-1
            if nb_jours<=0:
                break
        return new_date.strftime('%Y-%m-%d')


    def get_date_fin(self, partner_id, date_debut, nb_jours):
        """ Calcul la date de fin à partir de la date de début en jours ouvrés 
        """
        if nb_jours<=0:
            return date_debut
        num_closing_days = self.num_closing_days(partner_id)
        leave_dates      = self.get_leave_dates(partner_id)
        new_date = datetime.datetime.strptime(date_debut, '%Y-%m-%d')
        while True:
            new_date = new_date + datetime.timedelta(days=1)
            date_txt=new_date.strftime('%Y-%m-%d')
            num_day = int(time.strftime('%w', time.strptime( date_txt, '%Y-%m-%d')))
            if not(num_day in num_closing_days or date_txt in leave_dates):
                nb_jours=nb_jours-1
            if nb_jours<=0:
                break
        return new_date.strftime('%Y-%m-%d')


    def get_messages(self,partner_id):
        """Recherche des messages pour les mettre sur les appels de livraison et commande des fourniseurs"""

        where=['|',('name','=',partner_id),('name','=',False)]
        messages=[]
        for row in self.env['is.cde.ouverte.fournisseur.message'].search(where):
            messages.append(row.message)
        return messages


    def bon_sortie_matiere(self, filename):
        '''
        Test génération 'Bon de sortie matière' pour être utilisée en PHP
        '''
        for obj in self:
            orders=self.env['is.cde.ouverte.fournisseur'].search([('partner_id','=',obj.id)])
            ids=[]
            for order in orders:
                ids.append(order.id)

            # ** Récupération du fichier PDF du rapport indiqué ****************
            pdf = self.pool.get('report').get_pdf(self._cr, self._uid, ids, 'is_plastigray.report_cde_ouverte_fournisseur', context=self._context)
            # ******************************************************************

            # Enregistrement du PDF sur le serveur *****************************
            path=u"/tmp/"+filename+u".pdf"
            err=""
            # try:
            #     fichier = open(path, "w")
            # except IOError, e:
            #     err="Problème d'accès au fichier '"+path+"' => "+ str(e)
            if err=="":
                fichier.write(pdf)
                fichier.close()
            # ******************************************************************
            return {'pdf': base64.b64encode(pdf)}


