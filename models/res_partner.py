# -*- coding: utf-8 -*-
from odoo import models,fields,api,tools,SUPERUSER_ID
import os
import time
import datetime
import base64
from xmlrpc import client as xmlrpclib

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


class is_site(models.Model):
    _name = 'is.site'
    _description = 'Sites'
    
    name = fields.Char('Site', required=True) 
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
            'name' : self.name,
            'is_database_origine_id':self.id
        }
        return vals
    

class is_segment_achat(models.Model):
    _name = 'is.segment.achat'
    _description = "Segment d'achat"
    
    name        = fields.Char('Code', size=256, required=True)
    description = fields.Text('Commentaire')
    family_line = fields.One2many('is.famille.achat', 'segment_id', 'Familles')
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
            'description'           : self.description,
            'is_database_origine_id': self.id
        }
        return vals


class is_famille_achat(models.Model):
    _name = 'is.famille.achat'
    _description = "Famille d'achat"
    
    name        = fields.Char('Code', size=256, required=True)
    segment_id  = fields.Many2one('is.segment.achat', 'Segment', required=True)
    description = fields.Text('Commentaire')  
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
            'description'           : self.description,
            'segment_id'            : self.get_segment_id(DB, USERID, USERPASS, sock),
            'is_database_origine_id': self.id
        }
        return vals

    def get_segment_id(self, DB, USERID, USERPASS, sock):
        if self.segment_id:
            segment_ids = sock.execute(DB, USERID, USERPASS, 'is.segment.achat', 'search', [('is_database_origine_id', '=', self.segment_id.id)])
            if not segment_ids:
                self.env['is.database'].copy_other_database(self.segment_id)
                segment_ids = sock.execute(DB, USERID, USERPASS, 'is.segment.achat', 'search', [('is_database_origine_id', '=', self.segment_id.id)])
            if segment_ids:
                return segment_ids[0]
        return False


class is_transmission_cde(models.Model):
    _name = 'is.transmission.cde'
    _description = 'Mode de transmission des cmds'
    
    name        = fields.Char('Mode de transmission des commandes', required=True)
    commentaire = fields.Char('Commentaire')
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
            'commentaire'           : self.commentaire,
            'is_database_origine_id': self.id
        }
        return vals


class is_norme_certificats(models.Model):
    _name = 'is.norme.certificats'
    _description = u'Norme Certificat qualit??'
    
    name                   = fields.Char('Nome certificat', required=True)
    notation_fournisseur   = fields.Integer('Coefficient notation fournisseur')
    commentaire            = fields.Char('Commentaire')
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
            'notation_fournisseur'  : self.notation_fournisseur,
            'commentaire'           : self.commentaire,
            'is_database_origine_id': self.id
        }
        return vals


class is_certifications_qualite(models.Model):
    _name = 'is.certifications.qualite'
    _description = u'Certifications qualit??'
    
    is_norme           = fields.Many2one('is.norme.certificats', u'Norme Certificat qualit??', required=True)
    is_date_validation = fields.Date(u'Date de validit?? du certificat', required=True)
    is_certificat      = fields.Binary('Certificat qualit??')
    is_certificat_ids  = fields.Many2many('ir.attachment', 'is_certificat_attachment_rel', 'certificat_id', 'attachment_id', u'Pi??ces jointes')
    partner_id         = fields.Many2one('res.partner', 'Client/Fournisseur')    
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    
    def write(self, vals):
        res=super().write(vals)
        for obj in self:
            filtre=[('is_norme', '=', obj.is_norme.id),('is_date_validation', '=', obj.is_date_validation)]
            self.env['is.database'].copy_other_database(obj,filtre)
        return res
            
    @api.model_create_multi
    def create(self, vals_list):
        res=super().create(vals_list)
        filtre=[('is_norme', '=', res.is_norme.id),('is_date_validation', '=', res.is_date_validation)]
        self.env['is.database'].copy_other_database(res,filtre)
        return res

    def get_copy_other_database_vals(self, DB, USERID, USERPASS, sock):
        vals ={
            'is_norme'              : self.get_is_norme(DB, USERID, USERPASS, sock),
            'is_date_validation'    : self.is_date_validation,
            'is_certificat_ids'     : self._get_certificat_ids(DB, USERID, USERPASS, sock),
            'is_database_origine_id': self.id
        }
        return vals

    def get_is_norme(self, DB, USERID, USERPASS, sock):
        if self.is_norme:
            ids = sock.execute(DB, USERID, USERPASS, 'is.norme.certificats', 'search', [('is_database_origine_id', '=', self.is_norme.id)])
            if not ids:
                self.env['is.database'].copy_other_database(self.is_norme)
                ids = sock.execute(DB, USERID, USERPASS, 'is.norme.certificats', 'search', [('is_database_origine_id', '=', self.is_norme.id)])
            if ids:
                return ids[0]
        return False

    def _get_certificat_ids(self, DB, USERID, USERPASS, sock):
        certificat_data = []
        for  certificat in self.is_certificat_ids:
            certificat_data.append(((0, 0, {'name':tools.ustr(certificat.name), 'datas':certificat.datas, 'res_model':certificat.res_model})))
        return certificat_data


