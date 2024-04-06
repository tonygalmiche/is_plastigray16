# -*- coding: utf-8 -*-

from email.policy import default
from odoo import models,fields,api


class is_demande_transport(models.Model):
    _name='is.demande.transport'
    _inherit=['mail.thread']
    _description="Demande de transport"
    _order='name desc'

    name                 = fields.Char("N° de demande", readonly=True)
    type_demande         = fields.Selection([('transport', 'Transport'),('enlevement', 'Enlèvement')], "Type de demande", required=True, default='transport')
    demandeur_id         = fields.Many2one('res.users', 'Demandeur', required=True, default=lambda self: self.env.uid)
    date_demande         = fields.Date("Date de la demande", required=True, default=lambda *a: fields.datetime.now())
    dest_raison_sociale  = fields.Char("Raison Sociale destinataire", required=True)
    dest_adresse1        = fields.Char("Ligne adresse 1 destinataire")
    dest_adresse2        = fields.Char("Ligne adresse 2 destinataire")
    dest_code_postal     = fields.Char("Code postal destinataire")
    dest_ville           = fields.Char("Ville destinataire")
    dest_pays_id         = fields.Many2one('res.country', 'Pays destinataire')
    contact              = fields.Char("Contact")
    poids_net            = fields.Float("Poids net")
    poids_brut           = fields.Float("Poids brut")
    colisage             = fields.Char("Colisage")
    enlev_raison_sociale = fields.Char("Raison Sociale")
    enlev_adresse1       = fields.Char("Ligne adresse 1")
    enlev_adresse2       = fields.Char("Ligne adresse 2")
    enlev_code_postal    = fields.Char("Code postal")
    enlev_ville          = fields.Char("Ville")
    enlev_pays_id        = fields.Many2one('res.country', 'Pays')
    date_dispo           = fields.Datetime("Date-heure de disponibilité", required=False)
    date_liv_souhaitee   = fields.Datetime("Date-heure de livraison souhaitée", required=False)
    infos_diverses       = fields.Text("Informations diverses ")
    state                = fields.Selection([('brouillon', 'Brouillon'),('a_traiter', 'A traiter'),('termine', 'Terminé')], "Etat", default='brouillon')
    bl_id                = fields.Many2one('is.bl.manuel', 'BL manuel', readonly=True)


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('is.demande.transport')
        return super().create(vals_list)


    def envoi_mail(self, email_from,email_to,email_cc,subject,body_html):
        for obj in self:
            vals={
                'email_from'    : email_from, 
                'email_to'      : email_to, 
                'email_cc'      : email_cc,
                'subject'       : subject,
                'body_html'     : body_html, 
            }
            email=self.env['mail.mail'].create(vals)
            if email:
                self.env['mail.mail'].send(email)


    def vers_a_traiter_action(self):
        for obj in self:
            company  = self.env.user.company_id
            email_to = company.is_gest_demande_transport_id.email
            if email_to:
                subject=u'['+obj.name+u'] Demande de transport à traiter'
                user  = self.env['res.users'].browse(self._uid)
                email_from = user.email
                email_cc   = email_from
                nom   = user.name
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url=base_url+u'/web#id='+str(obj.id)+u'&view_type=form&model=is.demande.transport'
                body_html=u"""
                    <p>Bonjour,</p>
                    <p>"""+nom+""" vient de passer la demande de transport <a href='"""+url+"""'>"""+obj.name+"""</a> à l'état 'A traiter'.</p>
                    <p>Merci d'en prendre connaissance.</p>
                """
                self.envoi_mail(email_from,email_to,email_cc,subject,body_html)
            obj.state="a_traiter"


    def vers_brouillon_action(self):
        for obj in self:
            obj.sudo().state="brouillon"


    def vers_termine_action(self):
        for obj in self:
            email_to = obj.demandeur_id.email
            if email_to:
                subject=u'['+obj.name+u'] Demande de transport terminée'
                user  = self.env['res.users'].browse(self._uid)
                email_from = user.email
                if email_from:
                    email_cc   = email_from
                    nom   = user.name
                    base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                    url=base_url+u'/web#id='+str(obj.id)+u'&view_type=form&model=is.demande.transport'
                    body_html=u"""
                        <p>Bonjour,</p>
                        <p>"""+nom+""" vient de passer la demande de transport <a href='"""+url+"""'>"""+obj.name+"""</a> à l'état 'Terminé'.</p>
                        <p>Merci d'en prendre connaissance.</p>
                    """
                    self.envoi_mail(email_from,email_to,email_cc,subject,body_html)
            obj.state="termine"


