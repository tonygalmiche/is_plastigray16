# -*- coding: utf-8 -*-
from odoo import models,fields,api,tools

class stock_inventory(models.Model):
    _name='stock.inventory'
    _description="Inventaire (model d'Odoo 8 supprimé dans Odoo 16 => Recréé pour migration)"
    _order="id desc"

    INVENTORY_STATE_SELECTION = [
        ('draft', 'Brouillon'),
        ('cancel', 'Annulé'),
        ('confirm', 'En cours'),
        ('done', 'Validé'),
    ]
    INVENTORY_FILTER_SELECTION = [
        ('none'   , 'Tous les articles'),
        ('product', 'Un article seulement'),
    ]

    name= fields.Char('Référence', required=True, readonly=True, states={'draft': [('readonly', False)]})
    date= fields.Datetime('Date', required=True, readonly=True, default=fields.Datetime.now, copy=False)
    line_ids= fields.One2many('stock.inventory.line', 'inventory_id', 'Lignes', readonly=False, states={'done': [('readonly', True)]}, copy=False)
    move_ids= fields.One2many('stock.move', 'inventory_id', 'Mouvements', help="Inventory Moves.", states={'done': [('readonly', True)]})
    state= fields.Selection(INVENTORY_STATE_SELECTION, 'Etat', readonly=True, index=True, copy=False, default="draft")
    company_id= fields.Many2one('res.company', 'Société', required=True, index=True, readonly=True, default=1)
    location_id= fields.Many2one('stock.location', 'Emplacement', domain=[("usage","=","internal")],  required=True, readonly=True, states={'draft': [('readonly', False)]})
    product_id= fields.Many2one('product.product', 'Article', readonly=True, states={'draft': [('readonly', False)]})
    #package_id= fields.Many2one('stock.quant.package', 'Inventoried Pack', readonly=True, states={'draft': [('readonly', False)]})
    #partner_id= fields.Many2one('res.partner', 'Inventoried Owner', readonly=True, states={'draft': [('readonly', False)]})
    lot_id= fields.Many2one('stock.lot', 'Lot', readonly=True, states={'draft': [('readonly', False)]}, copy=False)
    #move_ids_exist= fields.function(_get_move_ids_exist, type='boolean', string=' Stock Move Exists?', help='technical field for attrs in view'),
    filter=fields.Selection(INVENTORY_FILTER_SELECTION, 'Inventaire de', required=True, readonly=True, states={'draft': [('readonly', False)]}, default='none')


    def demarrer_inventaire_action(self):
        for obj in self:
            filtre=[ 
                ('location_id', '=', obj.location_id.id),
            ]
            if obj.product_id and obj.filter=="product":
                filtre.append(('product_id', '=', obj.product_id.id))
            quants=self.env['stock.quant'].search(filtre)
            for quant in quants:
                vals={
                    "inventory_id": obj.id,
                    "location_id": quant.location_id.id,
                    "product_id": quant.product_id.id,
                    "product_uom_id": quant.product_id.uom_id.id,
                    "product_qty": quant.quantity,
                    "prod_lot_id": quant.lot_id.id,
                }
                line=self.env['stock.inventory.line'].create(vals)
            obj.state="confirm"
        return self.continuer_inventaire_action()


    def continuer_inventaire_action(self):
        for obj in self:
            context = {
                'default_inventory_id': obj.id,
                'default_location_id' : obj.location_id.id,
            }
            if obj.product_id and obj.filter=="product":
                context["default_product_id"] = obj.product_id.id
            return {
                'name': 'Lignes',
                'view_mode': 'tree',
                'res_model': 'stock.inventory.line',
                'domain': [
                    ('inventory_id','=',obj.id),
                ],
                'context':context,
                'type': 'ir.actions.act_window',
                'limit': 1000,
            }


    def valider_inventaire_action(self):
        for obj in self:
            for line in obj.line_ids:
                name = obj.name
                qty = line.theoretical_qty - line.product_qty
                inventory_location_id = 5 #TODO ; Emplacement inventaire
                location_id = line.location_id.id
                location_dest_id = inventory_location_id 
                if qty<0:
                    qty=-qty
                    location_dest_id = line.location_id.id
                    location_id = inventory_location_id
                if qty>0:
                    vals={
                        "inventory_id": line.inventory_id.id,
                        "product_id": line.product_id.id,
                        "product_uom": line.product_uom_id.id,
                        "location_id": location_id,
                        "location_dest_id": location_dest_id,
                        "origin": name,
                        "name": name,
                        "reference": name,
                        "procure_method": "make_to_stock",
                        "product_uom_qty": qty,
                        "scrapped": False,
                        "propagate_cancel": True,
                        "is_inventory": True,
                        "additional": False,
                    }
                    move=self.env['stock.move'].create(vals)
                    vals={
                        "move_id": move.id,
                        "product_id": line.product_id.id,
                        "product_uom_id": line.product_uom_id.id,
                        "location_id": location_id,
                        "location_dest_id": location_dest_id,
                        "lot_id": line.prod_lot_id.id,
                        "qty_done": qty,
                        "reference": name,
                    }
                    move_line=self.env['stock.move.line'].create(vals)
                    #move._action_confirm()
                    move._action_done()
            obj.state="done"


    def voir_mouvements_action(self):
        for obj in self:
            return {
                'name': 'Mouvements',
                'view_mode': 'tree,form',
                'res_model': 'stock.move',
                'domain': [
                    ('inventory_id','=',obj.id),
                ],
                'type': 'ir.actions.act_window',
                'limit': 1000,
            }