class is_secteur_activite(models.Model):
    _name='is.secteur.activite'
    _description="Secteur d'activit??"
    _order='name'
    _sql_constraints = [('name_uniq','UNIQUE(name)', 'Ce code existe d??j??')] 

    name        = fields.Char("Secteur d'activit??", required=True)
    commentaire = fields.Char('Commentaire') 
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
            'commentaire'           : self.commentaire,
            'is_database_origine_id': self.id
        }
        return vals


class is_type_contact(models.Model):
    _name='is.type.contact'
    _description="Type de contact"
    _order='name'
    _sql_constraints = [('name_uniq','UNIQUE(name)', 'Ce code existe d??j??')] 

    name        = fields.Char("Type de contact", required=True)
    commentaire = fields.Char('Commentaire')
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
            'commentaire'           : self.commentaire,
            'is_database_origine_id': self.id
        }
        return vals


class is_escompte(models.Model):
    _name='is.escompte'
    _description="Escompte"
    _order='name'

    name = fields.Char("Intitul??", required=True)
    taux = fields.Float("Taux d'escompte", required=True)
    compte = fields.Many2one('account.account', "Compte")
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
            'taux'                  : self.taux,
            'compte'                : self.get_compte(DB, USERID, USERPASS, sock),
            'is_database_origine_id': self.id
        }
        return vals

    def get_compte(self, DB, USERID, USERPASS, sock):
        if self.compte:
            ids = sock.execute(DB, USERID, USERPASS, 'account.account', 'search', [('code', '=', self.compte.code)])
            if ids:
                return ids[0]
        return False


class res_partner_category(models.Model):
    _inherit = 'res.partner.category'

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


