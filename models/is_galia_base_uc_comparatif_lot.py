# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools # type: ignore
from odoo.exceptions import ValidationError  # type: ignore
import logging
_logger = logging.getLogger(__name__)


class is_galia_base_uc_comparatif_lot(models.Model):
    _name        = 'is.galia.base.uc.comparatif.lot'
    _description = "Comparatif stock lot / UC par emplacement"
    _order       = 'id desc'

    name           = fields.Char("Comparatif", compute='_compute_name', store=True)
    is_category_id = fields.Many2one('is.category', 'Catégorie')
    segment_id     = fields.Many2one('is.product.segment', 'Segment')
    client         = fields.Char('Client', help="Recherche des articles dont le nom du client par défaut contient ce texte")
    date_calcul    = fields.Datetime("Date de la recherche", readonly=True)
    line_ids       = fields.One2many('is.galia.base.uc.comparatif.lot.line', 'comparatif_id', "Lignes", readonly=True)
    nb_lignes      = fields.Integer("Nb lignes", compute='_compute_nb_lignes')
    nb_ecarts      = fields.Integer("Nb écarts", compute='_compute_nb_lignes')


    def init(self):
        # Suppression de l'ancienne vue SQL remplacée par ce modèle
        tools.drop_view_if_exists(self._cr, 'is_galia_base_uc_comparatif_stock_lot')


    @api.depends('is_category_id', 'segment_id', 'client')
    def _compute_name(self):
        for obj in self:
            filtres = [x for x in [obj.is_category_id.name, obj.segment_id.name, obj.client] if x]
            obj.name = ' / '.join(filtres) or 'Comparatif'


    def _compute_nb_lignes(self):
        for obj in self:
            obj.nb_lignes = len(obj.line_ids)
            obj.nb_ecarts = len(obj.line_ids.filtered(lambda l: l.diff!=0))


    def lancer_recherche_action(self):
        "Calcule et enregistre les lignes du comparatif pour la catégorie, le segment et/ou le client"
        cr = self._cr
        for obj in self:
            if not obj.is_category_id and not obj.segment_id and not obj.client:
                raise ValidationError("Il faut saisir une catégorie, un segment ou un client")
            cr.execute("DELETE FROM is_galia_base_uc_comparatif_lot_line WHERE comparatif_id=%s", [obj.id])
            # Lot des UC : tableau des lots (CI), sinon champ Lot, sinon lot portant le nom de la Fabrication
            cr.execute("""
                WITH produits AS (
                    SELECT pp.id
                    FROM product_product pp
                    INNER JOIN product_template pt ON pt.id = pp.product_tmpl_id
                    LEFT JOIN res_partner rp ON rp.id = pt.is_client_id
                    WHERE (%(category_id)s IS NULL OR pt.is_category_id = %(category_id)s)
                    AND   (%(segment_id)s  IS NULL OR pt.segment_id     = %(segment_id)s)
                    AND   (%(client)s      IS NULL OR rp.name ILIKE %(client)s)
                ),
                -- État actif et emplacement lus sur l'UM (et non sur uc.um_active / uc.location_id, recopiés par l'ORM
                -- et faux si l'UC ou l'UM a été écrite en SQL)
                uc_lot AS (
                    SELECT uc.id AS uc_id, uc.um_id, uc.product_id, um.location_id, l.lot_id, l.qt_pieces
                    FROM is_galia_base_uc uc
                    INNER JOIN is_galia_base_um um ON um.id = uc.um_id
                    INNER JOIN produits p ON p.id = uc.product_id
                    INNER JOIN is_galia_base_uc_lot l ON l.uc_id = uc.id
                    INNER JOIN stock_location sl ON sl.id = um.location_id
                    WHERE uc.active = true AND um.active = true AND sl.usage = 'internal'
                    UNION ALL
                    SELECT uc.id, uc.um_id, uc.product_id, um.location_id, COALESCE(uc.lot_id, lot.id), uc.qt_pieces
                    FROM is_galia_base_uc uc
                    INNER JOIN is_galia_base_um um ON um.id = uc.um_id
                    INNER JOIN produits p ON p.id = uc.product_id
                    INNER JOIN stock_location sl ON sl.id = um.location_id
                    LEFT JOIN stock_lot lot ON lot.product_id = uc.product_id AND lot.name = uc.production
                    LEFT JOIN (SELECT DISTINCT uc_id FROM is_galia_base_uc_lot) l ON l.uc_id = uc.id
                    WHERE uc.active = true AND um.active = true AND sl.usage = 'internal'
                    AND l.uc_id IS NULL
                ),
                uc AS (
                    SELECT product_id, location_id, lot_id,
                        COUNT(DISTINCT uc_id) AS nb_uc, COUNT(DISTINCT um_id) AS nb_um, SUM(qt_pieces) AS qt_uc
                    FROM uc_lot
                    GROUP BY product_id, location_id, lot_id
                ),
                stock AS (
                    -- ROUND : certains quants ont des résidus flottants (ex : 26.000000000000004)
                    SELECT sq.product_id, sq.location_id, sq.lot_id, ROUND(SUM(sq.quantity), 4) AS qty
                    FROM stock_quant sq
                    INNER JOIN produits p ON p.id = sq.product_id
                    INNER JOIN stock_location sl ON sl.id = sq.location_id
                    WHERE sl.usage = 'internal'
                    GROUP BY sq.product_id, sq.location_id, sq.lot_id
                    HAVING ROUND(SUM(sq.quantity), 4) <> 0
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
                INSERT INTO is_galia_base_uc_comparatif_lot_line (
                    comparatif_id, product_id, location_id, lot_id,
                    client_id, is_category_id, is_gestionnaire_id, segment_id,
                    qty_stock, nb_um, nb_uc, qt_uc, diff,
                    create_uid, create_date, write_uid, write_date
                )
                SELECT
                    %(comparatif_id)s, l.product_id, l.location_id, l.lot_id,
                    pt.is_client_id, pt.is_category_id, pt.is_gestionnaire_id, pt.segment_id,
                    l.qty_stock, l.nb_um, l.nb_uc, l.qt_uc, l.qty_stock - l.qt_uc,
                    %(uid)s, now() AT TIME ZONE 'UTC', %(uid)s, now() AT TIME ZONE 'UTC'
                FROM lignes l
                INNER JOIN product_product pp ON pp.id = l.product_id
                INNER JOIN product_template pt ON pt.id = pp.product_tmpl_id
            """, {
                'comparatif_id': obj.id,
                'category_id'  : obj.is_category_id.id or None,
                'segment_id'   : obj.segment_id.id or None,
                'client'       : obj.client and '%%%s%%'%obj.client.strip() or None,
                'uid'          : self._uid,
            })
            _logger.info("lancer_recherche_action : %s : %s lignes"%(obj.name, cr.rowcount))
            obj.date_calcul = fields.Datetime.now()
            obj.invalidate_recordset(['line_ids'])
        return self.voir_lignes_action()


    def voir_lignes_action(self):
        for obj in self:
            return {
                'name': "Comparatif %s"%obj.name,
                'view_mode': 'tree,pivot',
                'res_model': 'is.galia.base.uc.comparatif.lot.line',
                'type': 'ir.actions.act_window',
                'domain': [('comparatif_id','=',obj.id)],
                'context': {'search_default_avec_ecart': 1},
            }


