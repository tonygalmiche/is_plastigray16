# -*- coding: utf-8 -*-
import re
from math import *
from odoo import models,fields,api
from odoo.exceptions import ValidationError


class is_config_champ(models.Model):
    _name='is.config.champ'
    _description="Configuration champs fiche article"
    _order='name'

    name                = fields.Many2one('is.product.segment', 'Segment à paramètrer', required=False)
    afficher_onglet_cas = fields.Boolean("Afficher l'onglet 'Code CAS'", default=False)
    champs_line         = fields.One2many('is.config.champ.line', 'segment_id', 'Champs')

    _sql_constraints = [
        ('name_uniq'       , 'unique(name)'       , u"Ce formulaire existe déja !"),
    ]

    def copy(self,vals):
        for obj in self:
            vals.update({
                'name' : False,
            })
            res=super(is_config_champ, self).copy(vals)
            for item in obj.champs_line:
                v = {
                    'segment_id': res.id,
                    'name'      : item.name.id,
                    'vsb'       : item.vsb,
                }
                id = self.env['is.config.champ.line'].create(v)
            return res




class is_config_champ_line(models.Model):
    _name='is.config.champ.line'
    _description="Configuration champs fiche article - Lignes"
    _order='segment_id,name'

    segment_id = fields.Many2one('is.config.champ', 'Segment à paramètrer')
    name     = fields.Many2one('ir.model.fields', 'Champ', domain=[
            ('model_id.model', '=','product.template' ),
            ('name', 'like', '_vsb'),
            ('field_description', '!=', 'Champ technique'),
        ]
    )

    vsb      = fields.Boolean('Visible')
    _defaults = {
        'vsb': False,
    }





class is_category(models.Model):
    _name='is.category'
    _description="Catégorie article"
    _order='name'    #Ordre de tri par defaut des listes
    _sql_constraints = [('name_uniq','UNIQUE(name)', 'Ce code existe déjà')] 
    name         = fields.Char("Code",size=40,required=True, index=True)
    commentaire  = fields.Char('Intitulé')
    fantome      = fields.Boolean('Article fantôme', \
        help="Si cette case est cochée, les articles de cette catégorie passeront en fantôme dans les composants de la nomenclature")
    calcul_cout  = fields.Boolean('Calculer le coût', \
        help="Si cette case est cochée, le coût sera calculé pour les articles de cette catégorie")
    a_inventorier = fields.Boolean(u'Articles à inventorier', \
        help="Si cette case est cochée, les articles de cette catégorie seront inventoriés",default=True)

    _defaults = {
        'calcul_cout': True,
    }


    def _calcul_cout(self):
        cats=self.search([('calcul_cout', '=', True)])
        res=[]
        for cat in cats:
            res.append(cat.id)
        return res




class is_gestionnaire(models.Model):
    _name='is.gestionnaire'
    _description="Gestionnaire article"
    _order='name'
    _sql_constraints = [('name_uniq','UNIQUE(name)', 'Ce code existe déjà')] 

    name        = fields.Char("Code",size=40,required=True, index=True)
    actif       = fields.Boolean('Actif')
    commentaire = fields.Text('Commentaire')

    _defaults = {
        'actif': True,
    }



class is_section_analytique(models.Model):
    _name = 'is.section.analytique'
    _description = 'Section analytique'
    name = fields.Char('Section analytique', required=True)


class is_budget_responsable(models.Model):
    _name = 'is.budget.responsable'
    _description="Responsable budget"
    name = fields.Char('Responsable budget', required=True)


class is_budget_nature(models.Model):
    _name = 'is.budget.nature'
    _description="Nature budget"
    name = fields.Char('Nature budget', required=True)


class is_product_segment(models.Model):
    _name = 'is.product.segment'
    _description = 'Segment article'
    name         = fields.Char('Code', size=256, required=True)
    description  = fields.Text('Commentaire')
    family_line  = fields.One2many('is.product.famille', 'segment_id', 'Familles')


class is_product_famille(models.Model):
    _name = 'is.product.famille'
    _description = 'Famille article'
    name            = fields.Char('Code', size=256, required=True)
    segment_id      = fields.Many2one('is.product.segment', 'Segment', required=True)
    description     = fields.Text('Commentaire')
    sub_family_line = fields.One2many('is.product.sous.famille', 'family_id', 'Sous Familles')


