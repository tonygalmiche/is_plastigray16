# -*- coding: utf-8 -*-

from odoo import models,fields,tools
import time
import logging
_logger = logging.getLogger(__name__)


class is_certifications_qualite_suivi(models.Model):
    _name='is.certifications.qualite.suivi'
    _description="Suivi validité des certificats"
    _order='partner_id,is_norme'
    _auto = False

    partner_id         = fields.Many2one('res.partner', 'Fournisseur')
    is_segment_achat   = fields.Many2one('is.segment.achat', "Segment d'achat")
    is_norme           = fields.Many2one('is.norme.certificats', 'Norme')
    is_date_validation = fields.Date('Date de validité du certificat')
    certificat_id      = fields.Many2one('is.certifications.qualite', 'Certificat qualité')


    def init(self):
        start = time.time()
        cr = self._cr
        tools.drop_view_if_exists(cr, 'is_certifications_qualite_suivi')
        cr.execute("""
            CREATE OR REPLACE view is_certifications_qualite_suivi AS (
                select 
                    row_number() over(order by icq.id) as id,
                    rp.id partner_id,
                    rp.is_segment_achat,
                    icq.is_norme,
                    icq.is_date_validation,
                    icq.id certificat_id
                from res_partner rp left outer join is_certifications_qualite icq on rp.id=icq.partner_id
                where rp.supplier='t' and rp.is_company='t' and active='t'
            )
        """)
        _logger.info('## init is_certifications_qualite_suivi en %.2fs'%(time.time()-start))

