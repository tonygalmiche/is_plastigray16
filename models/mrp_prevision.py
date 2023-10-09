# -*- coding: utf-8 -*-
from odoo import models,fields,api
from odoo.exceptions import ValidationError
from odoo.tools import float_compare, float_round
from datetime import datetime, timedelta
import time
import sys
from math import *


class mrp_prevision(models.Model):
    _name = 'mrp.prevision'
    _description = 'Prevision des fabrication dans le secteur automobile'


    @api.depends('quantity','product_id')
    def _compute(self):
        for obj in self:
            quantity_ha = obj.uom_id._compute_quantity(obj.quantity, obj.uom_po_id)
            self.quantity_ha = quantity_ha

    def _get_company_id(self):
        company_id  = self.env.user.company_id.id
        return company_id

    num_od           = fields.Integer("Numéro", readonly=True)
    name             =  fields.Char('OD', size=128, required=True, default="/")
    parent_id        = fields.Many2one('mrp.prevision', "FS d'origine", ondelete='cascade')
    type             = fields.Selection([
        ('fs', u"FS"),
        ('ft', u"FT"),
        ('sa', "SA")
    ], "Type", required=True, index=True)
    product_id         = fields.Many2one('product.product', 'Article', required=True, index=True)
    is_category_id     = fields.Many2one('is.category', 'Catégorie', readonly=True)
    is_gestionnaire_id = fields.Many2one('is.gestionnaire', 'Gestionnaire', readonly=True)
    partner_id         = fields.Many2one('res.partner', 'Client/Fournisseur', readonly=True)
    start_date         = fields.Date('Date de début', index=True)
    start_date_cq      = fields.Date('Date début CQ (Réception)')
    end_date           = fields.Date('Date fin contrôle qualité')
    quantity           = fields.Float('Quantité', required=True)
    quantity_ha        = fields.Float("Quantité (UA)", compute="_compute", digits=(12, 4))
    quantity_origine   = fields.Float("Quantité d'origine")
    uom_id             = fields.Many2one('uom.uom', 'Unité'        , related='product_id.uom_id'   , readonly=True)
    uom_po_id          = fields.Many2one('uom.uom', "Unité d'achat", related='product_id.uom_po_id', readonly=True)
    delai_cq           = fields.Float("Délai contrôle qualité", readonly=True  , digits=(12, 2))
    tps_fab            = fields.Float("Temps de fabrication (Jour)", readonly=True, digits=(12, 1))
    delai_livraison    = fields.Integer("Délai de livraison", readonly=True)
    note               = fields.Text('Information')
    niveau             = fields.Integer('Niveau', readonly=True, required=True, default=0)
    stock_th           = fields.Float('Stock Théorique', readonly=True)
    company_id         = fields.Many2one('res.company', 'Société', required=True, change_default=True, readonly=True,  default=lambda self: self._get_company_id())
    active             = fields.Boolean('Active', default=True)
    ft_ids             = fields.One2many('mrp.prevision', 'parent_id', u'Composants')
    state              = fields.Selection([('creation', u'Création'),('valide', u'Validé')], u"État", readonly=True, index=True, default="creation")


    def convertir_sa(self):
        rules=self.env['auditlog.rule'].sudo().search([('name','=','purchase.order')])
        if rules:
            rules[0].unsubscribe()

        ids=[]
        for obj in self:
            if obj.type=='sa':
                if len(obj.product_id.seller_ids)>0:
                    ids.append(obj)
                else:
                    obj.note="Aucun fournisseur indiqué dans la fiche article => Convertion en commande impossible"

        order_obj      = self.env['purchase.order']
        order_line_obj = self.env['purchase.order.line']
        for obj in ids:
            partner=obj.product_id.seller_ids[0].name
            if partner.property_product_pricelist_purchase:
                is_contact_id=False
                r=order_obj.onchange_partner_id(partner.id)
                if r and 'value' in r:
                    v=r['value']
                    if 'is_contact_id' in v:
                        is_contact_id=v['is_contact_id']
                vals={
                    'partner_id'      : partner.id,
                    'is_contact_id'   : is_contact_id,
                    'is_livre_a_id'   : partner.is_livre_a_id.id,
                    'location_id'     : partner.is_source_location_id.id,
                    'fiscal_position' : partner.property_account_position.id,
                    'payment_term_id' : partner.property_supplier_payment_term.id,
                    'pricelist_id'    : partner.property_product_pricelist_purchase.id,
                    'incoterm_id'     : partner.is_incoterm.id,
                    'is_lieu'         : partner.is_lieu,
                }
                order=order_obj.create(vals)
                if order:
                    unlink=True
                    note=False
                    vals=False
                    try:
                        res=order_line_obj.onchange_product_id(
                            order.pricelist_id.id, 
                            obj.product_id.id, 
                            obj.quantity_ha, 
                            obj.uom_po_id.id, 
                            partner.id, 
                            date_order         = str(obj.start_date_cq)+' 12:00:00', 
                            fiscal_position_id = partner.property_account_position.id, 
                            date_planned       = obj.start_date_cq, 
                            name               = False, 
                            price_unit         = False, 
                            state              = 'draft'
                        )
                        vals=res['value']
                    except:
                        unlink=False
                        note='\n'.join(sys.exc_info()[1])

                    prix=0
                    if vals and vals['price_unit']:
                        prix = vals['price_unit']

                    # si le prix est nul ou s'il y a une justification du prix nul
                    if vals and (vals['price_unit'] or vals.get('is_justification')) and obj.quantity>=obj.product_id.lot_mini:
                        #** Création d'une commande ****************************
                        vals['order_id']=order.id
                        vals['product_id']=obj.product_id.id
                        if 'taxes_id' in vals:
                            vals.update({'taxes_id': [[6, False, vals['taxes_id']]]})
                        try:
                            order_line=order_line_obj.create(vals)
                            order.wkf_bid_received() 
                            order.wkf_confirm_order()
                            order.action_picking_create() 
                            order.wkf_approve_order()
                        except:
                            unlink=False
                            if note==False:
                                note='\n'.join(sys.exc_info()[1])
                            else:
                                note=note+'\n'+'\n'.join(sys.exc_info()[1])
                        obj.note=unicode(note)
                    else:
                        #** Création d'une demande d'achat série ***************
                        order.unlink()
                        #TODO : Voir comment gérer l'acheteur pour ne pas le mettre en dur ici
                        user        = self.env["res.users"].browse(self._uid)
                        company     = user.company_id
                        acheteur_id = company.is_acheteur_id.id
                        vals={
                            'acheteur_id'      : acheteur_id, 
                            'fournisseur_id'   : partner.id, 
                            'delai_livraison'  : obj.start_date_cq, 
                            'motif'            : 'pas_tarif', 
                        }
                        if partner.is_livre_a_id.id:
                            vals["lieu_livraison_id"]=partner.is_livre_a_id.id
                        da=self.env['is.demande.achat.serie'].create(vals)
                        vals={
                            'da_id'     : da.id, 
                            'sequence'  : 10, 
                            'product_id': obj.product_id.id, 
                            'uom_id'    : obj.uom_po_id.id, 
                            'quantite'  : obj.quantity_ha,
                            'prix'      : prix,
                        }
                        line=self.env['is.demande.achat.serie.line'].create(vals)
                        da.vers_transmis_achat_action()
                        obj.unlink()
                    if unlink:
                        obj.unlink()

        if rules:
            rules[0].subscribe()


    def convertir_fs(self):
        ids=[]
        for obj in self:
            if obj.type=='fs':
                if len(obj.ft_ids)>0:
                    ids.append(obj)
                else:
                    obj.note="Aucune nomenclature pour cet article => Convertion en OF impossible"

        for obj in ids:
            if obj.type=='fs':
                mrp_production_obj = self.env['mrp.production']
                bom_obj = self.env['mrp.bom']


                bom_id = bom_obj._bom_find(product_id=obj.product_id.id, properties=[])
                routing_id = False
                if bom_id:
                    bom_point = bom_obj.browse(bom_id)
                    routing_id = bom_point.routing_id.id or False


                vals={
                    'product_id': obj.product_id.id,
                    'product_uom': obj.product_id.uom_id.id,
                    'product_qty': obj.quantity,
                    'date_planned': obj.start_date,
                    'bom_id': bom_id,
                    'routing_id': routing_id,
                    'origin': obj.name,
                }

                if obj.product_id.is_emplacement_destockage_id:
                    location_id = obj.product_id.is_emplacement_destockage_id.id
                    vals["location_src_id"] = location_id

                mrp_id = mrp_production_obj.create(vals)
                name=obj.name
                unlink=True
                try:
                    mrp_id.action_confirm()
                    mrp_id.force_production()
                    mrp_id.action_in_production()
                except Exception as inst:
                    unlink=False
                    msg="Impossible de convertir la "+name+'\n('+str(inst)+')'
                    obj.note=msg

                if unlink:
                    obj.unlink()



    def _start_date(self, product_id, quantity, end_date):
        start_date=end_date
        for obj in self:
            product_obj = self.env['product.product']
            for product in product_obj.browse(self._cr, self._uid, [product_id], context=self._context):
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
                tps_fab=quantity*product.temps_realisation/(3600*24)
                days=int(ceil(tps_fab))
                start_date= end_date - timedelta(days=days)
                start_date = start_date.strftime('%Y-%m-%d')
        return start_date



    # @api.model_create_multi
    # def create(self, vals_list):
    #     for vals in vals_list:
    #         print(vals)
    #     return super().create(vals_list)


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            partner_obj = self.env['res.partner']
            user        = self.env["res.users"].browse(self._uid)
            product_id  = vals.get('product_id', None)
            product     = self.env['product.product'].browse(product_id)
            company     = user.company_id

            vals['is_gestionnaire_id'] = product.is_gestionnaire_id.id
            vals['is_category_id']     = product.is_category_id.id

            #** Quantité arrondie au lot à la création uniquement ******************
            type       = vals.get('type'      , None)
            quantity   = vals.get('quantity'  , None)
            if quantity==None or quantity==0:
                raise ValidationError(u'Quantité à 0 non autorisée !')

            end_date   = vals.get('end_date'  , None)
            if (type=='sa' or type=='fs') and quantity:
                quantity=self.get_quantity2lot(product, quantity)
                vals["quantity"]         = quantity
                vals["quantity_origine"] = quantity
            #***********************************************************************


            #** Client ou Fournisseur par défaut ***********************************
            partner_id=False
            if type=='sa':
                if len(product.seller_ids)>0:
                    partner_id=product.seller_ids[0].partner_id.id
            if type=='fs':
                if product.is_client_id:
                    partner_id=product.is_client_id.id
            vals["partner_id"]=partner_id
            #***********************************************************************


            #** Si création via le CBN, la date fournie est la date de fin *********
            if type=='sa' and end_date:
                #Date de fin des SA pendant les jours ouvrés de l'entreprise
                end_date=partner_obj.get_date_dispo(company.partner_id, end_date)
                vals["end_date"]=end_date
                r=self.get_delai_cq_tps_fab_start_date(type, product_id, quantity, end_date, partner_id)
                vals.update(r)
            #***********************************************************************


            #** Si création manuelle, date fournie=start_date_cq (date réception) **
            start_date_cq = vals.get('start_date_cq', None)
            if type=='sa' and start_date_cq:
                r=self.get_dates_from_start_date_cq(type, product_id, quantity,start_date_cq, partner_id)
                vals.update(r)
            #***********************************************************************

            if type=='fs':
                r=self.get_delai_cq_tps_fab_start_date(type, product_id, quantity, end_date, partner_id)
                vals.update(r)

            #** Numérotation *******************************************************
            ref = 'is_plastigray16.seq_mrp_prevision_'+str(type)
            sequence = self.env.ref(ref)
            if sequence:
                vals['name'] = sequence.next_by_id()
            #obj = super(mrp_prevision, self).create(vals)
            #***********************************************************************

        obj = super().create(vals_list)


        #** Recherche des composants de la nomenclature pour les fs ************
        if obj:
            id=obj.id
            for row in self.browse([id]):
                if row.type=='fs':
                    boms_by_product = self.env['mrp.bom'].with_context(active_test=True)._bom_find(row.product_id)
                    bom = boms_by_product[row.product_id]
                    res = bom.explode_phantom(qty=row.quantity)
                    for line in res:
                        vals={
                            'parent_id'       : row.id,
                            'type'            : 'ft',
                            'product_id'      : line["line"].product_id.id,
                            'start_date'      : row.start_date,
                            'start_date_cq'   : row.start_date,
                            'end_date'        : row.start_date,
                            'quantity'        : line["product_qty"],
                            'quantity_origine': line["product_qty"],
                            'state'           : 'valide',
                        }
                        self.create(vals)


                    # #** Recherche en tenant compte des articles fantomes *******
                    # bom_obj = self.env['mrp.bom']
                    # #bom_id = bom_obj._bom_find(row.product_id) #.product_tmpl_id) #.id, properties=None)
                    # #bom = bom_obj.browse(bom_id)
                    # #res= bom_obj._bom_explode(bom, row.product_id, row.quantity)
                    # boms_by_product = bom_obj.with_context(active_test=True)._bom_find(row.product_id) #, picking_type=picking_type, company_id=company_id, bom_type='normal')
                    # bom = boms_by_product[row.product_id]
                    # #factor = obj.product_id.uom_id._compute_quantity(qty, obj.bom_id.product_uom_id) / obj.bom_id.product_qty
                    # factor=1
                    # #factor=row.quantity
                    # boms, lines = bom.explode(row.product_id, factor, picking_type=bom.picking_type_id)
                    # for bom_line, line_data in lines:

                    #     if bom_line.child_bom_id and bom_line.child_bom_id.type == 'phantom' or\
                    #             bom_line.product_id.type not in ['product', 'consu']:
                    #         continue
                    #     qty=row.quantity
                    #     qt = float_round(bom_line.product_qty * qty, precision_rounding=bom_line.product_id.uom_id.rounding)
                    #     #qt = bom_line.product_qty
                    #     vals={
                    #         'parent_id'       : row.id,
                    #         'type'            : 'ft',
                    #         'product_id'      : bom_line.product_id.id,
                    #         'start_date'      : row.start_date,
                    #         'start_date_cq'   : row.start_date,
                    #         'end_date'        : row.start_date,
                    #         'quantity'        : qt,
                    #         'quantity_origine': qt,
                    #         'state'           : 'valide',
                    #     }
                    #     #print(obj.name, bom_line.product_id.is_code)
                    #     self.create(vals)
                    # #***********************************************************
        return obj


    def write(self,vals):
        partner_obj = self.env['res.partner']
        user = self.env["res.users"].browse(self._uid)
        company = user.company_id

        for obj in self:
            product_id    = vals.get('product_id'   , obj.product_id.id)
            partner_id    = vals.get('partner_id'   , obj.partner_id.id)
            quantity      = vals.get('quantity'     , obj.quantity)
            start_date_cq = vals.get('start_date_cq', obj.start_date_cq)
            end_date      = vals.get('end_date'     , obj.end_date)

            if quantity==None or quantity==0:
                raise ValidationError(u'Quantité à 0 non autorisée !')


            #** Si modification start_date_cq **********************************
            if obj.type=='sa' and start_date_cq:
                r=self.get_dates_from_start_date_cq(obj.type, product_id, quantity,start_date_cq, partner_id)
                vals.update(r)
            #***********************************************************************


            if obj.type=='fs':
                r=self.get_delai_cq_tps_fab_start_date(obj.type, product_id, quantity, end_date, partner_id)
                vals.update(r)

        res = super(mrp_prevision, self).write(vals)

        #** Calcul quantity et date des FT *************************************
        for obj in self:
            if obj.type=='fs':
                coef=0
                if obj.quantity!=0:
                    coef=obj.quantity_origine/obj.quantity
                ft_ids = self.search([('type','=','ft'),('parent_id','=',obj.id),])
                for row in ft_ids:
                    quantity=row.quantity
                    if coef!=0:
                        quantity=row.quantity_origine/coef
                    else:
                        quantity=0
                    row.quantity      = quantity
                    row.start_date    = obj.start_date
                    row.start_date_cq = obj.start_date
                    row.end_date      = obj.start_date
        #***********************************************************************
        return res


    def get_delai_cq_tps_fab_start_date(self, type_od, product_id, quantity, end_date, partner_id):
        partner_obj = self.env['res.partner']
        user = self.env["res.users"].browse(self._uid)
        company = user.company_id
        vals={}
        start_date=end_date
        product_obj = self.env['product.product']
        product = product_obj.browse(product_id)
        delai_cq = ceil(product.delai_cq)
        start_date_cq = partner_obj.get_date_debut(company.partner_id, end_date, delai_cq)
        #La date d'arrivée (= start_date_cq) doit tomber sur un jour d'ouverture du fournisseur pour fixer la date de réception par fournisseur
        if type_od=='sa' and partner_id:
            partner = self.env["res.partner"].browse(partner_id)
            start_date_cq = partner_obj.get_date_dispo(partner           , start_date_cq, avec_jours_feries=True)  # Date dispo pour le fourniseur avec calendrier pays
            start_date_cq = partner_obj.get_date_dispo(company.partner_id, start_date_cq, avec_jours_feries=False) # Date dispo pour Plastigray sans calendrier pays
        start_date = start_date_cq
        days=0
        tps_fab=0
        delai_livraison=0
        if type_od=='sa':
            if len(product.seller_ids)>0:
                partner_obj=self.env['res.partner']
                days=product.seller_ids[0].delay
                delai_livraison=days
                start_date = datetime.strptime(start_date_cq, '%Y-%m-%d')  - timedelta(days=days)
                start_date = start_date.strftime('%Y-%m-%d')
                start_date = partner_obj.get_date_dispo(company.partner_id, start_date) # Date dispo pour Plastigray
        if type_od=='fs':
            tps_fab = round(quantity*product.temps_realisation/(3600*24),1)
            days    = ceil(tps_fab)
            start_date = partner_obj.get_date_debut(company.partner_id, start_date, days)
        vals={
            'delai_cq'        : product.delai_cq,
            'delai_livraison' : delai_livraison,
            'tps_fab'         : tps_fab,
            'start_date_cq'   : start_date_cq,
            'start_date'      : start_date,
        }
        return vals


    def get_dates_from_start_date_cq(self, type_od, product_id, quantity, start_date_cq, partner_id):
        partner_obj = self.env['res.partner']
        user = self.env["res.users"].browse(self._uid)
        company = user.company_id
        vals={}
        #** start_date_cq pendant jours ouvrés entreprise et fourniseur ********
        #start_date_cq=partner_obj.get_date_dispo(company.partner_id, start_date_cq)
        partner = self.env["res.partner"].browse(partner_id)
        if partner:
            start_date_cq = partner_obj.get_date_dispo(partner       , start_date_cq, avec_jours_feries=True)  # Date dispo pour le fourniseur avec calendrier pays
        start_date_cq = partner_obj.get_date_dispo(company.partner_id, start_date_cq, avec_jours_feries=False) # Date dispo pour Plastigray sans calendrier pays
        #***********************************************************************

        product_obj = self.env['product.product']
        for product in product_obj.browse(product_id):
            #** end_date = start_date_cq + delai_cq (en jours ouvrés) **********
            delai_cq = ceil(product.delai_cq)
            end_date = partner_obj.get_date_fin(company.partner_id, start_date_cq, delai_cq)
            #*******************************************************************

            #** Pour les sa, tenir compte du délai de livraison ****************
            start_date = start_date_cq
            delai_livraison=0
            if type_od=='sa':
                if len(product.seller_ids)>0:
                    days=product.seller_ids[0].delay
                    delai_livraison=days
                    start_date = datetime.strptime(start_date_cq, '%Y-%m-%d')  - timedelta(days=days)
                    start_date = start_date.strftime('%Y-%m-%d')
                    start_date = partner_obj.get_date_dispo(company.partner_id, start_date)
            #*******************************************************************

            #** Pour les fs, tenir compte du temps de fabrication **************
            tps_fab=0
            if type_od=='fs':
                tps_fab = round(quantity*product.temps_realisation/(3600*24),1)
                days    = ceil(tps_fab)
                start_date = partner_obj.get_date_debut(company.partner_id, start_date, days)
            #*******************************************************************

            vals={
                'delai_cq'        : product.delai_cq,
                'delai_livraison' : delai_livraison,
                'tps_fab'         : tps_fab,
                'start_date'      : start_date,
                'start_date_cq'   : start_date_cq,
                'end_date'        : end_date,
            }
        return vals








    def get_quantity2lot(self, product, quantity):
        if quantity<product.lot_mini:
            quantity=product.lot_mini
        delta=quantity-product.lot_mini
        if delta>0:
            if product.multiple!=0:
                x=ceil(delta/product.multiple)
                quantity=product.lot_mini+x*product.multiple
        return quantity


    def get_start_date_sa(self,product, end_date):
        """
        Date de début des SA en tenant compte du délai de livraison
        """
        start_date=end_date
        if len(product.seller_ids)>0:
            partner_obj=self.env['res.partner']
            delay=product.seller_ids[0].delay
            partner_id=product.seller_ids[0].name
            new_date = datetime.strptime(end_date, '%Y-%m-%d')
            new_date = new_date - timedelta(days=delay)
            new_date = new_date.strftime('%Y-%m-%d')
            new_date = partner_obj.get_date_dispo(product.seller_ids[0].name, new_date)
            start_date=new_date
        return start_date



