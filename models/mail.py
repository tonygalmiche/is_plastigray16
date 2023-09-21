# -*- coding: utf-8 -*-
from odoo import models,fields,api


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"


    def _message_auto_subscribe_notify(self, partner_ids, template):
        "Désactiver les notifications d'envoi des mails"
        return True

