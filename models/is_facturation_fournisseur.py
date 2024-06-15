# -*- coding: utf-8 -*-
import datetime
from odoo import models,fields,api
from odoo.exceptions import ValidationError
import math
from decimal import getcontext, Decimal
import numpy as np


#TODO : Cette fonction permet de résoudre les problèmes d'arrondi avec les float et le nombre de décimales
def _total(quantite,prix):
    resolution = 0.0001 # 4 décimales
    quantite = int(np.round(quantite/resolution))*resolution
    prix     = int(np.round(prix/resolution))*resolution

    total=quantite*prix
    resolution = 0.01 # 2 décimales
    total = int(np.round(total/resolution))*resolution

    #La fonction Decimal permet d'afficher la représentation réélle d'un float
    #print Decimal(quantite), Decimal(prix), Decimal(total)

    return total


class is_facturation_fournisseur(models.Model):
    _name = "is.facturation.fournisseur"
    _description = "Facturation fournisseur"
    _order='id desc'

    afficher_lignes     = fields.Selection([('oui', u'Oui'),('non', u'Non')], u"Afficher les lignes", default="oui")
    masquer_montant_0   = fields.Boolean(u"Masquer les montants à 0", default=True)
    name                = fields.Many2one('res.partner', 'Fournisseur à facturer', required=True)
    is_incoterm         = fields.Many2one('account.incoterms', "Incoterm  / Conditions de livraison", related='name.is_incoterm', readonly=True)
    account_position_id = fields.Many2one('account.fiscal.position', string="Position fiscale", related='name.property_account_position_id')
    partner_ids         = fields.Many2many('res.partner', "is_facturation_fournisseur_partner_rel", 'facturation_id', 'partner_id', string='Autres fournisseurs')
    date_fin            = fields.Date('Date de fin'                      , required=True, default=lambda *a: fields.datetime.now())
    date_facture        = fields.Date('Date facture fournisseur'         , required=True)
    num_facture         = fields.Char('N° facture fournisseur'           , required=True)
    total_ht            = fields.Float("Total HT"         , digits=(14,2), required=True)
    total_ht_calcule    = fields.Float("Total HT Calculé" , digits=(14,2), compute='_compute', readonly=True, store=False)
    ecart_ht            = fields.Float("Ecart HT"         , digits=(14,2), compute='_compute', readonly=True, store=False)
    ecart_ht_compte_id  = fields.Many2one('product.product', "Compte d'écart HT")
    total_tva           = fields.Float("Total TVA"         , digits=(14,2))
    total_tva_calcule   = fields.Float("Total TVA Calculé" , digits=(14,2), compute='_compute', readonly=True, store=False)
    ecart_tva           = fields.Float("Ecart TVA"         , digits=(14,2), compute='_compute', readonly=True, store=False)
    ecart_tva_compte_id = fields.Many2one('product.product', "Compte d'écart TVA")
    total_ttc_calcule   = fields.Float("Total TTC Calculé", digits=(14,2), compute='_compute', readonly=True, store=False)
    justification_id    = fields.Many2one('is.facturation.fournisseur.justification', 'Justification')
    bon_a_payer         = fields.Boolean("Bon à payer", compute='_compute', readonly=True, store=False)
    forcer_bon_a_payer  = fields.Selection([('oui', u'Bon à payer = Oui'),('non', u'Bon à payer = Non')], "Forcer bon à payer")
    is_masse_nette      = fields.Float("Masse nette (Kg)")
    line_ids            = fields.One2many('is.facturation.fournisseur.line', 'facturation_id', u"Lignes")
    state               = fields.Selection([('creation', u'Création'),('termine', u'Terminé')], u"État", readonly=True, index=True, default="creation")

 
    @api.depends('line_ids','total_ht','total_tva')
    def _compute(self):
        for obj in self:
            ht=ttc=tva=0.0
            for line in obj.line_ids:
                if line.selection:
                    #total=math.ceil(100*line.prix*line.quantite)/100
                    #total=math.ceil(100.0*round(line.quantite*line.prix,2))/100.0
                    #TODO : Nouvelle modif du 04/08/2018 suite au mail de Sonia du 17/05/2018
                    #total=round(line.prix*line.quantite,2)
                    #TODO : Modification du 12/09/18 suite problème avec round et les float
                    total=_total(line.quantite,line.prix)

                    ht=ht+total
                    tva=tva+total*line.taxe_taux/100
                    ttc=ttc+total*(1+line.taxe_taux/100)
            ht  = round(ht,2)
            tva = round(tva,2)
            ttc = round(ttc,2)
            ecart_ht  = round(obj.total_ht-ht,2)
            ecart_tva = round(obj.total_tva-tva,2)
            bon_a_payer=True
            if ecart_ht or ecart_tva:
                bon_a_payer=False
            obj.total_ht_calcule  = ht
            obj.ecart_ht          = ecart_ht
            obj.total_tva_calcule = tva
            obj.ecart_tva         = ecart_tva
            obj.total_ttc_calcule = ttc

            #Si prix modifié sur les lignes, bon_a_payer=False
            for line in obj.line_ids:
                if line.selection:
                    if round(line.prix,4)!=round(line.prix_origine,4):
                        bon_a_payer=False
            obj.bon_a_payer       = bon_a_payer


    @api.onchange('masquer_montant_0','name','partner_ids','date_fin')
    def cherche_receptions(self):
        cr=self._cr
        for obj in self:
            lines = []
            if obj.name and obj.date_fin:
                partner_ids=[str(obj.name._origin.id)]
                for partner in obj.partner_ids:
                    partner_ids.append(str(partner._origin.id))
                sql="""
                    select  sp.name as num_reception, 
                            sp.is_num_bl, 
                            sp.is_date_reception, 
                            sm.product_id,
                            pt.is_ref_fournisseur,

                            -- sm.product_uom_qty as qty,
                            round(sm.product_uom_qty-coalesce((select sum(quantity) from account_move_line ail where  ail.parent_state='posted' and ail.is_move_id=sm.id ),0),4) as qty,

                            sm.product_uom, 
                            pol.price_unit,
                            sm.id as move_id,
                            pol.id as pol_id,
                            sm.name as description
                    from stock_picking sp inner join stock_move                sm on sp.id=sm.picking_id
                                        inner join product_product           pp on sm.product_id=pp.id
                                        inner join product_template          pt on pp.product_tmpl_id=pt.id 
                                        left outer join purchase_order_line pol on sm.purchase_line_id=pol.id
                    where 
                        sm.state='done' and 
                        sp.state='done' and
                        -- round(sm.product_uom_qty-coalesce((select sum(quantity) from account_move_line ail where ail.is_move_id=sm.id ),0),4)>0 and 
                        sp.picking_type_id=1 and
                        pt.is_facturable='t' and
                        sm.invoice_state='2binvoiced' and
                        sp.is_date_reception<='%s' and
                        sp.partner_id in(%s)
                    order by sp.name, pol.id
                """%(obj.date_fin, ",".join(partner_ids))
                cr.execute(sql)
                result=cr.dictfetchall()

                print(sql)


                for row in result:

                    print(row)

                    move = self.env['stock.move'].browse(row["move_id"])

                    #** Recherche des taxes ****************************************
                    taxe_ids  = []
                    taxe_taux = 0
                    pol_id=row["pol_id"]
                    if pol_id:
                        sql="""
                            select pot.account_tax_id, at.amount
                            from account_tax_purchase_order_line_rel pot left outer join account_tax at on pot.account_tax_id=at.id 
                            where pot.purchase_order_line_id=%s
                        """
                        cr.execute(sql,[pol_id])
                        result2=cr.dictfetchall()
                        for row2 in result2:
                            taxe_ids.append(row2["account_tax_id"])
                            taxe_taux=taxe_taux+row2["amount"]
                    #***************************************************************

                    #** Recherche du compte d'achat associé au mouvement de stock **
                    #move_id=row["move_id"]
                    #move=self.env['stock.move'].browse(move_id)
                    product_id=row["product_id"]
                    product=self.env['product.product'].browse(product_id)
                    account_id = product.property_account_expense_id.id
                    #***************************************************************

                    #** Recalcul quantité en unité d'achat *************************
                    qty = move.product_uom._compute_quantity(row["qty"], move.product_id.uom_po_id)
                    #***************************************************************
                    total = qty*(row["price_unit"] or 0)
                    test=True
                    if obj.masquer_montant_0 and total==0:
                        test=False
                    if test:
                        vals = {
                            'num_reception'      : row["num_reception"],
                            'num_bl_fournisseur' : row["is_num_bl"],
                            'date_reception'     : row["is_date_reception"],
                            'product_id'         : row["product_id"],
                            'description'        : row["description"],
                            'account_id'         : account_id,
                            'ref_fournisseur'    : row["is_ref_fournisseur"],
                            'quantite_facturable': qty,
                            'quantite'           : qty,
                            'uom_id'             : move.product_id.uom_po_id.id,
                            'prix'               : row["price_unit"],
                            #'prix_origine'      : row["price_unit"],
                            'total'              : total,
                            'taxe_ids'           : [(6,0,taxe_ids)],
                            'taxe_taux'          : taxe_taux,
                            'move_id'            : row["move_id"],
                            'selection'          : False,
                        }
                        lines.append([0,0,vals])
                obj.line_ids = False
                obj.line_ids = lines
      

    def action_afficher_lignes(self):
        for obj in self:
            view_id=self.env.ref('is_plastigray16.is_facturation_fournisseur_line_tree_view')
            return {
                'name': u'Lignes',
                'view_mode': 'tree',
                'view_id': view_id.id,
                'res_model': 'is.facturation.fournisseur.line',
                'domain': [
                    ('facturation_id','=',obj.id),
                ],
                'type': 'ir.actions.act_window',
                'limit': 1000,
            }


    def action_creer_facture(self):
        for obj in self:
            bon_a_payer=obj.bon_a_payer
            if obj.forcer_bon_a_payer=='oui':
                bon_a_payer=True
            if obj.forcer_bon_a_payer=='non':
                bon_a_payer=False
            #date_invoice=datetime.date.today().strftime('%Y-%m-%d')
            #res=self.env['account.invoice'].onchange_partner_id('in_invoice', obj.name.id, date_invoice)
            #vals=res['value']
            vals = {
                'partner_id'      : obj.name.id,
                #'account_id'     : obj.name.property_account_payable_id.id,
                'journal_id'      : 2,
                'move_type'       : 'in_invoice',
                'invoice_date'    : obj.date_facture,
                'date'            : obj.date_facture,
                'invoice_date_due': obj.date_facture,
                'supplier_invoice_number': obj.num_facture,
                #'ref'             : obj.num_facture,
                'is_bon_a_payer'  : bon_a_payer,
                'is_masse_nette'  : obj.is_masse_nette,
            }
            lines = []
            invoice_line_tax_id=[]
            for line in obj.line_ids:
                if line.selection:
                    product_id      = line.product_id.id
                    description     = line.description
                    #uom_id          = line.uom_id.id 
                    quantite        = line.quantite
                    #name            = line.product_id.name
                    #invoice_type    = 'in_invoice'
                    #partner_id      = obj.name.id
                    #fiscal_position = vals['fiscal_position']

                    invoice_line_tax_id=[]
                    for taxe_id in line.taxe_ids:
                        invoice_line_tax_id.append(taxe_id.id)

                    if len(invoice_line_tax_id)==0:
                        invoice_line_tax_id=False
                    #res=self.env['account.move.line'].product_id_change(product_id, uom_id, quantite, name, invoice_type, partner_id, fiscal_position)
                    #v=res['value']

                    is_document=line.move_id.purchase_line_id.is_num_chantier
                    if is_document==False:
                        is_document=line.move_id.purchase_line_id.order_id.is_document

                    v = {
                        'product_id'      : product_id,
                        'name'            : description,
                        'quantity'        : quantite,
                        'product_uom_id'  : line.uom_id.id,
                        'price_unit'      : line.prix,
                        'tax_ids'         : [(6,0,invoice_line_tax_id)],
                        'is_document'     : is_document,
                        'is_move_id'      : line.move_id.id,
                        'purchase_line_id': line.move_id.purchase_line_id.id,
                        'is_section_analytique_id': line.product_id.is_section_analytique_ha_id.id,
                    }
                    lines.append([0,False,v]) 

            #** Ajout de la ligne pour l'écart de facturation ******************
            if obj.ecart_ht_compte_id:
                product = obj.ecart_ht_compte_id
                v = {
                    'product_id'      : product.id,
                    'name'            : product.name,
                    'quantity'        : 1,
                    'price_unit'      : obj.ecart_ht,
                    'tax_ids'         : [(6,0,invoice_line_tax_id)],
                    'is_section_analytique_id': product.is_section_analytique_ha_id.id,
                }
                lines.append([0,False,v]) 
            #*******************************************************************

            vals.update({
                'invoice_line_ids': lines,
            })
            res=self.env['account.move'].create(vals)
            # res.button_reset_taxes()
            view_id = self.env.ref('account.view_move_form').id
            obj.state='termine'

            #** Changement d'état des réceptions et des lignes *****************
            for line in obj.line_ids:
                if line.selection:
                    if line.move_id:
                        if line.quantite>=line.quantite_facturable:
                            line.move_id.invoice_state='invoiced'
                        line.move_id.picking_id._compute_invoice_state()
                        #test=True
                        #for l in line.move_id.picking_id.move_ids_without_package:
                        #    if l.invoice_state=='2binvoiced':
                        #        test=False
                        #if test:
                        #    line.move_id.picking_id.invoice_state='invoiced'
            #*******************************************************************

            return {
                'name': "Facture Fournisseur",
                'view_mode': 'form',
                'view_id': view_id,
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'res_id': res.id,
                'domain': '[]',
            }




    # def action_creer_facture(self):
    #     for obj in self:
    #         bon_a_payer=obj.bon_a_payer
    #         if obj.forcer_bon_a_payer=='oui':
    #             bon_a_payer=True
    #         if obj.forcer_bon_a_payer=='non':
    #             bon_a_payer=False
    #         date_invoice=datetime.date.today().strftime('%Y-%m-%d')
    #         res=self.env['account.invoice'].onchange_partner_id('in_invoice', obj.name.id, date_invoice)
    #         vals=res['value']
    #         vals.update({
    #             'partner_id'  : obj.name.id,
    #             'account_id'  : obj.name.property_account_payable.id,
    #             'journal_id'  : 2,
    #             'type'        : 'in_invoice',
    #             'date_invoice': obj.date_facture,
    #             'supplier_invoice_number': obj.num_facture,
    #             'is_bon_a_payer': bon_a_payer,
    #             'is_masse_nette': obj.is_masse_nette,
    #         })
    #         lines = []
    #         invoice_line_tax_id=[]
    #         for line in obj.line_ids:
    #             if line.selection:
    #                 product_id      = line.product_id.id
    #                 description     = line.description
    #                 uom_id          = line.uom_id.id 
    #                 quantite        = line.quantite
    #                 name            = line.product_id.name
    #                 invoice_type    = 'in_invoice'
    #                 partner_id      = obj.name.id
    #                 fiscal_position = vals['fiscal_position']

    #                 invoice_line_tax_id=[]
    #                 for taxe_id in line.taxe_ids:
    #                     invoice_line_tax_id.append(taxe_id.id)

    #                 if len(invoice_line_tax_id)==0:
    #                     invoice_line_tax_id=False
    #                 res=self.env['account.invoice.line'].product_id_change(product_id, uom_id, quantite, name, invoice_type, partner_id, fiscal_position)
    #                 v=res['value']

    #                 is_document=line.move_id.purchase_line_id.is_num_chantier
    #                 if is_document==False:
    #                     is_document=line.move_id.purchase_line_id.order_id.is_document

    #                 v.update({
    #                     'product_id'          : product_id,
    #                     'name'                : description,
    #                     'quantity'            : quantite,
    #                     'price_unit'          : line.prix,
    #                     'invoice_line_tax_id' : [(6,0,invoice_line_tax_id)],
    #                     'is_document'         : is_document,
    #                     'is_move_id'          : line.move_id.id,
    #                 })
    #                 lines.append([0,False,v]) 


    #         #** Ajout de la ligne pour l'écart de facturation ******************
    #         if obj.ecart_ht_compte_id:
    #             product_id      = obj.ecart_ht_compte_id.id
    #             uom_id          = obj.ecart_ht_compte_id.uom_id.id
    #             name            = obj.ecart_ht_compte_id.name
    #             invoice_type    = 'in_invoice'
    #             partner_id      = obj.name.id
    #             fiscal_position = vals['fiscal_position']
    #             res=self.env['account.invoice.line'].product_id_change(product_id, uom_id, quantite, name, invoice_type, partner_id, fiscal_position)
    #             v=res['value']
    #             v.update({
    #                 'product_id'          : product_id,
    #                 'quantity'            : 1,
    #                 'price_unit'          : obj.ecart_ht,
    #                 'invoice_line_tax_id' : [(6,0,invoice_line_tax_id)],
    #             })
    #             lines.append([0,False,v]) 
    #         #*******************************************************************

    #         vals.update({
    #             'invoice_line': lines,
    #         })
    #         res=self.env['account.invoice'].create(vals)
    #         res.button_reset_taxes()
    #         #res.repartir_frais_de_port()
    #         view_id = self.env.ref('account.invoice_supplier_form').id
    #         obj.state='termine'

    #         #** Changement d'état des réceptions et des lignes *****************
    #         for line in obj.line_ids:
    #             if line.selection:
    #                 if line.move_id:
    #                     line.move_id.invoice_state='invoiced'
    #                     test=True
    #                     for l in line.move_id.picking_id.move_lines:
    #                         if l.invoice_state=='2binvoiced':
    #                             test=False
    #                     if test:
    #                         line.move_id.picking_id.invoice_state='invoiced'
    #         #*******************************************************************

    #         return {
    #             'name': "Facture Fournisseur",
    #             'view_mode': 'form',
    #             'view_id': view_id,
    #             'res_model': 'account.invoice',
    #             'type': 'ir.actions.act_window',
    #             'res_id': res.id,
    #             'domain': '[]',
    #         }


