# -*- coding: utf-8 -*-
from odoo import models,fields,api,tools,SUPERUSER_ID
import os
import time
import datetime
import pytz
import base64
from xmlrpc import client as xmlrpclib
import logging
_logger = logging.getLogger(__name__)


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
    ('STELLANTIS'     , 'STELLANTIS / Weidplas'),
    ('THERMOR'        , 'THERMOR'),
    ('Valeo'          , 'Valeo'),
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


configuration_facture=[
    ('standard'                  , 'Standard'),
    ('regrouper_article_commande', 'Regrouper les lignes par article et commande client'),
]


class is_champ_obligatoire(models.Model):
    _name = 'is.champ.obligatoire'
    _description = 'Champs obligatoires dans EDI, commande et livraison'

    name                      = fields.Char('Code', required=True)
    point_dechargement        = fields.Boolean('Point de déchargement'   , help="Champ 'CodeIdentificationPointDechargement' pour EDI Weidplas")
    numero_document           = fields.Boolean('N° Document'             , help="Champ 'NumeroDocument'")  
    caldel_number             = fields.Boolean('Caldel Number'           , help="Champ 'CaldelNumber' pour EDI Weidplas")
    num_ran                   = fields.Boolean('NumRAN'                  , help="Champ 'NumRAN' pour EDI PO => N°UM de PO")
    identifiant_transport     = fields.Boolean("N° identifiant transport", help="Champ 'IdTransport' pour EDI Weidplas/PO à remettre sur le BL")
    tg_number                 = fields.Boolean('TG Number'               , help="Champ 'TGNumber' pour EDI Weidplas => N°UM de Weidplas")
    code_routage              = fields.Boolean('Code routage'            , help="Champ 'CodeRoutage' pour EDI Weidplas")
    point_destination         = fields.Boolean('Point destination'       , help="Champ 'CodeIdentificationPointDestination' pour EDI Weidplas")
    num_commande_client       = fields.Boolean('N° Cde Client')
    is_plaque_immatriculation = fields.Boolean("Plaque d’immatriculation")
    is_dossier_transport      = fields.Boolean("N° de dossier de transport")
    ref_pg_unique             = fields.Boolean("Ref PG unique par ref client", help="Si coché, il ne sera pas possible de générer une commande de liste à servir si une référence client correspond à plusieurs références PG")
    is_database_origine_id    = fields.Integer("Id d'origine", readonly=True)


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
            'name'                     : self.name,
            'point_dechargement'       : self.point_dechargement,
            'numero_document'          : self.numero_document,
            'caldel_number'            : self.caldel_number,
            'num_ran'                  : self.num_ran,
            'identifiant_transport'    : self.identifiant_transport,
            'tg_number'                : self.tg_number,
            'code_routage'             : self.code_routage,
            'point_destination'        : self.point_destination,
            'num_commande_client'      : self.num_commande_client,
            'is_plaque_immatriculation': self.is_plaque_immatriculation,
            'is_dossier_transport'     : self.is_dossier_transport,
            'ref_pg_unique'            : self.ref_pg_unique,
            'is_database_origine_id'   : self.id
        }
        return vals


