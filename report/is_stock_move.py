# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools
import datetime
import pytz
import time
import logging
_logger = logging.getLogger(__name__)


# _SELECT_STOCK_MOVE="""
#     select 
#             row_number() over(order by sm.id )  as id,
#             sm.id                               as move_id,
#             sm2.date                            as date,
#             sm2.product_id                      as product_id, 
#             ic.name                             as category,
#             COALESCE(im.name,id.name)           as mold,
#             COALESCE(spt.name,sm.src)           as type_mv,
#             COALESCE(spt.name,sp.name,sm2.name) as name,
#             sm2.picking_id                      as picking_id,
#             sm2.purchase_line_id,
#             sm2.raw_material_production_id,
#             sm2.production_id,
#             sm2.sale_line_id,
#             sm.lot_id                          as lot_id,
#             spl.is_lot_fournisseur             as lot_fournisseur,
#             sm.qty                             as qty,
#             pt.uom_id                          as product_uom,
#             sm.dest                            as location_dest,
#             sm2.is_employee_theia_id	   as is_employee_theia_id,
#             rp.name                            as login
#     from (

#         select 
#             sm.id,
#             sq.lot_id           as lot_id,
#             sum(sq.qty)         as qty,
#             sl1.name            as src,
#             sl2.name            as dest
#         from stock_move sm inner join stock_location        sl1 on sm.location_id=sl1.id
#                             inner join stock_location        sl2 on sm.location_dest_id=sl2.id
#                             left outer join stock_quant_move_rel sqmr on sm.id=sqmr.move_id
#                             left outer join stock_quant            sq on sqmr.quant_id=sq.id
#         where sm.state='done' and sl2.usage='internal' 
#         group by 
#             sm.id,
#             sq.lot_id,
#             sl1.name,
#             sl2.name

#         union

#         select 
#             sm.id,
#             sq.lot_id           as lot_id,
#             -sum(sq.qty)        as qty,
#             sl1.name            as dest,
#             sl2.name            as src
#         from stock_move sm inner join stock_location        sl1 on sm.location_dest_id=sl1.id
#                             inner join stock_location        sl2 on sm.location_id=sl2.id
#                             left outer join stock_quant_move_rel sqmr on sm.id=sqmr.move_id
#                             left outer join stock_quant            sq on sqmr.quant_id=sq.id
#         where sm.state='done' and sl2.usage='internal' 
#         group by 
#             sm.id,
#             sq.lot_id,
#             sl1.name,
#             sl2.name

#     ) sm    inner join stock_move                sm2 on sm.id=sm2.id           
#             inner join product_product            pp on sm2.product_id=pp.id
#             inner join product_template           pt on pp.product_tmpl_id=pt.id
#             inner join res_users                  ru on sm2.write_uid=ru.id
#             inner join res_partner                rp on ru.partner_id=rp.id
#             left outer join stock_picking_type   spt on sm2.picking_type_id=spt.id
#             left outer join stock_picking         sp on sm2.picking_id=sp.id
#             left outer join is_category           ic on pt.is_category_id=ic.id
#             left outer join is_mold               im on pt.is_mold_id=im.id
#             left outer join is_dossierf           id on pt.is_dossierf_id=id.id
#             left outer join stock_production_lot spl on sm.lot_id=spl.id
# """



_SELECT_STOCK_MOVE="""
    select 
            row_number() over(order by sm.id )  as id,
            sm.id                               as move_id,
            sm2.date                            as date,
            sm2.product_id                      as product_id, 
            ic.name                             as category,
            COALESCE(im.name,id.name)           as mold,
            -- COALESCE(spt.name,sm.src)           as type_mv,
            -- COALESCE(spt.name,sp.name,sm2.name) as name,
            sm2.picking_id                      as picking_id,
            sm2.purchase_line_id,
            sm2.raw_material_production_id,
            sm2.production_id,
            sm2.sale_line_id,
            sm.lot_id                          as lot_id,
            spl.is_lot_fournisseur             as lot_fournisseur,
            sm.qty                             as qty,
            pt.uom_id                          as product_uom,
            sm.dest                            as location_dest,
            sm2.is_employee_theia_id	       as is_employee_theia_id,
            rp.name                            as login,
            sm2.picking_type_id                as picking_type_id
    from (

        select 
            sm.id,
            sml.lot_id          as lot_id,
            sum(sml.qty_done)         as qty,
            sl1.name            as src,
            sl2.name            as dest
        from stock_move sm join stock_location        sl1 on sm.location_id=sl1.id
                        join stock_location        sl2 on sm.location_dest_id=sl2.id
                        join stock_move_line       sml on sm.id=sml.move_id
        where sm.state='done' and sl2.usage='internal' 
        group by 
            sm.id,
            sml.lot_id,
            sl1.name,
            sl2.name

        union

        
        select 
            sm.id,
            sml.lot_id          as lot_id,
            -sum(sml.qty_done)         as qty,
            sl1.name            as src,
            sl2.name            as dest
        from stock_move sm join stock_location        sl1 on sm.location_dest_id=sl1.id
                        join stock_location        sl2 on sm.location_id=sl2.id
                        join stock_move_line       sml on sm.id=sml.move_id
        where sm.state='done' and sl2.usage='internal' 
        group by 
            sm.id,
            sml.lot_id,
            sl1.name,
            sl2.name



    ) sm    inner join stock_move                sm2 on sm.id=sm2.id           
            inner join product_product            pp on sm2.product_id=pp.id
            inner join product_template           pt on pp.product_tmpl_id=pt.id
            inner join res_users                  ru on sm2.write_uid=ru.id
            inner join res_partner                rp on ru.partner_id=rp.id
            left outer join stock_picking_type   spt on sm2.picking_type_id=spt.id
            left outer join stock_picking         sp on sm2.picking_id=sp.id
            left outer join is_category           ic on pt.is_category_id=ic.id
            left outer join is_mold               im on pt.is_mold_id=im.id
            left outer join is_dossierf           id on pt.is_dossierf_id=id.id
            left outer join stock_lot spl on sm.lot_id=spl.id

"""







