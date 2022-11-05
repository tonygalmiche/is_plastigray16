# -*- coding: utf-8 -*-
#import ssl
from odoo import models, fields, api
import datetime
from dateutil.relativedelta import relativedelta
#import os
#import unicodedata
#import codecs
#import base64
#import csv, cStringIO
#from openerp.exceptions import Warning
#import xmlrpclib
#from openerp import SUPERUSER_ID
#import pytz


_TYPE_DEMANDE = [
    ('cp_rtt_journee'     , u'CP ou RTT par journée entière'),
    ('cp_rtt_demi_journee', u'CP ou RTT par ½ journée'),
    ('rc_heures'          , u'RC en heures'),
    ('sans_solde'         , u'Congés sans solde'),
    ('autre'              , u'Autre'),
]


class is_demande_conges(models.Model):
    _name        = 'is.demande.conges'
    _inherit=['mail.thread']
    _description = u'Demande de congés'
    _order       = 'name desc'


    def _format_mobile(self,mobile):
        err=''
        if not mobile:
            err=u'Mobile non renseigné pour le contact'
        else:
            mobile = mobile.replace(' ','')
            if len(mobile)!=10:
                err=u'Le numéro doit contenir 10 chiffres'
            else:
                if mobile[0:2]!='06' and mobile[0:2]!='07':
                    err=u'Le numéro du mobile doit commencer par 06 ou 07'
                else:
                    mobile='0033'+mobile[-9:]
        return mobile,err


    def envoi_sms(self, mobile, message):
        """Envoi de SMS avec OVH"""
        cr , uid, context = self.env.args
        mobile,err = self._format_mobile(mobile)
        res=''
        quota=0
        if err=='':
            err=''
            user = self.env['res.users'].browse(uid)
            company = user.company_id
            message = unicodedata.normalize('NFD', message).encode('ascii', 'ignore')
            to = mobile
            param = \
                'account='+(company.is_sms_account or '')+\
                '&login='+(company.is_sms_login or '')+\
                '&password='+(company.is_sms_password or '')+\
                '&from='+(company.is_sms_from or '')+\
                '&to='+to+\
                '&message='+message
            cde = 'curl --data "'+param+'" https://www.ovh.com/cgi-bin/sms/http2sms.cgi'
            res=os.popen(cde).readlines()
            if res[0].strip()=='KO':
                err=res[1].strip()
            if res[0].strip()=='OK':
                res=str(int(float(res[1].strip())))
        return res,err


    def envoi_mail(self, email_from, email_to, email_cc, subject, body_html):
        for obj in self:
            vals = {
                'email_from'    : email_from,
                'email_to'      : email_to,
                'email_cc'      : email_cc,
                'subject'       : subject,
                'body_html'     : body_html,
            }
            email = self.env['mail.mail'].create(vals)
            if email:
                self.env['mail.mail'].send(email)


    def creer_notification(self, subject,body_html):
        for obj in self:
            user = self.env['res.users'].browse(self._uid)
            vals={
                'subject'       : subject,
                'body'          : body_html, 
                'body_html'     : body_html, 
                'model'         : self._name,
                'res_id'        : obj.id,
                'notification'  : True,
                'author_id'     : user.partner_id.id
                #'message_type'  : 'comment',
            }
            email=self.env['mail.mail'].sudo().create(vals)


    def vers_validation_n1_action(self):
        for obj in self:
            if obj.demande_collective=='oui':
                for employe in obj.demandeur_ids:
                    vals={
                        #'name'               : obj.name,
                        #'createur_id'        : obj.createur_id,
                        #'date_creation'      : obj.date_creation,
                        'demandeur_id'         : employe.user_id.id,
                        #'valideur_n1'        : obj.valideur_n1,
                        #'valideur_n2'        : obj.valideur_n2,
                        #'responsable_rh_id'  : obj.responsable_rh_id,
                        'type_demande'         : obj.type_demande,
                        'autre_id'             : obj.autre_id.id,
                        'date_debut'           : obj.date_debut,
                        'date_fin'             : obj.date_fin,
                        'le'                   : obj.le,
                        'matin_ou_apres_midi'  : obj.matin_ou_apres_midi,
                        'heure_debut'          : obj.heure_debut,
                        'heure_fin'            : obj.heure_fin,
                        'demande_collective'   : 'non',
                        'demande_collective_id': obj.id,
                    }
                    demande = self.env['is.demande.conges'].create(vals)
                    demande.vers_validation_n1_action()

            obj.date_validation_n1 = datetime.datetime.today()

            if not obj.demande_collective_id:
                subject = u'[' + obj.name + u'] Demande de congés - Envoyé au N+1 pour validation'
                email_to = obj.valideur_n1.email
                user = self.env['res.users'].browse(self._uid)
                email_from = user.email
                email_cc = ''
                if obj.mode_communication in ['courriel','courriel+sms'] and obj.courriel:
                    email_cc = obj.courriel
                nom = user.name
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = base_url + u'/web#id=' + str(obj.id) + u'&view_type=form&model=is.demande.conges'
                body_html = u""" 
                    <p>Bonjour,</p> 
                    <p>""" + nom + """ vient de passer la Demande de congés <a href='""" + url + """'>""" + obj.name + """</a> à l'état 'Validation Niveau 1'.</p> 
                    <p>Merci d'en prendre connaissance.</p> 
                """ 
                self.envoi_mail(email_from, email_to, email_cc, subject, body_html)
                subject   = u"vers Validation niveau 1"
                body_html = u"<p>Mail envoyé de "+str(email_from)+u" à "+str(email_to)+u" (cc="+str(email_cc)+u")</p>"+body_html
                self.creer_notification(subject,body_html)
                if obj.mode_communication in ['sms','courriel+sms'] and obj.mobile:
                    message = """Bonjour, """ + nom + """ vient de passer la Demande de congés """ + obj.name + """ à l'état 'Validation Niveau 1'."""
                    res,err = self.envoi_sms(obj.mobile, message)
                    if err=='':
                        subject = u'SMS envoyé sur le '+obj.mobile+u' (il reste '+res+u' SMS sur le compte)'
                        self.creer_notification(subject,message)
                    else:
                        self.creer_notification(u'ATTENTION : SMS non envoyé', err)

            obj.signal_workflow('validation_n1')
        return True

    def vers_validation_n2_action(self):
        for obj in self:
            if obj.demande_collective=='oui':
                for demande in obj.demande_conges_ids:
                    demande.vers_validation_n2_action()

            obj.date_validation_n2 = datetime.datetime.today()

            if not obj.demande_collective_id:
                subject = u'[' + obj.name + u'] Demande de congés - Envoyé au N+2 pour validation'
                email_to = obj.valideur_n2.email
                user = self.env['res.users'].browse(self._uid)
                email_from = user.email

                email_cc = ''
                if obj.mode_communication in ['courriel','courriel+sms'] and obj.courriel:
                    email_cc = obj.courriel

                nom = user.name
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = base_url + u'/web#id=' + str(obj.id) + u'&view_type=form&model=is.demande.conges'
                body_html = u""" 
                    <p>Bonjour,</p> 
                    <p>""" + nom + """ vient de passer la Demande de congés <a href='""" + url + """'>""" + obj.name + """</a> à l'état 'Validation Niveau 2'.</p> 
                    <p>Merci d'en prendre connaissance.</p> 
                """ 
                self.envoi_mail(email_from, email_to, email_cc, subject, body_html)

                subject   = u"vers Validation niveau 2"
                body_html = u"<p>Mail envoyé de "+str(email_from)+u" à "+str(email_to)+u" (cc="+str(email_cc)+u")</p>"+body_html
                self.creer_notification(subject,body_html)

                if obj.mode_communication in ['sms','courriel+sms'] and obj.mobile:
                    message = """Bonjour, """ + nom + """ vient de passer la Demande de congés """ + obj.name + """ à l'état 'Validation Niveau 2'."""
                    res,err = self.envoi_sms(obj.mobile, message)
                    if err=='':
                        subject = u'SMS envoyé sur le '+obj.mobile+u' (il reste '+res+u' SMS sur le compte)'
                        self.creer_notification(subject,message)
                    else:
                        self.creer_notification(u'ATTENTION : SMS non envoyé', err)

            obj.signal_workflow('validation_n2')
        return True

    def vers_validation_rh_action(self):
        for obj in self:
            if obj.demande_collective=='oui':
                for demande in obj.demande_conges_ids:
                    demande.vers_validation_rh_action()
            obj.date_validation_rh = datetime.datetime.today()
            if not obj.demande_collective_id:
                subject = u'[' + obj.name + u'] Demande de congés - Accepté et transmis au RH'
                email_to = obj.responsable_rh_id.email
                user = self.env['res.users'].browse(self._uid)
                email_from = user.email
                email_cc = ''
                if obj.mode_communication in ['courriel','courriel+sms'] and obj.courriel:
                    email_cc = obj.courriel
                nom = user.name
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = base_url + u'/web#id=' + str(obj.id) + u'&view_type=form&model=is.demande.conges'
                body_html = u""" 
                    <p>Bonjour,</p> 
                    <p>""" + nom + """ vient de passer la Demande de congés <a href='""" + url + """'>""" + obj.name + """</a> à l'état 'Validation RH'.</p> 
                    <p>Merci d'en prendre connaissance.</p> 
                """ 
                self.envoi_mail(email_from, email_to, email_cc, subject, body_html)
                subject   = u"vers Validation RH"
                body_html = u"<p>Mail envoyé de "+str(email_from)+u" à "+str(email_to)+u" (cc="+str(email_cc)+u")</p>"+body_html
                self.creer_notification(subject,body_html)
                if obj.mode_communication in ['sms','courriel+sms'] and obj.mobile:
                    message = """Bonjour, """ + nom + """ vient de passer la Demande de congés """ + obj.name + """ à l'état 'Validation RH'."""
                    res,err = self.envoi_sms(obj.mobile, message)
                    if err=='':
                        subject = u'SMS envoyé sur le '+obj.mobile+u' (il reste '+res+u' SMS sur le compte)'
                        self.creer_notification(subject,message)
                    else:
                        self.creer_notification(u'ATTENTION : SMS non envoyé', err)

                #** Creation du commentaire de pointage ************************
                if obj.type_demande in ['sans_solde','autre']:
                    employes = self.env['hr.employee'].search([('user_id', '=', obj.demandeur_id.id),('is_pointage','=',True)], limit=1)
                    for employe in employes:
                        d0 = datetime.datetime.strptime(obj.date_debut, '%Y-%m-%d')
                        d1 = datetime.datetime.strptime(obj.date_fin  , '%Y-%m-%d')
                        nb_jours = (d1 - d0).days
                        self.env['is.pointage.commentaire'].sudo().search([('demande_conges_id', '=', obj.id)]).unlink()
                        for x in range(nb_jours+1):
                            name = d0 + datetime.timedelta(days=x)
                            if obj.type_demande=='sans_solde':
                                commentaire = u'[' + obj.name +u'] Congés sans solde'
                            else:
                                commentaire = u'[' + obj.name +u'] '+obj.autre_id.name
                            vals={
                                'name'             : name,
                                'employee'         : employe.id,
                                'commentaire'      : commentaire,
                                'demande_conges_id': obj.id,
                            }
                            res=self.env['is.pointage.commentaire'].sudo().create(vals)
                #***************************************************************

            try:
                if obj.demande_collective=='non':
                    obj.ajouter_dans_agenda()
            except:
                pass
            obj.signal_workflow('validation_rh')
        return True

    def vers_solde_action(self):
        for obj in self:
            if obj.demande_collective=='oui':
                alerte=False
                for demande in obj.demande_conges_ids:
                    if demande.state not in ['solde','refuse','annule']:
                        alerte=True
                if alerte:
                    raise Warning(u'Il est nécessaire de solder chaque demande individuellement pour pouvoir solder cette demande collective !')
            subject   = u"vers Soldé"
            self.creer_notification(subject,"")

            obj.signal_workflow('solde')
        return True


    def default_get(self, default_fields):
        res = super(is_demande_conges, self).default_get(default_fields)
        emp_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1) or False
        if emp_id:
            res['valideur_n1'] = emp_id.is_valideur_n1.id
            res['valideur_n2'] = emp_id.is_valideur_n2.id
        return res


    def test_dates(self):
        uid=self._uid
        if self.date_debut and self.date_fin:
            mois_demande = str(self.date_debut)[:8]
            ce_mois      = str(datetime.date.today())[:8]
            if mois_demande<ce_mois and self.responsable_rh_id.id!=uid and uid!=1:
                raise Warning(u"Le mois de la demande ne peux pas être inférieur au mois en cours")
            if str(self.date_debut)[:8]!=str(self.date_fin)[:8]:
                raise Warning(u"La date de fin doit être dans le même mois que la date de début")
            if self.date_debut>self.date_fin:
                raise Warning(u"La date de fin doit être supérieure à la date de début")
        return True


    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].get('is.demande.conges') or ''
        res=super(is_demande_conges, self).create(vals)
        res.test_dates()
        return res



    def ajouter_dans_agenda(self):
        now = datetime.datetime.now()
        tz = pytz.timezone('CET')
        offset=tz.utcoffset(now).total_seconds()
        events=[]
        if self.type_demande in ["cp_rtt_journee","sans_solde","autre"]:
            dt1 = datetime.datetime.strptime(self.date_debut + " 08:00:00", '%Y-%m-%d %H:%M:%S')
            dt2 = datetime.datetime.strptime(self.date_fin   + " 08:00:00", '%Y-%m-%d %H:%M:%S')
            start = dt1
            while start <= dt2:
                events.append([
                    start - datetime.timedelta(seconds=offset), 
                    start - datetime.timedelta(seconds=offset) + datetime.timedelta(hours=10), 
                ])
                start = start + datetime.timedelta(days=1)
        if self.type_demande=="cp_rtt_demi_journee":
            start = self.le
            if self.matin_ou_apres_midi=="matin":
                start = self.le+" 08:00:00"
            else:
                start = self.le+" 13:30:00"
            start = datetime.datetime.strptime(start, '%Y-%m-%d %H:%M:%S')
            start = start - datetime.timedelta(seconds=offset)
            stop = start + datetime.timedelta(hours=4)
            events.append([start, stop])
        if self.type_demande=="rc_heures": 
            hours, minutes = divmod(self.heure_debut*60, 60)
            debut = " %02d:%02d:00"%(hours,minutes)
            hours, minutes = divmod(self.heure_fin*60, 60)
            fin   = " %02d:%02d:00"%(hours,minutes)
            start = self.le + debut
            start = datetime.datetime.strptime(start, '%Y-%m-%d %H:%M:%S')
            start = start - datetime.timedelta(seconds=offset)
            stop = self.le + fin
            stop = datetime.datetime.strptime(stop, '%Y-%m-%d %H:%M:%S')
            stop = stop - datetime.timedelta(seconds=offset)
            events.append([start, stop])
        email = self.demandeur_id.partner_id.email
        company = self.env.user.company_id
        DB = "odoo-agenda"
        USERID = 2
        DBLOGIN = "admin"
        USERPASS = company.is_agenda_pwd
        url = company.is_agenda_url+'/xmlrpc/2/common'
        common = xmlrpclib.ServerProxy(url, verbose=False, use_datetime=True, context=ssl._create_unverified_context())
        uid = common.authenticate(DB, DBLOGIN, USERPASS, {})
        url = company.is_agenda_url+'/xmlrpc/object'
        models = xmlrpclib.ServerProxy(url, verbose=False, use_datetime=True, context=ssl._create_unverified_context())
        partner = models.execute_kw(
            DB, USERID, USERPASS, 
            'res.partner', 
            'search_read', 
            [[('email', '=', email)]],
            {'fields': ['name','email'], 'limit': 1}
        )
        if partner:
            partner_id=partner[0]["id"]
            user = models.execute_kw(
                DB, USERID, USERPASS, 
                'res.users', 
                'search_read', 
                [[('partner_id', '=',partner_id)]],
                {'fields': ['login'], 'limit': 1}
            )
            if user:
                user_id=user[0]["id"]
                name=self.type_demande
                for line in _TYPE_DEMANDE:
                    if line[0]==self.type_demande:
                        name = line[1]
                name=u"[Congé] "+name
                for event in events:
                    vals={
                        "name"       : name,
                        "user_id"    : user_id,
                        "start"      : str(event[0]),
                        "stop"       : str(event[1]),
                        "partner_ids": [[6, False, [partner_id]]],
                    }
                    event_id = models.execute_kw(DB, USERID, USERPASS, 'calendar.event', 'create', [vals])
                    print(event_id,vals)
                    if event_id:
                        attendee = models.execute_kw(
                            DB, USERID, USERPASS, 
                            'calendar.attendee', 
                            'search_read', 
                            [[('event_id', '=', event_id)]],
                            {'fields': ['state'], 'limit': 1}
                        )
                        if attendee:
                            attendee_id=attendee[0]["id"]
                            models.execute_kw(DB, USERID, USERPASS, 'calendar.attendee', 'write', [[attendee_id], {'state': "accepted"}])


    def write(self,vals):
        res=super(is_demande_conges, self).write(vals)
        self.test_dates()
        return res


    @api.depends('state','demandeur_id','createur_id','responsable_rh_id','valideur_n1','valideur_n1')
    def _get_btn_vsb(self):
        uid = self._uid
        for obj in self:
            vers_creation       = False
            vers_annuler        = False
            vers_refuse         = False
            vers_validation_n1  = False
            vers_validation_n2  = False
            vers_validation_rh  = False
            vers_solde          = False
            fld_vsb             = False
            droit_actualise_vsb = False
            test_date           = False
            current_date = datetime.date.today()
            current_date_plus_ten = current_date + relativedelta(days=10)
            if obj.date_debut:
                if str(current_date_plus_ten) < obj.date_debut:
                    test_date = True
            if obj.le:
                if str(current_date_plus_ten) < obj.le:
                    test_date = True
            if test_date:
                if obj.state == 'validation_n1' or obj.state == 'validation_n2' or obj.state == 'validation_rh':
                    if obj.createur_id.id == uid or obj.demandeur_id.id == uid or obj.valideur_n1.id == uid or obj.valideur_n2.id == uid or obj.responsable_rh_id.id == uid:
                        vers_creation = True
                        vers_annuler  = True


            if obj.state == 'validation_rh' and  obj.responsable_rh_id.id == uid:
                fld_vsb = True

            if obj.state == 'creation':
                if obj.valideur_n1:
                    if obj.createur_id.id == uid or obj.demandeur_id.id == uid or obj.valideur_n1.id == uid or obj.valideur_n2.id == uid or obj.responsable_rh_id.id == uid:
                        vers_validation_n1 = True
                else:
                    if obj.valideur_n2:
                        if obj.valideur_n2.id == uid or obj.responsable_rh_id.id == uid:
                            vers_validation_rh = True
                            vers_annuler       = True
                            vers_refuse        = True
                    else:
                        if obj.responsable_rh_id.id == uid:
                            vers_validation_rh = True
                            vers_annuler       = True
                            vers_refuse        = True

            if obj.state == 'validation_n1':
                if obj.valideur_n2:
                    if obj.valideur_n1.id == uid or obj.valideur_n2.id == uid or obj.responsable_rh_id.id == uid:
                        vers_validation_n2 = True
                        vers_annuler       = True
                        vers_refuse        = True
                else:
                    if obj.valideur_n1.id == uid or obj.responsable_rh_id.id == uid:
                        vers_validation_rh = True
                        vers_annuler       = True
                        vers_refuse        = True

            if obj.state == 'validation_n2':
                if obj.valideur_n2.id == uid or obj.responsable_rh_id.id == uid:
                    vers_validation_rh = True
                    vers_annuler       = True
                    vers_refuse        = True
            if obj.state == 'validation_rh':
                if obj.responsable_rh_id.id == uid:
                    vers_solde   = True
                    vers_annuler = True
                    vers_annuler = True

            if obj.responsable_rh_id.id == uid:
                droit_actualise_vsb = True

            obj.vers_creation_btn_vsb      = vers_creation
            obj.vers_annuler_btn_vsb       = vers_annuler
            obj.vers_refuse_btn_vsb        = vers_refuse
            obj.vers_validation_n1_btn_vsb = vers_validation_n1
            obj.vers_validation_n2_btn_vsb = vers_validation_n2
            obj.vers_validation_rh_btn_vsb = vers_validation_rh
            obj.vers_solde_btn_vsb         = vers_solde
            obj.fld_vsb                    = fld_vsb
            obj.droit_actualise_vsb        = droit_actualise_vsb


    @api.depends('demandeur_id')
    def _compute_mode_communication(self):
        for obj in self:
            employes = self.env['hr.employee'].search([('user_id', '=', obj.demandeur_id.id)], limit=1)
            mode_communication = False
            mobile             = False
            courriel           = False
            droit_cp  = 0
            droit_rtt = 0
            droit_rc  = 0
            for employe in employes:
                mode_communication = employe.is_mode_communication
                mobile             = employe.is_mobile
                courriel           = employe.is_courriel
                droits = self.env['is.droit.conges'].search([('employe_id', '=', employe.id)])
                for droit in droits:
                    if droit.name=='CP':
                        droit_cp = droit.nombre
                    if droit.name=='RTT':
                        droit_rtt = droit.nombre
                    if droit.name=='RC':
                        droit_rc = droit.nombre
            obj.mode_communication = mode_communication
            obj.mobile             = mobile
            obj.courriel           = courriel
            obj.droit_cp  = droit_cp
            obj.droit_rtt = droit_rtt
            obj.droit_rc  = droit_rc
        return True


    @api.depends('demandeur_id')
    def _compute_droit_actualise(self):
        for obj in self:
            employes = self.env['hr.employee'].search([('user_id', '=', obj.demandeur_id.id)], limit=1)
            droit_cp  = 0
            droit_rtt = 0
            droit_rc  = 0
            for employe in employes:
                droits = self.env['is.droit.conges'].search([('employe_id', '=', employe.id)])
                for droit in droits:
                    if droit.name=='CP':
                        droit_cp = droit.nombre
                    if droit.name=='RTT':
                        droit_rtt = droit.nombre
                    if droit.name=='RC':
                        droit_rc = droit.nombre
            obj.droit_cp_actualise  = droit_cp
            obj.droit_rtt_actualise = droit_rtt
            obj.droit_rc_actualise  = droit_rc
        return True


    @api.depends('demandeur_id')
    def _compute_matricule(self):
        for obj in self:
            obj.matricule = obj.demandeur_id.login


    @api.onchange('employe_id')
    def _onchange_employe_id(self):
        if self.employe_id and self.employe_id.user_id:
            self.demandeur_id = self.employe_id.user_id.id

 
    name                          = fields.Char(u"N° demande")
    createur_id                   = fields.Many2one('res.users', u'Créateur', default=lambda self: self.env.user        , copy=False)
    date_creation                 = fields.Datetime(string=u'Date de création', default=lambda *a: fields.datetime.now(), copy=False)
    employe_id                    = fields.Many2one('hr.employee', 'Autre demandeur')
    demandeur_id                  = fields.Many2one('res.users', 'Demandeur', default=lambda self: self.env.user)
    matricule                     = fields.Char(u"Matricule", compute='_compute_matricule', readonly=True, store=True)
    mode_communication = fields.Selection([
                                        ('courriel'    , u'Courriel'),
                                        ('sms'         , u'SMS'),
                                        ('courriel+sms','Courriel + SMS'),
                                        ], string='Mode de communication'                                                , compute='_compute_mode_communication', readonly=True, store=True)
    mobile   = fields.Char(u"Mobile"  , help="Téléphone utilisé pour l'envoi des SMS pour les demandes de congés"        , compute='_compute_mode_communication', readonly=True, store=True)
    courriel = fields.Char(u"Courriel", help="Courriel utilisé pour l'envoi des informations pour les demandes de congés", compute='_compute_mode_communication', readonly=True, store=True)

    valideur_n1                   = fields.Many2one('res.users', 'Valideur Niveau 1')
    date_validation_n1            = fields.Datetime(string='Date création', copy=False)
    valideur_n2                   = fields.Many2one('res.users', 'Valideur Niveau 2')
    date_validation_n2            = fields.Datetime(string='Date validation N1', copy=False)
    responsable_rh_id             = fields.Many2one('res.users', 'Responsable RH', default=lambda self: self.env.user.company_id.is_responsable_rh_id)
    date_validation_rh            = fields.Datetime(string='Date validation N2', copy=False)

