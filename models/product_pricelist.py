# -*- coding: utf-8 -*-
from odoo import models,fields,api
import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError


class product_pricelist_item(models.Model):
    _inherit = "product.pricelist.item"
    _order="price_version_id,product_id,sequence"

    sequence           = fields.Integer('Séquence', index=True, default=5) #TODO : Ce champ a été supprimé dans Odoo 16
    date_start         = fields.Date('Date de début de validité')
    date_end           = fields.Date('Date de fin de validité')
    justification      = fields.Char('Justification du prix')
    product_uom_id     = fields.Many2one('uom.uom', 'Unité'        , related='product_id.uom_id'   , readonly=True)
    product_po_uom_id  = fields.Many2one('uom.uom', "Unité d'achat", related='product_id.uom_po_id', readonly=True)
    is_ref_client      = fields.Char("Référence client"  , related='product_id.is_ref_client', readonly=True)
    is_mold_dossierf   = fields.Char("Moule ou Dossier F", related='product_id.is_mold_dossierf', readonly=True)
    is_gestionnaire_id = fields.Many2one('is.gestionnaire', "Gestionnaire", related='product_id.is_gestionnaire_id', readonly=True)
    min_quantity       = fields.Float('Quantité minimum', required=True, digits=(14, 4))
    pricelist_id       = fields.Many2one('product.pricelist', 'Liste de prix', required=False)
    price_version_id   = fields.Many2one('product.pricelist.version', 'Version', required=False, index=True)
    #company_id         = fields.Many2one(default=1)


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["company_id"]=1
        return super().create(vals_list)


    @api.onchange('product_id')
    def on_change_product_id(self):
        for obj in self:
            version = obj.price_version_id
            product = obj.product_id
            if version.pricelist_id.type=='sale':
                partner=version.pricelist_id.partner_id
                min_quantity=self.env['product.template'].get_lot_livraison(product.product_tmpl_id, partner)
            else:
                min_quantity=product.lot_mini
                min_quantity = product.uom_id._compute_quantity(min_quantity, product.uom_po_id) #, , product.uom_po_id.id)
            obj.product_uom_id    = product.uom_id.id
            obj.product_po_uom_id = product.uom_po_id.id
            obj.min_quantity      = min_quantity
            #obj.price_surcharge']   = product.uom_po_id.amount


class product_pricelist_version(models.Model):
    """product.pricelist.version n'existe plus dans Odoo 16 !"""
    _name = 'product.pricelist.version'
    _description = 'Version de liste de prix'

    name         =  fields.Char('Version'      , required=True, index=True)
    date_start   =  fields.Date('Date de début', index=True)
    date_end     =  fields.Date('Date de fin'  , index=True)
    pricelist_id = fields.Many2one('product.pricelist', 'Liste de prix',  required=True)
    active       =  fields.Boolean('Active', default=1)
    item_ids     = fields.One2many('product.pricelist.item', 'price_version_id', 'Items', copy=True)

  
    def action_liste_items(self):
        for obj in self:
            if obj.pricelist_id.type=='sale':
                view_id=self.env.ref('is_plastigray16.is_product_pricelist_item_sale_tree_view')
            else:
                view_id=self.env.ref('is_plastigray16.is_product_pricelist_item_purchase_tree_view')
            return {
                'name': obj.name,
                'view_mode': 'tree',
                'res_model': 'product.pricelist.item',
                'type': 'ir.actions.act_window',
                'view_id': view_id.id,
                'domain': [('price_version_id','=',obj.id)],
                'context': {
                    'default_pricelist_id': obj.pricelist_id.id,
                    'default_price_version_id': obj.id,
                    'default_company_id': 1,
                }
            }


    def print_pricelist_version(self):
        for obj in self:
            #return self.pool['report'].get_action(cr, uid, obj.id, 'is_plastigray16.report_pricelist_version', context=context)
            return self.env.ref('is_plastigray16.report_pricelist_version').report_action(self)



    def action_dupliquer(self):
        for obj in self:
            if not obj.date_end:
                raise ValidationError("Date de fin non définie !")
            date_end = obj.date_end
            date_start = date_end   + datetime.timedelta(days=1)
            date_end = date_start + relativedelta(years=1)
            date_end = date_end   + datetime.timedelta(days=-1)
            name=str(int(obj.name)+1)
            vals = {
                'pricelist_id' : obj.pricelist_id.id,
                'name': name,
                'active': obj.active,
                'date_start': date_start,
                'date_end': date_end ,
            }
            new_id = self.env['product.pricelist.version'].create(vals)
            for item in obj.item_ids:
                start=item.date_start
                if start:
                    start=date_start
                end=item.date_end
                if end:
                    end=date_end
                vals = {
                    'price_version_id': new_id.id,
                    'name' : name,
                    'product_id': item.product_id.id,
                    'min_quantity': item.min_quantity,
                    'sequence': item.sequence,
                    'date_start': item.date_start,
                    'date_end': item.date_end,
                    'justification': item.justification,
                    'price_surcharge': item.price_surcharge,
                    'company_id': item.company_id.id,
                    'applied_on': item.applied_on,
                    'compute_price': item.compute_price,
                }
                id = self.env['product.pricelist.item'].create(vals)