class stock_inventory_line(models.Model):
    _name='stock.inventory.line'
    _description="Lignes d'Inventaire (model d'Odoo 8 supprimé dans Odoo 16 => Recréé pour migration)"
    _order="id"

    inventory_id=fields.Many2one('stock.inventory', 'Inventaire', ondelete='cascade', index=True)
    location_id=fields.Many2one('stock.location', 'Emplacement', required=True, index=True)
    product_id=fields.Many2one('product.product', 'Article', required=True, index=True)
    product_uom_id=fields.Many2one('uom.uom', 'unité', compute='_compute_product_id', readonly=True, store=True)
    product_qty=fields.Float('Quantité inventoriée', digits='Product Unit of Measure', default=0)
    company_id=fields.Many2one('res.company', 'Société', index=True, readonly=True,default=1)
    prod_lot_id=fields.Many2one('stock.lot', 'Lot', domain="[('product_id','=',product_id)]")
    state=fields.Selection(related='inventory_id.state')
    theoretical_qty=fields.Float('Quantité théorique', compute='_compute_theoretical_qty', digits='Product Unit of Measure', readonly=True, store=True)
    partner_id=fields.Many2one('res.partner', 'Partenaire')
    product_name=fields.Char('Nom Article'     , compute='_compute_product_id' , readonly=True, store=True)
    location_name=fields.Char('Nom Emplacement', compute='_compute_location_id', readonly=True, store=True)
    prodlot_name=fields.Char('Nom Lot'         , compute='_compute_prod_lot_id', readonly=True, store=True)


    @api.depends('product_id')
    def _compute_product_id(self):
        for obj in self:
            obj.product_uom_id = obj.product_id.uom_id.id
            obj.product_name = obj.product_id.name


    @api.depends('location_id')
    def _compute_location_id(self):
        for obj in self:
            obj.location_name = obj.location_id.name


    @api.depends('prod_lot_id')
    def _compute_prod_lot_id(self):
        for obj in self:
            obj.prodlot_name = obj.prod_lot_id.name


    @api.depends('product_id','prod_lot_id','location_id')
    def _compute_theoretical_qty(self):
        for obj in self:
            filtre=[ 
                ('location_id', '=', obj.location_id.id),
                ('lot_id', '=', obj.prod_lot_id.id),
                ('product_id', '=', obj.product_id.id),
            ]
            quants=self.env['stock.quant'].search(filtre)
            qty=0
            for quant in quants:
                qty+=quant.quantity
            obj.theoretical_qty = qty






# class stock_inventory(osv.osv):
#     _name = "stock.inventory"
#     _description = "Inventory"

