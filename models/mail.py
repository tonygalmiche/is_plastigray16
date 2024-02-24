# -*- coding: utf-8 -*-
from odoo import models,fields,api


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"


    def _message_auto_subscribe_notify(self, partner_ids, template):
        "Désactiver les notifications d'envoi des mails"
        return True


# class Channel(models.Model):
#     _inherit = 'mail.channel'

#     def _subscribe_users_automatically(self):
#         """Fonction désactivée le 24/02/2024 car bug lors de la création d'utilisateurs"""

#TODO : Ce bug était lié à des utilisateurs actifs reliés à des partenaires inactifs
# J'ai corrigé ce bug avec cette requete : 
# update res_partner set active='t' where id in (select partner_id from res_users where active='t') and active='f';