class is_facturation_fournisseur_line(models.Model):
    _name='is.facturation.fournisseur.line'
    _description="is_facturation_fournisseur_line"
    _order='id'


    @api.depends('quantite','prix','taxe_ids')
    def _compute(self):
        for obj in self:
            #obj.total=math.ceil(100.0*round(obj.quantite*obj.prix,2))/100.0
            #TODO : Nouvelle modif du 04/08/2018 suite au mail de Sonia du 17/05/2018
            #obj.total=round(obj.quantite*obj.prix,2)
            
            #TODO : Modification du 12/09/2018 (problème round avec les float)
            obj.total=_total(obj.quantite, obj.prix)

            taxe_taux=0
            for taxe in obj.taxe_ids:
                taxe_taux=taxe_taux+taxe.amount
            obj.taxe_taux=taxe_taux


    @api.depends('product_id')
    def _compute_prix_origine(self):
        for obj in self:
            obj.prix_origine = obj.prix


    facturation_id      = fields.Many2one('is.facturation.fournisseur', 'Facturation fournisseur', required=True, ondelete='cascade')
    num_reception       = fields.Char('N° de réception')
    num_bl_fournisseur  = fields.Char('N° BL fournisseur')
    date_reception      = fields.Date('Date réception')
    product_id          = fields.Many2one('product.product', 'Article')
    description         = fields.Char('Description')
    account_id          = fields.Many2one('account.account', 'Compte')
    ref_fournisseur     = fields.Char('Référence fournisseur')
    quantite_facturable = fields.Float('Qt facturable', digits='Product Unit of Measure')
    quantite            = fields.Float('Qt à facturer', digits='Product Unit of Measure')
    uom_id              = fields.Many2one('uom.uom', 'Unité')
    prix                = fields.Float('Prix'          , digits=(14,4))
    prix_origine        = fields.Float("Prix d'origine", digits=(14,4), compute='_compute_prix_origine', readonly=True, store=True)
    total               = fields.Float("Total" , digits=(14,4), compute='_compute', readonly=True, store=False)
    taxe_ids            = fields.Many2many('account.tax', 'is_facturation_fournisseur_line_taxe_ids', 'facturation_id', 'taxe_id', 'Taxes')
    taxe_taux           = fields.Float('Taux', compute='_compute', readonly=True, store=False)
    selection           = fields.Boolean('Sélection', default=True)
    move_id             = fields.Many2one('stock.move', 'Mouvement de stock')


    def action_cocher_lignes(self):
        for obj in self:
            obj.selection=True


    def action_decocher_lignes(self):
        for obj in self:
            obj.selection=False



class is_facturation_fournisseur_justification(models.Model):
    _name='is.facturation.fournisseur.justification'
    _description="is_facturation_fournisseur_justification"
    _order='name'

    name        = fields.Char('Justification')
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
