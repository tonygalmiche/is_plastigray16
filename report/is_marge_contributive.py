# -*- coding: utf-8 -*-
from odoo import models,fields,tools
import time
import logging
_logger = logging.getLogger(__name__)


class is_marge_contributive(models.Model):
    _name='is.marge.contributive'
    _description="Marge contributive sur facture"
    _order='id desc'
    _auto = False

    line_id                 = fields.Many2one('account.move.line', 'ligne de facture')
    invoice_id              = fields.Many2one('account.move', 'Facture')
    invoice_date            = fields.Date("Date facture")
    code_pg                 = fields.Char('Code PG')
    cat                     = fields.Char('Cat')
    gest                    = fields.Char('Gest')
    segment                 = fields.Char('Segment')
    fam                     = fields.Char('Famille')
    moule                   = fields.Char('Moule')
    partner_id              = fields.Many2one('res.partner', 'Partenaire')
    client_fac              = fields.Char('Client facturé')
    raison_sociale          = fields.Char('Raison sociale')
    designation             = fields.Char('Désignation')
    amortissement_moule     = fields.Float('Amt Moule'             , digits=(14,4))
    cout_std_matiere        = fields.Float('Coût Std Matière'      , digits=(14,4))
    cout_std_machine        = fields.Float('Coût Std Machine'      , digits=(14,4))
    cout_std_mo             = fields.Float('Coût Std MO'           , digits=(14,4))
    cout_std_st             = fields.Float('Coût Std ST'           , digits=(14,4))
    cout_std_prix_vente     = fields.Float('Prix de vente standard', digits=(14,4))
    cout_act_matiere        = fields.Float('Coût Act Matière'      , digits=(14,4))
    cout_act_machine        = fields.Float('Coût Act Machine'      , digits=(14,4))
    cout_act_mo             = fields.Float('Coût Act MO'           , digits=(14,4))
    cout_act_st             = fields.Float('Coût Act ST'           , digits=(14,4))
    product_id              = fields.Many2one('product.product', 'Article')
    quantity                = fields.Float('Quantité'              , digits=(14,4))
    price_unit              = fields.Float('Prix unitaire'         , digits=(14,4))
    montant                 = fields.Float('CA Facturé'            , digits=(14,2))
    ca_prix_vente_std       = fields.Float('CA Prix vente standard', digits=(14,2))

    def init(self):
        start = time.time()
        cr = self._cr
        tools.drop_view_if_exists(cr, 'is_marge_contributive')
        cr.execute("""
            CREATE OR REPLACE view is_marge_contributive AS (
                select 
                    ail.id          id,
                    ail.id          line_id,
                    ai.id           invoice_id,
                    ai.invoice_date invoice_date,
                    pt.is_code      code_pg,
                    ic.name         cat,
                    ig.name         gest,
                    ips.name        segment,
                    ipf.name        fam,
                    coalesce(im.name,id.name) moule,
                    ai.partner_id,
                    rp.is_code      client_fac,
                    rp.name         raison_sociale,
                    pt.name->>'fr_FR' designation,
                    get_amortissement_moule_a_date(rp.is_code, pt.id, ai.invoice_date) as amortissement_moule,
                    get_amt_interne_a_date(rp.is_code, pt.id, ai.invoice_date) as amt_interne,
                    get_cagnotage_a_date(rp.is_code, pt.id, ai.invoice_date) as cagnotage,

                    (select cout_std_matiere    from is_cout cout where pp.id=cout.name limit 1) cout_std_matiere,
                    (select cout_std_machine    from is_cout cout where pp.id=cout.name limit 1) cout_std_machine,
                    (select cout_std_mo         from is_cout cout where pp.id=cout.name limit 1) cout_std_mo,
                    (select cout_std_st         from is_cout cout where pp.id=cout.name limit 1) cout_std_st,
                    (select cout_std_prix_vente from is_cout cout where pp.id=cout.name limit 1) cout_std_prix_vente,
                    (select cout_act_matiere    from is_cout cout where pp.id=cout.name limit 1) cout_act_matiere,
                    (select cout_act_machine    from is_cout cout where pp.id=cout.name limit 1) cout_act_machine,
                    (select cout_act_mo         from is_cout cout where pp.id=cout.name limit 1) cout_act_mo,
                    (select cout_act_st         from is_cout cout where pp.id=cout.name limit 1) cout_act_st,
                    ail.product_id,
                    fsens(ai.move_type)*ail.quantity quantity,
                    ail.price_unit,
                    fsens(ai.move_type)*(ail.quantity*ail.price_unit) montant,
                    fsens(ai.move_type)*ail.quantity*(select cout_std_prix_vente from is_cout cout where pp.id=cout.name limit 1) ca_prix_vente_std
                from account_move ai    inner join account_move_line       ail on ai.id=ail.move_id
                                        inner join res_partner              rp on ai.partner_id=rp.id
                                        inner join product_product          pp on ail.product_id=pp.id
                                        inner join product_template         pt on pp.product_tmpl_id=pt.id
                                        left outer join is_category         ic on pt.is_category_id=ic.id
                                        left outer join is_gestionnaire     ig on pt.is_gestionnaire_id=ig.id
                                        left outer join is_product_famille ipf on pt.family_id=ipf.id
                                        left outer join is_product_segment ips on pt.segment_id=ips.id
                                        left outer join is_mold             im on pt.is_mold_id=im.id
                                        left outer join is_dossierf         id on pt.is_dossierf_id=id.id
                where ai.move_type in ('out_invoice','out_refund')
            )
        """)
        _logger.info('## init is_marge_contributive en %.2fs'%(time.time()-start))