class pg_stock_move(models.Model):
    _name='pg.stock.move'
    _description="Mouvemments de stocks PG"
    _order='date desc'

    move_id            = fields.Many2one('stock.move', 'Mouvement'   , index=True)
    date               = fields.Datetime('Date'                      , index=True)
    product_id         = fields.Many2one('product.product', 'Article', index=True)
    category           = fields.Char('Cat'                           , index=True)
    mold               = fields.Char('Moule / DossierF'              , index=True)
    #type_mv            = fields.Char('Type'                          , index=True)
    #name               = fields.Char('Description')
    picking_id         = fields.Many2one('stock.picking', 'Rcp/Liv')
    lot_id             = fields.Many2one('stock.lot', 'Lot')
    lot_fournisseur    = fields.Char('Lot fournisseur')
    qty                = fields.Float('Quantité')
    product_uom        = fields.Many2one('uom.uom', 'Unité')
    location_dest      = fields.Char("Lieu"                          , index=True)
    login              = fields.Char('Utilisateur')
    is_employee_theia_id       = fields.Many2one('hr.employee', 'Employé Theia')
    purchase_line_id           = fields.Many2one('purchase.order.line', 'Ligne commande achat')
    raw_material_production_id = fields.Many2one('mrp.production'     , 'Composant ordre de fabrication')
    production_id              = fields.Many2one('mrp.production'     , 'Ordre de fabrication')
    sale_line_id               = fields.Many2one('sale.order.line'    , 'Ligne commande vente')


class is_stock_move(models.Model):
    _name='is.stock.move'
    _description="Vue Mouvemments de stocks"
    _order='date desc'
    _auto = False

    move_id            = fields.Many2one('stock.move', 'Mouvement')
    date               = fields.Datetime('Date')
    product_id         = fields.Many2one('product.product', 'Article')
    category           = fields.Char('Cat')
    mold               = fields.Char('Moule / DossierF')
    #type_mv            = fields.Char('Type')
    #name               = fields.Char('Description')
    picking_id         = fields.Many2one('stock.picking', 'Rcp/Liv')
    picking_type_id    = fields.Many2one('stock.picking.type', 'Type')
    lot_id             = fields.Many2one('stock.lot', 'Lot')
    lot_fournisseur    = fields.Char('Lot fournisseur')
    qty                = fields.Float('Quantité')
    product_uom        = fields.Many2one('uom.uom', 'Unité')
    location_dest      = fields.Char("Lieu")
    login              = fields.Char('Utilisateur')
    is_employee_theia_id  = fields.Many2one('hr.employee', 'Employé Theia')

    purchase_line_id           = fields.Many2one('purchase.order.line', 'Ligne commande achat')
    raw_material_production_id = fields.Many2one('mrp.production'     , 'Composant ordre de fabrication')
    production_id              = fields.Many2one('mrp.production'     , 'Ordre de fabrication')
    sale_line_id               = fields.Many2one('sale.order.line'    , 'Ligne commande vente')


    def refresh_stock_move_action(self):
        start = time.time()
        cr = self._cr
        cr.execute("REFRESH MATERIALIZED VIEW is_stock_move;")
        _logger.info('## refresh_stock_move_action en %.2fs'%(time.time()-start))
        now = datetime.datetime.now(pytz.timezone('Europe/Paris')).strftime('%H:%M:%S')
        return {
            'name': 'Mouvements de stocks actualisés à '+str(now),
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'is.stock.move',
            'type': 'ir.actions.act_window',
        }


#    
#    print("%s : %06.2fs : %s"%(now.strftime('%H:%M:%S') , (now-debut).total_seconds(), msg))



    def init(self):
        if self.env.company.is_activer_init:
            start = time.time()
            cr = self._cr
            cr.execute("""
                DROP MATERIALIZED VIEW IF EXISTS is_stock_move;
                CREATE MATERIALIZED view is_stock_move AS ("""+_SELECT_STOCK_MOVE+"""
                );
            """)
            _logger.info('## init is_stock_move en %.2fs'%(time.time()-start))



