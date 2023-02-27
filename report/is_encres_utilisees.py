# -*- coding: utf-8 -*-
from odoo import models,fields,tools
import time
import logging
_logger = logging.getLogger(__name__)


class is_encres_utilisees(models.Model):
    _name = 'is.encres.utilisees'
    _description = "Encres utilisees"
    _order = 'id desc'
    _auto = False

    name                 = fields.Selection([
            ('1', '1'),
            ('2', '2'),
            ('3', '3'),
        ], 'N°encrier')
    constituant_id       = fields.Many2one('is.fiche.tampographie.constituant', 'Constituant')
    product_id           = fields.Many2one('product.product', u'Référence article')
    poids                = fields.Char('Poids (gr)')
    ift_name             = fields.Char(u'Désignation')
    article_injection_id = fields.Many2one('product.product', u'Référence pièce sortie injection')
    is_mold_dossierf     = fields.Char('Moule')
    article_tampo_id     = fields.Many2one('product.product', u'Référence pièce tampographiée')


    def init(self):
        start = time.time()
        cr = self.env.cr
        tools.drop_view_if_exists(cr, 'is_encres_utilisees')
        cr.execute("""
            CREATE OR REPLACE view is_encres_utilisees AS (
                select
                    iftr.id,
                    ift.name as ift_name,
                    ift.article_injection_id,
                    tmpl.is_mold_dossierf,
                    ift.article_tampo_id,
                    iftr.name,
                    iftr.constituant_id,
                    iftr.product_id,
                    iftr.poids
                from is_fiche_tampographie_recette iftr 
                inner join is_fiche_tampographie ift on ift.id=iftr.tampographie_id
                left join product_product on product_product.id=ift.article_injection_id
                left join product_template as tmpl on tmpl.id=product_product.product_tmpl_id
            )
        """)
        _logger.info('## init is_livraison_gefco en %.2fs'%(time.time()-start))