#     def _get_move_ids_exist(self, cr, uid, ids, field_name, arg, context=None):
#         res = {}
#         for inv in self.browse(cr, uid, ids, context=context):
#             res[inv.id] = False
#             if inv.move_ids:
#                 res[inv.id] = True
#         return res

#     def _get_available_filters(self, cr, uid, context=None):
#         """
#            This function will return the list of filter allowed according to the options checked
#            in 'Settings\Warehouse'.

#            :rtype: list of tuple
#         """
#         #default available choices
#         res_filter = [('none', _('All products')), ('partial', _('Manual Selection of Products')), ('product', _('One product only'))]
#         if self.pool.get('res.users').has_group(cr, uid, 'stock.group_tracking_owner'):
#             res_filter.append(('owner', _('One owner only')))
#             res_filter.append(('product_owner', _('One product for a specific owner')))
#         if self.pool.get('res.users').has_group(cr, uid, 'stock.group_production_lot'):
#             res_filter.append(('lot', _('One Lot/Serial Number')))
#         if self.pool.get('res.users').has_group(cr, uid, 'stock.group_tracking_lot'):
#             res_filter.append(('pack', _('A Pack')))
#         return res_filter

#     def _get_total_qty(self, cr, uid, ids, field_name, args, context=None):
#         res = {}
#         for inv in self.browse(cr, uid, ids, context=context):
#             res[inv.id] = sum([x.product_qty for x in inv.line_ids])
#         return res

#     _columns = {
#         'name': fields.char('Inventory Reference', required=True, readonly=True, states={'draft': [('readonly', False)]}, help="Inventory Name."),
#         'date': fields.datetime('Inventory Date', required=True, readonly=True, help="The date that will be used for the stock level check of the products and the validation of the stock move related to this inventory."),
#         'line_ids': fields.one2many('stock.inventory.line', 'inventory_id', 'Inventories', readonly=False, states={'done': [('readonly', True)]}, help="Inventory Lines.", copy=True),
#         'move_ids': fields.one2many('stock.move', 'inventory_id', 'Created Moves', help="Inventory Moves.", states={'done': [('readonly', True)]}),
#         'state': fields.selection(INVENTORY_STATE_SELECTION, 'Status', readonly=True, select=True, copy=False),
#         'company_id': fields.many2one('res.company', 'Company', required=True, select=True, readonly=True, states={'draft': [('readonly', False)]}),
#         'location_id': fields.many2one('stock.location', 'Inventoried Location', required=True, readonly=True, states={'draft': [('readonly', False)]}),
#         'product_id': fields.many2one('product.product', 'Inventoried Product', readonly=True, states={'draft': [('readonly', False)]}, help="Specify Product to focus your inventory on a particular Product."),
#         'package_id': fields.many2one('stock.quant.package', 'Inventoried Pack', readonly=True, states={'draft': [('readonly', False)]}, help="Specify Pack to focus your inventory on a particular Pack."),
#         'partner_id': fields.many2one('res.partner', 'Inventoried Owner', readonly=True, states={'draft': [('readonly', False)]}, help="Specify Owner to focus your inventory on a particular Owner."),
#         'lot_id': fields.many2one('stock.production.lot', 'Inventoried Lot/Serial Number', readonly=True, states={'draft': [('readonly', False)]}, help="Specify Lot/Serial Number to focus your inventory on a particular Lot/Serial Number.", copy=False),
#         'move_ids_exist': fields.function(_get_move_ids_exist, type='boolean', string=' Stock Move Exists?', help='technical field for attrs in view'),
#         'filter': fields.selection(_get_available_filters, 'Inventory of', required=True,
#                                    help="If you do an entire inventory, you can choose 'All Products' and it will prefill the inventory with the current stock.  If you only do some products  "\
#                                       "(e.g. Cycle Counting) you can choose 'Manual Selection of Products' and the system won't propose anything.  You can also let the "\
#                                       "system propose for a single product / lot /... "),
#         'total_qty': fields.function(_get_total_qty, type="float"),
#     }

