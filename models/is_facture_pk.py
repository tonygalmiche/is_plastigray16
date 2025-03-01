# -*- coding: utf-8 -*-
from odoo import models,fields,api
import time
from datetime import datetime
from math import *
from odoo.exceptions import ValidationError


class is_facture_pk(models.Model):
    _name='is.facture.pk'
    _inherit=['mail.thread']
    _description="Facture PK"
    _rec_name = 'num_facture'
    _order = 'num_facture desc'
    
    @api.depends('date_facture','nb_colis','moule_ids','frais_perturbation')
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
          
    num_facture        = fields.Char('N° de Facture')
    date_facture       = fields.Date('Date de facture', required=True, default=lambda *a: fields.datetime.now())
    annee_facture      = fields.Char('Année de la facture'  , compute='_compute', store=True)
    semaine_facture    = fields.Char('Semaine de la facture', compute='_compute', store=True)
    num_bl             = fields.Many2one('stock.picking', string='N° de BL', required=True, domain=[('sale_id', '!=', False),('is_facture_pk_id', '=', False)]) 
    num_import_matiere = fields.Char("N° d'import matière première")
    matiere_premiere   = fields.Float('Total Matière première (€)'                     , digits=(14, 4), readonly=True)
    main_oeuvre        = fields.Float("Total Main d'oeuvre / Prestation de service (€)", digits=(14, 4), readonly=True)
    total_moules       = fields.Float("Total des moules à taxer (€)"                   , digits=(14, 4), compute='_compute', store=True)
    frais_perturbation = fields.Float("Total frais de préparation à taxer (€)"         , digits=(14, 4))
    frais_perturbation_commentaire = fields.Char("Commentaire frais de préparation")
    total              = fields.Float("TOTAL (€)"           , digits=(14, 4), compute='_compute', store=True)
    total_plastigray   = fields.Float("Total Plastigray (€)", digits=(14, 4), compute='_compute_total_plastigray', store=True, help="Total Main d'oeuvre / Prestation de service + Total frais de préparation à taxer")
    nb_cartons         = fields.Integer("Nombre de cartons", readonly=True)
    nb_colis           = fields.Integer("Nombre de colis")
    nb_pieces          = fields.Integer("Nombre de pièces", readonly=True)
    poids_net          = fields.Float("Poids net (Kg)" , digits=(14, 2))
    poids_brut         = fields.Float("Poids brut (Kg)", digits=(14, 2))
    volume             = fields.Integer("Vomule (m3)", compute='_compute', store=True)
    line_ids           = fields.One2many('is.facture.pk.line' , 'is_facture_id', string='Lignes de la facture')
    moule_ids          = fields.One2many('is.facture.pk.moule', 'is_facture_id', string='Moules à taxer')

      

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

            #sequence_ids = data_obj.search([('name','=','seq_is_facture_pk')])
            #if len(sequence_ids)>0:
            #    sequence_id = sequence_ids[0].res_id
            #    vals['num_facture'] = self.env['ir.sequence'].get_id(sequence_id, 'id')
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
        #self.check_bl(res)
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
    product_id    = fields.Many2one('product.product', string='Article')
    ref_pk        = fields.Char('Réf PK')
    designation   = fields.Char('Désignation')
    poids_net     = fields.Float('Poids net (Kg)')
    poids_brut    = fields.Float('Poids brut (Kg)')
    qt            = fields.Float('Quantité')
    uc            = fields.Float('UC')
    nb_uc         = fields.Float('Nb UC')
    pump          = fields.Float('P.U.M.P €'     , digits=(14, 4))
    ptmp          = fields.Float('P.T.M.P €'     , digits=(14, 4))
    pupf          = fields.Float('P.U.P.F €'     , digits=(14, 4))
    total_pf      = fields.Float('P.Total P.F. €', digits=(14, 4))


class is_facture_pk_moule(models.Model):
    _name='is.facture.pk.moule'
    _description="Moule facture PK"
    
    is_facture_id = fields.Many2one('is.facture.pk', string='Moules')
    mold_id       = fields.Many2one('is.mold', string='Moule à taxer', required=True)
    montant       = fields.Integer('Montant à taxer (€)')