class is_product_sous_famille(models.Model):
    _name = 'is.product.sous.famille'
    _description = 'Sous famille article'
    name        = fields.Char('Code', size=256, required=True)
    family_id   = fields.Many2one('is.product.famille', 'Famille', required=True)
    description = fields.Text('Commentaire')


class is_emb_emplacement(models.Model):
    _name = 'is.emb.emplacement'
    _description="Emplacement"
    name  = fields.Char('Emplacement', required=True)


class is_emb_norme(models.Model):
    _name = 'is.emb.norme'
    _description="Norme"
    name  = fields.Char('Nomenclature/Norme', required=True)


class is_product_client(models.Model):
    _name='is.product.client'
    _description="Article client"
    _order='product_id'

    product_id         = fields.Many2one('product.template', 'Article', required=True, ondelete='cascade')
    client_id          = fields.Many2one('res.partner', 'Client', domain=[('customer','=',True),('is_company','=',True)], required=True)
    client_defaut      = fields.Boolean('Client par défaut', default=True)
    lot_livraison      = fields.Float('Lot de livraison')
    multiple_livraison = fields.Float('Multiple de livraison')


class is_type_etiquette(models.Model):
    _name='is.type.etiquette'
    _description="Type étiquette"
    _order='name'

    name             = fields.Char("Type d'étiquette"     , required=True)
    code_fournisseur = fields.Char('Code Fournisseur'     , required=True)
    adresse          = fields.Char('Adresse'              , required=True)
    format_etiquette = fields.Selection([ 
        ('DD','DD'),
        ('EC','EC'),
        ('MGI','MGI'),
        ('PG','PG'),
        ('RE','RE'),
        ('VS','VS'),
    ], "Format de l'étiquette", required=True)


class is_code_cas(models.Model):
    _name='is.code.cas'
    _description="Code CAS"
    _order='name'

    @api.constrains('poids_autorise')
    def _check_poids_autorise(self):
        for obj in self:
            if obj.poids_autorise == 0:
                raise ValidationError("% de poids autorisé obligatoire !")

    name           = fields.Char("Nom de la substance",           required=True)
    code_einecs    = fields.Char('Code EINECS (EC Number)',       required=True)
    code_cas       = fields.Char('Substance présente (code CAS)', required=True)
    liste_echa     = fields.Selection([ 
        ('Oui','Oui'),
        ('Non','Non'),
    ], "Liste ECHA", required=True)
    poids_autorise = fields.Float('% de poids autorisé', required=True, default=0.1)
    interdit       = fields.Selection([ 
        ('Oui','Oui'),
        ('Non','Non'),
    ], "Substance réglementée", required=True)


    # def name_get(self, cr, uid, ids, context=None):
    #     res = []
    #     for obj in self.browse(cr, uid, ids, context=context):
    #         name=obj.code_cas or obj.name or obj.code_einecs
    #         res.append((obj.id,name))
    #     return res

    # def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
    #     if not args:
    #         args = []
    #     if name:
    #         ids = self.search(cr, user, ['|','|',('name','ilike', name),('code_einecs','ilike', name),('code_cas','ilike', name)], limit=limit, context=context)
    #     else:
    #         ids = self.search(cr, user, args, limit=limit, context=context)
    #     result = self.name_get(cr, user, ids, context=context)
    #     return result







class is_product_code_cas(models.Model):
    _name='is.product.code.cas'
    _description="Article code CAS"
    _order='code_cas_id'

    @api.constrains('poids')
    def _check_poids(self):
        for obj in self:
            if obj.poids == 0:
                raise ValidationError("% en poids obligatoire !")

    product_id   = fields.Many2one('product.template', 'Article', required=True, ondelete='cascade', readonly=True)
    code_cas_id  = fields.Many2one('is.code.cas', 'Code CAS', required=True)
    poids        = fields.Float('% en poids de ce code CAS dans cette matière', required=True)