#     def _default_stock_location(self, cr, uid, context=None):
#         try:
#             warehouse = self.pool.get('ir.model.data').get_object(cr, uid, 'stock', 'warehouse0')
#             return warehouse.lot_stock_id.id
#         except:
#             return False

#     _defaults = {
#         'date': fields.datetime.now,
#         'state': 'draft',
#         'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.inventory', context=c),
#         'location_id': _default_stock_location,
#         'filter': 'none',
#     }

#     def reset_real_qty(self, cr, uid, ids, context=None):
#         inventory = self.browse(cr, uid, ids[0], context=context)
#         line_ids = [line.id for line in inventory.line_ids]
#         self.pool.get('stock.inventory.line').write(cr, uid, line_ids, {'product_qty': 0})
#         return True

#     def action_done(self, cr, uid, ids, context=None):
#         """ Finish the inventory
#         @return: True
#         """
#         for inv in self.browse(cr, uid, ids, context=context):
#             for inventory_line in inv.line_ids:
#                 if inventory_line.product_qty < 0 and inventory_line.product_qty != inventory_line.theoretical_qty:
#                     raise osv.except_osv(_('Warning'), _('You cannot set a negative product quantity in an inventory line:\n\t%s - qty: %s' % (inventory_line.product_id.name, inventory_line.product_qty)))
#             self.action_check(cr, uid, [inv.id], context=context)
#             self.write(cr, uid, [inv.id], {'state': 'done'}, context=context)
#             self.post_inventory(cr, uid, inv, context=context)
#         return True

#     def post_inventory(self, cr, uid, inv, context=None):
#         #The inventory is posted as a single step which means quants cannot be moved from an internal location to another using an inventory
#         #as they will be moved to inventory loss, and other quants will be created to the encoded quant location. This is a normal behavior
#         #as quants cannot be reuse from inventory location (users can still manually move the products before/after the inventory if they want).
#         move_obj = self.pool.get('stock.move')
#         move_obj.action_done(cr, uid, [x.id for x in inv.move_ids if x.state != 'done'], context=context)

#     def action_check(self, cr, uid, ids, context=None):
#         """ Checks the inventory and computes the stock move to do
#         @return: True
#         """
#         inventory_line_obj = self.pool.get('stock.inventory.line')
#         stock_move_obj = self.pool.get('stock.move')
#         for inventory in self.browse(cr, uid, ids, context=context):
#             #first remove the existing stock moves linked to this inventory
#             move_ids = [move.id for move in inventory.move_ids]
#             stock_move_obj.unlink(cr, uid, move_ids, context=context)
#             for line in inventory.line_ids:
#                 #compare the checked quantities on inventory lines to the theorical one
#                 stock_move = inventory_line_obj._resolve_inventory_line(cr, uid, line, context=context)

#     def action_cancel_draft(self, cr, uid, ids, context=None):
#         """ Cancels the stock move and change inventory state to draft.
#         @return: True
#         """
#         for inv in self.browse(cr, uid, ids, context=context):
#             self.write(cr, uid, [inv.id], {'line_ids': [(5,)]}, context=context)
#             self.pool.get('stock.move').action_cancel(cr, uid, [x.id for x in inv.move_ids], context=context)
#             self.write(cr, uid, [inv.id], {'state': 'draft'}, context=context)
#         return True

#     def action_cancel_inventory(self, cr, uid, ids, context=None):
#         self.action_cancel_draft(cr, uid, ids, context=context)

#     def prepare_inventory(self, cr, uid, ids, context=None):
#         inventory_line_obj = self.pool.get('stock.inventory.line')
#         for inventory in self.browse(cr, uid, ids, context=context):
#             # If there are inventory lines already (e.g. from import), respect those and set their theoretical qty
#             line_ids = [line.id for line in inventory.line_ids]
#             if not line_ids and inventory.filter != 'partial':
#                 #compute the inventory lines and create them
#                 vals = self._get_inventory_lines(cr, uid, inventory, context=context)
#                 for product_line in vals:
#                     inventory_line_obj.create(cr, uid, product_line, context=context)
#         return self.write(cr, uid, ids, {'state': 'confirm', 'date': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})

