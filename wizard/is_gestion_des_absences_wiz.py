# -*- coding: utf-8 -*-
from odoo import models,fields,api


class is_gestion_des_absences_wiz(models.TransientModel):
    _name = 'is.gestion.des.absences.wiz'
    _description = "is_gestion_des_absences_wiz"

    conges_reason = fields.Text('Motif', required=True)

    def valider_reponse(self):
        conges_obj = self.env['is.demande.conges']
        if self._context and self._context.get('active_id'):
            conges = conges_obj.browse(self._context.get(('active_id')))

            user = self.env['res.users'].browse(self._uid)
            nom = user.name

            if conges.mode_communication in ['courriel','courriel+sms'] and conges.courriel:
                subject = u'[' + conges.name + u'] Demande de congés - retour Brouillon ('+self.conges_reason+u')'
                email_to = conges.courriel
                email_from = user.email
                email_cc = email_from
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = base_url + u'/web#id=' + str(conges.id) + u'&view_type=form&model=is.demande.conges'
                body_html = u""" 
                    <p>Bonjour,</p> 
                    <p>""" + nom + """ vient de repasser la Demande de congés <a href='""" + url + """'>""" + conges.name + """</a> à l'état 'Brouillon'.</p> 
                    <p>Motif du retour : """+self.conges_reason+u"""</p>
                    <p>Merci d'en prendre connaissance.</p> 
                """
                conges.sudo().envoi_mail(email_from, email_to, email_cc, subject, body_html)

            conges.sudo().raison_du_retour = self.conges_reason
            conges.sudo().state = 'creation'
            #conges.sudo().delete_workflow()
            #conges.sudo().create_workflow()

            subject   = u"vers Brouillon"
            if conges.mode_communication in ['courriel','courriel+sms'] and conges.courriel:
                body_html = u"<p>Mail envoyé de "+str(email_from)+u" à "+str(email_to)+u" (cc="+str(email_cc)+u")</p>"+body_html
            else:
                body_html =u''
            conges.creer_notification(subject,body_html)

            if conges.mode_communication in ['sms','courriel+sms'] and conges.mobile:
                message = u'Bonjour, ' + nom + u' vient de passer la Demande de congés ' + conges.name + u" à l'état 'Brouillon'. Motif du retour : "+self.conges_reason
                # res,err = conges.envoi_sms(conges.mobile, message)
                # if err=='':
                #     subject = u'SMS envoyé sur le '+conges.mobile+u' (il reste '+res+u' SMS sur le compte)'
                #     conges.creer_notification(subject,message)
                # else:
                #     conges.creer_notification(u'ATTENTION : SMS non envoyé', err)
        return {'type': 'ir.actions.act_window_close'}