# - Date vers validation N1 => Ne sert à rien => Ou "Date de création" si tu veux
# - Date vers validation N2 => Date validation N1
# - Date vers  responsable RH => Date validation N2

    type_demande                  = fields.Selection(_TYPE_DEMANDE, string='Type de demande', required=True)
    autre_id                      = fields.Many2one('is.demande.conges.autre', 'Type autre')
    justificatif_ids              = fields.Many2many('ir.attachment', 'is_demande_conges_attachment_rel', 'demande_conges_id', 'file_id', u"Justificatif")
    cp                            = fields.Float(string='CP (jours)' , digits=(14,2), copy=False)
    rtt                           = fields.Float(string='RTT (jours)', digits=(14,2), copy=False)
    rc                            = fields.Float(string='RC (heures)', digits=(14,2), copy=False)

    droit_cp                      = fields.Float(string='Droit CP (jours)' , digits=(14,2), compute='_compute_mode_communication', readonly=True, store=True)
    droit_rtt                     = fields.Float(string='Droit RTT (jours)', digits=(14,2), compute='_compute_mode_communication', readonly=True, store=True)
    droit_rc                      = fields.Float(string='Droit RC (heures)', digits=(14,2), compute='_compute_mode_communication', readonly=True, store=True)

    droit_cp_actualise            = fields.Float(string='Droit CP actualisé (jours)' , digits=(14,2), compute='_compute_droit_actualise', readonly=True, store=False)
    droit_rtt_actualise           = fields.Float(string='Droit RTT actualisé (jours)', digits=(14,2), compute='_compute_droit_actualise', readonly=True, store=False)
    droit_rc_actualise            = fields.Float(string='Droit RC actualisé (heures)', digits=(14,2), compute='_compute_droit_actualise', readonly=True, store=False)

    date_debut                    = fields.Date(string=u'Date début')
    date_fin                      = fields.Date(string='Date fin')
    le                            = fields.Date(string='Le')
    matin_ou_apres_midi           = fields.Selection([
                                        ('matin', 'Matin'),
                                        ('apres_midi', u'Après-midi')
                                        ], string=u'Matin ou après-midi')
    #heure_debut                  = fields.Integer(string=u'Heure début')
    #heure_fin                    = fields.Integer(string=u'Heure fin')
    heure_debut                   = fields.Float(u"Heure début", digits=(14, 2))
    heure_fin                     = fields.Float(u"Heure fin"  , digits=(14, 2))
    raison_du_retour              = fields.Text(string='Motif du retour'       , copy=False)
    raison_annulation             = fields.Text(string='Motif refus/annulation', copy=False)
    demande_collective            = fields.Selection([
                                        ('oui', u'Oui'),
                                        ('non', u'Non'),
                                        ], string=u'Demande collective', required=True, default='non')
    demandeur_ids                 = fields.Many2many('hr.employee', string=u'Demandeurs')
    demande_conges_ids            = fields.One2many('is.demande.conges', 'demande_collective_id', u"Demandes de congés")
    demande_collective_id         = fields.Many2one('is.demande.conges', u"Demandes collective d'origine")

    state                         = fields.Selection([
                                        ('creation', u'Brouillon'),
                                        ('validation_n1', 'Validation niveau 1'),
                                        ('validation_n2', 'Validation niveau 2'),
                                        ('validation_rh', 'Validation RH'),
                                        ('solde' , u'Soldé'),
                                        ('refuse', u'Refusé'),
                                        ('annule', u'Annulé')], string=u'État', readonly=True, default='creation')

    vers_creation_btn_vsb      = fields.Boolean(string='vers_creation_btn_vsb'     , compute='_get_btn_vsb', default=False, readonly=True)
    vers_annuler_btn_vsb       = fields.Boolean(string='vers_annuler_btn_vsb'      , compute='_get_btn_vsb', default=False, readonly=True)
    vers_refuse_btn_vsb        = fields.Boolean(string='vers_refuse_btn_vsb'       , compute='_get_btn_vsb', default=False, readonly=True)
    vers_validation_n1_btn_vsb = fields.Boolean(string='vers_validation_n1_btn_vsb', compute='_get_btn_vsb', default=False, readonly=True)
    vers_validation_n2_btn_vsb = fields.Boolean(string='vers_validation_n2_btn_vsb', compute='_get_btn_vsb', default=False, readonly=True)
    vers_validation_rh_btn_vsb = fields.Boolean(string='vers_validation_rh_btn_vsb', compute='_get_btn_vsb', default=False, readonly=True)
    vers_solde_btn_vsb         = fields.Boolean(string='vers_solde_btn_vsb'        , compute='_get_btn_vsb', default=False, readonly=True)
    fld_vsb                    = fields.Boolean(string='Field Vsb'                 , compute='_get_btn_vsb', default=False, readonly=True)
    droit_actualise_vsb        = fields.Boolean(string='droit_actualise_vsb'       , compute='_get_btn_vsb', default=False, readonly=True)



