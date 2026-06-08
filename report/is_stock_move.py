# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools
import datetime
import pytz
import time
import logging
_logger = logging.getLogger(__name__)







class pg_stock_move(models.Model):
    _name='pg.stock.move'
    _description="Mouvemments de stocks PG"
    _order='date desc'
    _rec_name = 'id'

    move_id            = fields.Many2one('stock.move', 'Mouvement'   , index=True)
    date               = fields.Datetime('Date'                      , index=True)
    product_id         = fields.Many2one('product.product', 'Article', index=True)
    category           = fields.Char('Cat'                           , index=True)
    mold               = fields.Char('Moule', help='Moule / DossierF', index=True)
    name               = fields.Char('Description')
    origin             = fields.Char('Origine'                       , index=True)
    picking_id         = fields.Many2one('stock.picking', 'Rcp/Liv'  , index=True)
    picking_type_id    = fields.Many2one('stock.picking.type', 'Type', index=True)
    lot_id             = fields.Many2one('stock.lot', 'Lot'          , index=True)
    lot_fournisseur    = fields.Char('Lot fournisseur'               , index=True)
    qty                = fields.Float('Quantité')
    product_uom        = fields.Many2one('uom.uom', 'Unité')
    location_dest_id   = fields.Many2one('stock.location', "Lieu"     , index=True)
    login              = fields.Char('Utilisateur')
    is_employee_theia_id       = fields.Many2one('hr.employee', 'Employé Theia')
    purchase_line_id           = fields.Many2one('purchase.order.line', 'Ligne commande achat')
    raw_material_production_id = fields.Many2one('mrp.production'     , 'Composant ordre de fabrication')
    production_id              = fields.Many2one('mrp.production'     , 'Ordre de fabrication')
    sale_line_id               = fields.Many2one('sale.order.line'    , 'Ligne commande vente', index=True)




    
#Suppression le 08/06/2026 car n'est plus utilisé depuis longtempt (normalement)

# _SELECT_STOCK_MOVE="""
#     select 
#             row_number() over(order by sm.id )  as id,
#             sm.id                               as move_id,
#             sm2.date                            as date,
#             sm2.product_id                      as product_id, 
#             ic.name                             as category,
#             COALESCE(im.name,id.name)           as mold,
#             -- COALESCE(spt.name,sm.src)           as type_mv,
#             -- COALESCE(spt.name,sp.name,sm2.name) as name,
#             sm2.picking_id                      as picking_id,
#             sm2.purchase_line_id,
#             sm2.raw_material_production_id,
#             sm2.production_id,
#             sm2.sale_line_id,
#             sm.lot_id                          as lot_id,
#             spl.is_lot_fournisseur             as lot_fournisseur,
#             sm.qty                             as qty,
#             sm.product_uom_id                  as product_uom,
#             sm.dest                            as location_dest,
#             sm2.is_employee_theia_id	       as is_employee_theia_id,
#             rp.name                            as login,
#             sm2.picking_type_id                as picking_type_id
#     from (

#         select 
#             sm.id,
#             sml.lot_id          as lot_id,
#             sum(sml.qty_done)         as qty,
#             sml.product_uom_id,
#             sl1.name            as src,
#             sl2.name            as dest
#         from stock_move sm join stock_location        sl1 on sm.location_id=sl1.id
#                         join stock_location        sl2 on sm.location_dest_id=sl2.id
#                         join stock_move_line       sml on sm.id=sml.move_id
#         where sm.state='done' and sl2.usage='internal' 
#         group by 
#             sm.id,
#             sml.lot_id,
#             sml.product_uom_id,
#             sl1.name,
#             sl2.name

#         union

        
#         select 
#             sm.id,
#             sml.lot_id          as lot_id,
#             -sum(sml.qty_done)         as qty,
#             sml.product_uom_id,

#             sl1.name            as src,
#             sl2.name            as dest
#         from stock_move sm join stock_location        sl1 on sm.location_dest_id=sl1.id
#                         join stock_location        sl2 on sm.location_id=sl2.id
#                         join stock_move_line       sml on sm.id=sml.move_id
#         where sm.state='done' and sl2.usage='internal' 
#         group by 
#             sm.id,
#             sml.lot_id,
#             sml.product_uom_id,
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
#             left outer join stock_lot spl on sm.lot_id=spl.id
# """


# class is_stock_move(models.Model):
#     _name='is.stock.move'
#     _description="Vue Mouvemments de stocks"
#     _order='date desc'
#     _auto = False

#     move_id            = fields.Many2one('stock.move', 'Mouvement')
#     date               = fields.Datetime('Date')
#     product_id         = fields.Many2one('product.product', 'Article')
#     category           = fields.Char('Cat')
#     mold               = fields.Char('Moule / DossierF')
#     #type_mv            = fields.Char('Type')
#     #name               = fields.Char('Description')
#     picking_id         = fields.Many2one('stock.picking', 'Rcp/Liv')
#     picking_type_id    = fields.Many2one('stock.picking.type', 'Type')
#     lot_id             = fields.Many2one('stock.lot', 'Lot')
#     lot_fournisseur    = fields.Char('Lot fournisseur')
#     qty                = fields.Float('Quantité')
#     product_uom        = fields.Many2one('uom.uom', 'Unité')
#     location_dest      = fields.Char("Lieu")
#     login              = fields.Char('Utilisateur')
#     is_employee_theia_id  = fields.Many2one('hr.employee', 'Employé Theia')

