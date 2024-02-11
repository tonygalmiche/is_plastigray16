# -*- coding: utf-8 -*-
from odoo import models,fields,tools,api
from odoo.exceptions import ValidationError
import time
import logging
_logger = logging.getLogger(__name__)


class is_gestion_lot(models.Model):
    _name = 'is.gestion.lot'
    _description = "gestion contrôle qualité"
    
    product_id              = fields.Many2one('product.product', 'Article', readonly=True)
    is_uc_qt                = fields.Integer('Qt/UC', related='product_id.is_uc_qt', readonly=True)
    prod_lot_id             = fields.Many2one('stock.lot', 'Lot', readonly=True)
    planned_date            = fields.Datetime('Date prévue')
    location_src_id         = fields.Many2one('stock.location', 'Emplacement source',readonly=True)
    location_dest_bloq_id   = fields.Many2one('stock.location', 'Emplacement de destination bloqué')
    location_dest_debloq_id = fields.Many2one('stock.location', 'Emplacement de destination débloqué')
    location_dest_change_id = fields.Many2one('stock.location', 'Emplacement de destination')
    location_dest_rebut_id  = fields.Many2one('stock.location', 'Emplacement de destination rebut')
    product_qty             = fields.Float(u'Quantité', required=True)
    description             = fields.Many2one('is.commentaire.mouvement.stock', 'Description')
    operation               = fields.Selection([
        ('bloque'         , 'Bloquer un lot'),
        ('debloque'       , 'Débloqué'),
        ('change_location', 'Changement emplacement'),
        ('change_location_multiple', 'Changement emplacement multiple'),
        ('rebut'          , 'Mise au rebut'),
        ('remettre'       , 'Remettre en stock'),
    ], 'Operation', readonly=True)   
    
    
    # Retourne la quantité en stock d'un lot de produit dans un emplacement donnée
    # def get_product_qty_lot_location(self, cr, uid, product_id, lot_id, location_src_id, context=None):
    #     quant_obj = self.env.get('stock.quant')
    #     qty = 0
    #     if product_id and lot_id and location_src_id:
    #         quant_ids = quant_obj.search(cr, uid, [('product_id','=',product_id), ('lot_id','=',lot_id), ('location_id','=',location_src_id)], context=context)
    #         if quant_ids:
    #             for quant in quant_obj.read(cr, uid, quant_ids, ['qty'], context=context):
    #                 qty += quant['qty']
    #     return qty
    
    # def _check_product_qty(self, cr, uid, ids, context=None):
    #     obj = self.browse(cr, uid, ids[0], context=context)
    #     if obj.product_id and obj.prod_lot_id and obj.location_src_id:
    #         qty = self.get_product_qty_lot_location(cr, uid, obj.product_id.id, obj.prod_lot_id.id, obj.location_src_id.id, context)
    #         if obj.product_qty > qty:
    #             return False
    #     return True

    # '_constraints' is no longer supported, please use @api.constrains on methods instead.
    # _constraints = [
    #     (_check_product_qty, u'La quantité que vous avez entrée est supérieure à celle existante en stock', ['product_qty']),
    # ]
    

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        context      = self._context
        active_model = context.get('active_model')
        active_id    = context.get('active_id')
        operation    = context.get('operation')
        line = self.env[active_model].browse(active_id)
        res.update(operation=operation)
        if 'product_id' in fields:
            res.update(product_id=line.product_id.id)
        if 'prod_lot_id' in fields:
            res.update(prod_lot_id=line.lot_id.id)
        if 'product_qty' in fields:
            res.update(product_qty=line.qty)
        if 'location_src_id' in fields:
            res.update(location_src_id=line.location_id.id)
        return res

    
    def create_stock_move(self):
        context = self._context
        for data in self:
            if 'active_ids' in context:
                filtre=[('id', 'in', context["active_ids"])]
                lines = self.env['is.gestion.lot.report'].search(filtre)
                for line in lines:





                    move_obj = self.env["stock.move"]
                    location_dest_id = False
                    if data.operation == 'bloque':
                        location_dest_id = data.location_dest_bloq_id.id
                    if data.operation == 'debloque':
                        location_dest_id = data.location_dest_debloq_id.id
                    if data.operation in ['change_location', 'remettre', 'change_location_multiple']:
                        location_dest_id = data.location_dest_change_id.id
                    if data.operation == 'rebut':
                        location_dest_id = data.location_dest_rebut_id.id
                    if data.operation in ['change_location_multiple']:
                        qty_done = round(line.qty,8)
                    else:
                        qty_done = round(data.product_qty,8)
                    if qty_done>round(line.qty,8):
                        raise ValidationError("Il n'est pas autorisé de déplacer plus que la quantité d'origine")
                    line_vals={
                        "location_id"     : line.location_id.id,
                        "location_dest_id": location_dest_id,
                        "lot_id"          : line.lot_id.id,
                        "qty_done"        : qty_done,
                        "product_id"      : line.product_id.id,
                    }
                    move_vals={
                        "location_id"     : line.location_id.id,
                        "location_dest_id": location_dest_id,
                        "product_uom_qty" : qty_done,
                        "product_id"      : line.product_id.id,
                        "name"            : data.description and data.description.name or line.product_id.name,
                    }
                    #TODO : La création du picking est facultative, mais je la garde pour avoir un exemple complet
                    filtre=[('code', '=', 'internal')]
                    picking_type_id = self.env['stock.picking.type'].search(filtre)[0]
                    picking_vals={
                        "picking_type_id" : picking_type_id.id,
                        "location_id"     : line.location_id.id,
                        "location_dest_id": location_dest_id,
                        'move_line_ids'   : [[0,False,line_vals]],
                        'move_ids'        : [[0,False,move_vals]],
                    }
                    picking=self.env['stock.picking'].create(picking_vals)
                    picking.action_confirm()
                    picking._action_done()

                    # line_vals={
                    #     "location_id"     : data.location_src_id.id,
                    #     "location_dest_id": location_dest_id,
                    #     "lot_id"          : data.prod_lot_id.id,
                    #     "qty_done"        : data.product_qty,
                    #     "product_id"      : data.product_id.id,
                    # }
                    # move_vals={
                    #     "location_id"     : data.location_src_id.id,
                    #     "location_dest_id": location_dest_id,
                    #     "product_uom_qty" : data.product_qty,
                    #     "product_id"      : data.product_id.id,
                    #     "name"            : data.description and data.description.name or data.product_id.name,
                    # }
                    # #TODO : La création du picking est facultative, mais je la garde pour avoir un exemple complet
                    # filtre=[('code', '=', 'internal')]
                    # picking_type_id = self.env['stock.picking.type'].search(filtre)[0]
                    # picking_vals={
                    #     "picking_type_id" : picking_type_id.id,
                    #     "location_id"     : data.location_src_id.id,
                    #     "location_dest_id": location_dest_id,
                    #     'move_line_ids'   : [[0,False,line_vals]],
                    #     'move_ids'        : [[0,False,move_vals]],
                    # }
                    # picking=self.env['stock.picking'].create(picking_vals)
                    # picking.action_confirm()
                    # picking._action_done()
        return True
                
    
    def validate_lot(self):
        for obj in self:
            move = self.create_stock_move()


