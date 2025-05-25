# -*- coding: utf-8 -*-
from odoo import models,fields,api           # type: ignore
from odoo.exceptions import ValidationError  # type: ignore
from datetime import datetime
from math import *


class is_facture_pk_type(models.Model):
    _name='is.facture.pk.type'
    _description="Facture PK Type"
    _order = 'name'
    
    name   = fields.Char('Type facture', required=True)
    client_id            = fields.Boolean("Client", default=False)
    num_cde              = fields.Boolean("N° de Cde", default=False)
    num_bl               = fields.Boolean("N° de BL", default=True)
    facture_avoir        = fields.Boolean("Type", default=True)
    annee_facture        = fields.Boolean("Année de la facture", default=True)
    semaine_facture      = fields.Boolean("Semaine de la facture", default=True)

    matiere_premiere      = fields.Boolean("Total Matière première (€)", default=True)
    main_oeuvre           = fields.Boolean("Total Main d'oeuvre / Prestation de service (€)", default=True)
    total_moules          = fields.Boolean("Total des moules à taxer (€)", default=True)
    frais_perturbation    = fields.Boolean("Total frais de préparation à taxer (€)", default=True)
    total                 = fields.Boolean("TOTAL (€)", default=True)
    total_plastigray      = fields.Boolean("Total Plastigray (€)", default=True)

    nb_pieces          = fields.Boolean("Nombre de pièces", default=True)
    nb_cartons         = fields.Boolean("Nombre de cartons", default=True)
    nb_colis           = fields.Boolean("Nombre de colis", default=True)
    volume             = fields.Boolean("Vomule (m3)", default=True)
    poids_net          = fields.Boolean("Poids net (Kg)", default=True)
    poids_brut         = fields.Boolean("Poids brut (Kg)", default=True)

    moule_ids            = fields.Boolean("Moules à taxer", default=True)
    conditions_generales = fields.Boolean("Conditions générales", default=True)

    #Lignes de la facture
    num_colis      = fields.Boolean('N°Colis', default=True)
    commande       = fields.Boolean('Commande', default=True)
    reception      = fields.Boolean('Réception', default=True)  # Nouveau champ du 04/05/2025
    product_id     = fields.Boolean('Article', default=True)
    ref_pk         = fields.Boolean('Réf PK', default=True)
    ref_client     = fields.Boolean('Réf Client') # Nouveau champ du 04/05/2025
    designation    = fields.Boolean('Désignation', default=True)
    poids_net      = fields.Boolean('Poids net (Kg)', default=True)
    poids_brut     = fields.Boolean('Poids brut (Kg)', default=True)
    qt             = fields.Boolean('Quantité', default=True)
    uc             = fields.Boolean('UC', default=True)
    nb_uc          = fields.Boolean('Nb UC', default=True)
    pump           = fields.Boolean('P.U.M.P €', default=True)
    pump_tnd       = fields.Boolean('P.U.M.P (TND)') # Nouveau champ du 04/05/2025
    pump_1000      = fields.Boolean('P.U.M.P x 1000 (€))', default=True)  # Nouveau champ du 04/05/2025
    ptmp           = fields.Boolean('P.T.M.P €', default=True)
    ptmp_tnd       = fields.Boolean('P.T.M.P (TND)', default=True)     # Nouveau champ du 04/05/2025
    pupf           = fields.Boolean('P.U.P.F €', default=True)
    total_pf       = fields.Boolean('P.T.P.F. €', default=True)
    pu_ht          = fields.Boolean('P.U. H.T. (€)', default=True) # Nouveau champ du 04/05/2025
    pu_ht_tnd      = fields.Boolean('P.U. H.T. (TND)', default=True) # Nouveau champ du 04/05/2025
    pu_ht_1000     = fields.Boolean('P.U. H.T. x 1000 (€)', default=True)  # Nouveau champ du 04/05/2025
    pu_ht_1000_ass = fields.Boolean('P.U. H.T. x 1000 assistance incluse (€)', default=True)  # Nouveau champ du 04/05/2025
    montant_total     = fields.Boolean('Montant H.T. (€)', default=True) # Nouveau champ du 04/05/2025
    montant_total_tnd = fields.Boolean('Montant H.T. (TND)', default=True) # Nouveau champ du 04/05/2025


