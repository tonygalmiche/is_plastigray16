# -*- coding: utf-8 -*-

from odoo import models


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _is_invoice_report(self, report_ref):
        # account_invoice_en16931 (module OCA/Akretion) n'injecte le XML
        # Factur-X dans le PDF que si _is_invoice_report() renvoie True.
        # Le core Odoo (addons/account/models/ir_actions_report.py) ne
        # reconnaît que les report_name "account.report_invoice_with_payments"
        # et "account.report_invoice" ; notre template maison
        # "is_report_invoice_template" (utilisé par l'action
        # account.account_invoices, cf. imprimer_simple_double() dans
        # account_invoice.py) n'est donc jamais reconnu comme un report de
        # facture, et le XML Factur-X n'est jamais ajouté au PDF.
        return super()._is_invoice_report(report_ref) or (
            self._get_report(report_ref).report_name
            == "is_plastigray16.is_report_invoice_template"
        )