class is_gestion_vers_annuler_wiz(models.TransientModel):
    _name = 'is.gestion.vers.annuler.wiz'
    _description = "is_gestion_vers_annuler_wiz"


    conges_reason = fields.Text(u"Motif de l'annulation", required=True)

    def valider_reponse(self):
        conges_obj = self.env['is.demande.conges']
        if self._context and self._context.get('active_id'):
            conges = conges_obj.browse(self._context.get(('active_id')))
            motif = self.conges_reason.replace('\n',' ')

            user = self.env['res.users'].browse(self._uid)    
            nom = user.name

            if conges.mode_communication in ['courriel','courriel+sms'] and conges.courriel:
                subject = u'[' + conges.name + u'] Demande de congés - Annulation ('+motif+u')'
                email_to = conges.courriel
                email_from = user.email
                email_cc = email_from
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = base_url + u'/web#id=' + str(conges.id) + u'&view_type=form&model=is.demande.conges'
                body_html = u""" 
                    <p>Bonjour,</p> 
                    <p>""" + nom + """ vient de passer la Demande de congés <a href='""" + url + """'>""" + conges.name + """</a> à l'état 'Annulé'.</p> 
                    <p>Motif de l'annulation : """+self.conges_reason+u"""</p>
                    <p>Merci d'en prendre connaissance.</p> 
                """
                conges.sudo().envoi_mail(email_from, email_to, email_cc, subject, body_html)
            conges.sudo().raison_annulation = self.conges_reason
            #conges.sudo().signal_workflow('annule')
            conges.sudo().state = 'annule'


            subject   = u"vers Annulé"
            if conges.mode_communication in ['courriel','courriel+sms'] and conges.courriel:
                body_html = u"<p>Mail envoyé de "+str(email_from)+u" à "+str(email_to)+u" (cc="+str(email_cc)+u")</p>"+body_html
            else:
                body_html =u''
            conges.creer_notification(subject,body_html)

            if conges.mode_communication in ['sms','courriel+sms'] and conges.mobile:
                message = u'Bonjour, ' + nom + u' vient de passer la Demande de congés ' + conges.name + u" à l'état 'Annulé'. Motif de l'annulation : "+motif
                # res,err = conges.envoi_sms(conges.mobile, message)
                # if err=='':
                #     subject = u'SMS envoyé sur le '+conges.mobile+u' (il reste '+res+u' SMS sur le compte)'
                #     conges.creer_notification(subject,message)
                # else:
                #     conges.creer_notification(u'ATTENTION : SMS non envoyé', err)
        return {'type': 'ir.actions.act_window_close'}


class is_gestion_vers_refuse_wiz(models.TransientModel):
    _name = 'is.gestion.vers.refuse.wiz'
    _description = "is_gestion_vers_refuse_wiz"


    conges_reason = fields.Text('Motif du refus', required=True)

    def valider_reponse(self):
        conges_obj = self.env['is.demande.conges']
        if self._context and self._context.get('active_id'):
            conges = conges_obj.browse(self._context.get(('active_id')))
            motif = self.conges_reason.replace('\n',' ')

            user = self.env['res.users'].browse(self._uid)
            nom = user.name

            if conges.mode_communication in ['courriel','courriel+sms'] and conges.courriel:
                subject = u'[' + conges.name + u'] Demande de congés - Refus ('+motif+u')'
                email_to = conges.courriel
                email_from = user.email
                email_cc = email_from
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = base_url + u'/web#id=' + str(conges.id) + u'&view_type=form&model=is.demande.conges'
                body_html = u""" 
                    <p>Bonjour,</p> 
                    <p>""" + nom + """ vient de passer la Demande de congés <a href='""" + url + """'>""" + conges.name + """</a> à l'état 'Refusé'.</p> 
                    <p>Motif du refus : """+self.conges_reason+u"""</p>
                    <p>Merci d'en prendre connaissance.</p> 
                """
                conges.sudo().envoi_mail(email_from, email_to, email_cc, subject, body_html)
            conges.sudo().raison_annulation = self.conges_reason
            #conges.sudo().signal_workflow('refuse')
            conges.sudo().state = 'refuse'


            subject   = u"vers Refusé"
            if conges.mode_communication in ['courriel','courriel+sms'] and conges.courriel:
                body_html = u"<p>Mail envoyé de "+str(email_from)+u" à "+str(email_to)+u" (cc="+str(email_cc)+u")</p>"+body_html
            else:
                body_html =u''
            conges.creer_notification(subject,body_html)

            if conges.mode_communication in ['sms','courriel+sms'] and conges.mobile:
                message = u'Bonjour, ' + nom + u' vient de passer la Demande de congés ' + conges.name + u" à l'état 'Refusé'. Motif du refus : "+motif
                # res,err = conges.envoi_sms(conges.mobile, message)
                # if err=='':
                #     subject = u'SMS envoyé sur le '+conges.mobile+u' (il reste '+res+u' SMS sur le compte)'
                #     conges.creer_notification(subject,message)
                # else:
                #     conges.creer_notification(u'ATTENTION : SMS non envoyé', err)
        return {'type': 'ir.actions.act_window_close'}




