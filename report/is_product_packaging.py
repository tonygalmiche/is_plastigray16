# -*- coding: utf-8 -*-
from odoo import models, fields, tools
import time
import logging
_logger = logging.getLogger(__name__)


class is_product_packaging(models.Model):
    _name='is.product.packaging'
    _description="is_product_packaging"
    _order='product_tmpl_id,sequence,id'
    _auto = False

    product_tmpl_id    = fields.Many2one('product.template', 'Article')
    segment_id         = fields.Many2one('is.product.segment', 'Segment')
    is_category_id     = fields.Many2one('is.category', 'Catégorie')
    is_gestionnaire_id = fields.Many2one('is.gestionnaire', 'Gestionnaire')
    is_mold_dossierf   = fields.Char('Moule ou Dossier F')
    weight_net         = fields.Float('Poids net' , digits='Stock Weight')
    weight             = fields.Float('Poids brut', digits='Stock Weight')
    sequence           = fields.Integer('Séquence')
    qty                = fields.Integer('Quantité par colis')
    ul                 = fields.Many2one('is.product.ul', 'Unité logistique colis')
    ul_qty             = fields.Integer('Colis par couche')
    rows               = fields.Integer('Nombre de couches')
    ul_container       = fields.Many2one('is.product.ul', 'Unité logistique palette')

    def init(self):
        if self.env.company.is_activer_init:
            start = time.time()
            cr = self.env.cr
            tools.drop_view_if_exists(cr, 'is_product_packaging')
            cr.execute("""
                CREATE OR REPLACE view is_product_packaging AS (
                    select 
                        pack.id,
                        pp.product_tmpl_id,
                        pt.segment_id,
                        pt.is_category_id,
                        pt.is_gestionnaire_id,
                        pt.is_mold_dossierf,
                        pt.weight_net,
                        pt.weight,
                        pack.sequence, 
                        pack.qty, 
                        pack.ul,
                        pack.ul_qty, 
                        pack.rows,
                        pack.ul_container
                    from product_template pt join product_product pp     on pp.product_tmpl_id=pt.id                
                                            join product_packaging pack on pp.id=pack.product_id
                );
            """)
            _logger.info('## init is_product_packaging en %.2fs'%(time.time()-start))



