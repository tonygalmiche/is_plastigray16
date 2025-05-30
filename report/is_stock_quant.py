# -*- coding: utf-8 -*-
from odoo import models,fields,tools
import time
import logging
_logger = logging.getLogger(__name__)


class is_stock_quant(models.Model):
    _name='is.stock.quant'
    _description="Stock détaillé"
    _order='product_id,location_id,lot'
    _auto = False

    product_id         = fields.Many2one('product.template', 'Article')
    code_pg            = fields.Char('Code PG')
    designation        = fields.Char('Désignation')
    gestionnaire_id    = fields.Many2one('is.gestionnaire' , 'Gestionnaire')
    category_id        = fields.Many2one('is.category'     , 'Catégorie')
    moule              = fields.Char('Moule')
    client_id          = fields.Many2one('res.partner', 'Client')
    ref_client         = fields.Char('Référence Client')
    ref_fournisseur    = fields.Char('Référence Fournisseur')
    location_id        = fields.Many2one('stock.location'     , 'Emplacement Id')
    emplacement        = fields.Char('Emplacement')
    lot_id             = fields.Many2one('stock.lot', 'Lot')
    lot                = fields.Char('Nom lot')
    lot_fournisseur    = fields.Char('Lot fournisseur')
    quantite           = fields.Float('Quantité', digits=(16,6))
    uom_id             = fields.Many2one('uom.uom', 'Unité')
    date_entree        = fields.Datetime("Date d'entrée")


    def init(self):
        if self.env.company.is_activer_init:
            start = time.time()
            cr = self._cr
            tools.drop_view_if_exists(cr, 'is_stock_quant')
            cr.execute("""
                CREATE OR REPLACE view is_stock_quant AS (
                    select
                        max(isq.id) as id,
                        isq.product_id, 
                        isq.code_pg,
                        isq.designation,
                        isq.gestionnaire_id,
                        isq.category_id,
                        isq.moule,
                        isq.ref_client,
                        isq.ref_fournisseur,
                        isq.location_id,
                        isq.emplacement,
                        isq.lot,
                        isq.lot_fournisseur,
                        sum(isq.quantite) as quantite, 
                        isq.uom_id,
                        max(isq.date_entree) as date_entree,
                        isq.client_id,
                        isq.lot_id
                    from (

                        select 
                            sq.id                  id,
                            pt.id                  product_id, 
                            pt.is_code             code_pg,
                            pt.name->>'fr_FR'      designation,
                            pt.is_gestionnaire_id  gestionnaire_id,
                            pt.is_category_id      category_id,
                            pt.is_mold_dossierf    moule,
                            pt.is_ref_client       ref_client,
                            pt.is_ref_fournisseur  ref_fournisseur,
                            sq.location_id         location_id,
                            sl.name                emplacement,
                            spl.name               lot,
                            spl.is_lot_fournisseur lot_fournisseur,
                            sq.quantity            quantite, 
                            pt.uom_id              uom_id,
                            in_date                date_entree,
                            pt.is_client_id        client_id,
                            sq.lot_id
                        from stock_quant sq join product_product            pp on sq.product_id=pp.id
                                            join product_template           pt on pp.product_tmpl_id=pt.id
                                            join stock_location             sl on sq.location_id=sl.id
                                            join is_category                ic on pt.is_category_id=ic.id
                                            left outer join stock_lot      spl on sq.lot_id=spl.id
                        where 
                            sl.usage='internal' and 
                            sq.quantity<>0 and 
                            ic.name not in ('70','71','72','73','74','75','82')
                    ) isq
                    group by
                        isq.product_id, 
                        isq.code_pg,
                        isq.designation,
                        isq.gestionnaire_id,
                        isq.category_id,
                        isq.moule,
                        isq.ref_client,
                        isq.ref_fournisseur,
                        isq.location_id,
                        isq.emplacement,
                        isq.lot,
                        isq.lot_fournisseur,
                        isq.uom_id,
                        isq.client_id,
                        isq.lot_id
                )
            """)
            _logger.info('## init is_stock_quant en %.2fs'%(time.time()-start))



