# -*- coding: utf-8 -*-
from odoo import tools,models,fields


class is_comparatif_tarif_commande(models.Model):
    _name='is.comparatif.tarif.commande'
    _description='Comparatif Prix Liste de prix / Commandes'
    _order='product_id'
    _auto = False

    sale_id           = fields.Many2one('sale.order', 'Commande')
    partner_id        = fields.Many2one('res.partner', 'Client')
    product_id        = fields.Many2one('product.template', 'Article')
    is_category_id    = fields.Many2one('is.category', 'Catégorie')
    product_uom_qty   = fields.Float('Quantité', digits=(12, 4))
    is_date_livraison = fields.Date('Date de livraison')
    prix_commande     = fields.Float('Prix Commande'             , digits=(12, 4))
    justification     = fields.Char('Justification')
    prix_liste_prix   = fields.Float('Prix Liste de prix'        , digits=(12, 4))
    delta             = fields.Float('Delta'                     , digits=(12, 4))


    def init(self):
        cr = self._cr
        tools.drop_view_if_exists(cr, 'is_comparatif_tarif_commande')
        cr.execute("""
            CREATE OR REPLACE view is_comparatif_tarif_commande AS (
                SELECT 
                    sol.id               as id,
                    so.id                as sale_id,
                    pt.id                as product_id,
                    so.partner_id        as partner_id,
                    pt.is_category_id    as is_category_id,
                    sol.product_uom_qty,
                    sol.is_date_livraison,
                    sol.price_unit       as prix_commande,
                    sol.is_justification as justification,
                    COALESCE(is_prix_vente(so.pricelist_id,pp.id,sol.product_uom_qty,sol.is_date_livraison),0) as prix_liste_prix,
                    round(cast(abs(COALESCE(is_prix_vente(so.pricelist_id,pp.id,sol.product_uom_qty,sol.is_date_livraison),0)-sol.price_unit) as numeric),4) as delta


                FROM sale_order_line sol inner join sale_order       so on sol.order_id=so.id
                                        inner join product_product  pp on sol.product_id=pp.id
                                        inner join product_template pt on pp.product_tmpl_id=pt.id
                                        inner join is_category      ic on pt.is_category_id=ic.id
                WHERE 
                    so.state='draft' and sol.state='draft' and 
                    sol.price_unit!=COALESCE(is_prix_vente(so.pricelist_id,pp.id,sol.product_uom_qty,sol.is_date_livraison),0) and
                    sol.is_justification is null     
            )
        """)