class is_configuration_bl(models.Model):
    _name = 'is.configuration.bl'
    _description = 'Configuration du BL Galia par client'

    name                     = fields.Char('Code', required=True)
    logo_pg                  = fields.Boolean('Afficher logo Plastigray', default=True)
    code_barre               = fields.Boolean('Afficher code barre', default=True)
    code_pg                  = fields.Boolean('Afficher code Plastigray', default=True)
    nomenclature_douaniere   = fields.Boolean('Afficher nomenclature douanière', default=True)
    numero_lot               = fields.Boolean('Afficher numéro de lot', default=True)
    type_colis               = fields.Boolean('Afficher le tableau des colis', default=True)
    mode_transport           = fields.Boolean('Afficher mode de transport', default=True)
    port                     = fields.Boolean('Afficher port', default=True)
    identification_transport = fields.Boolean('Afficher identication transport', default=True)
    poids_net                = fields.Boolean('Afficher poids net', default=True)
    is_database_origine_id   = fields.Integer("Id d'origine", readonly=True)

    caldel_number = fields.Boolean("Afficher 'Caldel Number' dans 'N° de l'ordre", default=False)
    num_ran       = fields.Boolean("Afficher 'NumRAN' dans 'N° de l'ordre", default=True)


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
            'name'                    : self.name,
            'logo_pg'                 : self.logo_pg,
            'code_barre'              : self.code_barre,
            'code_pg'                 : self.code_pg,
            'nomenclature_douaniere'  : self.nomenclature_douaniere,
            'numero_lot'              : self.numero_lot,
            'type_colis'              : self.type_colis,
            'mode_transport'          : self.mode_transport,
            'port'                    : self.port,
            'identification_transport': self.identification_transport,
            'poids_net'               : self.poids_net,
            'is_database_origine_id'  : self.id
        }
        return vals


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
    _description = u'Norme Certificat qualité'
    
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
    _description = u'Certifications qualité'
    _rec_name = 'is_norme'
    
    is_norme           = fields.Many2one('is.norme.certificats', u'Norme Certificat qualité', required=True)
    is_date_validation = fields.Date(u'Date de validité du certificat', required=True)
    is_certificat      = fields.Binary('Certificat qualité')
    is_certificat_ids  = fields.Many2many('ir.attachment', 'is_certificat_attachment_rel', 'certificat_id', 'attachment_id', u'Pièces jointes')
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
        for obj in res:
            filtre=[('is_norme', '=', obj.is_norme.id),('is_date_validation', '=', obj.is_date_validation)]
            self.env['is.database'].copy_other_database(obj,filtre)
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
    _description="Secteur d'activité"
    _order='name'
    _sql_constraints = [('name_uniq','UNIQUE(name)', 'Ce code existe déjà')] 

    name        = fields.Char("Secteur d'activité", required=True)
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
    _sql_constraints = [('name_uniq','UNIQUE(name)', 'Ce code existe déjà')] 

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

    name = fields.Char("Intitulé", required=True)
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