class is_facture_pk(models.Model):
    _name='is.facture.pk'
    _inherit=['mail.thread']
    _description="Facture PK"
    _rec_name = 'num_facture'
    _order = 'num_facture desc'
    
    @api.depends('date_facture','nb_colis','moule_ids','frais_perturbation','num_bl','line_ids')
    def _compute(self):
        for obj in self:
            total_moules=0
            for row in obj.moule_ids:
                total_moules=total_moules+row.montant
            obj.total_moules=total_moules
            obj.total=obj.matiere_premiere+obj.main_oeuvre+obj.total_moules+obj.frais_perturbation
            obj.volume=ceil(obj.nb_colis*3.5)
            annee_facture = ''
            semaine_facture = ''
            if obj.date_facture:
                date_facture = datetime.strptime(str(obj.date_facture), '%Y-%m-%d')
                annee_facture   = date_facture.strftime('%Y')
                semaine_facture = date_facture.strftime('%W')
            obj.annee_facture   = annee_facture
            obj.semaine_facture = semaine_facture


  
    @api.depends('main_oeuvre','frais_perturbation')
    def _compute_total_plastigray(self):
        for obj in self:
            obj.total_plastigray = obj.main_oeuvre + obj.frais_perturbation
          
    num_facture        = fields.Char('N° de Facture',tracking=True)
    date_facture       = fields.Date('Date de facture', required=True, default=lambda *a: fields.datetime.now(),tracking=True)
    annee_facture      = fields.Char('Année de la facture'  , compute='_compute', store=True,tracking=True)
    semaine_facture    = fields.Char('Semaine de la facture', compute='_compute', store=True,tracking=True)
    client_id          = fields.Many2one('res.partner', string='Client',tracking=True, domain=[('is_company', '=', True), ('customer', '=', True)]) 
    num_cde            = fields.Char("N° de commande",tracking=True)
    num_bl             = fields.Many2one('stock.picking', string='N° de BL',tracking=True, domain=[('sale_id', '!=', False),('is_facture_pk_id', '=', False)]) 
    num_import_matiere = fields.Char("N° d'import matière première",tracking=True)

    matiere_premiere   = fields.Float('Total Matière première (€)'                     , digits=(14, 4), readonly=True,tracking=True)
    main_oeuvre        = fields.Float("Total Main d'oeuvre / Prestation de service (€)", digits=(14, 4), readonly=True,tracking=True)
    total_moules       = fields.Float("Total des moules à taxer (€)"                   , digits=(14, 4), compute='_compute', store=True,tracking=True)
    frais_perturbation = fields.Float("Total frais de préparation à taxer (€)"         , digits=(14, 4),tracking=True)
    frais_perturbation_commentaire = fields.Char("Commentaire frais de préparation",tracking=True)
    total              = fields.Float("TOTAL (€)"           , digits=(14, 4), compute='_compute', store=True,tracking=True)
    total_plastigray   = fields.Float("Total Plastigray (€)", digits=(14, 4), compute='_compute_total_plastigray',tracking=True, store=True, help="Total Main d'oeuvre / Prestation de service + Total frais de préparation à taxer")

    nb_pieces          = fields.Integer("Nombre de pièces", readonly=True,tracking=True)
    nb_cartons         = fields.Integer("Nombre de cartons", readonly=True,tracking=True)
    nb_colis           = fields.Integer("Nombre de colis",tracking=True)
    volume             = fields.Integer("Vomule (m3)", compute='_compute', store=True,tracking=True, readonly=False)
    poids_net          = fields.Float("Poids net (Kg)" , digits=(14, 2),tracking=True)
    poids_brut         = fields.Float("Poids brut (Kg)", digits=(14, 2),tracking=True)

    line_ids           = fields.One2many('is.facture.pk.line' , 'is_facture_id', string='Lignes de la facture',tracking=True)
    moule_ids          = fields.One2many('is.facture.pk.moule', 'is_facture_id', string='Moules à taxer',tracking=True)

    type_facture_id    = fields.Many2one('is.facture.pk.type', string='Type facture', tracking=True) 
    facture_avoir      = fields.Selection([
            ('Facture', 'Facture'),
            ('Avoir'  , 'Avoir'),
        ], "Type", default='Facture', tracking=True)
    facture_origine_id   = fields.Many2one('is.facture.pk', string="Facture d'origine de cet avoir", tracking=True) 
    conditions_generales = fields.Text('Conditions générales',tracking=True)

    client_id_vsb            = fields.Boolean("client_id_vsb"             , compute='_compute_vsb')
    num_cde_vsb              = fields.Boolean("num_cde_vsb"               , compute='_compute_vsb')
    num_bl_vsb               = fields.Boolean("num_bl_vsb"                , compute='_compute_vsb')
    facture_avoir_vsb        = fields.Boolean("facture_avoir_vsb"         , compute='_compute_vsb')
    annee_facture_vsb        = fields.Boolean("annee_facture_vsb"         , compute='_compute_vsb')
    semaine_facture_vsb      = fields.Boolean("semaine_facture_vsb"       , compute='_compute_vsb')

    matiere_premiere_vsb      = fields.Boolean("matiere_premiere_vsb"     , compute='_compute_vsb')
    main_oeuvre_vsb           = fields.Boolean("main_oeuvre_vsb"          , compute='_compute_vsb')
    total_moules_vsb          = fields.Boolean("total_moules_vsb"         , compute='_compute_vsb')
    frais_perturbation_vsb    = fields.Boolean("frais_perturbation_vsb"   , compute='_compute_vsb')
    total_vsb                 = fields.Boolean("total_vsb"                , compute='_compute_vsb')
    total_plastigray_vsb      = fields.Boolean("total_plastigray_vsb"     , compute='_compute_vsb')

    nb_pieces_vsb             = fields.Boolean("nb_pieces_vsb"            , compute='_compute_vsb')
    nb_cartons_vsb            = fields.Boolean("nb_cartons_vsb"           , compute='_compute_vsb')
    nb_colis_vsb              = fields.Boolean("nb_colis_vsb"             , compute='_compute_vsb')
    volume_vsb                = fields.Boolean("volume_vsb"               , compute='_compute_vsb')
    poids_net_vsb             = fields.Boolean("poids_net_vsb"            , compute='_compute_vsb')
    poids_brut_vsb            = fields.Boolean("poids_brut_vsb"           , compute='_compute_vsb')

    moule_ids_vsb            = fields.Boolean("moule_ids_vsb"             , compute='_compute_vsb')
    conditions_generales_vsb = fields.Boolean("conditions_generales_vsb"  , compute='_compute_vsb')

    #Lignes de la facture 
    num_colis_vsb   = fields.Boolean("num_colis_vsb"  , compute='_compute_vsb')
    commande_vsb    = fields.Boolean("commande_vsb"   , compute='_compute_vsb')
    reception_vsb   = fields.Boolean("reception_vsb"  , compute='_compute_vsb')
    product_id_vsb  = fields.Boolean("product_id_vsb" , compute='_compute_vsb')
    ref_pk_vsb      = fields.Boolean("ref_pk_vsb"     , compute='_compute_vsb')
    ref_client_vsb  = fields.Boolean("ref_client_vsb" , compute='_compute_vsb')
    designation_vsb = fields.Boolean("designation_vsb", compute='_compute_vsb')
    poids_net_vsb   = fields.Boolean("poids_net_vsb"  , compute='_compute_vsb')
    poids_brut_vsb  = fields.Boolean("poids_brut_vsb" , compute='_compute_vsb')
    qt_vsb          = fields.Boolean("qt_vsb"         , compute='_compute_vsb')
    uc_vsb          = fields.Boolean("uc_vsb"         , compute='_compute_vsb')
    nb_uc_vsb       = fields.Boolean("nb_uc_vsb"      , compute='_compute_vsb')
    pump_vsb        = fields.Boolean("pump_vsb"       , compute='_compute_vsb')
    pump_tnd_vsb    = fields.Boolean("pump_tnd_vsb"   , compute='_compute_vsb')
    pump_1000_vsb   = fields.Boolean("pump_1000_vsb"  , compute='_compute_vsb')
    ptmp_vsb        = fields.Boolean("ptmp_vsb"       , compute='_compute_vsb')
    ptmp_tnd_vsb    = fields.Boolean("ptmp_tnd_vsb"   , compute='_compute_vsb')
    pupf_vsb        = fields.Boolean("pupf_vsb"       , compute='_compute_vsb')
    total_pf_vsb    = fields.Boolean("total_pf_vsb"   , compute='_compute_vsb')
    pu_ht_vsb             = fields.Boolean("pu_ht_vsb"            , compute='_compute_vsb')
    pu_ht_tnd_vsb         = fields.Boolean("pu_ht_tnd_vsb"        , compute='_compute_vsb')
    pu_ht_1000_vsb        = fields.Boolean("pu_ht_1000_vsb"       , compute='_compute_vsb')
    pu_ht_1000_ass_vsb    = fields.Boolean("pu_ht_1000_ass_vsb"   , compute='_compute_vsb')
    montant_total_vsb     = fields.Boolean("montant_total_vsb"    , compute='_compute_vsb')
    montant_total_tnd_vsb = fields.Boolean("montant_total_tnd_vsb", compute='_compute_vsb')


    @api.depends('type_facture_id')
    def _compute_vsb(self):
        for obj in self:
            vsb=False
            champs=[
                'facture_avoir','client_id','num_cde','num_bl','annee_facture','semaine_facture','moule_ids','conditions_generales',
                'matiere_premiere','main_oeuvre','total_moules','frais_perturbation','total','total_plastigray',
                'nb_pieces', 'nb_cartons','nb_colis', 'volume', 'poids_net', 'poids_brut',
                'num_colis','commande','product_id','ref_pk','designation','poids_net','poids_brut','qt','uc','nb_uc','pump','ptmp','pupf','total_pf',
                'reception','ref_client','pump_tnd','pump_1000','ptmp_tnd','pu_ht','pu_ht_tnd','pu_ht_1000','pu_ht_1000_ass','montant_total','montant_total_tnd',
            ]
            for champ in champs:
                vsb=False
                if  obj.type_facture_id:
                    vsb = getattr(obj.type_facture_id, champ)
                champ_vsb ="%s_vsb"%champ
                setattr(obj, champ_vsb, vsb)


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:

            data_obj          = self.env['ir.model.data']
            stock_picking_obj = self.env['stock.picking']
            cout_obj          = self.env['is.cout']

            #** Recherche si le BL est déjà facturé ********************************
            if 'num_bl' in vals:
                pickings = stock_picking_obj.search([('id', '=', vals['num_bl'])])
                for picking in pickings:
                    if picking.is_facture_pk_id:
                        raise ValidationError('Ce BL est déjà facturé !')
            #***********************************************************************

            vals['num_facture'] = self.env['ir.sequence'].next_by_code('is.facture.pk')
            if vals.get('num_bl', False):
                picking = stock_picking_obj.search([('id', '=', vals['num_bl'])])
                line_ids = []
                matiere_premiere=0
                main_oeuvre=0
                nb_pieces=0
                nb_cartons=0
                total_poids_net=0
                total_poids_brut=0
                for move in picking.move_ids_without_package:

                    #** Cout actualisé *********************************************
                    couts = cout_obj.search([('name', '=', move.product_id.id)])
                    cout_act_matiere=0
                    for cout in couts:
                        cout_act_matiere=cout.cout_act_matiere
                    #***************************************************************

                    #** Conditionnement ********************************************
                    uc=1
                    for pack in move.product_id.packaging_ids:
                        uc=pack.qty or 1
                    #***************************************************************

                    pupf=move.sale_line_id.price_unit
                    matiere_premiere=matiere_premiere+move.product_uom_qty*cout_act_matiere
                    main_oeuvre=main_oeuvre+move.product_uom_qty*pupf
                    nb_pieces=nb_pieces+move.product_uom_qty
                    nb_cartons=nb_cartons+move.product_uom_qty/uc

                    poids_net  = move.product_id and move.product_uom_qty*move.product_id.weight_net
                    poids_brut = move.product_id and move.product_uom_qty*move.product_id.weight
                    total_poids_net  = total_poids_net  + poids_net
                    total_poids_brut = total_poids_brut + poids_brut
                    val = {
                        'commande'   : move.sale_line_id.is_client_order_ref or '',
                        'product_id' : move.product_id.id,
                        'ref_pk'     : move.product_id and move.product_id.is_code or False,
                        'designation': move.product_id and move.product_id.name or '',
                        'poids_net'  : poids_net,
                        'poids_brut' : poids_brut,
                        'qt'         : move.product_uom_qty,
                        'uc'         : uc,
                        'nb_uc'      : move.product_uom_qty/uc,
                        'pump'       : cout_act_matiere,
                        'ptmp'       : move.product_uom_qty*cout_act_matiere,
                        'pupf'       : pupf,
                        'total_pf'   : move.product_uom_qty*pupf,
                    }
                    line_ids.append((0, 0, val))
                vals.update({
                    'line_ids': line_ids,
                    'matiere_premiere': matiere_premiere,
                    'main_oeuvre'     : main_oeuvre,
                    'nb_pieces'       : nb_pieces,
                    'nb_cartons'      : nb_cartons,
                    'poids_net'       : total_poids_net,
                    'poids_brut'      : total_poids_brut,
                })
        res = super().create(vals)
        res.num_bl.is_facture_pk_id=res.id
        res._compute()
        return res


    def write(self,vals):
        res = super(is_facture_pk, self).write(vals)
        if 'num_bl' in vals:
            for obj in self:
                self.check_bl(obj)
        return res


    def check_bl(self,obj):
        if obj.num_bl.is_facture_pk_id:
            raise ValidationError('Ce BL est déjà facturé !')
        obj.num_bl.is_facture_pk_id=obj.id


    def afficher_lignes(self):
        for obj in self:
            view_id=self.env.ref('is_plastigray16.is_facture_pk_line_tree_view')
            return {
                'name': u'Lignes '+obj.num_facture,
                'view_mode': 'tree',
                'view_id': view_id.id,
                'res_model': 'is.facture.pk.line',
                'domain': [
                    ('is_facture_id','=',obj.id),
                ],
                'type': 'ir.actions.act_window',
            }