class is_demande_conges_autre(models.Model):
    _name        = 'is.demande.conges.autre'
    _description="is_demande_conges_autre"

    name = fields.Char(string='Autre congé', required=True)



class is_demande_absence_type(models.Model):
    _name        = 'is.demande.absence.type'
    _description="is_demande_absence_type"

    name = fields.Char(string='Type', required=True)
    code = fields.Char(string='Code', help=u"Code sur 1 ou 2 caractères utilisé dans le calendrier des absences")

class is_demande_absence(models.Model):
    _name        = 'is.demande.absence'
    _description = u'Demande d’absence'
    _order       = 'name desc'


    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].get('is.demande.absence') or ''
        return super(is_demande_absence, self).create(vals)

    name          = fields.Char(u"N° demande", index=True)
    createur_id   = fields.Many2one('res.users', u'Créateur', default=lambda self: self.env.user)
    date_creation = fields.Datetime(string=u'Date de création', default=lambda *a: fields.datetime.now())
    type_absence  = fields.Many2one('is.demande.absence.type', string=u'Type d’absence', required=True)
    date_debut    = fields.Date(string='Date de début', required=True, index=True)
    date_fin      = fields.Date(string='Date de fin', required=True)
    employe_ids   = fields.Many2many('hr.employee', string=u'Employés', required=True)


