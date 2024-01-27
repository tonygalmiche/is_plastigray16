# -*- coding: utf-8 -*-
from odoo import api, exceptions, fields, models, _, Command

class MailActivity(models.Model):
    _inherit = 'mail.activity'

    def action_notify(self):
        "Désactivation de l'envoi des mails pour les activités"
        print(self)
        return
