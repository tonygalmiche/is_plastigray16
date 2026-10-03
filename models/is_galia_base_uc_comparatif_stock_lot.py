# -*- coding: utf-8 -*-
from odoo import models, fields, tools # type: ignore


class is_galia_base_uc_comparatif_stock_lot(models.Model):
    _name        = 'is.galia.base.uc.comparatif.stock.lot'
    _description = "Comparatif stock lot / UC par emplacement"
    _order       = 'product_id,location_id,lot_id'
    _auto        = False

    product_id         = fields.Many2one('product.product', 'Article', readonly=True)
    location_id        = fields.Many2one('stock.location', 'Emplacement', readonly=True)
    lot_id             = fields.Many2one('stock.lot', 'Lot', readonly=True)
    client_id          = fields.Many2one('res.partner', 'Client', readonly=True)
    is_category_id     = fields.Many2one('is.category', 'Catégorie', readonly=True)
    is_gestionnaire_id = fields.Many2one('is.gestionnaire', 'Gestionnaire', readonly=True)
    segment_id         = fields.Many2one('is.product.segment', 'Segment', readonly=True)
    qty_stock          = fields.Float("Qté en stock", readonly=True)
    nb_um              = fields.Integer("Nb UM", readonly=True)
    nb_uc              = fields.Integer("Nb UC", readonly=True)
    qt_uc              = fields.Float("Qté dans UC", readonly=True)
    diff               = fields.Float("Différence", readonly=True)


    def init(self):
        # Lot des UC : tableau des lots (CI), sinon champ Lot, sinon lot portant le nom de la Fabrication
        cr = self._cr
        tools.drop_view_if_exists(cr, 'is_galia_base_uc_comparatif_stock_lot')
        cr.execute("""CREATE OR REPLACE VIEW is_galia_base_uc_comparatif_stock_lot AS (
            WITH uc_lot AS (
                SELECT uc.id AS uc_id, uc.um_id, uc.product_id, uc.location_id, l.lot_id, l.qt_pieces
                FROM is_galia_base_uc uc
                INNER JOIN is_galia_base_uc_lot l ON l.uc_id = uc.id
                INNER JOIN stock_location sl ON sl.id = uc.location_id
                WHERE uc.active = true AND uc.um_active = true AND sl.usage = 'internal'
                UNION ALL
                SELECT uc.id, uc.um_id, uc.product_id, uc.location_id, COALESCE(uc.lot_id, lot.id), uc.qt_pieces
                FROM is_galia_base_uc uc
                INNER JOIN stock_location sl ON sl.id = uc.location_id
                LEFT JOIN stock_lot lot ON lot.product_id = uc.product_id AND lot.name = uc.production
                LEFT JOIN (SELECT DISTINCT uc_id FROM is_galia_base_uc_lot) l ON l.uc_id = uc.id
                WHERE uc.active = true AND uc.um_active = true AND sl.usage = 'internal'
                AND l.uc_id IS NULL
            ),
            uc AS (
                SELECT product_id, location_id, lot_id,
                    COUNT(DISTINCT uc_id) AS nb_uc, COUNT(DISTINCT um_id) AS nb_um, SUM(qt_pieces) AS qt_uc
                FROM uc_lot
                GROUP BY product_id, location_id, lot_id
            ),
            stock AS (
                SELECT sq.product_id, sq.location_id, sq.lot_id, SUM(sq.quantity) AS qty
                FROM stock_quant sq
                INNER JOIN stock_location sl ON sl.id = sq.location_id
                WHERE sl.usage = 'internal'
                GROUP BY sq.product_id, sq.location_id, sq.lot_id
                HAVING SUM(sq.quantity) <> 0
            ),
            lignes AS (
                SELECT
                    COALESCE(s.product_id, u.product_id)   AS product_id,
                    COALESCE(s.location_id, u.location_id) AS location_id,
                    COALESCE(s.lot_id, u.lot_id)           AS lot_id,
                    COALESCE(s.qty, 0)                     AS qty_stock,
                    COALESCE(u.nb_um, 0)                   AS nb_um,
                    COALESCE(u.nb_uc, 0)                   AS nb_uc,
                    COALESCE(u.qt_uc, 0)                   AS qt_uc
                FROM stock s
                FULL OUTER JOIN uc u
                    ON  u.product_id = s.product_id
                    AND u.location_id = s.location_id
                    AND COALESCE(u.lot_id, 0) = COALESCE(s.lot_id, 0)
            )
            SELECT
                row_number() OVER (ORDER BY l.product_id, l.location_id, l.lot_id) AS id,
                l.product_id,
                l.location_id,
                l.lot_id,
                pt.is_client_id        AS client_id,
                pt.is_category_id      AS is_category_id,
                pt.is_gestionnaire_id  AS is_gestionnaire_id,
                pt.segment_id          AS segment_id,
                l.qty_stock,
                l.nb_um,
                l.nb_uc,
                l.qt_uc,
                l.qty_stock - l.qt_uc  AS diff
            FROM lignes l
            INNER JOIN product_product pp ON pp.id = l.product_id
            INNER JOIN product_template pt ON pt.id = pp.product_tmpl_id
            INNER JOIN is_product_segment ips ON ips.id = pt.segment_id
            WHERE ips.name IN ('NEGOCE', 'NEGOCE INTERSITE', 'PRODUIT FINI SOUS TRAITE', 'PRODUIT FINI')
        )
        """)


    def voir_uc_action(self):
        for obj in self:
            domain = [
                ('product_id' ,'=',obj.product_id.id),
                ('location_id','=',obj.location_id.id),
                ('um_active'  ,'=',True),
            ]
            if obj.lot_id:
                domain += [
                    '|','|',
                    ('lot_id','=',obj.lot_id.id),
                    ('lot_ids.lot_id','=',obj.lot_id.id),
                    '&','&',('lot_id','=',False),('lot_ids','=',False),('production','=',obj.lot_id.name),
                ]
            else:
                domain += [('lot_id','=',False),('lot_ids','=',False)]
            return {
                'name': "UCs %s %s %s"%(obj.product_id.is_code, obj.location_id.name, obj.lot_id.name or ''),
                'view_mode': 'tree,form',
                'res_model': 'is.galia.base.uc',
                'type': 'ir.actions.act_window',
                'domain': domain,
            }


    def voir_quant_action(self):
        for obj in self:
            return {
                'name': "Stock %s %s %s"%(obj.product_id.is_code, obj.location_id.name, obj.lot_id.name or ''),
                'view_mode': 'tree',
                'res_model': 'stock.quant',
                'type': 'ir.actions.act_window',
                'domain': [
                    ('product_id' ,'=',obj.product_id.id),
                    ('location_id','=',obj.location_id.id),
                    ('lot_id'     ,'=',obj.lot_id.id),
                ],
            }