class is_droit_conges(models.Model):
    _name        = 'is.droit.conges'
    _description = u'Droit aux congés'
    _order       = 'employe_id,name'

    name       = fields.Char(u"Type", required=True)
    nombre     = fields.Float(u"Nombre", digits=(14,2))
    employe_id = fields.Many2one('hr.employee', 'Employé', required=True, ondelete='cascade', readonly=False)



class is_demande_conges_export_cegid(models.Model):
    _name        = 'is.demande.conges.export.cegid'
    _description="is_demande_conges_export_cegid"

    name       = fields.Char(u"N°export")
    date_debut = fields.Date(string='Date de début', required=True, default=lambda self: self._date_debut())
    date_fin   = fields.Date(string='Date de fin'  , required=True, default=lambda self: self._date_fin())


    def _date_debut(self):
        now  = datetime.date.today()              # Ce jour
        j    = now.day                            # Numéro du jour dans le mois
        d    = now - datetime.timedelta(days=j)   # Dernier jour du mois précédent
        j    = d.day                              # Numéro jour mois précédent
        d    = d - datetime.timedelta(days=(j-1)) # Premier jour du mois précédent
        return d.strftime('%Y-%m-%d')


    def _date_fin(self):
        now  = datetime.date.today()            # Ce jour
        j    = now.day                          # Numéro du jour dans le mois
        d    = now - datetime.timedelta(days=j) # Dernier jour du mois précédent
        return d.strftime('%Y-%m-%d')


    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].get('is.demande.conges.export.cegid') or ''
        return super(is_demande_conges_export_cegid, self).create(vals)


    def get_employe(self,user):
        employes = self.env['hr.employee'].search([('user_id','=',user.id)])
        if employes:
            return employes[0]
        return False

    def fdate(self,date):
        d=datetime.datetime.strptime(date, '%Y-%m-%d')
        return d.strftime('%d/%m/%Y')


    def export_cegid_action(self):
        cr=self._cr
        for obj in self:
            filename='export-conges-dans-cegid-'+obj.name+'.txt'
            dest='/tmp/'+filename
            t1={
                'matin'     : u'Matin',
                'apres_midi': u'Apres-midi',
            }
            SQL= """
                SELECT
                    ru.login,
                    idc.name,
                    idc.date_debut,
                    idc.date_fin,
                    idc.le,
                    idc.type_demande,
                    idc.state,
                    idc.cp,
                    idc.rtt,
                    idc.rc,
                    idc.matin_ou_apres_midi
                FROM is_demande_conges idc inner join res_users ru on idc.demandeur_id=ru.id
                WHERE 
                    ((idc.date_debut>='"""+obj.date_debut+"""' and idc.date_debut<='"""+obj.date_fin+"""') or
                    (idc.le>='"""+obj.date_debut+"""' and idc.le<='"""+obj.date_fin+"""')) and
                    idc.type_demande not in ('autre','sans_solde') and
                    idc.state in ('solde','validation_rh') and
                    (idc.cp>0 or idc.rtt>0 or idc.rc>0)
                ORDER BY ru.login,idc.name
            """
            cr.execute(SQL)
            rows = cr.dictfetchall()
            f = codecs.open(dest,'wb',encoding='utf-8')
            annee = str(obj.date_debut)[:4]
            f.write('***DEBUT***\r\n')
            f.write('000	000000	01/01/'+annee+'	31/12/'+annee+'\r\n')
            for row in rows:
                login = (u'0000000000'+row['login'])[-10:]
                if row['type_demande'] in ['le','rc_heures','cp_rtt_demi_journee']:
                    date_debut = row['le']
                    date_fin   = row['le']
                else:
                    date_debut = row['date_debut']
                    date_fin   = row['date_fin']
                code      = u''
                nb_heures = nb_jours = 0
                comment   = u''
                if row['rc']>0:
                    nb_heures = row['rc']
                    nb_jours  = 0
                    code      = u'HRC'
                    comment   = u'Heures RC Pris '+self.fdate(date_debut)+u' au '+self.fdate(date_fin)

                if row['cp']>0:
                    nb_heures = row['cp']*7
                    nb_jours  = row['cp']
                    code      = u'PRI'
                    if row['type_demande']=='cp_rtt_demi_journee':
                        comment   = u'Conges payes '+self.fdate(date_debut)+u' '+t1[row['matin_ou_apres_midi']]
                    else:
                        comment   = u'Conges payes '+self.fdate(date_debut)+u' au '+self.fdate(date_fin)

                if row['rtt']>0:
                    nb_heures = row['rtt']*7
                    nb_jours  = row['rtt']
                    code      = u'RTT'
                    if row['type_demande']=='cp_rtt_demi_journee':
                        comment   = u'Jours ARTT Pris '+self.fdate(date_debut)+u' '+t1[row['matin_ou_apres_midi']]
                    else:
                        comment   = u'Jours ARTT Pris '+self.fdate(date_debut)+u' au '+self.fdate(date_fin)
                f.write(u'MAB\t')
                f.write(login+u'\t')
                f.write(self.fdate(date_debut)+u'\t')
                f.write(self.fdate(date_fin)+u'\t')
                f.write('{:07.2f}'.format(nb_jours)+u'\t')
                f.write('{:07.2f}'.format(nb_heures)+u'\t')
                f.write(code+u'\t')
                f.write(comment+u'\t\t\t\r\n')
            f.write(u'***FIN***\r\n')
            f.close()

            model='is.demande.conges.export.cegid'
            attachments = self.env['ir.attachment'].search([('res_model','=',model),('res_id','=',obj.id),('name','=',filename)])
            attachments.unlink()
            r = open(dest,'rb').read().encode('base64')
            vals = {
                'name':        filename,
                'datas_fname': filename,
                'type':        'binary',
                'res_model':   model,
                'res_id':      obj.id,
                'datas':       r,
            }
            id = self.env['ir.attachment'].create(vals)