class is_galia_base_uc_comparatif_lot_line(models.Model):
    _name        = 'is.galia.base.uc.comparatif.lot.line'
    _description = "Lignes du comparatif stock lot / UC par emplacement"
    _order       = 'product_id,location_id,lot_id'

    comparatif_id      = fields.Many2one('is.galia.base.uc.comparatif.lot', 'Comparatif', required=True, ondelete='cascade', index=True)
    product_id         = fields.Many2one('product.product', 'Article', readonly=True, index=True)
    location_id        = fields.Many2one('stock.location', 'Emplacement', readonly=True, index=True)
    lot_id             = fields.Many2one('stock.lot', 'Lot', readonly=True, index=True)
    client_id          = fields.Many2one('res.partner', 'Client', readonly=True)
    is_category_id     = fields.Many2one('is.category', 'Catégorie', readonly=True)
    is_gestionnaire_id = fields.Many2one('is.gestionnaire', 'Gestionnaire', readonly=True)
    segment_id         = fields.Many2one('is.product.segment', 'Segment', readonly=True)
    qty_stock          = fields.Float("Qté en stock", readonly=True)
    nb_um              = fields.Integer("Nb UM", readonly=True)
    nb_uc              = fields.Integer("Nb UC", readonly=True)
    qt_uc              = fields.Float("Qté dans UC", readonly=True)
    diff               = fields.Float("Différence", readonly=True)


    def voir_uc_action(self):
        for obj in self:
            domain = [
                ('product_id'       ,'=',obj.product_id.id),
                ('um_id.location_id','=',obj.location_id.id),
                ('um_id.active'     ,'=',True),
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
