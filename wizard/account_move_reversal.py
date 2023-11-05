# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import UserError


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def _prepare_default_reversal(self, move):
        reverse_date = self.date if self.date_mode == 'custom' else move.date
        return {
            'supplier_invoice_number': False,
            'ref'                    : self.reason,
            'invoice_origin'         : '%s %s'%(move.name, move.supplier_invoice_number),
            'date'                   : reverse_date,
            'invoice_date_due'       : reverse_date,
            'invoice_date'           : move.is_invoice(include_receipts=True) and (self.date or move.date) or False,
            'journal_id'             : self.journal_id.id,
            'invoice_payment_term_id': None,
            'invoice_user_id'        : move.invoice_user_id.id,
            'auto_post'              : 'at_date' if reverse_date > fields.Date.context_today(self) else 'no',
        }
