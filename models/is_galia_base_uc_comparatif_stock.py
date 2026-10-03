# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools # type: ignore


class is_galia_base_uc_comparatif_stock(models.Model):
    _name        = 'is.galia.base.uc.comparatif.stock'
    _description = "Comparatif stock article / UC"
    _order       = 'product_id'
    _auto        = False

    product_id         = fields.Many2one('product.product', 'Article', readonly=True)
    client_id          = fields.Many2one('res.partner', 'Client', readonly=True)
    is_category_id     = fields.Many2one('is.category', 'Catégorie', readonly=True)
    is_gestionnaire_id = fields.Many2one('is.gestionnaire', 'Gestionnaire', readonly=True)
    segment_id         = fields.Many2one('is.product.segment', 'Segment', readonly=True)
    qty_stock          = fields.Float("Qté en stock", readonly=True)
    nb_um              = fields.Integer("Nb UM", readonly=True)
    nb_uc              = fields.Integer("Nb UC", readonly=True)
    qt_uc              = fields.Float("Qté dans UC", readonly=True)
    diff               = fields.Float("Différence", readonly=True)
    qt_par_uc          = fields.Integer("Qt/UC", related='product_id.is_uc_qt', readonly=True)
    nb_uc_par_um       = fields.Integer("Nb UC/UM", related='product_id.is_uc_par_um', readonly=True)
    nb_uc_stock        = fields.Float("Nb UC stock", compute='_compute_nb_stock', readonly=True)
    nb_um_stock        = fields.Float("Nb UM stock", compute='_compute_nb_stock', readonly=True)

    @api.depends('qty_stock', 'product_id.is_uc_qt', 'product_id.is_uc_par_um')
    def _compute_nb_stock(self):
        for obj in self:
            qt_par_uc = obj.product_id.is_uc_qt
            nb_uc_par_um = obj.product_id.is_uc_par_um
            obj.nb_uc_stock = obj.qty_stock / qt_par_uc if qt_par_uc else 0
            obj.nb_um_stock = obj.nb_uc_stock / nb_uc_par_um if nb_uc_par_um else 0


    def init(self):
        cr = self._cr
        tools.drop_view_if_exists(cr, 'is_galia_base_uc_comparatif_stock')
        cr.execute("""CREATE OR REPLACE VIEW is_galia_base_uc_comparatif_stock AS (
            SELECT
                pp.id                        AS id,
                pp.id                        AS product_id,
                pt.is_client_id              AS client_id,
                pt.is_category_id            AS is_category_id,
                pt.is_gestionnaire_id        AS is_gestionnaire_id,
                pt.segment_id                AS segment_id,
                COALESCE(stock.qty, 0)       AS qty_stock,
                COALESCE(um.nb_um, 0)        AS nb_um,
                COALESCE(uc.nb_uc, 0)        AS nb_uc,
                COALESCE(uc.qt_uc, 0)        AS qt_uc,
                COALESCE(stock.qty, 0) - COALESCE(uc.qt_uc, 0) AS diff
            FROM product_product pp
            INNER JOIN product_template pt ON pt.id = pp.product_tmpl_id
            LEFT JOIN (
                SELECT sq.product_id, SUM(sq.quantity) AS qty
                FROM stock_quant sq
                INNER JOIN stock_location sl ON sl.id = sq.location_id
                WHERE sl.usage = 'internal'
                GROUP BY sq.product_id
            ) stock ON stock.product_id = pp.id
            LEFT JOIN (
                SELECT guc.product_id, COUNT(*) AS nb_uc, SUM(guc.qt_pieces) AS qt_uc
                FROM is_galia_base_uc guc
                INNER JOIN stock_location sl2 ON sl2.id = guc.location_id
                WHERE guc.active = true
                AND sl2.usage = 'internal'
                GROUP BY guc.product_id
            ) uc ON uc.product_id = pp.id
            LEFT JOIN (
                SELECT guc.product_id, COUNT(DISTINCT guc.um_id) AS nb_um
                FROM is_galia_base_uc guc
                INNER JOIN stock_location sl2 ON sl2.id = guc.location_id
                INNER JOIN is_galia_base_um gum ON gum.id = guc.um_id
                WHERE guc.active = true
                AND gum.active = true
                AND sl2.usage = 'internal'
                GROUP BY guc.product_id
            ) um ON um.product_id = pp.id
            INNER JOIN is_product_segment ips ON ips.id = pt.segment_id
            WHERE ips.name IN ('NEGOCE', 'NEGOCE INTERSITE', 'PRODUIT FINI SOUS TRAITE', 'PRODUIT FINI')
        )
        """)


    def voir_uc_action(self):
        for obj in self:
            return {
                'name': "UCs %s"%obj.product_id.display_name,
                'view_mode': 'tree,form',
                'res_model': 'is.galia.base.uc',
                'type': 'ir.actions.act_window',
                'domain': [
                    ('product_id','=',obj.product_id.id),
                    ('location_id.usage','=','internal'),
                ],
            }


    def voir_um_action(self):
        for obj in self:
            return {
                'name': "UMs %s"%obj.product_id.display_name,
                'view_mode': 'tree,form',
                'res_model': 'is.galia.base.um',
                'type': 'ir.actions.act_window',
                'domain': [
                    ('uc_ids.product_id','=',obj.product_id.id),
                    ('location_id.usage','=','internal'),
                ],
            }