class is_mode_transport(models.Model):
    _name='is.mode.transport'
    _description="Mode de transport"
    _order='name'

    name = fields.Char("Mode de transport", required=True)
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

    customer   = fields.Boolean('Client')      # Champ ajouté car n'existe plus dans Odoo 16
    supplier   = fields.Boolean('Fournisseur') # Champ ajouté car n'existe plus dans Odoo 16
    fax        = fields.Char('Fax')            # Champ ajouté car n'existe plus dans Odoo 16
    user_id    = fields.Many2one(string='Commercial') # Pour renommer 'Vendeur' en 'Commercial'

    display_name            = fields.Char(string='Nom affiché', compute='_compute_display_name')
    is_transporteur_id      = fields.Many2one('res.partner', 'Transporteur', tracking=True)
    is_mode_transport_id    = fields.Many2one('is.mode.transport', 'Mode de transport', tracking=True)
    is_distance             = fields.Integer(string='Distance (km)', tracking=True)
    is_delai_transport      = fields.Integer('Delai de transport (jour)', default=0, tracking=True)
    is_livre_a_id           = fields.Many2one('res.partner', 'Livrer à', tracking=True, help="Indiquez l'adresse de livraison si celle-ci est différente de celle de la société")
    is_certificat_matiere   = fields.Boolean(u'Certificat matière demandé', tracking=True)
    is_import_function      = fields.Selection(import_function, "Fonction d'importation EDI", tracking=True)
 
    is_traitement_edi                     = fields.Selection(traitement_edi, "Traitement EDI", tracking=True)
    is_numero_bal_recepteur               = fields.Char(string='Numero BAL recepteur', tracking=True)
    is_numero_identification_destinataire = fields.Char(string='Numero Identification Destinataire', tracking=True)
    is_numero_bal_emetteur                = fields.Char(string='Numero BAL Emetteur', tracking=True)
    is_standard_edi                       = fields.Char(string='Standard EDI', tracking=True)
    is_code_acheteur                      = fields.Char(string='Code Acheteur (BY)', tracking=True)
    is_code_expediteur                    = fields.Char(string='Code Expediteur (CZ)', tracking=True)
    is_code_vendeur                       = fields.Char(string='Code Vendeur (SE)', tracking=True)
    is_code_destinataire                  = fields.Char(string='Code Destinataire (CN)', tracking=True)
    is_code_destinataire_agence           = fields.Char(string='Code Destinataire Agence (CN)', tracking=True)

    is_raison_sociale2                    = fields.Char('Raison sociale 2', tracking=True)
    is_code                               = fields.Char('Code'        , index=True, tracking=True)
    is_adr_code                           = fields.Char('Code adresse', index=True, tracking=True, default=0)
    is_rue3                               = fields.Char('Rue 3 ou Boite Postale', tracking=True)
    is_secteur_activite                   = fields.Many2one('is.secteur.activite', "Secteur d'activité", tracking=True)
    is_type_contact                       = fields.Many2one('is.type.contact', "Type de contact", tracking=True)
    is_adr_facturation                    = fields.Many2one('res.partner', 'Adresse de facturation', tracking=True)
    is_adr_groupe                         = fields.Char('Code auxiliaire comptable', tracking=True, help="Code auxiliaire comptable de l'adresse groupe pour la comptabilité")
    is_cofor                              = fields.Char('N° fournisseur (COFOR)', tracking=True, help="Notre code fourniseur chez le client")
    is_incoterm                           = fields.Many2one('account.incoterms', "Incoterm  / Conditions de livraison", tracking=True)
    is_lieu                               = fields.Char("Lieu", tracking=True)
    is_escompte                           = fields.Many2one('is.escompte', "Escompte", tracking=True)
    is_type_reglement                     = fields.Many2one('account.journal', u'Type règlement', domain=[('type', 'in', ['bank','cash'])], tracking=True)
    is_num_siret                          = fields.Char(u'N° de SIRET', tracking=True)
    is_code_client                        = fields.Char('Code client', tracking=True, help=u'Notre code client chez le fourniseur')
    is_segment_achat                      = fields.Many2one('is.segment.achat', "Segment d'achat", tracking=True)
    is_famille_achat_ids                  = fields.Many2many('is.famille.achat', "is_famille_achat_res_partner_rel", 'partner_id', 'famille_id', string="Famille d'achat", tracking=True)
    is_fournisseur_imp                    = fields.Boolean(u'Fournisseur imposé', tracking=True)
    is_fournisseur_da_fg                  = fields.Boolean(u'Fournisseur pour DA-FG', default=False, tracking=True)
    is_site_livre_ids                     = fields.Many2many('is.site', "is_site_res_partner_rel", 'partner_id', 'site_id', string='sites livrés', tracking=True)
    is_groupage                           = fields.Boolean('Groupage', tracking=True)
    is_tolerance_delai                    = fields.Boolean('Tolérance sur délai', tracking=True)
    is_nb_jours_tolerance                 = fields.Integer('Nb jours tolérance sur délai', tracking=True)
    is_tolerance_quantite                 = fields.Boolean('Tolérance sur quantité', tracking=True)
    is_transmission_cde                   = fields.Many2one('is.transmission.cde', 'Mode de transmission des commandes', tracking=True)
    is_certifications                     = fields.One2many('is.certifications.qualite', 'partner_id', u'Certification qualité', tracking=True)
    is_type_contact                       = fields.Many2one('is.type.contact', "Type de contact", tracking=True)
    is_source_location_id                 = fields.Many2one('stock.location', 'Source Location', default=_get_default_location, tracking=True) 
    is_rib_id                             = fields.Many2one('res.partner.bank', 'RIB', tracking=True) 
    is_adr_liv_sur_facture                = fields.Boolean(u"Afficher l'adresse de livraison sur la facture", default=True, tracking=True)
    is_num_autorisation_tva               = fields.Char("N° d'autorisation", help="N° d'autorisation de franchise de taxe", tracking=True)
    is_caracteristique_liste_a_servir     = fields.Selection([
        ('point_de_chargement' , 'par point de chargement'),
        ('status_aqp'          , 'par status AQP'),
        ('point_de_chargement_et_status_aqp'          , 'par point de chargement et status AQP'),
    ], 'Caractéristique liste à servir', tracking=True)
    is_caracteristique_bl                 = fields.Selection([
        ('cde_odoo'   , '1 commande Odoo = 1 BL'),
        ('cde_client' , '1 commande client = 1 BL'),
        ('ref_article', '1 référence client = 1 BL'),
    ], 'Caractéristique des BL', tracking=True)
    is_mode_envoi_facture   = fields.Selection([
        ('courrier'        , 'Envoi par courrier'),
        ('courrier2'       , 'Envoi par courrier en double exemplaire'),
        ('mail'            , 'Envoi par mail (1 mail par facture)'),
        ('mail2'           , 'Envoi par mail (1 mail par facture en double exemplaire)'),
        ('mail_client'     , 'Envoi par mail (1 mail par client)'),
        ('mail_client_bl'  , 'Envoi par mail avec BL (1 mail par client)'),
        ('mail_regroupe_bl', 'Regroupement des BL sur une même facture et envoi par mail'),
    ], "Mode d'envoi des factures", tracking=True)

    is_vendeur_id           = fields.Many2one('res.partner', 'Vendeur', help="Champ utilisé pour les BL Galia de Weidplas / PO", domain="[('is_company','=',True),('customer','=',True)]" )
    is_type_cde_fournisseur = fields.Selection(type_commande_list, "Type commande fourniseur", readonly=True)
    is_horizon_besoins      = fields.Integer(u'Horizon des besoins (jour)', default=7, help=u"Champ utilisé pour le mail de l'horizon des besoins (7 jours en général ou 21 jours pendant la période de vacances)")

    is_database_origine_id = fields.Integer("Id d'origine", readonly=True, index=True, copy=False)
    is_database_line_ids   = fields.Many2many('is.database','partner_database_rel','partner_id','database_id', string="Sites")

    calendar_line   = fields.One2many('resource.calendar.leaves', 'partner_id', 'Congés')
    close_monday    = fields.Boolean('Lundi')
    close_tuesday   = fields.Boolean('Mardi')
    close_wednesday = fields.Boolean('Mercredi')
    close_thursday  = fields.Boolean('Jeudi')
    close_friday    = fields.Boolean('Vendredi')
    close_saturday  = fields.Boolean('Samedi', default=True)
    close_sunday    = fields.Boolean('Dimanche'  , default=True)
    
    pricelist_purchase_id    = fields.Many2one('product.pricelist',"Liste de prix d'achat", tracking=True)
    is_champ_obligatoire_id  = fields.Many2one('is.champ.obligatoire',"Champs obligatoires dans EDI, Cde et Liv", tracking=True)
    is_configuration_bl_id   = fields.Many2one('is.configuration.bl',"Configuration BL Galia", tracking=True)
    is_configuration_facture = fields.Selection(configuration_facture, "Configuration du PDF des factures", default='standard', tracking=True)



    def _message_auto_subscribe_notify(self, partner_ids, template):
        #Désactiver le message "Vous avez été assigné à"
        return


    #TODO : Fonction de base remplacée le 24/09/2024 car val=None
    @api.depends_context('company')
    def _credit_debit_get(self):
        tables, where_clause, where_params = self.env['account.move.line']._where_calc([
            ('parent_state', '=', 'posted'),
            ('company_id', '=', self.env.company.id)
        ]).get_sql()

        where_params = [tuple(self.ids)] + where_params
        if where_clause:
            where_clause = 'AND ' + where_clause
        self._cr.execute("""SELECT account_move_line.partner_id, a.account_type, SUM(account_move_line.amount_residual)
                      FROM """ + tables + """
                      LEFT JOIN account_account a ON (account_move_line.account_id=a.id)
                      WHERE a.account_type IN ('asset_receivable','liability_payable')
                      AND account_move_line.partner_id IN %s
                      AND account_move_line.reconciled IS NOT TRUE
                      """ + where_clause + """
                      GROUP BY account_move_line.partner_id, a.account_type
                      """, where_params)
        treated = self.browse()
        for pid, type, val in self._cr.fetchall():
            if val:
                partner = self.browse(pid)
                if type == 'asset_receivable':
                    partner.credit = val
                    if partner not in treated:
                        partner.debit = False
                        treated |= partner
                elif type == 'liability_payable':
                    partner.debit = -val
                    if partner not in treated:
                        partner.credit = False
                        treated |= partner
        remaining = (self - treated)
        remaining.debit = False
        remaining.credit = False


    @api.constrains('vat', 'country_id')
    def check_vat(self):
        print("OK",self)


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
        #** Ne pas désactiver le partner si il est relié à un utilisateur
        for obj in self:
            if "active" in vals:
                if vals["active"]==False:
                    users = self.env['res.users'].search([('partner_id','=',obj.id)])
                    if len(users)>0:
                        vals["active"]=True
        #******************************************************************     

        #** Ne pas syncroniser le partner si il est relié à un utilisateur
        test=True
        for obj in self:
            users = self.env['res.users'].search([('partner_id','=',obj.id)])
            if len(users)>0:
                test=False
        #******************************************************************     

        res=super().write(vals)
        if test:
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
            'is_caracteristique_liste_a_servir'  : self.is_caracteristique_liste_a_servir,
            'is_caracteristique_bl'   : self.is_caracteristique_bl,
            'is_champ_obligatoire_id'   : self._get_is_champ_obligatoire_id(DB, USERID, USERPASS, sock),
            'is_configuration_bl_id'    : self._get_is_configuration_bl_id(DB, USERID, USERPASS, sock),
            'is_configuration_facture'  : self.is_configuration_facture,
            'is_mode_envoi_facture'   : self.is_mode_envoi_facture,
            'is_vendeur_id'           : self._get_is_vendeur_id(DB, USERID, USERPASS, sock),
            'is_database_line_ids'    : self._get_is_database_line_ids(DB, USERID, USERPASS, sock),
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
        _logger.info("database=%s : vals=%s"%(DB,vals))
        return vals
    
    def _get_parent_id(self, DB, USERID, USERPASS, sock):
        if not self.parent_id:
            return False
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
        if not self.is_adr_facturation.id:
            return False
        ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', self.is_adr_facturation.id),'|',('active','=',True),('active','=',False)])
        if not ids:
            self.env['is.database'].copy_other_database(self.is_adr_facturation)
            ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', self.is_adr_facturation.id),'|',('active','=',True),('active','=',False)])
        if ids:
            return ids[0]
        return False


    def _get_is_vendeur_id(self, DB, USERID, USERPASS, sock):
        if not self.is_vendeur_id.id:
            return False
        ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', self.is_vendeur_id.id),'|',('active','=',True),('active','=',False)])
        if not ids:
            self.env['is.database'].copy_other_database(self.is_vendeur_id)
            ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', self.is_vendeur_id.id),'|',('active','=',True),('active','=',False)])
        if ids:
            return ids[0]
        return False


    def _get_is_champ_obligatoire_id (self, DB, USERID, USERPASS, sock):
        if not self.is_champ_obligatoire_id.id:
            return False
        ids = sock.execute(DB, USERID, USERPASS, 'is.champ.obligatoire', 'search', [('is_database_origine_id', '=', self.is_champ_obligatoire_id.id)])
        if not ids:
            self.env['is.database'].copy_other_database(self.is_configuis_champ_obligatoire_idration_bl_id)
            ids = sock.execute(DB, USERID, USERPASS, 'is.champ.obligatoire', 'search', [('is_database_origine_id', '=', self.is_champ_obligatoire_id.id)])
        if ids:
            return ids[0]
        return False


    def _get_is_configuration_bl_id(self, DB, USERID, USERPASS, sock):
        if not self.is_configuration_bl_id.id:
            return False
        ids = sock.execute(DB, USERID, USERPASS, 'is.configuration.bl', 'search', [('is_database_origine_id', '=', self.is_configuration_bl_id.id)])
        if not ids:
            self.env['is.database'].copy_other_database(self.is_configuration_bl_id)
            ids = sock.execute(DB, USERID, USERPASS, 'is.configuration.bl', 'search', [('is_database_origine_id', '=', self.is_configuration_bl_id.id)])
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
        if not self.is_rib_id.acc_number:
            return False
        #ids = sock.execute(DB, USERID, USERPASS, 'res.partner.bank', 'search', [('acc_number', '=', self.is_rib_id.acc_number)]) TODO : Ne fonctionne pas
        ids = sock.execute(DB, USERID, USERPASS, 'res.partner.bank', 'search', [('bank_name', '=', self.is_rib_id.bank_name)])
        #ids = sock.execute(DB, USERID, USERPASS, 'res.partner.bank', 'search', [])
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


    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        context =  self._context
        args = args or []
        if 'res_partner_search_mode' in context:
            if 'customer' in context['res_partner_search_mode']:
                args.append(['customer', '=', True])
            if 'supplier' in context['res_partner_search_mode']:
                args.append(['supplier', '=', True])
        res= super()._name_search(name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)
        return res


    def _get_name(self):
        """ Utility method to allow name_get to be overrided without re-browse the partner """
        partner = self
        name = partner.name or ''

        if partner.is_company:
            if partner.is_code and partner.is_adr_code:
                name =  "%s (%s/%s)" % (name, partner.is_code, partner.is_adr_code)
            if partner.is_code and not partner.is_adr_code:
                name =  "%s (%s)" % (name, partner.is_code)

        if partner.company_name or partner.parent_id:
            if not name and partner.type in ['invoice', 'delivery', 'other']:
                name = dict(self.fields_get(['type'])['type']['selection'])[partner.type]
            if not partner.is_company:
                name = self._get_contact_name(partner, name)
        if self._context.get('show_address_only'):
            name = partner._display_address(without_company=True)
        if self._context.get('show_address'):
            name = name + "\n" + partner._display_address(without_company=True)
        name = name.replace('\n\n', '\n')
        name = name.replace('\n\n', '\n')
        if self._context.get('partner_show_db_id'):
            name = "%s (%s)" % (name, partner.id)
        if self._context.get('address_inline'):
            splitted_names = name.split("\n")
            name = ", ".join([n for n in splitted_names if n.strip()])
        if self._context.get('show_email') and partner.email:
            name = "%s <%s>" % (name, partner.email)
        if self._context.get('html_format'):
            name = name.replace('\n', '<br/>')
        if self._context.get('show_vat') and partner.vat:
            name = "%s ‒ %s" % (name, partner.vat)
        return name


    def action_view_partner(self):
        view_id = self.env.ref('base.view_partner_form').id
        for partner in self:
            return {
            'name':partner.name,
            'view_mode': 'form',
            'view_id': view_id,
            'res_model': 'res.partner',
            'type': 'ir.actions.act_window',
            'res_id': partner.id,
            'domain': '[]',
        }



    def copy(self, default=None):
        for obj in self:
            default = dict(default or {})
            default['is_code']                           = self.is_code + ' (copie)'
            default['is_adr_code']                       = self.is_adr_code + ' (copie)'
            default['property_account_position_id']      = self.property_account_position_id
            default['property_payment_term_id']          = self.property_payment_term_id
            default['property_supplier_payment_term_id'] = self.property_supplier_payment_term_id
            res=super().copy(default=default)
            return res


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
                delta = line.date_to - line.date_from
                for i in range(delta.days + 1):
                    date = line.date_from + datetime.timedelta(days=i)
                    leave_dates.append(date.strftime('%Y-%m-%d'))
        if avec_jours_feries:
            jours_feries=self.get_jours_feries(partner)
            for date in jours_feries:
                if date not in leave_dates:
                    leave_dates.append(date.strftime('%Y-%m-%d'))
        return leave_dates
    

    def get_jours_feries(self, partner):
        """ Retourner les jours fériés du pays du partner indiqué 
        """
        jours_feries = []
        for line in partner.country_id.is_jour_ferie_ids:
            jours_feries.append(line.name)
        return jours_feries


    def utc_offset(self):
        now = datetime.datetime.now()
        offset = int(pytz.timezone('Europe/Paris').localize(now).utcoffset().total_seconds()/3600)
        return offset


    def utc2local(self,date_utc):
        offset = self.utc_offset()
        date_local = date_utc + datetime.timedelta(hours=offset)
        return date_local


    def test_date_dispo(self, date_utc, partner, avec_jours_feries=False):
        """ Test si la date indiquée tombe sur un jour ouvert du partner 
        """
        res=True
        if date_utc:
            date_local = self.utc2local(date_utc)
            #num_day = int(time.strftime('%w', time.strptime(date, '%Y-%m-%d'))) #Jour de la semaine (avec dimanche=0)
            num_day=int(date_local.strftime('%w'))
            if num_day in self.num_closing_days(partner):
                res=False
            if date_local.strftime('%Y-%m-%d') in self.get_leave_dates(partner, avec_jours_feries):
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

                if type(date_expedition) is str:
                    new_date=datetime.datetime.strptime(date_expedition, '%Y-%m-%d')
                else:
                    new_date = date_expedition

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
        #new_date = datetime.datetime.strptime(date, '%Y-%m-%d')
        new_date = date
        if type(new_date) is str:
            new_date = datetime.datetime.strptime(new_date, '%Y-%m-%d')


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
        if type(date_fin) is str:
            date_fin = datetime.datetime.strptime(date_fin, '%Y-%m-%d')
        new_date = date_fin
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

