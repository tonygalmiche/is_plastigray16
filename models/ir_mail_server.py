# -*- coding: utf-8 -*-
import logging
from email.utils import getaddresses, formataddr

from odoo import models

_logger = logging.getLogger(__name__)

# Clé du paramètre système contenant la liste des emails destinataires à bloquer
# (séparés par des virgules), ex : "exemple@domaine.fake,autre@domaine.fake"
CONFIG_PARAM_BLOCKED_EMAILS = 'is_plastigray16.blocked_recipient_emails'


class IrMailServer(models.Model):
    """
    Point d'entrée unique par lequel transitent tous les mails sortants d'Odoo,
    quelle que soit l'application à l'origine de l'envoi (mail.mail, notifications,
    envois directs via ir.mail_server, etc.).
    On y retire les destinataires bloqués (configurés dans le paramètre système
    'is_plastigray16.blocked_recipient_emails') tout en conservant l'envoi aux
    autres destinataires éventuels.
    """
    _inherit = 'ir.mail_server'

    def _get_blocked_recipient_emails(self):
        param = self.env['ir.config_parameter'].sudo().get_param(CONFIG_PARAM_BLOCKED_EMAILS, '')
        return {e.strip().lower() for e in param.split(',') if e.strip()}

    def send_email(self, message, *args, **kwargs):
        blocked_emails = self._get_blocked_recipient_emails()
        if not blocked_emails:
            return super().send_email(message, *args, **kwargs)

        for header in ('To', 'Cc', 'Bcc'):
            header_value = message[header]
            if not header_value:
                continue
            addresses = getaddresses([header_value])
            filtered_addresses = [
                (name, email) for name, email in addresses
                if email.lower() not in blocked_emails
            ]
            if len(filtered_addresses) != len(addresses):
                del message[header]
                if filtered_addresses:
                    message[header] = ', '.join(formataddr(a) for a in filtered_addresses)

        if not message['To'] and not message['Cc'] and not message['Bcc']:
            _logger.info(
                "Mail non envoyé : seul(s) destinataire(s) bloqué(s) (%s) - Sujet : %s",
                ', '.join(blocked_emails), message.get('Subject'),
            )
            return None

        return super().send_email(message, *args, **kwargs)