class product_template(models.Model):
    _inherit = 'product.template'
    _order='is_code'
    _sql_constraints = [('is_default_code_uniq','UNIQUE(is_code)', 'Ce code existe déjà')]


    @api.depends('is_mold_id','is_dossierf_id')
    def _compute_is_mold_dossierf(self):
        for obj in self:
            mold_dossierf=False
            if obj.is_dossierf_id:
                mold_dossierf=obj.is_dossierf_id.name
            if obj.is_mold_id:
                mold_dossierf=obj.is_mold_id.name
            obj.is_mold_dossierf=mold_dossierf


    @api.depends('is_client_ids')
    def _compute_is_client_id(self):
        for obj in self:
            client_id=False
            for line in obj.is_client_ids:
                if line.client_defaut:
                    client_id=line.client_id
            obj.is_client_id=client_id


    @api.depends('seller_ids')
    def _compute_is_fournisseur_id(self):
        for obj in self:
            fournisseur_id=False
            for line in obj.seller_ids:
                fournisseur_id=line.name
                break
            obj.is_fournisseur_id=fournisseur_id


    @api.depends('segment_id','family_id')
    def _compute(self):
        for obj in self:

            #** Conditionnement (UC) *******************************************
            is_uc = is_uc_qt = False
            if obj.packaging_ids:
                packaging=obj.packaging_ids[0]
                is_uc    = packaging.ul.name
                is_uc_qt = packaging.qty
            obj.is_uc    = is_uc
            obj.is_uc_qt = is_uc_qt
            #*******************************************************************


            if len(obj.segment_id)==0:
                # Si pas de segment => Masquer tous les champs
                for model in self.env['ir.model'].search([['model','=',self._name]]):
                    for champ in model.field_id:
                        if champ.name[-4:]=='_vsb':
                            setattr(obj, champ.name, True)
            else:
                # Si segment => Afficher tous les champs
                for model in self.env['ir.model'].search([['model','=',self._name]]):
                    for champ in model.field_id:
                        if champ.name[-4:]=='_vsb':
                            setattr(obj, champ.name, False)

                # Masquer les champs indiqués
                config_champ=self.env['is.config.champ'].search([['name', '=', obj.segment_id.id]])
                for o in config_champ:
                    for line in o.champs_line:
                        if line.vsb==False and line.name:
                            try:
                                setattr(obj, line.name.name, True)
                            except:
                                continue
                    #** Onglet Code CAS ****************************************
                    if o.afficher_onglet_cas==False:
                        obj.is_code_cas_vsb=True
                    #***********************************************************


            #** Onglet Emballage ***********************************************
            vsb=True
            if obj.family_id.name=='EMBALLAGES':
                vsb=False
            obj.is_emb_vsb=vsb
            #*******************************************************************


    is_code                       = fields.Char('Code PG', index=True, required=True)
    segment_id                    = fields.Many2one('is.product.segment', 'Segment', required=True)
    family_id                     = fields.Many2one('is.product.famille', 'Famille')
    sub_family_id                 = fields.Many2one('is.product.sous.famille', 'Sous famille')

    is_category_id                = fields.Many2one('is.category', 'Catégorie')
    is_category_id_vsb            = fields.Boolean('Catégorie vsb', store=False, compute='_compute')

    is_gestionnaire_id            = fields.Many2one('is.gestionnaire', 'Gestionnaire')
    is_gestionnaire_id_vsb        = fields.Boolean('Gestionnaire vsb', store=False, compute='_compute')

    is_mold_id                    = fields.Many2one('is.mold', 'Moule')
    is_mold_id_vsb                = fields.Boolean('Moule vsb', store=False, compute='_compute')

    is_dossierf_id                = fields.Many2one('is.dossierf', 'Dossier F')
    is_dossierf_id_vsb            = fields.Boolean('Dossier F vsb', store=False, compute='_compute')

    is_ref_client                 = fields.Char('Référence client')
    is_ref_client_vsb             = fields.Boolean('Référence client vsb', store=False, compute='_compute')

    is_client_ids                 = fields.One2many('is.product.client', 'product_id', u"Clients")
    is_client_ids_vsb             = fields.Boolean('Clients vsb', store=False, compute='_compute')


    is_ref_plan                   = fields.Char('Référence plan')
    is_ref_plan_vsb               = fields.Boolean('Référence plan vsb', store=False, compute='_compute')

    is_ind_plan                   = fields.Char('Indice plan')
    is_ind_plan_vsb               = fields.Boolean('Indice plan vsb', store=False, compute='_compute')

    is_nomenclature_douaniere     = fields.Char('Nomenclature douanière')
    is_nomenclature_douaniere_vsb = fields.Boolean('Nomenclature douanière vsb', store=False, compute='_compute')

    is_stock_secu                 = fields.Integer('Stock de sécurité')
    is_stock_secu_vsb             = fields.Boolean('Stock de sécurité vsb', store=False, compute='_compute')

    is_soumise_regl               = fields.Selection([('S','S'),('R','R'),('SR','SR'),], "Pièce soumise à réglementation")
    is_soumise_regl_vsb           = fields.Boolean('Pièce soumise à réglementation vsb', store=False, compute='_compute')

    is_livree_aqp                 = fields.Boolean('Pièce livrée en AQP')
    is_livree_aqp_vsb             = fields.Boolean('Pièce livrée en AQP vsb', store=False, compute='_compute')

    is_droite_grauche             = fields.Selection([('D','D'),('G','G')], "Pièce droite/gauche")
    is_droite_grauche_vsb         = fields.Boolean('Pièce droite/gauche vsb', store=False, compute='_compute')

    is_type_etiquette_id          = fields.Many2one('is.type.etiquette', 'Type étiquette GALIA')
    is_type_etiquette_id_vsb      = fields.Boolean('Type étiquette GALIA vsb', store=False, compute='_compute')

    is_um_egale_uc                = fields.Boolean("UM=UC", help=u"Si l'UM est égale à l'UC, il faut cocher cette case et dans ce cas, l'étiquette UM ne sera pas imprimée")
    is_um_egale_uc_vsb            = fields.Boolean('UM=UC vsb', store=False, compute='_compute')

    is_couleur                    = fields.Char('Couleur / Type matière', help="Mettre la couleur pour les matières et la matière pour les produits fabriqués")
    is_couleur_vsb                = fields.Boolean('Couleur / Type matière vsb', store=False, compute='_compute')

    is_livraison_gefbox           = fields.Boolean('Livraison GEFBOX')
    is_livraison_gefbox_vsb       = fields.Boolean('Livraison GEFBOX vsb', store=False, compute='_compute')

    is_perte                      = fields.Float('% de perte')
    is_perte_vsb                  = fields.Boolean('% de perte vsb', store=False, compute='_compute')

    is_destockage                 = fields.Boolean('Déstockage automatique nomenclature')
    is_destockage_vsb             = fields.Boolean('Déstockage automatique nomenclature vsb', store=False, compute='_compute')

    is_emplacement_destockage_id     = fields.Many2one('stock.location', u'Emplacement déstockage matières OF', domain=[('usage','=','internal')])
    is_emplacement_destockage_id_vsb = fields.Boolean(u'Emplacement déstockage matières OF vsb', store=False, compute='_compute')

    is_ref_fournisseur            = fields.Char('Référence fournisseur')
    is_ref_fournisseur_vsb        = fields.Boolean('Référence fournisseur vsb', store=False, compute='_compute')
    
    lot_mini                      = fields.Float("Lot d'appro.")
    lot_mini_vsb                  = fields.Boolean("Lot d'appro. vsb", store=False, compute='_compute')

    multiple                      = fields.Float('Multiple de')
    multiple_vsb                  = fields.Boolean('Multiple de vsb', store=False, compute='_compute')

    delai_cq                      = fields.Float('Délai contrôle qualité')
    delai_cq_vsb                  = fields.Boolean('Délai contrôle qualité vsb', store=False, compute='_compute')

    temps_realisation             = fields.Float('Temps de realisation en secondes')
    temps_realisation_vsb         = fields.Boolean('Temps de realisation en secondes vsb', store=False, compute='_compute')

    is_origine_produit_id         = fields.Many2one('res.country', 'Origine du produit')
    is_origine_produit_id_vsb     = fields.Boolean('Origine du produit vsb', store=False, compute='_compute')

    is_produit_perissable         = fields.Boolean('Produit périssable')
    is_produit_perissable_vsb     = fields.Boolean('Produit périssable vsb', store=False, compute='_compute')

    is_section_analytique_id      = fields.Many2one('is.section.analytique', 'Section analytique de revenus')
    is_section_analytique_id_vsb  = fields.Boolean('Section analytique de revenus vsb', store=False, compute='_compute')

    is_section_analytique_ha_id      = fields.Many2one('is.section.analytique', 'Section analytique de dépenses')
    is_section_analytique_ha_id_vsb  = fields.Boolean('Section analytique de dépenses vsb', store=False, compute='_compute')

    is_facturable                 = fields.Boolean('Article facturable', default=True)
    is_facturable_vsb             = fields.Boolean('Article facturable vsb', store=False, compute='_compute')

    is_budget_responsable_id      = fields.Many2one('is.budget.responsable', 'Responsable budget')
    is_budget_responsable_id_vsb  = fields.Boolean('Responsable budget vsb', store=False, compute='_compute')

    is_budget_nature_id           = fields.Many2one('is.budget.nature'     , 'Nature budget')
    is_budget_nature_id_vsb       = fields.Boolean('Nature budget vsb', store=False, compute='_compute')

    is_budget_fv                  = fields.Selection([('F','Fixe'),('V','Variable')], "Budget Fixe ou Variable")
    is_budget_fv_vsb              = fields.Boolean('Budget Fixe ou Variable vsb', store=False, compute='_compute')

    is_ctrl_rcp                   = fields.Selection([('bloque','Produit bloqué'),('aqp','AQP')], "Contrôle réception")
    is_ctrl_rcp_vsb               = fields.Boolean('Contrôle réception vsb', store=False, compute='_compute')

    volume_vsb                    = fields.Boolean('Volume vsb'    , store=False, compute='_compute')
    weight_vsb                    = fields.Boolean('Poids brut vsb', store=False, compute='_compute')
    weight_net_vsb                = fields.Boolean('Poids net vsb' , store=False, compute='_compute')

    is_location_vsb              = fields.Boolean('Emplacement de stockage vsb', store=False, compute='_compute')
    is_location                  = fields.Char('Emplacement de stockage')

    is_uc                         = fields.Char('UC'      , store=False, compute='_compute')
    is_uc_qt                      = fields.Integer('Qt/UC', store=False, compute='_compute')

    is_mold_dossierf              = fields.Char('Moule ou Dossier F'                       , store=True, compute='_compute_is_mold_dossierf')
    is_client_id                  = fields.Many2one('res.partner', 'Client par défaut'     , store=True, compute='_compute_is_client_id')
    is_fournisseur_id             = fields.Many2one('res.partner', 'Fournisseur par défaut', store=True, compute='_compute_is_fournisseur_id')

    is_dosmat_ctrl_qual           = fields.Char('Contrôle qualité', readonly=True)


    #** Champs pour le livret logistique des emballages ************************
    is_emb_vsb                    = fields.Boolean('Visibilité onglet Emballage vsb', store=False, compute='_compute')
    is_emb_couvercle_id           = fields.Many2one('product.template', u"Couvercle", domain=[('is_code','=like','700%')], help="Renseigné uniquement si l'emballage n'inclus pas déjà le couvercle")
    is_emb_palette_id             = fields.Many2one('product.template', u"Palette"  , domain=[('is_code','=like','720%')], help="Renseigné uniquement si l'emballage n'inclus pas déjà la palette")
    is_emb_cerclage               = fields.Selection([
                                        ('filmage','filmage'),
                                        ('cerclage','cerclage'),
                                        ('filmage+cerclage','filmage+cerclage')
                                    ], "Cerclage/film")
    is_emb_nb_uc_par_um           = fields.Integer('Nb UC/UM')
    is_gerbage_stockage           = fields.Integer('Gerbage au stockage')
    is_emb_matiere                = fields.Selection([
                                        ('bois'      , 'bois'),
                                        ('carton'    , 'carton'),
                                        ('grille'    , 'grille'),
                                        ('metallique', 'métallique'),
                                        ('plastique' , 'plastique'),
                                    ], "Matière")

    is_emb_emplacement_id         = fields.Many2one('is.emb.emplacement', 'Emplacement de stock')
    is_emb_norme_id               = fields.Many2one('is.emb.norme', 'Nomenclature/Norme')
    is_emb_long_interne           = fields.Float('Longueur interne (mm)', digits=(14,2))
    is_emb_larg_interne           = fields.Float('Largeur interne (mm)' , digits=(14,2))
    is_emb_haut_interne           = fields.Float('Hauteur interne (mm)' , digits=(14,2))
    is_emb_long_externe           = fields.Float('Longueur externe (mm)', digits=(14,2))
    is_emb_larg_externe           = fields.Float('Largeur externe (mm)' , digits=(14,2))
    is_emb_haut_externe           = fields.Float('Hauteur externe (mm)' , digits=(14,2))
    is_emb_haut_plie              = fields.Float('Hauteur plié (mm)'    , digits=(14,2), help="0 = non pliable")
    is_emb_masse                  = fields.Float('Masse (en kg)'        , digits=(14,3))
    #***************************************************************************

    #** Onglet 'Code CAS' pour REACH pour les matière **************************
    is_code_cas_vsb               = fields.Boolean('Visibilité onglet Code CAS vsb', store=False, compute='_compute')
    is_code_cas_ids               = fields.One2many('is.product.code.cas', 'product_id', u"Code CAS")
    #***************************************************************************


    _defaults = {        
        'list_price': 0.0,
        'standard_price': 0.0,
        'lot_mini': 0.0,
        'multiple': 1.0,
        'delai_fabrication': 0.0,
        'temps_realisation': 0.0,
    }

    # def name_get(self, cr, uid, ids, context=None):
    #     res = []
    #     for product in self.browse(cr, uid, ids, context=context):
    #         name=product.is_code+" "+product.name
    #         res.append((product.id,name))
    #     return res

    # def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
    #     if not args:
    #         args = []
    #     if name:
    #         ids = self.search(cr, user, ['|',('is_code','ilike', name),('name','ilike', name)], limit=limit, context=context)
    #     else:
    #         ids = self.search(cr, user, args, limit=limit, context=context)
    #     result = self.name_get(cr, user, ids, context=context)
    #     return result



    def onchange_segment_id(self, cr, uid, ids, segment_id, context=None):
        domain = []
        val = {
            'family_id': False,
            'sub_family_id': False,
        }            
        domain.append(('segment_id','=',segment_id))
        return {
            'value': val,
            'domain': {'family_id': domain}
        }
        

    def onchange_family_id(self, cr, uid, ids, family_id, context=None):
        domain = []
        val = {'sub_family_id': False}
            
        domain.append(('family_id','=',family_id))
        return {
            'value': val,
            'domain': {'sub_family_id': domain}
        }


    def get_lot_livraison(self, product, client):
        lot_livraison=1
        product_client=self.env['is.product.client'].search([
            ('client_id'    , '=', client.id),
            ('product_id'   , '=', product.id),
        ])
        if len(product_client)>0:
            lot_livraison=product_client.lot_livraison
        return lot_livraison


    def get_arrondi_lot_livraison(self, product_id, partner_id, qty):
        product=self.env['product.product'].browse(product_id)
        product_client=self.env['is.product.client'].search([
            ('client_id'    , '=', partner_id),
            ('product_id'   , '=', product.product_tmpl_id.id),
        ])
        if len(product_client)>0:
            lot      = product_client.lot_livraison
            multiple = product_client.multiple_livraison
            if multiple==0:
                multiple=1
            if qty<lot:
                qty=lot
            else:
                delta=qty-lot
                qty=lot+multiple*ceil(delta/multiple)
        return qty



class product_product(models.Model):
    _inherit = 'product.product'
    _order   = 'is_code'

    # def name_get(self, cr, uid, ids, context=None):
    #     res = []
    #     for product in self.browse(cr, uid, ids, context=context):
    #         name=product.is_code+" "+product.name
    #         res.append((product.id,name))
    #     return res


    # def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
    #     if not args:
    #         args = []
    #     if name:
    #         ids = self.search(cr, user, ['|',('is_code','ilike', name),('name','ilike', name)], limit=limit, context=context)
    #     else:
    #         ids = self.search(cr, user, args, limit=limit, context=context)
    #     result = self.name_get(cr, user, ids, context=context)
    #     return result



