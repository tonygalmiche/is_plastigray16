# -*- coding: utf-8 -*-
from odoo import models,fields,tools


class is_comparatif_livraison_facture(models.Model):
    _name='is.comparatif.livraison.facture'
    _description="Comparatif Liv / Facture"
    _order='invoice_id,product_id'
    _auto = False

    invoice_id      = fields.Many2one('account.move', 'Facture')
    name            = fields.Char('N°Facture')
    state           = fields.Char('Etat Facture')
    picking_id      = fields.Many2one('stock.picking', 'Livraison')
    partner_id      = fields.Many2one('res.partner', 'Client')
    product_id      = fields.Many2one('product.product', 'Article')
    product_uom     = fields.Many2one('uom.uom', 'Unité Livraison')
    product_uom_id  = fields.Many2one('uom.uom', 'Unité Facture')
    product_uom_qty = fields.Float('Quantité Livraison', digits=(14, 2))
    quantity        = fields.Float('Quantité Facture', digits=(14, 2))


    def init(self):
        cr = self._cr
        tools.drop_view_if_exists(cr, 'is_comparatif_livraison_facture')
        cr.execute("""

CREATE OR REPLACE view is_comparatif_livraison_facture AS (
    select 
        ail.id,
        ail.move_id invoice_id,
        ai.name,
        ai.state,
        sm.picking_id,
        ai.partner_id,
        ail.product_id,
        sm.product_uom,
        ail.product_uom_id,
        sm.product_uom_qty,
        ail.quantity
    from account_move_line ail inner join account_move ai on ail.move_id=ai.id
                               inner join stock_move      sm on ail.is_move_id=sm.id
    where ai.move_type='out_invoice' and (ail.product_uom_id!=sm.product_uom or ail.quantity!=sm.quantity_done)
)
        """)


