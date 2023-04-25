# -*- coding: utf-8 -*-

from odoo import tools,models,fields


class is_comparatif_uc_lot_mini(models.Model):
    _name='is.comparatif.uc.lot.mini'
    _description='is.comparatif.uc.lot.mini'
    _order='product_id'
    _auto = False

    product_id         = fields.Many2one('product.template', 'Article')
    is_category_id     = fields.Many2one('is.category', 'Catégorie')
    uc                 = fields.Float('Conditionnement')
    lot_mini           = fields.Float("Lot d'appro")
    multiple           = fields.Float("Multiple")
    test_lot_mini      = fields.Float("Test Lot d'appro")
    test_multiple      = fields.Float("Test Multiple")


    def init(self):
        cr = self._cr
        tools.drop_view_if_exists(cr, 'is_comparatif_uc_lot_mini')
        cr.execute("""

CREATE OR REPLACE view is_comparatif_uc_lot_mini AS (
    select 
        pt.id                   as id,
        pt.id                   as product_id, 
        pt.is_category_id       as is_category_id, 
        is_qt_par_uc(pp.id)     as uc,
        pt.lot_mini             as lot_mini,
        pt.multiple             as multiple,
        round(cast(pt.lot_mini      / is_qt_par_uc(pp.id) as numeric),4) as test_lot_mini,
        round(cast(pt.multiple      / is_qt_par_uc(pp.id) as numeric),4) as test_multiple
    from product_template pt inner join product_product  pp on pt.id=pp.product_tmpl_id
    where 
        pt.id>0
        and is_qt_par_uc(pp.id)!=0
        and (
            round(cast(pt.lot_mini/is_qt_par_uc(pp.id) as numeric),0) != round(cast(pt.lot_mini/is_qt_par_uc(pp.id) as numeric),4) 
            or
            (round(cast(pt.multiple/is_qt_par_uc(pp.id) as numeric),0) != round(cast(pt.multiple/is_qt_par_uc(pp.id) as numeric),4) and multiple>1)
        )
)

        """)