#     def _get_inventory_lines(self, cr, uid, inventory, context=None):
#         location_obj = self.pool.get('stock.location')
#         product_obj = self.pool.get('product.product')
#         location_ids = location_obj.search(cr, uid, [('id', 'child_of', [inventory.location_id.id])], context=context)
#         domain = ' location_id in %s'
#         args = (tuple(location_ids),)
#         if inventory.partner_id:
#             domain += ' and owner_id = %s'
#             args += (inventory.partner_id.id,)
#         if inventory.lot_id:
#             domain += ' and lot_id = %s'
#             args += (inventory.lot_id.id,)
#         if inventory.product_id:
#             domain += ' and product_id = %s'
#             args += (inventory.product_id.id,)
#         if inventory.package_id:
#             domain += ' and package_id = %s'
#             args += (inventory.package_id.id,)

#         cr.execute('''
#            SELECT product_id, sum(qty) as product_qty, location_id, lot_id as prod_lot_id, package_id, owner_id as partner_id
#            FROM stock_quant WHERE''' + domain + '''
#            GROUP BY product_id, location_id, lot_id, package_id, partner_id
#         ''', args)
#         vals = []
#         for product_line in cr.dictfetchall():
#             #replace the None the dictionary by False, because falsy values are tested later on
#             for key, value in product_line.items():
#                 if not value:
#                     product_line[key] = False
#             product_line['inventory_id'] = inventory.id
#             product_line['theoretical_qty'] = product_line['product_qty']
#             if product_line['product_id']:
#                 product = product_obj.browse(cr, uid, product_line['product_id'], context=context)
#                 product_line['product_uom_id'] = product.uom_id.id
#             vals.append(product_line)
#         return vals

#     def _check_filter_product(self, cr, uid, ids, context=None):
#         for inventory in self.browse(cr, uid, ids, context=context):
#             if inventory.filter == 'none' and inventory.product_id and inventory.location_id and inventory.lot_id:
#                 return True
#             if inventory.filter not in ('product', 'product_owner') and inventory.product_id:
#                 return False
#             if inventory.filter != 'lot' and inventory.lot_id:
#                 return False
#             if inventory.filter not in ('owner', 'product_owner') and inventory.partner_id:
#                 return False
#             if inventory.filter != 'pack' and inventory.package_id:
#                 return False
#         return True

#     def onchange_filter(self, cr, uid, ids, filter, context=None):
#         to_clean = { 'value': {} }
#         if filter not in ('product', 'product_owner'):
#             to_clean['value']['product_id'] = False
#         if filter != 'lot':
#             to_clean['value']['lot_id'] = False
#         if filter not in ('owner', 'product_owner'):
#             to_clean['value']['partner_id'] = False
#         if filter != 'pack':
#             to_clean['value']['package_id'] = False
#         return to_clean

#     _constraints = [
#         (_check_filter_product, 'The selected inventory options are not coherent.',
#             ['filter', 'product_id', 'lot_id', 'partner_id', 'package_id']),
#     ]

# class stock_inventory_line(osv.osv):
#     _name = "stock.inventory.line"
#     _description = "Inventory Line"
#     _order = "inventory_id, location_name, product_code, product_name, prodlot_name"

#     def _get_product_name_change(self, cr, uid, ids, context=None):
#         return self.pool.get('stock.inventory.line').search(cr, uid, [('product_id', 'in', ids)], context=context)

#     def _get_location_change(self, cr, uid, ids, context=None):
#         return self.pool.get('stock.inventory.line').search(cr, uid, [('location_id', 'in', ids)], context=context)

#     def _get_prodlot_change(self, cr, uid, ids, context=None):
#         return self.pool.get('stock.inventory.line').search(cr, uid, [('prod_lot_id', 'in', ids)], context=context)

#     def _get_theoretical_qty(self, cr, uid, ids, name, args, context=None):
#         res = {}
#         quant_obj = self.pool["stock.quant"]
#         uom_obj = self.pool["product.uom"]
#         for line in self.browse(cr, uid, ids, context=context):
#             quant_ids = self._get_quants(cr, uid, line, context=context)
#             quants = quant_obj.browse(cr, uid, quant_ids, context=context)
#             tot_qty = sum([x.qty for x in quants])
#             if line.product_uom_id and line.product_id.uom_id.id != line.product_uom_id.id:
#                 tot_qty = uom_obj._compute_qty_obj(cr, uid, line.product_id.uom_id, tot_qty, line.product_uom_id, context=context)
#             res[line.id] = tot_qty
#         return res