#     purchase_line_id           = fields.Many2one('purchase.order.line', 'Ligne commande achat')
#     raw_material_production_id = fields.Many2one('mrp.production'     , 'Composant ordre de fabrication')
#     production_id              = fields.Many2one('mrp.production'     , 'Ordre de fabrication')
#     sale_line_id               = fields.Many2one('sale.order.line'    , 'Ligne commande vente')


#     def refresh_stock_move_action(self):
#         start = time.time()
#         cr = self._cr
#         cr.execute("REFRESH MATERIALIZED VIEW is_stock_move;")
#         _logger.info('## refresh_stock_move_action en %.2fs'%(time.time()-start))
#         now = datetime.datetime.now(pytz.timezone('Europe/Paris')).strftime('%H:%M:%S')
#         return {
#             'name': 'Mouvements de stocks actualisés à '+str(now),
#             'view_mode': 'tree,form',
#             'res_model': 'is.stock.move',
#             'type': 'ir.actions.act_window',
#         }


#     def init(self):
#         if self.env.company.is_activer_init:
#             start = time.time()
#             cr = self._cr
#             cr.execute("""
#                 DROP MATERIALIZED VIEW IF EXISTS is_stock_move;
#                 CREATE MATERIALIZED view is_stock_move AS ("""+_SELECT_STOCK_MOVE+"""
#                 );
#             """)
#             _logger.info('## init is_stock_move en %.2fs'%(time.time()-start))



# Requete optimisée le 08/06/2026, mais qui n'a pas été mise en place car is_stock_move n'est plus utilisés depuis longtemps

# -- Début de la transaction et configuration de la mémoire
# BEGIN;
# SET LOCAL work_mem = '256MB';

# SELECT 
#     row_number() OVER(ORDER BY sm.move_id) AS id,
#     sm.move_id                             AS move_id,
#     sm2.date                               AS date,
#     sm2.product_id                         AS product_id, 
#     ic.name                                AS category,
#     COALESCE(im.name, id.name)             AS mold,
#     sm2.picking_id                         AS picking_id,
#     sm2.purchase_line_id                   AS purchase_line_id,
#     sm2.raw_material_production_id         AS raw_material_production_id,
#     sm2.production_id                      AS production_id,
#     sm2.sale_line_id                       AS sale_line_id,
#     sm.lot_id                              AS lot_id,
#     spl.is_lot_fournisseur                 AS lot_fournisseur,
#     sm.qty                                 AS qty,
#     sm.product_uom_id                      AS product_uom,
#     sl_dest.name                           AS location_dest,
#     sm2.is_employee_theia_id               AS is_employee_theia_id,
#     rp.name                                AS login,
#     sm2.picking_type_id                    AS picking_type_id
# FROM (
#     -- Des parenthèses ont été ajoutées autour des sous-requêtes pour autoriser le LIMIT
#     (
#         SELECT 
#             sm.id AS move_id,
#             sml.lot_id,
#             sum(sml.qty_done) AS qty,
#             sml.product_uom_id,
#             sm.location_dest_id AS dest_location_id
#         FROM stock_move sm 
#         INNER JOIN stock_move_line sml ON sm.id = sml.move_id
#         INNER JOIN stock_location sl2 ON sm.location_dest_id = sl2.id
#         WHERE sm.state = 'done' AND sl2.usage = 'internal' 
#         GROUP BY sm.id, sml.lot_id, sml.product_uom_id, sm.location_dest_id
#         LIMIT 5
#     )

#     UNION ALL

#     (
#         SELECT 
#             sm.id AS move_id,
#             sml.lot_id,
#             -sum(sml.qty_done) AS qty,
#             sml.product_uom_id,
#             sm.location_id AS dest_location_id
#         FROM stock_move sm 
#         INNER JOIN stock_move_line sml ON sm.id = sml.move_id
#         INNER JOIN stock_location sl2 ON sm.location_id = sl2.id
#         WHERE sm.state = 'done' AND sl2.usage = 'internal' 
#         GROUP BY sm.id, sml.lot_id, sml.product_uom_id, sm.location_id
#         LIMIT 5
#     )
# ) sm  
# INNER JOIN stock_move sm2          ON sm.move_id = sm2.id           
# INNER JOIN product_product pp      ON sm2.product_id = pp.id
# INNER JOIN product_template pt     ON pp.product_tmpl_id = pt.id
# INNER JOIN res_users ru            ON sm2.write_uid = ru.id
# INNER JOIN res_partner rp          ON ru.partner_id = rp.id
# INNER JOIN stock_location sl_dest  ON sm.dest_location_id = sl_dest.id
# LEFT OUTER JOIN stock_picking_type spt ON sm2.picking_type_id = spt.id
# LEFT OUTER JOIN stock_picking sp       ON sm2.picking_id = sp.id
# LEFT OUTER JOIN is_category ic         ON pt.is_category_id = ic.id
# LEFT OUTER JOIN is_mold im             ON pt.is_mold_id = im.id
# LEFT OUTER JOIN is_dossierf id         ON pt.is_dossierf_id = id.id
# LEFT OUTER JOIN stock_lot spl          ON sm.lot_id = spl.id;

# COMMIT;
