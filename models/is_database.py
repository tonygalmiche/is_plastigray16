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



    #TODO : Rechercher si le champ actvie existe dans le model concernée et modifié les filtres en conséquence

            #    dest_gabarit_controle_ids = sock.execute(DB, USERID, USERPASS, 'is.gabarit.controle', 'search',
            #     [('is_database_origine_id', '=', controle.id),
            #     '|',
            #        ('active','=',True),('active','=',False)], {})

    def copy_other_database(self, obj, filtre=False):
        if not filtre:
            filtre=[('name', '=', obj.name)]
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
                vals = obj.get_copy_other_database_vals(DB, USERID, USERPASS, sock)
                ids = sock.execute(DB, USERID, USERPASS, model, 'search', [('is_database_origine_id', '=', obj.id)])
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




    # def copy_other_database(self, obj):
    #     try:
    #         cr , uid, context = self.env.args
    #         class_name=obj.__class__.__name__
    #         database_lines = self.env['is.database'].search([])
    #         for database in database_lines:
    #             if database.database:
    #                 _logger.info(u'database='+str(database.database))
    #                 if class_name=='res.partner':
    #                     if obj.id==obj.is_adr_facturation.id:
    #                         raise osv.except_osv('Client recursif 2 !','')
    #                 DB = database.database
    #                 USERID = SUPERUSER_ID
    #                 DBLOGIN = database.login
    #                 USERPASS = database.password
    #                 DB_SERVER = database.ip_server
    #                 DB_PORT = database.port_server
    #                 sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object' % (DB_SERVER, DB_PORT))
    #                 vals=False
    #                 if class_name=='res.partner':
    #                     vals = self.get_partner_vals(obj, DB, USERID, USERPASS, sock)
    #                 if vals:
    #                     ids = sock.execute(DB, USERID, USERPASS, class_name, 'search', [('is_database_origine_id', '=', obj.id),'|',('active','=',True),('active','=',False)], {})
    #                     if not ids:
    #                         if class_name=='res.partner':
    #                             search=[
    #                                 ('name'       , '=', obj.name),
    #                                 ('parent_id'  , '=', obj.parent_id.id or False),
    #                                 ('is_code'    , '=', obj.is_code),
    #                                 ('is_adr_code', '=', obj.is_adr_code),
    #                                 '|',('active','=',True),('active','=',False)
    #                             ]
    #                             ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', search, {})
    #                     if ids:
    #                         sock.execute(DB, USERID, USERPASS, class_name, 'write', ids, vals, {})
    #                         created_id = ids[0]
    #                     else:
    #                         created_id = sock.execute(DB, USERID, USERPASS, class_name, 'create', vals, {})
    #     except Exception as e:
    #         raise osv.except_osv('Client recursif !','')
    #     return True

    # @api.model
    # def get_state_id(self, state , DB, USERID, USERPASS, sock):
    #     state_ids = sock.execute(DB, USERID, USERPASS, 'res.country.state', 'search', [('name', '=', state.name)], {})
    #     if state_ids:
    #         return state_ids[0]
    #     else:
    #         state_vals = {'name':state.name, 'code':state.code, 'country_id':state.country_id and state.country_id.id or False}
    #         new_state_id = sock.execute(DB, USERID, USERPASS, 'res.country.state', 'create', state_vals, {})
    #         return new_state_id

    # @api.model
    # def get_title(self, title , DB, USERID, USERPASS, sock):
    #     title_ids = sock.execute(DB, USERID, USERPASS, 'res.partner.title', 'search', [('name', '=', title.name)], {})
    #     if title_ids:
    #         return title_ids[0]
    #     else:
    #         title_vals = {'name':title.name, 'shortcut':title.shortcut}
    #         new_title_id = sock.execute(DB, USERID, USERPASS, 'res.partner.title', 'create', title_vals, {})
    #         return new_title_id

    # @api.model
    # def get_is_secteur_activite(self, obj , DB, USERID, USERPASS, sock):
    #     ids = sock.execute(DB, USERID, USERPASS, 'is.secteur.activite', 'search', [('is_database_origine_id', '=', obj.id)], {})
    #     if not ids:
    #         obj.copy_other_database_secteur_activite()
    #         ids = sock.execute(DB, USERID, USERPASS, 'is.secteur.activite', 'search', [('is_database_origine_id', '=', obj.id)], {})
    #     if ids:
    #         return ids[0]
    #     return False
            
    # @api.model
    # def create_check_categ(self, category, DB, USERID, USERPASS, sock):
    #     category_ids = sock.execute(DB, USERID, USERPASS, 'res.partner.category', 'search', [('name', '=', category.name)], {})
    #     if category_ids:
    #         return category_ids[0]
    #     else:
    #         category_vals = {'name':category.name, 'parent_id':category.parent_id and self.create_check_categ(category.parent_id, DB, USERID, USERPASS, sock) or False}
    #         categoty_id = sock.execute(DB, USERID, USERPASS, 'res.partner.category', 'create', category_vals, {})
    #         return categoty_id

    # @api.model
    # def _get_category_id(self, category_line_ids, DB, USERID, USERPASS, sock):
    #     categ_lst = []
    #     for category in category_line_ids:
    #         n_categ_id = self.create_check_categ(category, DB, USERID, USERPASS, sock)
    #         categ_lst.append(n_categ_id)
    #     return [(6, 0, categ_lst)]

    # def _get_child_ids(self, child_ids, DB, USERID, USERPASS, sock):
    #     new_child_ids = []
    #     flag = False
    #     for child in child_ids:
    #         dest_child_ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', child.id),'|',('active','=',True),('active','=',False)], {})
    #         if dest_child_ids:
    #             new_child_ids.append(dest_child_ids[0])
    #         else:
    #             child_vals = self.get_partner_vals(child, DB, USERID, USERPASS, sock)
    #             child_created_id = sock.execute(DB, USERID, USERPASS, 'res.partner', 'create', child_vals, {})
    #             new_child_ids.append(child_created_id)
    #     return [(6,0,new_child_ids)]

    # @api.model
    # def get_partner_is_adr_facturation(self, partner, DB, USERID, USERPASS, sock):
    #     partner_obj = self.pool.get('res.partner')
    #     try:
    #         ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', partner.id),'|',('active','=',True),('active','=',False)], {})
    #         if not ids:
    #             self.copy_other_database(partner)
    #             ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', partner.id),'|',('active','=',True),('active','=',False)], {})
    #         if ids:
    #             return ids[0]
    #         return False
    #     except Exception as e:
    #         raise osv.except_osv('Client recursif !','')

    # @api.model
    # def get_partner_parent_id(self, partner, DB, USERID, USERPASS, sock):

    #     ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', partner.id),'|',('active','=',True),('active','=',False)], {})
    #     if not ids:
    #         parent_id=False
    #         if partner.id:
    #             parent_id=self.get_partner_parent_id(partner, DB, USERID, USERPASS, sock)
    #         search=[
    #             ('name'       , '=', partner.name),
    #             ('parent_id'  , '=', parent_id),
    #             ('is_code'    , '=', partner.is_code),
    #             ('is_adr_code', '=', partner.is_adr_code),
    #             '|',('active','=',True),('active','=',False)
    #         ]
    #         ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', search, {})
    #     if ids:
    #         id=ids[0]
    #     else:
    #         vals = self.get_partner_vals(partner, DB, USERID, USERPASS, sock)
    #         id = sock.execute(DB, USERID, USERPASS, 'res.partner', 'create', vals, {})
    #     return id

    # def get_is_transporteur_id(self, obj, DB, USERID, USERPASS, sock):
    #     ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', obj.id),'|',('active','=',True),('active','=',False)], {})
    #     if not ids:
    #         self.copy_other_database(obj)
    #         ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', obj.id),'|',('active','=',True),('active','=',False)], {})
    #     if ids:  
    #         return ids[0]
    #     return False
    
    # def get_is_type_contact(self, obj , DB, USERID, USERPASS, sock):
    #     is_type_contact_ids = sock.execute(DB, USERID, USERPASS, 'is.type.contact', 'search', [('is_database_origine_id', '=', obj.id)], {})
    #     if is_type_contact_ids:
    #         return is_type_contact_ids[0]
    #     else:
    #         vals = {'name':tools.ustr(obj.name), 'is_database_origine_id':obj.id}
    #         is_type_contact = sock.execute(DB, USERID, USERPASS, 'is.type.contact', 'create', vals, {})
    #         return is_type_contact
        
    # def get_is_incoterm(self, obj, DB, USERID, USERPASS, sock):
    #     is_incoterm_ids = sock.execute(DB, USERID, USERPASS, 'stock.incoterms', 'search', [('name', '=', tools.ustr(obj.name))], {})
    #     if is_incoterm_ids:
    #         return is_incoterm_ids[0]
    #     else:
    #         vals = {'name':tools.ustr(obj.name),'code':obj.code, 'active':obj.active}
    #         is_incoterm = sock.execute(DB, USERID, USERPASS, 'stock.incoterms', 'create', vals, {})
    #         return is_incoterm


    # def get_is_rib_id(self, obj , DB, USERID, USERPASS, sock):
    #     is_rib_id = sock.execute(DB, USERID, USERPASS, 'res.partner.bank', 'search', [('acc_number', '=', obj.is_rib_id.acc_number)], {})
    #     if is_rib_id:
    #         return is_rib_id[0]
    #     return False

    # def get_is_type_reglement(self, obj , DB, USERID, USERPASS, sock):
    #     _logger.info(u'get_is_type_reglement : code='+str(obj.is_type_reglement.code))
    #     res = sock.execute(DB, USERID, USERPASS, 'account.journal', 'search', [('code', '=', obj.is_type_reglement.code)], {})
    #     if res:
    #         return res[0]
    #     return False

    # def get_user_id(self, obj , DB, USERID, USERPASS, sock):
    #     user_id = sock.execute(DB, USERID, USERPASS, 'res.users', 'search', [('login', '=', obj.user_id.login)], {})
    #     if user_id:
    #         return user_id[0]
    #     return False

    # def get_is_segment_achat(self, obj , DB, USERID, USERPASS, sock):
    #     is_segment_achat_ids = sock.execute(DB, USERID, USERPASS, 'is.segment.achat', 'search', [('is_database_origine_id', '=', obj.id)], {})
    #     if is_segment_achat_ids:
    #         return is_segment_achat_ids[0]
    #     else:
    #         vals = {'name':tools.ustr(obj.name),'description':tools.ustr(obj.description), 'is_database_origine_id':obj.id}
    #         is_segment_achat = sock.execute(DB, USERID, USERPASS, 'is.segment.achat', 'create', vals, {})
    #         return is_segment_achat
        
    # def get_is_famille_achat_ids(self, obj_ids , DB, USERID, USERPASS, sock):
    #     lst_is_famille_achat_ids = []
    #     for obj in obj_ids:
    #         famille_achat_ids = sock.execute(DB, USERID, USERPASS, 'is.famille.achat', 'search', [('is_database_origine_id', '=', obj.id)], {})
    #         if famille_achat_ids:
    #             lst_is_famille_achat_ids.append(famille_achat_ids[0])
    #         else:
    #             vals = {'is_database_origine_id':obj.id,'name':tools.ustr(obj.name),'description':obj.description, 'segment_id':self.get_is_segment_achat(obj.segment_id , DB, USERID, USERPASS, sock)}
    #             is_famille_achat = sock.execute(DB, USERID, USERPASS, 'is.famille.achat', 'create', vals, {})
    #             lst_is_famille_achat_ids.append(is_famille_achat)
    #     return [(6,0,lst_is_famille_achat_ids)]
        
    # def get_is_site_livre_ids(self, obj_ids , DB, USERID, USERPASS, sock):
    #     lst_site_livre_ids = []
    #     for obj in obj_ids:
    #         is_site_livre_ids = sock.execute(DB, USERID, USERPASS, 'is.site', 'search', [('is_database_origine_id', '=', obj.id)], {})
    #         if is_site_livre_ids:
    #             lst_site_livre_ids.append(is_site_livre_ids[0])
    #         else:
    #             vals = {'name':tools.ustr(obj.name), 'is_database_origine_id':obj.id}
    #             lst_site_livre_id = sock.execute(DB, USERID, USERPASS, 'is.site', 'create', vals, {})
    #             lst_site_livre_ids.append(lst_site_livre_id)
    #     return [(6,0,lst_site_livre_ids)]
    
    # def get_is_transmission_cde(self, obj, DB, USERID, USERPASS, sock):
    #     is_transmission_cde_ids = sock.execute(DB, USERID, USERPASS, 'is.transmission.cde', 'search', [('is_database_origine_id', '=', obj.id)], {})
    #     if is_transmission_cde_ids:
    #         return is_transmission_cde_ids[0]
    #     else:
    #         vals = {'name':tools.ustr(obj.name), 'is_database_origine_id':obj.id}
    #         is_transmission_cde = sock.execute(DB, USERID, USERPASS, 'is.transmission.cde', 'create', vals, {})
    #         return is_transmission_cde
    #         return False
    
    # def get_is_norme(self, obj, DB, USERID, USERPASS, sock):
    #     is_norme_ids = sock.execute(DB, USERID, USERPASS, 'is.norme.certificats', 'search', [('is_database_origine_id', '=', obj.id)], {})
    #     if is_norme_ids:
    #         return is_norme_ids[0]
    #     else:
    #         vals = {'name':tools.ustr(obj.name), 'is_database_origine_id':obj.id}
    #         is_norme = sock.execute(DB, USERID, USERPASS, 'is.norme.certificats', 'create', vals, {})
    #         return is_norme
    #         return False
    
    # def get_is_certifications(self, obj_ids, DB, USERID, USERPASS, sock):
    #     lst_is_certifications = []
    #     for obj in obj_ids:
    #         is_certifications_ids = sock.execute(DB, USERID, USERPASS, 'is.certifications.qualite', 'search', [('is_database_origine_id', '=', obj.id)], {})
    #         if is_certifications_ids:
    #             lst_is_certifications.append(is_certifications_ids[0])
    #         else:
    #             vals = {'is_norme':obj.is_norme and self.get_is_norme(obj.is_norme, DB, USERID, USERPASS, sock) or False,
    #                     'is_date_validation':obj.is_date_validation,
    #                     'is_database_origine_id':obj.id,
    #                     }
    #             is_certifications = sock.execute(DB, USERID, USERPASS, 'is.certifications.qualite', 'create', vals, {})
    #             lst_is_certifications.append(is_certifications)
    #     return [(6,0,lst_is_certifications)]
    
    # def get_is_database_line_ids(self, partner , DB, USERID, USERPASS, sock):
    #     lst_is_database_line_ids = []
    #     obj_ids = partner.is_database_line_ids
    #     for obj in obj_ids:
    #         is_database_line_ids = sock.execute(DB, USERID, USERPASS, 'is.database', 'search', [('is_database_origine_id', '=', obj.id)], {})
    #         if is_database_line_ids:
    #             lst_is_database_line_ids.append(is_database_line_ids[0])
    #         else:
    #             vals = {'name':obj.name,
    #                     'is_database_origine_id':obj.id,
    #                     }
    #             is_database_line_id = sock.execute(DB, USERID, USERPASS, 'is.database', 'create', vals, {})
    #             lst_is_database_line_ids.append(is_database_line_id)
    #     return [(6,0,lst_is_database_line_ids)]
        
    # @api.model
    # def get_partner_vals(self, partner, DB, USERID, USERPASS, sock):
    #     partner_vals = {
    #         'name': tools.ustr(partner.name),
    #         'is_raison_sociale2' : partner.is_raison_sociale2,
    #         'is_code'            : partner.is_code,
    #         'is_adr_code'        : partner.is_adr_code,
    #         'category_id'        : partner.category_id and self._get_category_id(partner.category_id, DB, USERID, USERPASS, sock)or [],
    #         'is_company'         : partner.is_company,
    #         'street'             : partner.street,
    #         'street2'            : partner.street2,
    #         'is_rue3'            : partner.is_rue3,
    #         'city'               : partner.city,
    #         'state_id'           : partner.state_id and self.get_state_id(partner.state_id, DB, USERID, USERPASS, sock) or False,
    #         'zip'                : partner.zip,
    #         'country_id'         : partner.country_id.id or False,
    #         'is_adr_facturation' : partner.is_adr_facturation and self.get_partner_is_adr_facturation(partner.is_adr_facturation, DB, USERID, USERPASS, sock) or False,
    #         'website'            : partner.website,
    #         'function'           : partner.function,
    #         'phone'              : partner.phone,
    #         'mobile'             : partner.mobile,
    #         'fax'                : partner.fax,
    #         'email'              : partner.email,
    #         'title'              : partner.title and self.get_title(partner.title , DB, USERID, USERPASS, sock) or False,
    #         'is_secteur_activite': partner.is_secteur_activite and self.get_is_secteur_activite(partner.is_secteur_activite , DB, USERID, USERPASS, sock) or False,
    #         'customer'           : partner.customer,
    #         'supplier'           : partner.supplier,
    #         'is_database_origine_id': partner.id,
    #         'is_raison_sociale2'    :  partner.is_raison_sociale2,
    #         'is_code'               :  partner.is_code,
    #         'is_adr_code'           :  partner.is_adr_code,
    #         'is_rue3'               :  partner.is_rue3,
    #         'is_type_contact'       :  partner.is_type_contact and self.get_is_type_contact(partner.is_type_contact , DB, USERID, USERPASS, sock) or False,
    #         'is_adr_groupe'         :  partner.is_adr_groupe,
    #         'is_cofor'              :  partner.is_cofor,
    #         'is_num_siret'          :  partner.is_num_siret,
    #         'is_code_client'        :  partner.is_code_client,
    #         'is_segment_achat'      :  partner.is_segment_achat and self.get_is_segment_achat(partner.is_segment_achat , DB, USERID, USERPASS, sock) or False,
    #         'is_famille_achat_ids'  :  partner.is_famille_achat_ids and self.get_is_famille_achat_ids(partner.is_famille_achat_ids , DB, USERID, USERPASS, sock) or False,
    #         'is_fournisseur_imp'    :  partner.is_fournisseur_imp,
    #         'is_fournisseur_da_fg'  :  partner.is_fournisseur_da_fg,
    #         'is_site_livre_ids'     :  partner.is_site_livre_ids and self.get_is_site_livre_ids(partner.is_site_livre_ids , DB, USERID, USERPASS, sock) or False,
    #         'is_groupage'           :  partner.is_groupage,
    #         'is_tolerance_delai'    :  partner.is_tolerance_delai,
    #         'is_nb_jours_tolerance' :  partner.is_nb_jours_tolerance,
    #         'is_tolerance_quantite' :  partner.is_tolerance_quantite,
    #         'is_transmission_cde'   :  partner.is_transmission_cde and self.get_is_transmission_cde(partner.is_transmission_cde , DB, USERID, USERPASS, sock) or False,
    #         'is_certifications'     :  partner.is_certifications and self.get_is_certifications(partner.is_certifications , DB, USERID, USERPASS, sock) or False,
    #         'is_adr_liv_sur_facture' : partner.is_adr_liv_sur_facture,
    #         'is_num_autorisation_tva': partner.is_num_autorisation_tva,
    #         'is_caracteristique_bl'  : partner.is_caracteristique_bl,
    #         'is_mode_envoi_facture'  : partner.is_mode_envoi_facture,
    #         'is_database_line_ids'   : self.get_is_database_line_ids(partner, DB, USERID, USERPASS, sock) or False,
    #         'vat'                            : partner.vat,
    #         'property_account_position'      : partner.property_account_position.id,
    #         'property_payment_term'          : partner.property_payment_term.id,
    #         'property_supplier_payment_term' : partner.property_supplier_payment_term.id,
    #         'is_escompte'                    : partner.is_escompte.id,
    #         'is_type_reglement'              : partner.is_type_reglement and self.get_is_type_reglement(partner, DB, USERID, USERPASS, sock) or False,
    #         'is_rib_id'                      : partner.is_rib_id and self.get_is_rib_id(partner, DB, USERID, USERPASS, sock) or False,
    #         'user_id'                        : partner.user_id and self.get_user_id(partner, DB, USERID, USERPASS, sock) or False,
    #         'active'                 : partner.active,
    #     }
    #     db_ids = self.env['is.database'].search([('database','=',DB)])
    #     if db_ids:
    #         is_database_line_ids = partner_vals.get('is_database_line_ids',[]) and partner_vals.get('is_database_line_ids',[])[0][2]
    #         database_rec = sock.execute(DB, USERID, USERPASS, 'is.database', 'read', is_database_line_ids,['is_database_origine_id','name'], {})
    #         origin_db_ids = []
    #         if database_rec:
    #             for db_rec in database_rec:
    #                 if db_rec.get('is_database_origine_id',False):
    #                     origin_db_ids.append(db_rec.get('is_database_origine_id'))
    #         if db_ids[0].id not in origin_db_ids:
    #             partner_vals.update({'active':False})
    #     if partner.is_company:
    #         partner_vals.update({'child_ids':partner.child_ids and self._get_child_ids(partner.child_ids, DB, USERID, USERPASS, sock) or [] })
    #     return partner_vals


    # def write(self, vals):
    #     try:
    #         res=super(is_database, self).write(vals)
    #         for obj in self:
    #             if obj.database:
    #                 obj.copy_other_database_is_database()
    #         return res
    #     except Exception as e:
    #         raise osv.except_osv(_('database!'),
    #                          _('(%s).') % str(e).decode('utf-8'))

    # def create(self, vals):
    #     try:
    #         obj=super(is_database, self).create(vals)
    #         obj.copy_other_database_is_database()
    #         return obj
    #     except Exception as e:
    #         raise osv.except_osv(_('database!'),
    #                          _('(%s).') % str(e).decode('utf-8'))

    


    # def copy_other_database_is_database(self):
    #     cr , uid, context = self.env.args
    #     context = dict(context)
    #     database_obj = self.env['is.database']
    #     database_lines = database_obj.search([])
    #     for obj in self:
    #         for database in database_lines:
    #             if not database.ip_server or not database.database or not database.port_server or not database.login or not database.password:
    #                 continue
    #             DB = database.database
    #             USERID = SUPERUSER_ID
    #             DBLOGIN = database.login
    #             USERPASS = database.password
    #             DB_SERVER = database.ip_server
    #             DB_PORT = database.port_server
    #             sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object' % (DB_SERVER, DB_PORT))
    #             vals = self.get_is_database_vals(obj, DB, USERID, USERPASS, sock)
    #             ids = sock.execute(DB, USERID, USERPASS, 'is.database', 'search', [('is_database_origine_id', '=', obj.id)], {})
    #             if not ids:
    #                 ids = sock.execute(DB, USERID, USERPASS, 'is.database', 'search', [('name', '=', obj.name)], {})
    #             if ids:
    #                 sock.execute(DB, USERID, USERPASS, 'is.database', 'write', ids, vals, {})
    #                 created_id = ids[0]
    #             else:
    #                 created_id = sock.execute(DB, USERID, USERPASS, 'is.database', 'create', vals, {})
    #     return True


    # @api.model
    # def get_is_database_vals(self, obj, DB, USERID, USERPASS, sock):
    #     vals ={
    #         'name'                   : tools.ustr(obj.name),
    #         'is_database_origine_id' : obj.id,
    #     }
    #     return vals







    
    

    
