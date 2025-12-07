# -*- coding: utf-8 -*-
from odoo import fields, models


class MailThread(models.AbstractModel):
    """
    Ajout de l'index sur message_main_attachment_id pour améliorer les performances
    lors des suppressions massives d'attachments
    """
    _inherit = 'mail.thread'

    # Ajout de l'index manquant dans Odoo standard
    message_main_attachment_id = fields.Many2one(index=True)
