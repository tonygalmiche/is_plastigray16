# -*- coding: utf-8 -*-

from odoo import tools,models,fields


class is_comparatif_uc_lot(models.Model):
    _name='is.comparatif.uc.lot'
    _description='is.comparatif.uc.lot'
    _order='product_id'
    _auto = False

    product_id         = fields.Many2one('product.template', 'Article')
    partner_id         = fields.Many2one('res.partner', 'Client')
    is_category_id     = fields.Many2one('is.category', 'Catégorie')
    uc                 = fields.Float('Conditionnement')
    lot_livraison      = fields.Float('Lot de livraison')
    multiple_livraison = fields.Float('Multiple de livraison')
    test_lot           = fields.Float('Test Lot')
    test_multiple      = fields.Float('Test Multiple')


    def init(self):
        cr = self._cr
        tools.drop_view_if_exists(cr, 'is_comparatif_uc_lot')
        cr.execute("""

CREATE OR REPLACE view is_comparatif_uc_lot AS (
    select 
        ipc.id                  as id,
        pt.id                   as product_id, 
        rp.id                   as partner_id, 
        pt.is_category_id       as is_category_id, 
        is_qt_par_uc(pp.id)     as uc,
        ipc.lot_livraison       as lot_livraison,
        ipc.multiple_livraison  as multiple_livraison, 
        round(cast(ipc.lot_livraison      / is_qt_par_uc(pp.id) as numeric),4)       as test_lot,
        round(cast(ipc.multiple_livraison / is_qt_par_uc(pp.id) as numeric),4)       as test_multiple
    from is_product_client ipc inner join product_template pt on ipc.product_id=pt.id
                               inner join product_product  pp on pt.id=pp.product_tmpl_id
                               inner join res_partner rp      on ipc.client_id=rp.id
    where 
        is_qt_par_uc(pp.id)!=0 
        and (
            round(cast(ipc.lot_livraison/is_qt_par_uc(pp.id) as numeric),0)      != round(cast(ipc.lot_livraison/is_qt_par_uc(pp.id) as numeric),4) 
            or
            round(cast(ipc.multiple_livraison/is_qt_par_uc(pp.id) as numeric),0) != round(cast(ipc.multiple_livraison/is_qt_par_uc(pp.id) as numeric),4) 
        )
    order by pt.is_code, rp.is_code
)


        """)




