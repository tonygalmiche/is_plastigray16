# -*- coding: utf-8 -*-
from odoo import models,fields,api
import datetime
import pytz
import time
import logging
_logger = logging.getLogger(__name__)


class is_account_invoice_line(models.Model):
    _name='is.account.invoice.line'
    _description="Lignes des factures"
    _order='id desc'
    _auto = False

    partner_id              = fields.Many2one('res.partner', 'Client/Fournisseur')
    partner_picking_id      = fields.Many2one('res.partner', 'Client/Fournisseur Livraison')
    invoice_id              = fields.Many2one('account.move', 'Facture')
    date_reception          = fields.Datetime("Date réception")
    invoice_date            = fields.Date("Date facture")
    internal_number         = fields.Char('N°Facture')
    invoice_date_due        = fields.Date("Date d'échéance")
    invoice_origin          = fields.Char('Origine/BL')
    supplier_invoice_number = fields.Char('Numéro de facture fournisseur')
    product_id              = fields.Many2one('product.product', 'Article')
    account_id              = fields.Many2one('account.account', 'Compte')

    segment_id              = fields.Many2one('is.product.segment', 'Segment')
    is_category_id          = fields.Many2one('is.category', 'Catégorie')
    is_gestionnaire_id      = fields.Many2one('is.gestionnaire', 'Gestionnaire')
    is_ref_client           = fields.Char('Référence client')
    is_mold_dossierf        = fields.Char('Moule ou Dossier F')

    description             = fields.Char('Description')
    is_document             = fields.Char("N° du chantier")
    quantity                = fields.Float('Quantité', digits=(14,2))
    product_uom_id          = fields.Many2one('uom.uom', 'Unité')
    price_unit              = fields.Float('Prix unitaire', digits=(14,4))
    total                   = fields.Float('Montant Total', digits=(14,2))

    amortissement_moule     = fields.Float('Amt client négocié', digits=(14,4))
    amt_interne             = fields.Float('Amt interne'       , digits=(14,4))
    cagnotage               = fields.Float('Cagnotage'         , digits=(14,4))

    montant_amt_moule       = fields.Float('Montant amt client négocié', digits=(14,2))
    montant_amt_interne     = fields.Float('Montant amt interne'       , digits=(14,2))
    montant_cagnotage       = fields.Float('Montant cagnotage'         , digits=(14,2))

    montant_matiere         = fields.Float('Montant matière livrée', digits=(14,2))

    invoice_line_id         = fields.Many2one('account.move.line', 'Ligne de facture')
    move_id                 = fields.Many2one('stock.move', 'Mouvement de stock')
    picking_id              = fields.Many2one('stock.picking', 'Livraison')
    purchase_order_id       = fields.Many2one('purchase.order', 'Commande fournisseur')
    order_id                = fields.Many2one('sale.order', 'Commande Client Odoo')
    client_order_ref        = fields.Char('Commande Client')
    order_line_id           = fields.Many2one('sale.order.line', 'Ligne commande client')
    is_type_facture = fields.Selection([
            ('standard', u'Standard'),
            ('diverse', u'Diverse')
        ], u"Type de facture", default='standard', index=True)
    move_type               = fields.Selection([
            ('in_invoice' , u'Facture fournisseur'),
            ('in_refund'  , u'Avoir fournisseur'),
            ('out_invoice', u'Facture client'),
            ('out_refund' , u'Avoir client'),

        ], u"Type", readonly=True, index=True)
    journal_id = fields.Many2one('account.journal', 'Journal')

    # state = fields.Char("État", readonly=True, index=True)
    state      = fields.Selection([
            ('draft' , 'Brouillon'),
            ('posted', 'Comptabilisé'),
            ('cancel', 'Annulé'),
        ], u"État", readonly=True, index=True)


    def refresh_ligne_facture_client_action(self):
        cr = self._cr
        cr.execute("REFRESH MATERIALIZED VIEW is_account_invoice_line;")
        now = datetime.datetime.now(pytz.timezone('Europe/Paris')).strftime('%H:%M:%S')
        view_id=self.env.ref('is_plastigray16.is_account_invoice_line_customer_tree_view').id
        return {
            'name': u'Lignes des factures client actualisées à '+str(now),
            'view_mode': 'tree,form,pivot,graph',
            'view_id'  : False,
            'views'    : [(view_id, 'tree'),(False, 'form'),(False, 'pivot'),(False, 'graph')],
            'res_model': 'is.account.invoice.line',
            'domain'   : [('move_type','=', 'out_invoice')],
            'type': 'ir.actions.act_window',
        }

    def refresh_ligne_facture_fournisseur_action(self):
        cr = self._cr
        cr.execute("REFRESH MATERIALIZED VIEW is_account_invoice_line;")
        now = datetime.datetime.now(pytz.timezone('Europe/Paris')).strftime('%H:%M:%S')
        view_id=self.env.ref('is_plastigray16.is_account_invoice_line_supplier_tree_view').id
        return {
            'name': u'Lignes des factures fournisseur actualisées à '+str(now),
            'view_mode': 'tree,form,pivot,graph',
            'view_id'  : False,
            'views'    : [(view_id, 'tree'),(False, 'form'),(False, 'pivot'),(False, 'graph')],
            'res_model': 'is.account.invoice.line',
            'domain'   : [('move_type','=', 'in_invoice')],
            'type': 'ir.actions.act_window',
        }


    def refresh_ca_facture_client_action(self):
        cr = self._cr
        cr.execute("REFRESH MATERIALIZED VIEW is_account_invoice_line;")
        now = datetime.datetime.now(pytz.timezone('Europe/Paris')).strftime('%H:%M:%S')
        view_id=self.env.ref('is_plastigray16.is_indicateur_ca_facture_tree_view').id
        return {
            'name': u'CA factures client actualisé à '+str(now),
            'view_mode': 'tree,form,pivot,graph',
            'view_id'  : False,
            'views'    : [(view_id, 'tree'),(False, 'form'),(False, 'pivot'),(False, 'graph')],
            'res_model': 'is.account.invoice.line',
            'domain'   : [('move_type','in', ['out_refund','out_invoice']),('state','=','posted')],
            'type': 'ir.actions.act_window',
        }


    def init(self):
        if self.env.company.is_activer_init:
            start = time.time()
            cr = self._cr
            cr.execute("""
                CREATE OR REPLACE FUNCTION fsens(t text) RETURNS integer AS $$
                BEGIN
                    RETURN (
                        SELECT
                        CASE
                        WHEN t::text = ANY (ARRAY['out_refund'::character varying::text, 'in_refund'::character varying::text])
                            THEN -1::int
                            ELSE 1::int
                        END
                    );
                END;
                $$ LANGUAGE plpgsql;

                DROP MATERIALIZED VIEW IF EXISTS is_account_invoice_line;
                CREATE MATERIALIZED view is_account_invoice_line AS (
                    select 
                        ail.id,
                        ail.id invoice_line_id,
                        ai.partner_id,
                        sp.partner_id        partner_picking_id,
                        ai.id invoice_id,
                        sm.date date_reception,
                        ai.invoice_date,
                        ai.name internal_number,
                        ai.invoice_date_due,
                        ai.invoice_origin,
                        ai.ref supplier_invoice_number,
                        ai.state,
                        ai.move_type,
                        ai.journal_id,
                        ai.is_type_facture,
                        ail.product_id,
                        ail.account_id,
                        pt.segment_id,
                        pt.is_category_id,
                        pt.is_gestionnaire_id,
                        pt.is_mold_dossierf,
                        pt.is_ref_client,
                        ail.name                  description,
                        ail.is_document           is_document,
                        (fsens(ai.move_type)*ail.quantity) as quantity,
                        ail.product_uom_id,
                        ail.price_unit,
                        (fsens(ai.move_type)*ail.quantity*ail.price_unit) total,

                        ail.is_amortissement_moule amortissement_moule,
                        ail.is_amt_interne         amt_interne,
                        ail.is_cagnotage           cagnotage,
                        ail.is_montant_amt_moule   montant_amt_moule,
                        ail.is_montant_amt_interne montant_amt_interne,
                        ail.is_montant_cagnotage   montant_cagnotage,
                        ail.is_montant_matiere     montant_matiere,

                        ail.is_move_id            move_id,
                        sm.picking_id             picking_id,
                        sp.is_purchase_order_id   purchase_order_id,
                        sol.order_id              order_id,
                        sol.is_client_order_ref   client_order_ref,
                        sol.id                    order_line_id
                    from account_move ai    inner join account_move_line ail    on ai.id=ail.move_id
                                            inner join product_product       pp on ail.product_id=pp.id
                                            inner join product_template      pt on pp.product_tmpl_id=pt.id
                                            inner join res_partner           rp on ai.partner_id=rp.id
                                            left outer join stock_move       sm on ail.is_move_id=sm.id
                                            left outer join stock_picking    sp on sm.picking_id=sp.id
                                            left outer join sale_order_line sol on sm.is_sale_line_id=sol.id
                    where ai.id>0
                    order by ail.id desc
                )
            """)
            _logger.info('## init is_ligne_livraison en %.2fs'%(time.time()-start))
