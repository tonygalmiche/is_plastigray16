# -*- coding: utf-8 -*-
from odoo import models,fields,api
import datetime
from dateutil.relativedelta import relativedelta


class product_pricelist_item(models.Model):
    _inherit = "product.pricelist.item"
    _order="price_version_id,product_id,sequence"

    date_start         = fields.Date('Date de début de validité')
    date_end           = fields.Date('Date de fin de validité')
    justification      = fields.Char('Justification du prix')
    product_uom_id     = fields.Many2one('product.uom', 'Unité'        , related='product_id.uom_id'   , readonly=True)
    product_po_uom_id  = fields.Many2one('product.uom', "Unité d'achat", related='product_id.uom_po_id', readonly=True)
    is_ref_client      = fields.Char("Référence client"  , related='product_id.is_ref_client', readonly=True)
    is_mold_dossierf   = fields.Char("Moule ou Dossier F", related='product_id.is_mold_dossierf', readonly=True)
    is_gestionnaire_id = fields.Many2one('is.gestionnaire', "Gestionnaire", related='product_id.is_gestionnaire_id', readonly=True)
    min_quantity       = fields.Float('Quantité minimum', required=True)


    def on_change_product_id(self, product_id):
        context=self._context
        res = {}
        if product_id:
            if 'default_price_version_id' in context:
                res.setdefault('value',{})
                product = self.env['product.product'].browse(product_id)
                if product:
                    version = self.env['product.pricelist.version'].browse(context['default_price_version_id'])
                    if version.pricelist_id.type=='sale':
                        partner=version.pricelist_id.partner_id
                        min_quantity=self.env['product.template'].get_lot_livraison(product.product_tmpl_id, partner)
                    else:
                        min_quantity=product.lot_mini
                        product_uom = self.env['product.uom'].browse(product.uom_po_id.id)
                        min_quantity = product_uom._compute_qty(product.uom_id.id, min_quantity, product.uom_po_id.id)
                    res['value']['product_uom_id']    = product.uom_id.id
                    res['value']['product_po_uom_id'] = product.uom_po_id.id
                    res['value']['min_quantity']      = min_quantity
                    res['value']['price_surcharge']   = product.uom_po_id.amount
        return res




#TODO product.pricelist.version n'existe plus !!!!


# class product_pricelist_version(models.Model):
#     _inherit = "product.pricelist.version"


#     def action_liste_items(self):
#         for obj in self:
#             if obj.pricelist_id.type=='sale':
#                 view_id=self.env.ref('is_plastigray.is_product_pricelist_item_sale_tree_view')
#             else:
#                 view_id=self.env.ref('is_plastigray.is_product_pricelist_item_purchase_tree_view')
#             return {
#                 'name': obj.name,
#                 'view_mode': 'tree',
#                 'view_type': 'form',
#                 'res_model': 'product.pricelist.item',
#                 'type': 'ir.actions.act_window',
#                 'view_id': view_id.id,
#                 'domain': [('price_version_id','=',obj.id)],
#                 'context': {'default_price_version_id': obj.id }
#             }


#     def print_pricelist_version(self):
#         cr, uid, context = self.env.args
#         for obj in self:
#             return self.pool['report'].get_action(cr, uid, obj.id, 'is_plastigray.report_pricelist_version', context=context)


#     def action_dupliquer(self, cr, uid, ids, context=None):
#         for obj in self.browse(cr, uid, ids, dict(context, active_test=False)):
#             date_end=datetime.datetime.strptime(obj.date_end, '%Y-%m-%d')
#             date_start = date_end   + datetime.timedelta(days=1)
#             date_end = date_start + relativedelta(years=1)
#             date_end = date_end   + datetime.timedelta(days=-1)
#             name=str(int(obj.name)+1)
#             vals = {
#                 'pricelist_id' : obj.pricelist_id.id,
#                 'name': name,
#                 'active': obj.active,
#                 'date_start': date_start,
#                 'date_end': date_end ,
#             }
#             model = self.pool.get('product.pricelist.version')
#             new_id = model.create(cr, uid, vals, context=context)


#             model = self.pool.get('product.pricelist.item')
#             for item in obj.items_id:
#                 start=item.date_start
#                 if start:
#                     start=date_start
#                 end=item.date_end
#                 if end:
#                     end=date_end
#                 vals = {
#                     'price_version_id': new_id,
#                     'name' : name,
#                     'product_id': item.product_id.id,
#                     'min_quantity': item.min_quantity,
#                     'sequence': item.sequence,
#                     'date_start': item.date_start,
#                     'date_end': item.date_end,
#                     'justification': item.justification,
#                     'price_surcharge': item.price_surcharge,
#                 }
#                 id = model.create(cr, uid, vals, context=context)


#         return {
#             'name': "Liste de prix",
#             'view_mode': 'form',
#             'view_type': 'form',
#             'res_model': 'product.pricelist',
#             'type': 'ir.actions.act_window',
#             'res_id': obj.pricelist_id.id,
#         }








class product_pricelist(models.Model):
    _inherit = "product.pricelist"
    
    partner_id = fields.Many2one('res.partner', 'Partenaire')




    
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