class is_facture_pk_line(models.Model):
    _name='is.facture.pk.line'
    _description="Lignes facture PK"
    _order = 'num_colis,product_id'
    
    is_facture_id = fields.Many2one('is.facture.pk', string='Lignes')
    num_colis     = fields.Char('N°Colis')
    commande      = fields.Char('Commande')
    reception     = fields.Char('Réception')  # Nouveau champ du 04/05/2025
    product_id    = fields.Many2one('product.product', string='Article')
    ref_pk        = fields.Char('Réf PK')
    ref_client    = fields.Char('Réf Client') # Nouveau champ du 04/05/2025
    designation   = fields.Char('Désignation')
    poids_net     = fields.Float('Poids net (Kg)')
    poids_brut    = fields.Float('Poids brut (Kg)')
    qt            = fields.Float('Quantité')
    uc            = fields.Float('UC')
    nb_uc         = fields.Float('Nb UC')
    pump          = fields.Float('P.U.M.P (€)'        , digits=(14, 4))
    pump_tnd      = fields.Float('P.U.M.P (TND)'      , digits=(14, 4))  # Nouveau champ du 04/05/2025
    pump_1000     = fields.Float('P.U.M.P x 1000 (€))', digits=(14, 4))  # Nouveau champ du 04/05/2025

    ptmp          = fields.Float('P.T.M.P (€)'     , digits=(14, 4), compute='_compute_montant', store=True, readonly=False)
    ptmp_tnd      = fields.Float('P.T.M.P (TND)'   , digits=(14, 4), compute='_compute_montant', store=True, readonly=False)     # Nouveau champ du 04/05/2025

    pupf          = fields.Float('P.U.P.F (€)'     , digits=(14, 4))
    total_pf      = fields.Float('P.T.P.F. (€)', digits=(14, 4), compute='_compute_montant', store=True, readonly=False)
    num_bl        = fields.Many2one(related='is_facture_id.num_bl') 

    pu_ht          = fields.Float('P.U. H.T. (€)'     , digits=(14, 4))     # Nouveau champ du 04/05/2025
    pu_ht_tnd      = fields.Float('P.U. H.T. (TND)'   , digits=(14, 4))     # Nouveau champ du 04/05/2025
    pu_ht_1000     = fields.Float('P.U. H.T. x 1000 (€)', digits=(14, 4))   # Nouveau champ du 04/05/2025
    pu_ht_1000_ass = fields.Float('P.U. H.T. x 1000 assistance incluse (€)', digits=(14, 4))  # Nouveau champ du 04/05/2025

    montant_total     = fields.Float('Montant H.T. (€)'  , digits=(14, 4), compute='_compute_montant', store=True, readonly=False) # Nouveau champ du 04/05/2025
    montant_total_tnd = fields.Float('Montant H.T. (TND)', digits=(14, 4), compute='_compute_montant', store=True, readonly=False) # Nouveau champ du 04/05/2025


    @api.depends('qt','pupf','pump','pump_tnd','pu_ht','pu_ht_tnd')
    def _compute_montant(self):
        for obj in self:
            obj.total_pf          = obj.qt * obj.pupf
            obj.ptmp              = obj.qt * obj.pump
            obj.ptmp_tnd          = obj.qt * obj.pump_tnd
            obj.montant_total     = obj.qt * obj.pu_ht
            obj.montant_total_tnd = obj.qt * obj.pu_ht_tnd


class is_facture_pk_moule(models.Model):
    _name='is.facture.pk.moule'
    _description="Moule facture PK"
    
    is_facture_id = fields.Many2one('is.facture.pk', string='Moules')
    mold_id       = fields.Many2one('is.mold', string='Moule à taxer', required=True)
    montant       = fields.Integer('Montant à taxer (€)')