#     _columns = {
#         'inventory_id': fields.many2one('stock.inventory', 'Inventory', ondelete='cascade', select=True),
#         'location_id': fields.many2one('stock.location', 'Location', required=True, select=True),
#         'product_id': fields.many2one('product.product', 'Product', required=True, select=True),
#         'package_id': fields.many2one('stock.quant.package', 'Pack', select=True),
#         'product_uom_id': fields.many2one('product.uom', 'Product Unit of Measure', required=True),
#         'product_qty': fields.float('Checked Quantity', digits_compute=dp.get_precision('Product Unit of Measure')),
#         'company_id': fields.related('inventory_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, select=True, readonly=True),
#         'prod_lot_id': fields.many2one('stock.production.lot', 'Serial Number', domain="[('product_id','=',product_id)]"),
#         'state': fields.related('inventory_id', 'state', type='char', string='Status', readonly=True),
#         'theoretical_qty': fields.function(_get_theoretical_qty, type='float', digits_compute=dp.get_precision('Product Unit of Measure'),
#                                            store={'stock.inventory.line': (lambda self, cr, uid, ids, c={}: ids, ['location_id', 'product_id', 'package_id', 'product_uom_id', 'company_id', 'prod_lot_id', 'partner_id'], 20),},
#                                            readonly=True, string="Theoretical Quantity"),
#         'partner_id': fields.many2one('res.partner', 'Owner'),
#         'product_name': fields.related('product_id', 'name', type='char', string='Product Name', store={
#                                                                                             'product.product': (_get_product_name_change, ['name', 'default_code'], 20),
#                                                                                             'stock.inventory.line': (lambda self, cr, uid, ids, c={}: ids, ['product_id'], 20),}),
#         'product_code': fields.related('product_id', 'default_code', type='char', string='Product Code', store={
#                                                                                             'product.product': (_get_product_name_change, ['name', 'default_code'], 20),
#                                                                                             'stock.inventory.line': (lambda self, cr, uid, ids, c={}: ids, ['product_id'], 20),}),
#         'location_name': fields.related('location_id', 'complete_name', type='char', string='Location Name', store={
#                                                                                             'stock.location': (_get_location_change, ['name', 'location_id', 'active'], 20),
#                                                                                             'stock.inventory.line': (lambda self, cr, uid, ids, c={}: ids, ['location_id'], 20),}),
#         'prodlot_name': fields.related('prod_lot_id', 'name', type='char', string='Serial Number Name', store={
#                                                                                             'stock.production.lot': (_get_prodlot_change, ['name'], 20),
#                                                                                             'stock.inventory.line': (lambda self, cr, uid, ids, c={}: ids, ['prod_lot_id'], 20),}),
#     }

#     _defaults = {
#         'product_qty': 0,
#         'product_uom_id': lambda self, cr, uid, ctx=None: self.pool['ir.model.data'].get_object_reference(cr, uid, 'product', 'product_uom_unit')[1]
#     }

#     def create(self, cr, uid, values, context=None):
#         product_obj = self.pool.get('product.product')
#         dom = [('product_id', '=', values.get('product_id')), ('inventory_id.state', '=', 'confirm'),
#                ('location_id', '=', values.get('location_id')), ('partner_id', '=', values.get('partner_id')),
#                ('package_id', '=', values.get('package_id')), ('prod_lot_id', '=', values.get('prod_lot_id'))]
#         res = self.search(cr, uid, dom, context=context)
#         if res:
#             location = self.pool['stock.location'].browse(cr, uid, values.get('location_id'), context=context)
#             product = product_obj.browse(cr, uid, values.get('product_id'), context=context)
#             raise Warning(_("You cannot have two inventory adjustements in state 'in Progess' with the same product(%s), same location(%s), same package, same owner and same lot. Please first validate the first inventory adjustement with this product before creating another one.") % (product.name, location.name))
#         return super(stock_inventory_line, self).create(cr, uid, values, context=context)