# class is_type_equipement(models.Model):
#     _inherit='is.type.equipement'

#     is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    
    
#     def write(self, vals):
#         try:
#             res=super(is_type_equipement, self).write(vals)
#             for obj in self:
#                 obj.copy_other_database_type_equipement()
#             return res
#         except Exception as e:
#             raise osv.except_osv(_('Equipement!'),
#                              _('(%s).') % str(e).decode('utf-8'))


#     @api.model
#     def create(self, vals):
#         try:
#             obj=super(is_type_equipement, self).create(vals)
#             obj.copy_other_database_type_equipement()
#             return obj
#         except Exception as e:
#             raise osv.except_osv(_('Equipement!'),
#                              _('(%s).') % str(e).decode('utf-8'))
            
#     def copy_other_database_type_equipement(self):
#         cr , uid, context = self.env.args
#         context = dict(context)
#         database_obj = self.env['is.database']
#         database_lines = database_obj.search([])
#         for equipement in self:
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
#                 type_equipement_vals = self.get_type_equipement_vals(equipement, DB, USERID, USERPASS, sock)
#                 dest_type_equipement_ids = sock.execute(DB, USERID, USERPASS, 'is.type.equipement', 'search', [('is_database_origine_id', '=', equipement.id)], {})
#                 if not dest_type_equipement_ids:
#                     dest_type_equipement_ids = sock.execute(DB, USERID, USERPASS, 'is.type.equipement', 'search', [('name', '=', equipement.name)], {})
#                 if dest_type_equipement_ids:
#                     sock.execute(DB, USERID, USERPASS, 'is.type.equipement', 'write', dest_type_equipement_ids, type_equipement_vals, {})
#                     type_equipement_created_id = dest_type_equipement_ids[0]
#                 else:
#                     type_equipement_created_id = sock.execute(DB, USERID, USERPASS, 'is.type.equipement', 'create', type_equipement_vals, {})
#         return True

#     @api.model
#     def get_type_equipement_vals(self, equipement, DB, USERID, USERPASS, sock):
#         type_equipement_vals ={
#                      'name' : tools.ustr(equipement.name),
#                      'is_database_origine_id':equipement.id,
#                      }
#         return type_equipement_vals