class res_partner(models.Model):
    _inherit = 'res.partner'

    def _get_default_location(self):
        company_id = self.env.user.company_id.id
        warehouse_obj = self.env['stock.warehouse']
        warehouse_id = warehouse_obj.search([('company_id','=',company_id)])
        location = warehouse_id.out_type_id and  warehouse_id.out_type_id.default_location_src_id
        return location and location or False

    customer   = fields.Boolean('Client')      # Champ ajout?? car n'existe plus dans Odoo 16
    supplier   = fields.Boolean('Fournisseur') # Champ ajout?? car n'existe plus dans Odoo 16
    fax        = fields.Char('Fax')            # Champ ajout?? car n'existe plus dans Odoo 16

    display_name            = fields.Char(string='Nom affich??', compute='_compute_display_name')
    is_transporteur_id      = fields.Many2one('res.partner', 'Transporteur')
    is_delai_transport      = fields.Integer('Delai de transport (jour)')
    is_livre_a_id           = fields.Many2one('res.partner', 'Livrer ??', help="Indiquez l'adresse de livraison si celle-ci est diff??rente de celle de la soci??t??")
    is_certificat_matiere   = fields.Boolean(u'Certificat mati??re demand??')
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
    is_secteur_activite     = fields.Many2one('is.secteur.activite', "Secteur d'activit??")
    is_type_contact         = fields.Many2one('is.type.contact', "Type de contact")
    is_adr_facturation      = fields.Many2one('res.partner', 'Adresse de facturation')
    is_adr_groupe           = fields.Char('Code auxiliaire comptable', help="Code auxiliaire comptable de l'adresse groupe pour la comptabilit??")
    is_cofor                = fields.Char('N?? fournisseur (COFOR)', help="Notre code fourniseur chez le client")
    is_incoterm             = fields.Many2one('account.incoterms', "Incoterm  / Conditions de livraison")
    is_lieu                 = fields.Char("Lieu")
    is_escompte             = fields.Many2one('is.escompte', "Escompte")
    is_type_reglement       = fields.Many2one('account.journal', u'Type r??glement', domain=[('type', 'in', ['bank','cash'])])
    is_num_siret            = fields.Char(u'N?? de SIRET')
    is_code_client          = fields.Char('Code client', help=u'Notre code client chez le fourniseur')
    is_segment_achat        = fields.Many2one('is.segment.achat', "Segment d'achat")
    is_famille_achat_ids    = fields.Many2many('is.famille.achat', "res_partner_famille_achat_rel", 'partner_id', 'famille_id', string="Famille d'achat")
    is_fournisseur_imp      = fields.Boolean(u'Fournisseur impos??')
    is_fournisseur_da_fg    = fields.Boolean(u'Fournisseur pour DA-FG')
    is_site_livre_ids       = fields.Many2many('is.site', "res_partner_site_livre_rel", 'partner_id', 'site_id', string='sites livr??s')
    is_groupage             = fields.Boolean('Groupage')
    is_tolerance_delai      = fields.Boolean('Tol??rance sur d??lai')
    is_nb_jours_tolerance   = fields.Integer('Nb jours tol??rance sur d??lai')
    is_tolerance_quantite   = fields.Boolean('Tol??rance sur quantit??')
    is_transmission_cde     = fields.Many2one('is.transmission.cde', 'Mode de transmission des commandes')
    is_certifications       = fields.One2many('is.certifications.qualite', 'partner_id', u'Certification qualit??')
    is_type_contact         = fields.Many2one('is.type.contact', "Type de contact")
    is_source_location_id   = fields.Many2one('stock.location', 'Source Location', default=_get_default_location) 
    is_rib_id               = fields.Many2one('res.partner.bank', 'RIB') 
    is_adr_liv_sur_facture  = fields.Boolean(u"Afficher l'adresse de livraison sur la facture", default=True)
    is_num_autorisation_tva = fields.Char("N?? d'autorisation", help="N?? d'autorisation de franchise de taxe")
    is_caracteristique_bl   = fields.Selection([
        ('cde_odoo'   , '1 commande Odoo = 1 BL'),
        ('cde_client' , '1 commande client = 1 BL'),
        ('ref_article', '1 r??f??rence client = 1 BL'),
    ], 'Caract??ristique des BL')
    is_mode_envoi_facture   = fields.Selection([
        ('courrier'        , 'Envoi par courrier'),
        ('courrier2'       , 'Envoi par courrier en double exemplaire'),
        ('mail'            , 'Envoi par mail (1 mail par facture)'),
        ('mail2'           , 'Envoi par mail (1 mail par facture en double exemplaire)'),
        ('mail_client'     , 'Envoi par mail (1 mail par client)'),
        ('mail_client_bl'  , 'Envoi par mail avec BL (1 mail par client)'),
        ('mail_regroupe_bl', 'Regroupement des BL sur une m??me facture et envoi par mail'),
    ], "Mode d'envoi des factures")
    is_type_cde_fournisseur = fields.Selection(type_commande_list, "Type commande fourniseur", readonly=True)
    is_horizon_besoins      = fields.Integer(u'Horizon des besoins (jour)', help=u"Champ utilis?? pour le mail de l'horizon des besoins (7 jours en g??n??ral ou 21 jours pendant la p??riode de vacances)")

    is_database_origine_id = fields.Integer("Id d'origine", readonly=True, index=True)
    is_database_line_ids   = fields.Many2many('is.database','partner_database_rel','partner_id','database_id', string="Sites")


    _defaults = {
        'delai_transport'     : 0,
        'is_adr_code'         : 0,
        'is_fournisseur_da_fg': False,
        'is_horizon_besoins'  : 7,
    }

    # _sql_constraints = [
    #     ('code_adr_uniq', 'unique(is_code, is_adr_code, company_id)', u'Le code et le code adresse doivent ??tre uniques par soci??t??!'),
    # ]
    

    # # Le champ display_name est un champ standard d'Odoo correspondant au titre de la fiche
    # # Cette fonction appelle la fonction name_get => Elle permet de d??finir les d??pendances de champs
    # @api.one
    # @api.depends('name', 'parent_id.name','is_code', 'is_adr_code')
    # def _compute_display_name(self):
    #     r=self.name_get()
    #     self.display_name = r[0][1]


    def _get_partner_filtre(self):
        filtre=[
            ('name'       , '=', self.name),
            ('parent_id'  , '=', self.parent_id.id),
            ('is_code'    , '=', self.is_code),
            ('is_adr_code', '=', self.is_adr_code),
            '|',('active','=',True),('active','=',False)
        ]
        return filtre

    def write(self, vals):
        res=super().write(vals)
        for obj in self:
            filtre=obj._get_partner_filtre()
            self.env['is.database'].copy_other_database(obj,filtre)
        return res
            
    @api.model_create_multi
    def create(self, vals_list):
        res=super().create(vals_list)
        for obj in res:
            filtre=obj._get_partner_filtre()
            self.env['is.database'].copy_other_database(obj,filtre)
        return res

    def get_copy_other_database_vals(self, DB, USERID, USERPASS, sock):
        vals ={
            'name'               : self.name,
            'is_raison_sociale2' : self.is_raison_sociale2,
            'is_code'            : self.is_code,
            'is_adr_code'        : self.is_adr_code,
            'category_id'        : self._get_category_id(DB, USERID, USERPASS, sock),
            'parent_id'          : self._get_parent_id(DB, USERID, USERPASS, sock),
            'is_company'         : self.is_company,
            'street'             : self.street,
            'street2'            : self.street2,
            'is_rue3'            : self.is_rue3,
            'city'               : self.city,
            'state_id'           : self._get_state_id(DB, USERID, USERPASS, sock),
            'zip'                : self.zip,
            'country_id'         : self.country_id.id or False,
            'is_adr_facturation' : self._get_partner_is_adr_facturation(DB, USERID, USERPASS, sock),
            'website'            : self.website,
            'function'           : self.function,
            'phone'              : self.phone,
            'mobile'             : self.mobile,
            'fax'                : self.fax,
            'email'              : self.email,
            'title'              : self._get_title(DB, USERID, USERPASS, sock),
            'is_secteur_activite': self._get_is_secteur_activite(DB, USERID, USERPASS, sock),
            'customer'           : self.customer,
            'supplier'           : self.supplier,
            'is_raison_sociale2'    :  self.is_raison_sociale2,
            'is_code'               :  self.is_code,
            'is_adr_code'           :  self.is_adr_code,
            'is_rue3'               :  self.is_rue3,
            'is_type_contact'       :  self._get_is_type_contact(DB, USERID, USERPASS, sock),
            'is_adr_groupe'         :  self.is_adr_groupe,
            'is_cofor'              :  self.is_cofor,
            'is_num_siret'          :  self.is_num_siret,
            'is_code_client'        :  self.is_code_client,
            'is_segment_achat'      :  self._get_is_segment_achat(DB, USERID, USERPASS, sock),
            'is_famille_achat_ids'  :  self._get_is_famille_achat_ids(DB, USERID, USERPASS, sock),
            'is_fournisseur_imp'    :  self.is_fournisseur_imp,
            'is_fournisseur_da_fg'  :  self.is_fournisseur_da_fg,
            'is_site_livre_ids'     :  self._get_is_site_livre_ids(DB, USERID, USERPASS, sock),
            'is_groupage'           :  self.is_groupage,
            'is_tolerance_delai'    :  self.is_tolerance_delai,
            'is_nb_jours_tolerance' :  self.is_nb_jours_tolerance,
            'is_tolerance_quantite' :  self.is_tolerance_quantite,
            'is_transmission_cde'   :  self._get_is_transmission_cde(DB, USERID, USERPASS, sock),
            'is_certifications'     :  self._get_is_certifications(DB, USERID, USERPASS, sock),
            'is_adr_liv_sur_facture' : self.is_adr_liv_sur_facture,
            'is_num_autorisation_tva': self.is_num_autorisation_tva,
            'is_caracteristique_bl'  : self.is_caracteristique_bl,
            'is_mode_envoi_facture'  : self.is_mode_envoi_facture,
            'is_database_line_ids'   : self._get_is_database_line_ids(DB, USERID, USERPASS, sock),
            'vat'                              : self.vat,
            'property_account_position_id'     : self.property_account_position_id.id,
            'property_payment_term_id'         : self.property_payment_term_id.id,
            'property_supplier_payment_term_id': self.property_supplier_payment_term_id.id,
            'is_escompte'                      : self.is_escompte.id,
            'is_type_reglement'                : self._get_is_type_reglement(DB, USERID, USERPASS, sock),
            'is_rib_id'                        : self._get_is_rib_id(DB, USERID, USERPASS, sock),
            'user_id'                          : self._get_user_id(DB, USERID, USERPASS, sock),
            'active'                           : self._get_active(DB, USERID, USERPASS, sock),
            'is_database_origine_id'           : self.id
        }
        return vals
    
    def _get_parent_id(self, DB, USERID, USERPASS, sock):
        ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', self.parent_id.id),'|',('active','=',True),('active','=',False)])
        if not ids:
            filtre=[
                ('name'       , '=', self.parent_id.name),
                ('parent_id'  , '=', self.parent_id.parent_id.id),
                ('is_code'    , '=', self.parent_id.is_code),
                ('is_adr_code', '=', self.parent_id.is_adr_code),
                '|',('active','=',True),('active','=',False)
            ]
            self.env['is.database'].copy_other_database(self.parent_id, filtre)
            ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', self.parent_id.id),'|',('active','=',True),('active','=',False)])
        if ids:
            return ids[0]
        return False

    def _get_category_id(self, DB, USERID, USERPASS, sock):
        categ_lst = []
        for category in self.category_id:
            ids = sock.execute(DB, USERID, USERPASS, 'res.partner.category', 'search', [('name', '=', category.name)])
            if not ids:
                self.env['is.database'].copy_other_database(category)
                ids = sock.execute(DB, USERID, USERPASS, 'res.partner.category', 'search', [('name', '=', category.name)])
            if ids:
                categ_lst.append(ids[0])
        return [(6, 0, categ_lst)]

    def _get_state_id(self, DB, USERID, USERPASS, sock):
        if not self.state_id:
            return False
        ids = sock.execute(DB, USERID, USERPASS, 'res.country.state', 'search', [('name', '=', self.state_id.name)])
        if ids:
            return ids[0]
        else:
            vals = {
                'name'      : self.state_id.name, 
                'code'      : self.state_id.code, 
                'country_id': self.state_id.country_id.id,
            }
            id = sock.execute(DB, USERID, USERPASS, 'res.country.state', 'create', vals)
            return id

    def _get_partner_is_adr_facturation(self, DB, USERID, USERPASS, sock):
        ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', self.is_adr_facturation.id),'|',('active','=',True),('active','=',False)])
        if not ids:
            self.env['is.database'].copy_other_database(self.is_adr_facturation)
            ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', self.is_adr_facturation.id),'|',('active','=',True),('active','=',False)])
        if ids:
            return ids[0]
        return False

    def _get_title(self, DB, USERID, USERPASS, sock):
        if not self.title:
            return False
        ids = sock.execute(DB, USERID, USERPASS, 'res.partner.title', 'search', [('name', '=', self.title.name)])
        if ids:
            return ids[0]
        else:
            vals = {'name':self.title.name, 'shortcut':self.title.shortcut}
            id = sock.execute(DB, USERID, USERPASS, 'res.partner.title', 'create', vals)
            return id

    def _get_is_secteur_activite(self, DB, USERID, USERPASS, sock):
        ids = sock.execute(DB, USERID, USERPASS, 'is.secteur.activite', 'search', [('is_database_origine_id', '=', self.is_secteur_activite.id)])
        if not ids:
            self.env['is.database'].copy_other_database(self.is_secteur_activite)
            ids = sock.execute(DB, USERID, USERPASS, 'is.secteur.activite', 'search', [('is_database_origine_id', '=', self.is_secteur_activite.id)])
        if ids:
            return ids[0]
        return False
            
    def _get_is_type_contact(self, DB, USERID, USERPASS, sock):
        ids = sock.execute(DB, USERID, USERPASS, 'is.type.contact', 'search', [('is_database_origine_id', '=', self.is_type_contact.id)])
        if not ids:
            self.env['is.database'].copy_other_database(self.is_type_contact)
            ids = sock.execute(DB, USERID, USERPASS, 'is.type.contact', 'search', [('is_database_origine_id', '=', self.is_type_contact.id)])
        if ids:
            return ids[0]
        return False

    def _get_is_segment_achat(self, DB, USERID, USERPASS, sock):
        ids = sock.execute(DB, USERID, USERPASS, 'is.segment.achat', 'search', [('is_database_origine_id', '=', self.is_segment_achat.id)])
        if not ids:
            self.env['is.database'].copy_other_database(self.is_segment_achat)
            ids = sock.execute(DB, USERID, USERPASS, 'is.segment.achat', 'search', [('is_database_origine_id', '=', self.is_segment_achat.id)])
        if ids:
            return ids[0]
        return False

    def _get_is_famille_achat_ids(self, DB, USERID, USERPASS, sock):
        lst_is_famille_achat_ids = []
        for obj in self.is_famille_achat_ids:
            ids = sock.execute(DB, USERID, USERPASS, 'is.famille.achat', 'search', [('is_database_origine_id', '=', obj.id)])
            if not ids:
                self.env['is.database'].copy_other_database(obj)
                ids = sock.execute(DB, USERID, USERPASS, 'is.segment.achat', 'search', [('is_database_origine_id', '=', obj.id)])
            if ids:
                lst_is_famille_achat_ids.append(ids[0])
        return [(6,0,lst_is_famille_achat_ids)]
         
    def _get_is_site_livre_ids(self, DB, USERID, USERPASS, sock):
        lst_site_livre_ids = []
        for obj in self.is_site_livre_ids:
            ids = sock.execute(DB, USERID, USERPASS, 'is.site', 'search', [('is_database_origine_id', '=', obj.id)])
            if not ids:
                self.env['is.database'].copy_other_database(obj)
                ids = sock.execute(DB, USERID, USERPASS, 'is.site', 'search', [('is_database_origine_id', '=', obj.id)])
            if ids:
                lst_site_livre_ids.append(ids[0])
        return [(6,0,lst_site_livre_ids)]
          
    def _get_is_transmission_cde(self, DB, USERID, USERPASS, sock):
        ids = sock.execute(DB, USERID, USERPASS, 'is.transmission.cde', 'search', [('is_database_origine_id', '=', self.is_transmission_cde.id)])
        if not ids:
            self.env['is.database'].copy_other_database(self.is_transmission_cde)
            ids = sock.execute(DB, USERID, USERPASS, 'is.transmission.cde', 'search', [('is_database_origine_id', '=', self.is_transmission_cde.id)])
        if ids:
            return ids[0]
        return False

    def _get_is_certifications(self, DB, USERID, USERPASS, sock):
        lst_is_certifications = []
        for obj in self.is_certifications:
            ids = sock.execute(DB, USERID, USERPASS, 'is.certifications.qualite', 'search', [('is_database_origine_id', '=', obj.id)])
            if not ids:
                self.env['is.database'].copy_other_database(obj)
                ids = sock.execute(DB, USERID, USERPASS, 'is.certifications.qualite', 'search', [('is_database_origine_id', '=', obj.id)])
            if ids:
                lst_is_certifications.append(ids[0])
        return [(6,0,lst_is_certifications)]
    
    def _get_is_database_line_ids(self, DB, USERID, USERPASS, sock):
        lst_is_database_line_ids = []
        for obj in self.is_database_line_ids:
            ids = sock.execute(DB, USERID, USERPASS, 'is.database', 'search', [('is_database_origine_id', '=', obj.id)])
            if not ids:
                self.env['is.database'].copy_other_database(obj)
                ids = sock.execute(DB, USERID, USERPASS, 'is.database', 'search', [('is_database_origine_id', '=', obj.id)])
            if ids:
                lst_is_database_line_ids.append(ids[0])
        return [(6,0,lst_is_database_line_ids)]
        
    def _get_is_type_reglement(self, DB, USERID, USERPASS, sock):
        ids = sock.execute(DB, USERID, USERPASS, 'account.journal', 'search', [('code', '=', self.is_type_reglement.code)])
        if ids:
            return ids[0]
        return False

    def _get_is_rib_id(self, DB, USERID, USERPASS, sock):
        ids = sock.execute(DB, USERID, USERPASS, 'res.partner.bank', 'search', [('acc_number', '=', self.is_rib_id.acc_number)])
        if ids:
            return ids[0]
        return False


    def _get_user_id(self, DB, USERID, USERPASS, sock):
        ids = sock.execute(DB, USERID, USERPASS, 'res.users', 'search', [('login', '=', self.user_id.login)])
        if ids:
            return ids[0]
        return False

    def _get_active(self, DB, USERID, USERPASS, sock):
        active=False
        for obj in self.is_database_line_ids:
            if obj.database==DB:
                active=True
        return active

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
            #Affiche l'adresse compl??te (ex dans les commandes)
            if context.get('show_address'):
                name = name + "\n" + self._display_address(record, without_company=True, context=context)
            name = name.replace('\n\n','\n')
            name = name.replace('\n\n','\n')
            if context.get('show_email') and record.email:
                name = "%s <%s>" % (name, record.email)
            res.append((record.id, name))
        return res


    def action_view_partner(self):
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


    # #TODO : Suite ?? l'installation du module 'project', j'ai du remettre l'ancienne api sinon plantage
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
        """ Retourner les jours de cong??s du partner
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
        """ Retourner les jours f??ri??s du pays du partner indiqu?? 
        """
        jours_feries = []
        for line in partner.country_id.is_jour_ferie_ids:
            jours_feries.append(line.name)
        return jours_feries


    def test_date_dispo(self, date, partner, avec_jours_feries=False):
        """ Test si la date indiqu??e tombe sur un jour ouvert du partner 
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
        """ Calculer la date d'exp??dition en exceptant les weekends
        """
        if int(num_day) not in [0, 6]:
            return date
        else:
            date = datetime.datetime.strptime(date, '%Y-%m-%d') - datetime.timedelta(days=1)
            date = date.strftime('%Y-%m-%d')
            num_day = time.strftime('%w', time.strptime(date, '%Y-%m-%d'))
            return self.get_day_except_weekend(date, num_day)

        
    def get_working_day(self, date, num_day, jours_fermes, leave_dates):
        """ D??terminer la date d'exp??dition en fonction des jours de fermeture de l'usine ou des jours de cong??s de l'usine 
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
            # jours de fermeture de la soci??t??
            jours_fermes = res_partner.num_closing_days(company.partner_id)
            # Jours de cong?? de la soci??t??
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
        """ Retourne la premi??re date disponible dans le pass?? en tenant compte des jours d'ouverture et des vacances 
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
        """ Calcul la date de d??but ?? partir de la date de fin en jours ouvr??s 
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
        """ Calcul la date de fin ?? partir de la date de d??but en jours ouvr??s 
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
        Test g??n??ration 'Bon de sortie mati??re' pour ??tre utilis??e en PHP
        '''
        for obj in self:
            orders=self.env['is.cde.ouverte.fournisseur'].search([('partner_id','=',obj.id)])
            ids=[]
            for order in orders:
                ids.append(order.id)

            # ** R??cup??ration du fichier PDF du rapport indiqu?? ****************
            pdf = self.pool.get('report').get_pdf(self._cr, self._uid, ids, 'is_plastigray.report_cde_ouverte_fournisseur', context=self._context)
            # ******************************************************************

            # Enregistrement du PDF sur le serveur *****************************
            path=u"/tmp/"+filename+u".pdf"
            err=""
            # try:
            #     fichier = open(path, "w")
            # except IOError, e:
            #     err="Probl??me d'acc??s au fichier '"+path+"' => "+ str(e)
            if err=="":
                fichier.write(pdf)
                fichier.close()
            # ******************************************************************
            return {'pdf': base64.b64encode(pdf)}