#     def _get_quants(self, cr, uid, line, context=None):
#         quant_obj = self.pool["stock.quant"]
#         dom = [('company_id', '=', line.company_id.id), ('location_id', '=', line.location_id.id), ('lot_id', '=', line.prod_lot_id.id),
#                         ('product_id','=', line.product_id.id), ('owner_id', '=', line.partner_id.id), ('package_id', '=', line.package_id.id)]
#         quants = quant_obj.search(cr, uid, dom, context=context)
#         return quants

#     def onchange_createline(self, cr, uid, ids, location_id=False, product_id=False, uom_id=False, package_id=False, prod_lot_id=False, partner_id=False, company_id=False, context=None):
#         quant_obj = self.pool["stock.quant"]
#         uom_obj = self.pool["product.uom"]
#         res = {'value': {}}
#         # If no UoM already put the default UoM of the product
#         if product_id:
#             product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
#             uom = self.pool['product.uom'].browse(cr, uid, uom_id, context=context)
#             if product.uom_id.category_id.id != uom.category_id.id:
#                 res['value']['product_uom_id'] = product.uom_id.id
#                 res['domain'] = {'product_uom_id': [('category_id','=',product.uom_id.category_id.id)]}
#                 uom_id = product.uom_id.id
#         # Calculate theoretical quantity by searching the quants as in quants_get
#         if product_id and location_id:
#             product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
#             if not company_id:
#                 company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
#             dom = [('company_id', '=', company_id), ('location_id', '=', location_id), ('lot_id', '=', prod_lot_id),
#                         ('product_id','=', product_id), ('owner_id', '=', partner_id), ('package_id', '=', package_id)]
#             quants = quant_obj.search(cr, uid, dom, context=context)
#             th_qty = sum([x.qty for x in quant_obj.browse(cr, uid, quants, context=context)])
#             if product_id and uom_id and product.uom_id.id != uom_id:
#                 th_qty = uom_obj._compute_qty(cr, uid, product.uom_id.id, th_qty, uom_id)
#             res['value']['theoretical_qty'] = th_qty
#             res['value']['product_qty'] = th_qty
#         return res

#     # Do not forward port in 10.0 and beyond
#     def _get_move_values(self, cr, uid, inventory_line, qty, location_id, location_dest_id):
#         return {
#             'name': _('INV:') + (inventory_line.inventory_id.name or ''),
#             'product_id': inventory_line.product_id.id,
#             'product_uom': inventory_line.product_uom_id.id,
#             'product_uom_qty': qty,
#             'date': inventory_line.inventory_id.date,
#             'company_id': inventory_line.inventory_id.company_id.id,
#             'inventory_id': inventory_line.inventory_id.id,
#             'state': 'confirmed',
#             'restrict_lot_id': inventory_line.prod_lot_id.id,
#             'restrict_partner_id': inventory_line.partner_id.id,
#             'location_id': location_id,
#             'location_dest_id': location_dest_id,
#         }

#     def _fixup_negative_quants(self, cr, uid, inventory_line):
#         """ This will handle the irreconciable quants created by a force availability followed by a
#         return. When generating the moves of an inventory line, we look for quants of this line's
#         product created to compensate a force availability. If there are some and if the quant
#         which it is propagated from is still in the same location, we move it to the inventory
#         adjustment location before getting it back. Getting the quantity from the inventory
#         location will allow the negative quant to be compensated.
#         """
#         quant_obj = self.pool.get('stock.quant')
#         stock_move_obj = self.pool.get('stock.move')
#         quant_ids = self._get_quants(cr, uid, inventory_line)
#         for quant in quant_obj.browse(cr, uid, quant_ids).filtered(lambda q: q.propagated_from_id.location_id.id == inventory_line.location_id.id):
#             # send the quantity to the inventory adjustment location
#             move_out_vals = self._get_move_values(cr, uid, inventory_line, quant.qty, inventory_line.location_id.id, inventory_line.product_id.property_stock_inventory.id)
#             move_out = stock_move_obj.create(cr, uid, move_out_vals)
#             move_out = stock_move_obj.browse(cr, uid, [move_out])
#             quant_obj.quants_reserve(cr, uid, [(quant, quant.qty)], move_out)
#             move_out.action_done()