class is_gestion_lot_report(models.Model):
    _name = "is.gestion.lot.report"
    _description = "stock des produits par lot"
    _order = "product_id,location_id,lot_id"
    _auto = False

    product_id      = fields.Many2one('product.product', 'Article'    , readonly=True)
    mold            = fields.Char('Moule'                             , readonly=True)
    location_id     = fields.Many2one('stock.location', 'Emplacement' , readonly=True)
    control_quality = fields.Boolean('Contrôle qualité'               , readonly=True)
    scrap_location  = fields.Boolean('Emplacement de rebut'           , readonly=True)
    usage           = fields.Char("Type d'emplacement"                , readonly=True)
    qty         = fields.Float('Quantité'                             , readonly=True)
    qty_par_uc  = fields.Integer('UC'                                 , readonly=True)
    qty_uc      = fields.Float('Nb UC'                                , readonly=True)
    lot_id      = fields.Many2one('stock.lot', 'Lot'                  , readonly=True)
    in_date     = fields.Datetime("Date d'entrée"                     , readonly=True)
    

    def init(self):
        start = time.time()
        cr = self._cr
        tools.drop_view_if_exists(cr, 'is_gestion_lot_report')
        cr.execute("""
                CREATE OR REPLACE FUNCTION is_qt_par_uc2(productid integer, OUT uc int) RETURNS int AS $$
                BEGIN
                    uc:=cast((select qty from product_packaging where product_id=productid order by id limit 1) as int);
                    IF uc=0 THEN
                        uc:=1;
                    END IF;
                    IF   uc IS NULL THEN
                        uc:=1;
                    END IF;
                END;
                $$ LANGUAGE plpgsql;

                CREATE OR REPLACE view is_gestion_lot_report AS (
                SELECT
                        min(quant.id)      as id,
                        sum(quant.quantity)     as qty,
                        is_qt_par_uc2(pp.id) as qty_par_uc,
                        (sum(quant.quantity) / is_qt_par_uc2(pp.id))  as qty_uc,
                        quant.lot_id       as lot_id,
                        quant.product_id   as product_id,
                        im.name            as mold,
                        quant.location_id  as location_id,
                        location.usage            as usage,
                        location.control_quality  as control_quality,
                        location.scrap_location   as scrap_location,
                        -- 'bloque'           as operation,
                        max(quant.in_date) as in_date

                FROM    stock_quant quant INNER JOIN stock_location location ON quant.location_id = location.id
                                          INNER JOIN product_product pp      ON quant.product_id  = pp.id
                                          INNER JOIN product_template pt     ON pp.product_tmpl_id = pt.id
                                          LEFT OUTER JOIN is_mold im         ON pt.is_mold_id=im.id 
                WHERE   quant.lot_id is not Null
                GROUP BY quant.lot_id, quant.product_id, pp.id, quant.location_id, im.name, location.usage, location.control_quality , location.scrap_location 
                HAVING     sum(quant.quantity) > 0
                ORDER BY quant.product_id
               )
        """)
        _logger.info('## init is_gestion_lot_report en %.2fs'%(time.time()-start))


    def bloquer_lot_action(self):
        for obj in self:
            new_context = dict(self.env.context).copy()
            new_context["operation"] = 'bloque'
            return {
                'name': "Bloquer un lot",
                'view_mode': 'form',
                'res_model': 'is.gestion.lot',
                'type': 'ir.actions.act_window',
                "context": new_context,
                'domain': '[]',
                'target': 'new',
            }


    def debloquer_lot_action(self):
        for obj in self:
            new_context = dict(self.env.context).copy()
            new_context["operation"] = 'debloque'
            return {
                'name': "Débloquer un lot",
                'view_mode': 'form',
                'res_model': 'is.gestion.lot',
                'type': 'ir.actions.act_window',
                "context": new_context,
                'domain': '[]',
                'target': 'new',
            }


    def mise_au_rebut_action(self):
        for obj in self:
            new_context = dict(self.env.context).copy()
            new_context["operation"] = 'rebut'
            return {
                'name': "Mise au rebut",
                'view_mode': 'form',
                'res_model': 'is.gestion.lot',
                'type': 'ir.actions.act_window',
                "context": new_context,
                'domain': '[]',
                'target': 'new',
            }


    def change_emplacement_action(self):
        for obj in self:
            new_context = dict(self.env.context).copy()
            new_context["operation"] = 'change_location'
            return {
                'name': "Changement d'emplacement",
                'view_mode': 'form',
                'res_model': 'is.gestion.lot',
                'type': 'ir.actions.act_window',
                "context": new_context,
                'domain': '[]',
                'target': 'new',
            }


    def change_emplacement_multiple_action(self):
        for obj in self:
            new_context = dict(self.env.context).copy()
            new_context["operation"] = 'change_location_multiple'
            return {
                'name': "Changement d'emplacement multiple",
                'view_mode': 'form',
                'res_model': 'is.gestion.lot',
                'type': 'ir.actions.act_window',
                "context": new_context,
                'domain': '[]',
                'target': 'new',
            }


    def remettre_stock_action(self):
        for obj in self:
            new_context = dict(self.env.context).copy()
            new_context["operation"] = 'remettre'
            return {
                'name': "Remettre en stock",
                'view_mode': 'form',
                'res_model': 'is.gestion.lot',
                'type': 'ir.actions.act_window',
                "context": new_context,
                'domain': '[]',
                'target': 'new',
            }



    
    