class product_pricelist(models.Model):
    _inherit = "product.pricelist"
    

    @api.model
    def _get_partner_pricelist_multi(self, partner_ids):
        "J'ai du remplacer cette fonction pour ne pas avoir de liste de prix par défaut"
        Partner = self.env['res.partner'].with_context(active_test=False)
        company_id = self.env.company.id
        Property = self.env['ir.property'].with_company(company_id)
        result = Property._get_multi('property_product_pricelist', Partner._name, partner_ids)
        return result


    def _compute_product_ids(self):
        for obj in self:
            ids=[]
            tmpl_ids=[]
            versions = self.env['product.pricelist.version'].search([('pricelist_id','=',obj.id)], order="name desc", limit=1)
            for version in  versions:
                for line in version.item_ids:
                    ids.append(line.product_id.id)
                    tmpl_ids.append(line.product_id.product_tmpl_id.id)
            obj.is_product_ids=ids 
            obj.is_product_tmpl_ids=tmpl_ids 
        

    partner_id = fields.Many2one('res.partner', 'Partenaire')
    type       = fields.Selection([
            ("purchase", "Liste de prix d'achat"), 
            ("sale"    , "Liste de prix de vente"), 
        ], " Type de liste de prix ", required=True, default="purchase")
    version_id  = fields.One2many('product.pricelist.version', 'pricelist_id', 'Versions', copy=True)
    is_product_ids      = fields.Many2many('product.product' ,'product_pricelist_product_rel'      ,'pricelist_id','product_id' , string="Variantes", compute='_compute_product_ids')
    is_product_tmpl_ids = fields.Many2many('product.template','product_pricelist_product_tmpl_rel' ,'pricelist_id','product_id' , string="Articles" , compute='_compute_product_ids')


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["company_id"]=1
        return super().create(vals_list)


    #TODO : Revoir la convertion des unités, car pour le moment, cette fonction ne tient pas compte de l'unité (product.uom_id._compute_quantity)
    def price_get(self, product=False, qty=False, date=False):
        price=0
        justification=False
        if product and qty and date:
            qty=round(qty,6)
            for version in self.version_id:
                if (version.date_start==False or version.date_start<=date) and (version.date_end==False or version.date_end>=date):
                    for item in version.item_ids:
                        if item.product_id==product:
                            if (item.date_start==False or item.date_start<=date) and (item.date_end==False or item.date_end>=date):
                                if qty>=item.min_quantity:
                                    price = item.price_surcharge
                                    justification = item.justification
                                    break
                    break
        return [price, justification]





    # def _price_rule_get_multi(self, cr, uid, pricelist, products_by_qty_by_partner, context=None):
    #     context = context or {}
    #     date = context.get('date') or time.strftime('%Y-%m-%d')
    #     date = date[0:10]
    #     products = map(lambda x: x[0], products_by_qty_by_partner)
    #     currency_obj = self.pool.get('res.currency')
    #     product_obj = self.pool.get('product.template')
    #     product_uom_obj = self.pool.get('product.uom')
    #     price_type_obj = self.pool.get('product.price.type')
    #     for product in products:
    #         if product.id==False:
    #             return {}

    #     version = False
    #     for v in pricelist.version_id:
    #         if ((v.date_start is False) or (v.date_start <= date)) and ((v.date_end is False) or (v.date_end >= date)):
    #             version = v
    #             break
    #     if not version:
    #         raise osv.except_osv(_('ValidationError!'), u"Au moins une liste de prix n'a pas de version active !\n \
    #             Créez ou activez en une.\nListe de prix="+str(_(pricelist.name))+' : date='+str(date) + ' : Article='+str(products[0].is_code))
    #     categ_ids = {}
    #     for p in products:
    #         categ = p.categ_id
    #         while categ:
    #             categ_ids[categ.id] = True
    #             categ = categ.parent_id
    #     categ_ids = categ_ids.keys()

    #     is_product_template = products[0]._name == "product.template"
    #     if is_product_template:
    #         prod_tmpl_ids = [tmpl.id for tmpl in products]
    #         # all variants of all products
    #         prod_ids = [p.id for p in
    #                     list(chain.from_iterable([t.product_variant_ids for t in products]))]
    #     else:
    #         prod_ids = [product.id for product in products]
    #         prod_tmpl_ids = [product.product_tmpl_id.id for product in products]


    #     cr.execute(
    #         'SELECT i.id '
    #         'FROM product_pricelist_item AS i '
    #         'WHERE (product_tmpl_id IS NULL OR product_tmpl_id = any(%s)) '
    #             'AND (product_id IS NULL OR (product_id = any(%s))) '
    #             'AND ((categ_id IS NULL) OR (categ_id = any(%s))) '
    #             'AND (price_version_id = %s) '
    #             'AND (date_start IS NULL OR date_start <= %s) '
    #             'AND (date_end IS NULL OR date_end >= %s) '
    #         'ORDER BY sequence, min_quantity desc',
    #         (prod_tmpl_ids, prod_ids, categ_ids, version.id, date, date))
    #     item_ids = [x[0] for x in cr.fetchall()]

    #     items = self.pool.get('product.pricelist.item').browse(cr, uid, item_ids, context=context)
    #     price_types = {}
    #     results = {}
    #     for product, qty, partner in products_by_qty_by_partner:
    #         #TODO : Permet de résoudre un bug de 0.99999999
    #         qty=round(qty,5)
    #         results[product.id] = 0.0
    #         rule_id = False
    #         price = False

    #         # La liste de prix de vente fonctionne en unité de mesure
    #         # La liste de prix d'achat  fonctionne en unité d'achat
    #         if pricelist.type=='sale':
    #             qty_uom_id = context.get('uom') or product.uom_id.id
    #             price_uom_id = product.uom_id.id
    #         else:
    #             qty_uom_id = context.get('uom') or product.uom_po_id.id
    #             price_uom_id = product.uom_po_id.id

    #         qty_in_product_uom = qty
    #         product_qty = qty
    #         if qty_uom_id != price_uom_id:
    #             try:

    #                 if pricelist.type=='sale':
    #                     qty_in_product_uom = product_uom_obj._compute_qty(
    #                         cr, uid, context['uom'], qty, product.uom_id.id or product.uos_id.id)
    #                 else:
    #                     qty_in_product_uom = product_uom_obj._compute_qty(
    #                         cr, uid, context['uom'], qty, product.uom_po_id.id or product.uos_id.id)

    #             except except_orm:
    #                 # Ignored - incompatible UoM in context, use default product UoM
    #                 pass


    #         for rule in items:
    #             if rule.min_quantity and qty_in_product_uom < rule.min_quantity:
    #                 continue
    #             if is_product_template:
    #                 if rule.product_tmpl_id and product.id != rule.product_tmpl_id.id:
    #                     continue
    #                 if rule.product_id and \
    #                         (product.product_variant_count > 1 or product.product_variant_ids[0].id != rule.product_id.id):
    #                     # product rule acceptable on template if has only one variant
    #                     continue
    #             else:
    #                 if rule.product_tmpl_id and product.product_tmpl_id.id != rule.product_tmpl_id.id:
    #                     continue
    #                 if rule.product_id and product.id != rule.product_id.id:
    #                     continue

    #             if rule.categ_id:
    #                 cat = product.categ_id
    #                 while cat:
    #                     if cat.id == rule.categ_id.id:
    #                         break
    #                     cat = cat.parent_id
    #                 if not cat:
    #                     continue

    #             if rule.base == -1:
    #                 if rule.base_pricelist_id:
    #                     price_tmp = self._price_get_multi(cr, uid,
    #                             rule.base_pricelist_id, [(product,
    #                             qty, partner)], context=context)[product.id]
    #                     ptype_src = rule.base_pricelist_id.currency_id.id
    #                     price_uom_id = qty_uom_id
    #                     price = currency_obj.compute(cr, uid,
    #                             ptype_src, pricelist.currency_id.id,
    #                             price_tmp, round=False,
    #                             context=context)
    #             elif rule.base == -2:
    #                 seller = False
    #                 for seller_id in product.seller_ids:
    #                     if (not partner) or (seller_id.name.id != partner):
    #                         continue
    #                     seller = seller_id
    #                 if not seller and product.seller_ids:
    #                     seller = product.seller_ids[0]
    #                 if seller:
    #                     qty_in_seller_uom = qty
    #                     seller_uom = seller.product_uom.id
    #                     if qty_uom_id != seller_uom:
    #                         qty_in_seller_uom = product_uom_obj._compute_qty(cr, uid, qty_uom_id, qty, to_uom_id=seller_uom)
    #                     price_uom_id = seller_uom
    #                     for line in seller.pricelist_ids:
    #                         if line.min_quantity <= qty_in_seller_uom:
    #                             price = line.price

    #             else:
    #                 if rule.base not in price_types:
    #                     price_types[rule.base] = price_type_obj.browse(cr, uid, int(rule.base))
    #                 price_type = price_types[rule.base]

    #                 # price_get returns the price in the context UoM, i.e. qty_uom_id
    #                 price_uom_id = qty_uom_id
    #                 price = currency_obj.compute(
    #                         cr, uid,
    #                         price_type.currency_id.id, pricelist.currency_id.id,
    #                         product_obj._price_get(cr, uid, [product], price_type.field, context=context)[product.id],
    #                         round=False, context=context)

    #             if price is not False:
    #                 price_limit = price
    #                 price = price * (1.0+(rule.price_discount or 0.0))
    #                 if rule.price_round:
    #                     price = tools.float_round(price, precision_rounding=rule.price_round)


    #                 if pricelist.type=='sale':
    #                     convert_to_price_uom = (lambda price: product_uom_obj._compute_price(
    #                                                 cr, uid, product.uom_id.id,
    #                                                 price, price_uom_id))
    #                 else:
    #                     convert_to_price_uom = (lambda price: product_uom_obj._compute_price(
    #                                                 cr, uid, product.uom_po_id.id,
    #                                                 price, price_uom_id))


    #                 if rule.price_surcharge and rule.min_quantity <= product_qty:
    #                     price_surcharge = convert_to_price_uom(rule.price_surcharge)
    #                     price += price_surcharge

    #                 if rule.price_min_margin:
    #                     price_min_margin = convert_to_price_uom(rule.price_min_margin)
    #                     price = max(price, price_limit + price_min_margin)

    #                 if rule.price_max_margin:
    #                     price_max_margin = convert_to_price_uom(rule.price_max_margin)
    #                     price = min(price, price_limit + price_max_margin)
    #                 rule_id = rule.id
    #             break

    #         # Final price conversion to target UoM
    #         price = product_uom_obj._compute_price(cr, uid, price_uom_id, price, qty_uom_id)
    #         results[product.id] = (price, rule_id)
    #     return results


# class product_uom(osv.osv):
#     _inherit = "product.uom"
    
#     _columns = {
#         'min_quantity': fields.float('Quantité minimum'),
#         'amount': fields.float('Montant', digits_compute= dp.get_precision('Product Price')),
#     }