#             # get back the quantity from the inventory adjustment location
#             move_in_vals = self._get_move_values(cr, uid, inventory_line, quant.qty, inventory_line.product_id.property_stock_inventory.id, inventory_line.location_id.id)
#             move_in = stock_move_obj.create(cr, uid, move_in_vals)
#             move_in = stock_move_obj.browse(cr, uid, [move_in])
#             move_in.action_done()

#     def _resolve_inventory_line(self, cr, uid, inventory_line, context=None):
#         stock_move_obj = self.pool.get('stock.move')
#         quant_obj = self.pool.get('stock.quant')
#         self._fixup_negative_quants(cr, uid, inventory_line)

#         if float_compare(inventory_line.theoretical_qty, inventory_line.product_qty, precision_rounding=inventory_line.product_id.uom_id.rounding) == 0:
#             return False
#         diff = inventory_line.theoretical_qty - inventory_line.product_qty

#         #each theorical_lines where difference between theoretical and checked quantities is not 0 is a line for which we need to create a stock move
#         inventory_location_id = inventory_line.product_id.property_stock_inventory.id
#         if diff < 0:  # found more than expected
#             vals = self._get_move_values(cr, uid, inventory_line, abs(diff), inventory_location_id, inventory_line.location_id.id)
#         else:
#             vals = self._get_move_values(cr, uid, inventory_line, abs(diff), inventory_line.location_id.id, inventory_location_id)

#         move_id = stock_move_obj.create(cr, uid, vals, context=context)
#         move = stock_move_obj.browse(cr, uid, move_id, context=context)
#         if diff > 0:
#             domain = [('qty', '>', 0.0), ('package_id', '=', inventory_line.package_id.id), ('lot_id', '=', inventory_line.prod_lot_id.id), ('location_id', '=', inventory_line.location_id.id)]
#             preferred_domain_list = [[('reservation_id', '=', False)], [('reservation_id.inventory_id', '!=', inventory_line.inventory_id.id)]]
#             quants = quant_obj.quants_get_prefered_domain(cr, uid, move.location_id, move.product_id, move.product_qty, domain=domain, prefered_domain_list=preferred_domain_list, restrict_partner_id=move.restrict_partner_id.id, context=context)
#             quant_obj.quants_reserve(cr, uid, quants, move, context=context)
#         elif inventory_line.package_id:
#             stock_move_obj.action_done(cr, uid, move_id, context=context)
#             quants = [x.id for x in move.quant_ids]
#             quant_obj.write(cr, SUPERUSER_ID, quants, {'package_id': inventory_line.package_id.id}, context=context)
#             res = quant_obj.search(cr, uid, [('qty', '<', 0.0), ('product_id', '=', move.product_id.id),
#                                     ('location_id', '=', move.location_dest_id.id), ('package_id', '!=', False)], limit=1, context=context)
#             if res:
#                 for quant in move.quant_ids:
#                     if quant.location_id.id == move.location_dest_id.id: #To avoid we take a quant that was reconcile already
#                         quant_obj._quant_reconcile_negative(cr, uid, quant, move, context=context)
#         return move_id

#     # Should be left out in next version
#     def restrict_change(self, cr, uid, ids, theoretical_qty, context=None):
#         return {}

#     # Should be left out in next version
#     def on_change_product_id(self, cr, uid, ids, product, uom, theoretical_qty, context=None):
#         """ Changes UoM
#         @param location_id: Location id
#         @param product: Changed product_id
#         @param uom: UoM product
#         @return:  Dictionary of changed values
#         """
#         if not product:
#             return {'value': {'product_uom_id': False}}
#         obj_product = self.pool.get('product.product').browse(cr, uid, product, context=context)
#         return {'value': {'product_uom_id': uom or obj_product.uom_id.id}}
