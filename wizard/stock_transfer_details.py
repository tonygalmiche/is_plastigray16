# -*- coding: utf-8 -*-
from odoo import models,fields,api
from datetime import datetime, date


# def _date_reception():
#     return datetime.date.today().strftime('%Y-%m-%d')


class stock_transfer_details(models.TransientModel):
    _name = 'stock.transfer_details'
    _description = "Wizard pour les picking qui n'existait plus dans Odoo 16"


    picking_id           = fields.Many2one('stock.picking', 'Picking', default=lambda self:self.env.context.get("active_id"))
    is_purchase_order_id = fields.Many2one(related="picking_id.purchase_id")
    is_num_bl            = fields.Char("N° BL fournisseur")
    is_date_reception    = fields.Date('Date de réception', default=lambda *a: fields.datetime.now())
    line_ids             = fields.One2many('stock.transfer_details_items', 'transfert_id', "Lignes", default=lambda self: self._default_get_line_ids())  #, compute='_compute_line_ids', store=True)


    def valider_action(self):
        for obj in self:
            obj.picking_id.is_num_bl         = obj.is_num_bl
            obj.picking_id.is_date_reception = obj.is_date_reception
            obj.picking_id.move_line_ids_without_package.unlink()
            for line in obj.line_ids:
                if  line.quantity>0:
                    if  line.is_lot_fournisseur:
                        line.lot_id.is_lot_fournisseur = line.is_lot_fournisseur
                    #** Création stock.move.line **********************************

                    location_dest_id = obj.picking_id.location_dest_id.id
                    if line.move_id.product_id.is_ctrl_rcp=='bloque':
                        locations = self.env['stock.location'].search([('name','=','Q2')])
                        for location in locations:
                            location_dest_id=location.id
                    vals={
                        #"location_id"     : location_id,
                        "location_dest_id": location_dest_id,
                        "lot_id"          : line.lot_id.id,
                        "qty_done"        : line.quantity,
                        "product_id"      : line.move_id.product_id.id,
                        "move_id"         : line.move_id.id,
                        "picking_id"      : obj.picking_id.id,
                    }
                    move_line=self.env['stock.move.line'].create(vals)
                    line.move_id.invoice_state='2binvoiced'
                #**************************************************************
            obj.picking_id._action_done()

    def _default_get_line_ids(self):
        lines = []
        active_id = self.env.context.get("active_id")
        if active_id:
            picking = self.env['stock.picking'].browse(active_id)
            for line in picking.move_ids_without_package:
                #** Création des lots *****************************************
                lot_id=False
                if picking.purchase_id:
                    numlot=date.today().strftime('%y%m%d')+picking.name
                    lots = self.env['stock.lot'].search([('product_id','=', line.product_id.id),('name','=',numlot)])
                    if len(lots)>0:
                        lot=lots[0]
                    else:
                        vals={
                            "name"      : numlot,
                            "product_id": line.product_id.id,
                        }
                        lot=self.env['stock.lot'].create(vals)
                    lot_id = lot.id
                #**************************************************************
                vals={
                    "move_id"    : line.id,
                    "product_id" : line.product_id.id,
                    "product_uom_id": line.product_uom.id,
                    "name"       : line.description_picking,
                    "quantity"   : line.product_uom_qty,
                    "lot_id"     : lot_id,
                }
                lines.append([0, False, vals])
        return lines
        #self.line_ids=lines






#     @api.one
#     def do_detailed_transfer(self):
#         res = super(stock_transfer_details, self).do_detailed_transfer()
#         for obj in self:
#             if obj.picking_id.is_purchase_order_id:
#                 for row in obj.item_ids:
#                     if row.lot_id:
#                         row.lot_id.is_lot_fournisseur=row.is_lot_fournisseur
#         return res


#     def default_get(self, cr, uid, fields, context=None):
#         if context is None: context = {}
#         picking_ids = context.get('active_ids', [])
#         picking_id, = picking_ids
#         picking = self.pool.get('stock.picking').browse(cr, uid, picking_id, context=context)
#         stock_product_lot_obj = self.pool.get('stock.production.lot')
#         res = super(stock_transfer_details, self).default_get(cr, uid, fields, context=context)


#         #** Permet de gérer les réceptions avec le même article ****************
#         picking_ids = context.get('active_ids', [])
#         active_model = context.get('active_model')

#         if not picking_ids or len(picking_ids) != 1:
#             return res
#         assert active_model in ('stock.picking'), 'Bad context propagation'
#         picking_id, = picking_ids
#         picking = self.pool.get('stock.picking').browse(cr, uid, picking_id, context=context)
#         items = []
#         packs = []
#         if not picking.pack_operation_ids:
#             picking.do_prepare_partial()
#         for op in picking.pack_operation_ids:
#             item = {
#                 'packop_id': op.id,
#                 'product_id': op.product_id.id,
#                 'product_uom_id': op.product_uom_id.id,
#                 'quantity': op.product_qty,
#                 'package_id': op.package_id.id,
#                 'lot_id': op.lot_id.id,
#                 'is_lot_fournisseur':op.lot_id.is_lot_fournisseur,
#                 'sourceloc_id': op.location_id.id,
#                 'destinationloc_id': op.location_dest_id.id,
#                 'result_package_id': op.result_package_id.id,
#                 'date': op.date, 
#                 'owner_id': op.owner_id.id,
#                 'name':op.move_id.name
#             }
#             if op.product_id:
#                 items.append(item)
#             elif op.package_id:
#                 packs.append(item)
#         res.update(item_ids=items)
#         res.update(packop_ids=packs)
#         #***********************************************************************



#         #** Créer lot avec le même numéro que la réception et la date devant ***
#         if picking.is_purchase_order_id:
#             res.update({'is_purchase_order_id': picking.is_purchase_order_id.id})
#             item_data = res.get('item_ids',[])
#             for item in item_data:
#                 if item.get('lot_id', False) == False:
#                     numlot=datetime.date.today().strftime('%y%m%d')+picking.name
#                     lot_id = stock_product_lot_obj.search(cr, uid, [
#                             ('name','=', numlot),
#                             ('product_id','=', item.get('product_id'))
#                         ], context=context)
#                     if lot_id: lot_id = lot_id[0]
#                     else:
#                         lot_id = stock_product_lot_obj.create(cr, uid, {
#                                 'name': numlot,
#                                 'product_id': item.get('product_id'),
#                         }, context=context)
#                     if lot_id:
#                         item['lot_id']=lot_id
#         #***********************************************************************

#         return res
        



class stock_transfer_details_items(models.TransientModel):
    _name = 'stock.transfer_details_items'
    _description = "Lignes du wizard pour les picking qui n'existait plus dans Odoo 16"

    transfert_id          = fields.Many2one('stock.transfer_details', 'Transfert', required=True, ondelete='cascade')
    move_id               = fields.Many2one('stock.move', 'Mouvement')
    product_id            = fields.Many2one('product.product', 'Article') #, required=True)
    name                  = fields.Char('Description')
    quantity              = fields.Float("Quantité"         , digits=(14, 6))
    #product_uom_id        = fields.Many2one(string="Unité", related='product_id.uom_id')
    product_uom_id        = fields.Many2one('uom.uom', string="Unité")
    lot_id                = fields.Many2one('stock.lot', 'Lot')
    is_lot_fournisseur    = fields.Char("Lot fournisseur / Date péremption")
    is_produit_perissable = fields.Boolean(related="product_id.is_produit_perissable")
    is_ctrl_rcp           = fields.Selection(related='product_id.is_ctrl_rcp')


#     @api.multi
#     def produit_perissable_action(self):
#         print self

