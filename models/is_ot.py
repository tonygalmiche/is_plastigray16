# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import datetime
from collections import defaultdict
from collections import OrderedDict
#from openerp import SUPERUSER_ID
#from lxml import etree


_NATURE=[
    ('preventif', u"Préventif"),
    ('curatif', "Curatif"),
    ('amelioratif', u"Amélioratif"),
    ('securite', u"Sécurité"),
    ('predictif', u"Prédictif"),
    ('changement_de_version', "Changement de version"),
]


class is_ot_affectation(models.Model):
    _name = 'is.ot.affectation'
    _description="is_ot_affectation"

    name = fields.Char("Affectation", required=True)


class is_ot_temps_passe(models.Model):
    _name = 'is.ot.temps.passe'
    _description="is_ot_temps_passe"

    technicien_id = fields.Many2one("res.users", "Nom du technicien", default=lambda self: self.env.uid)
    descriptif    = fields.Text("Descriptif des travaux")
    temps_passe   = fields.Float(u"Temps passé", digits=(14, 2))
    ot_id         = fields.Many2one("is.ot", "OT")


class is_ot(models.Model):
    _name = 'is.ot'
    _inherit=['mail.thread']
    _description="is_ot"
    _order = 'name desc'


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('is.ot')
            count = 0
            if vals and vals.get('equipement_id'):
                count += 1
            if vals and vals.get('moule_id'):
                count += 1
            if vals and vals.get('dossierf_id'):
                count += 1
            if vals and vals.get('gabarit_id'):
                count += 1
            if vals and vals.get('instrument_id'):
                count += 1
            if count == 0 or count > 1:
                msg="Il est obligatoire de saisir un équipement, un moule, un dossier F, un gabarit ou un instrument (un seul choix possible)"
                raise ValidationError(msg)
        return super().create(vals_list)


    # def create(self, vals):
    #     if self._uid:
    #         user_data = self.env['res.users'].browse(self._uid)
    #         if user_data and not user_data.is_site_id:
    #             raise except_orm(_('Configuration!'),
    #                          _("Site must be filled in its user form"))
    #     return super(is_ot, self).create(vals)


    def write(self, vals):
        for data in self:
            if data.state == 'travaux_a_valider':
                vals['valideur_id'] = self._uid
        res = super(is_ot, self).write(vals)
        for data in self:
            if data.state == 'analyse_ot' and data.validation_ot == 'oui':
                data.state="travaux_a_realiser"
            if data.state == 'analyse_ot' and data.validation_ot == 'non':
                #data.state="annule"
                data.action_annule()
            if data.state == 'travaux_a_valider' and data.validation_travaux == 'non_ok':
                data.state="analyse_ot"
            if data.state == 'travaux_a_valider' and data.validation_travaux == 'ok':
                data.state="termine"
            count = 0
            if data.equipement_id:
                count += 1
            if data.moule_id:
                count += 1
            if data.dossierf_id:
                count += 1
            if data.gabarit_id:
                count += 1
            if data.instrument_id:
                count += 1
            if count == 0 or count > 1:
                msg="Il est obligatoire de saisir un équipement, un moule, un dossier F, un gabarit ou un instrument (un seul choix possible)"
                raise ValidationError(msg)
        return res


    def vers_travaux_a_realiser(self):
        for obj in self:
            obj.state='travaux_a_realiser'


    def vers_travaux_a_valider(self):
        for obj in self:
            if not obj.date_realisation_travaux:
                obj.date_realisation_travaux = datetime.datetime.today()
            obj.validation_travaux=False
            obj.state="travaux_a_valider"


    def vers_analyse_ot(self):
        for obj in self:
            obj.state="analyse_ot"
        return True


    def envoi_mail(self, email_from, email_to, subject, body_html):
        for obj in self:
            if email_to=="robot@plastigray.com":
                email_to = email_from
            if email_to and email_to!='robot@plastigray.com':
                vals = {
                    'email_from'    : email_from,
                    'email_to'      : email_to,
                    'email_cc'      : email_from,
                    'subject'       : subject,
                    'body_html'     : body_html,
                }
                email = self.env['mail.mail'].create(vals)
                if email:
                    self.env['mail.mail'].send(email)

    def action_annule(self):
        for obj in self:
            if obj.demandeur_id.id!=1:
                subject = u'[' + obj.name + u'] Gestion des OT - Annule'
                user = self.env['res.users'].browse(self._uid)
                email_from = user.email
                nom = user.name
                email_to = obj.demandeur_id.email
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = base_url + u'/web#id=' + str(obj.id) + u'&view_type=form&model=is.ot'
                body_html = u""" 
                    <p>Bonjour,</p> 
                    <p>""" + nom + """ vient de passer la getion des ot <a href='""" + url + """'>""" + obj.name + """</a> à l'état 'Annule'.</p> 
                    <p>Merci d'en prendre connaissance.</p> 
                """ 
                self.envoi_mail(email_from, email_to, subject, body_html)
            obj.state="annule"


    def pj_action(self):
        for obj in self:
            attachments = self.env['ir.attachment'].search([('res_model','=',self._name),('res_id','=',obj.id)])
            if len(attachments):
                return {
                    'type' : 'ir.actions.act_url',
                    'url': '/web/content/%s?download=true'%(attachments[0].id),
                }


    # def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
    #     if context is None:context = {}
    #     res = super(is_ot, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=False)
    #     if view_type != 'form':
    #         return res
    #     if uid != 1:
    #         return res
    #     doc = etree.XML(res['arch'])
    #     for node in doc.xpath("//field[@name='state']"):
    #         node.set('clickable', "True")
    #     res['arch'] = etree.tostring(doc)
    #     return res


    def default_get(self, default_fields):
        res = super(is_ot, self).default_get(default_fields)
        if self._uid:
            user_data = self.env['res.users'].browse(self._uid)
            if user_data and user_data.is_site_id:
                res['site_id'] = user_data.is_site_id.id
        return res


    @api.depends('gravite')
    def _compute_gravite(self):
        for obj in self:
            obj.code_gravite = obj.gravite


    @api.depends('equipement_id','moule_id')
    def _compute_emplacement(self):
        for obj in self:
            emplacement=''
            if obj.equipement_id:
                emplacement = obj.equipement_id.emplacement_affectation_pe
            if obj.moule_id:
                emplacement = obj.moule_id.emplacement
            obj.emplacement = emplacement

    def _compute_pj(self):
        for obj in self:
            attachments = self.env['ir.attachment'].search([('res_model','=',self._name),('res_id','=',obj.id)])
            pj=False
            if attachments:
                pj=True
            obj.pj=pj


    @api.depends('temps_passe_ids')
    def _compute_temps_passe_total(self):
        for obj in self:
            temps_passe_total = 0
            for line in obj.temps_passe_ids:
                temps_passe_total+=line.temps_passe
            obj.temps_passe_total = temps_passe_total

    name                = fields.Char(u"N° de l'OT")
    state               = fields.Selection([
            ('creation', u'Création'),
            ('analyse_ot', u"Analyse de l'OT"),
            ('travaux_a_realiser', u'Travaux à réaliser'),
            ('travaux_a_valider', u'Travaux à valider'),
            ('annule', u'Annulé'),
            ('termine', u'Terminé'),
            ], "Etat", readonly=True, default="creation")
    site_id             = fields.Many2one("is.database", "Site", required=True)
    emplacement         = fields.Char("Emplacement", store=True, readonly=True, compute='_compute_emplacement')
    date_creation       = fields.Date(u"Date de création", copy=False, default=fields.Date.context_today, readonly=True)
    demandeur_id        = fields.Many2one("res.users", "Demandeur", default=lambda self: self.env.uid, readonly=True)
    type_equipement_id  = fields.Many2one("is.equipement.type", u"Type d'équipement")
    equipement_id       = fields.Many2one("is.equipement", "Équipement")
    moule_id            = fields.Many2one("is.mold", "Moule")
    dossierf_id         = fields.Many2one("is.dossierf", "Dossier F")
    gabarit_id          = fields.Many2one("is.gabarit.controle", u"Gabarit de Contrôle")
    instrument_id       = fields.Many2one("is.instrument.mesure", u"Instrument de mesure")
    gravite             = fields.Selection([
            ('1', u"1-risque de rupture client suite panne moule/machine ; risque pour outillage ou équipement ; risque sécurité ; risque environnemental"),
            ('2', u"2-moule ou équipement en production mais en mode dégradé / moule en cours de développement (sans risque avéré)"),
            ('3', u"3-action d'amélioration ou de modification sans impact sur la qualité ou le dimmensionnel du produit"),
            ], u"Gravité", required=True)
    code_gravite        = fields.Char(u"Code Gravité",help="Code gravité", store=True, readonly=True, compute='_compute_gravite')
    date_intervention_demandee = fields.Date(u"Date intervention demandée", copy=False)
    numero_qrci         = fields.Char(u"Numéro de QRCI/TPM")
    descriptif          = fields.Text('Descriptif')
    complement          = fields.Text(u"Complément d'information")
    nature              = fields.Selection(_NATURE, "Nature")
    affectation_id                   = fields.Many2one("is.ot.affectation", "Affectation")
    delai_previsionnel               = fields.Float(u"Temps d'intervention prévisionnel (H)", digits=(14, 2))
    date_previsionnelle_intervention = fields.Date(u"Date prévisionnelle d'intervention", copy=False)
    date_realisation_travaux         = fields.Date(u"Date de réalisation des travaux", copy=False)
    validation_ot       = fields.Selection([
            ("non", "Non"),
            ("oui", "Oui"),
        ], "Travaux à réaliser")
    motif               = fields.Char("Motif")
    temps_passe_ids     = fields.One2many('is.ot.temps.passe', 'ot_id', u"Temps passé")
    temps_passe_total   = fields.Float(u"Temps passé total", digits=(14, 2), store=True, readonly=True, compute='_compute_temps_passe_total')
    valideur_id         = fields.Many2one("res.users", "Valideur")
    validation_travaux  = fields.Selection([
            ("ok", "Ok"),
            ("non_ok", "Non Ok"),
        ], "Validation travaux")
    nouveau_delai       = fields.Date(u"Nouveau délai")
    commentaires_non_ok = fields.Text("Commentaire")
    pj                  = fields.Boolean(u"Pièce jointe", store=False, readonly=True, compute='_compute_pj')



class is_ot_indicateur(models.Model):
    _name = 'is.ot.indicateur'
    _description="is_ot_indicateur"
    _rec_name = "date_debut"
    _order = 'id desc'


    site_id              = fields.Many2one("is.database")
    date_debut           = fields.Date("Date de début", required=True)
    date_fin             = fields.Date("Date de fin"  , required=True)
    nb_heures_technicien = fields.Boolean(u"Nombre d'heures par technicien", default=True)
    nb_heures_nature     = fields.Boolean(u"Nombre d'heures par nature"    , default=True)
    nb_heures_equipement = fields.Boolean(u"Nombre d'heures par équipement", default=True)


    def default_get(self, default_fields):
        res = super(is_ot_indicateur, self).default_get(default_fields)
        if self._uid:
            user_data = self.env['res.users'].browse(self._uid)
            if user_data and user_data.is_site_id:
                res['site_id'] = user_data.is_site_id.id
        return res


    def get_nb_heures_technicien(self):
        """Nombre d'heures par technicien"""
        cr = self._cr
        r=[]
        for obj in self:
            SQL="""
                SELECT rp.name, sum(temps_passe)
                FROM is_ot io inner join is_ot_temps_passe iotp on io.id=iotp.ot_id 
                              inner join res_users ru on iotp.technicien_id=ru.id
                              inner join res_partner rp on ru.partner_id=rp.id
                WHERE 
                    io.site_id="""+str(obj.site_id.id)+""" and
                    io.date_realisation_travaux>='"""+str(obj.date_debut)+"""' and
                    io.date_realisation_travaux<='"""+str(obj.date_fin)+"""' and
                    io.state in ('termine','travaux_a_valider') 
                GROUP BY rp.name
                ORDER BY rp.name
            """
            cr.execute(SQL)
            res = cr.fetchall()
            for row in res:
                r.append(row)
        return r


    def get_nb_heures_nature(self):
        """Nombre d'heures par nature"""
        cr = self._cr
        r=[]
        for obj in self:
            SQL="""
                SELECT io.nature, sum(temps_passe)
                FROM is_ot io inner join is_ot_temps_passe iotp on io.id=iotp.ot_id 
                              inner join res_users ru on iotp.technicien_id=ru.id
                              inner join res_partner rp on ru.partner_id=rp.id
                WHERE 
                    io.site_id="""+str(obj.site_id.id)+""" and
                    io.date_realisation_travaux>='"""+str(obj.date_debut)+"""' and
                    io.date_realisation_travaux<='"""+str(obj.date_fin)+"""' and 
                    io.state in ('termine','travaux_a_valider') 
                GROUP BY io.nature
                ORDER BY io.nature
            """
            cr.execute(SQL)
            res = cr.fetchall()
            for row in res:
                nature=row[0]
                for l in _NATURE:
                    if l[0]==row[0]:
                        nature=l[1]
                line=[nature,row[1]]
                r.append(line)
        return r



    def get_natures(self):
        """Liste des natures"""
        return _NATURE


    def get_nb_heures(self,type_equipement,affiche_total,affiche_pourcentage):
        """Nombre d'heures par equipement et par nature"""
        cr = self._cr
        r={}
        for obj in self:
            if type_equipement=='equipement' or type_equipement=='batiment' or type_equipement=='presse':
                SQL="""
                    SELECT iet.name, io.nature, sum(temps_passe)
                    FROM is_ot io inner join is_ot_temps_passe iotp on io.id=iotp.ot_id 
                                  inner join res_users ru on iotp.technicien_id=ru.id
                                  inner join res_partner rp on ru.partner_id=rp.id
                                  inner join is_equipement_type iet on io.type_equipement_id=iet.id
                    WHERE 
                        io.site_id="""+str(obj.site_id.id)+""" and
                        io.date_realisation_travaux>='"""+str(obj.date_debut)+"""' and
                        io.date_realisation_travaux<='"""+str(obj.date_fin)+"""' and 
                        io.state in ('termine','travaux_a_valider')
                """
                if type_equipement=='equipement':
                    SQL+=" and iet.code not in ('BATIMENT','PE') "

                if type_equipement=='batiment':
                    SQL+=" and iet.code='BATIMENT' "

                if type_equipement=='presse':
                    SQL+=" and iet.code='PE' "
                SQL+="""
                    GROUP BY iet.name, io.nature
                    ORDER BY iet.name, io.nature
                """

            if type_equipement=='moule':
                SQL="""
                    SELECT 'Moule', io.nature, sum(temps_passe)
                    FROM is_ot io inner join is_ot_temps_passe iotp on io.id=iotp.ot_id 
                                  inner join res_users ru on iotp.technicien_id=ru.id
                                  inner join res_partner rp on ru.partner_id=rp.id
                                  inner join is_mold im on io.moule_id=im.id
                    WHERE 
                        io.site_id="""+str(obj.site_id.id)+""" and
                        io.date_realisation_travaux>='"""+str(obj.date_debut)+"""' and
                        io.date_realisation_travaux<='"""+str(obj.date_fin)+"""' and 
                        io.state in ('termine','travaux_a_valider') 
                    GROUP BY io.nature
                    ORDER BY io.nature
                """

            if type_equipement=='dossierf':
                SQL="""
                    SELECT 'Dossier F', io.nature, sum(temps_passe)
                    FROM is_ot io inner join is_ot_temps_passe iotp on io.id=iotp.ot_id 
                                  inner join res_users ru on iotp.technicien_id=ru.id
                                  inner join res_partner rp on ru.partner_id=rp.id
                                  inner join is_dossierf id on io.dossierf_id=id.id
                    WHERE 
                        io.site_id="""+str(obj.site_id.id)+""" and
                        io.date_realisation_travaux>='"""+str(obj.date_debut)+"""' and
                        io.date_realisation_travaux<='"""+str(obj.date_fin)+"""' and 
                        io.state in ('termine','travaux_a_valider') 
                    GROUP BY io.nature
                    ORDER BY io.nature
                """

            cr.execute(SQL)
            res = cr.fetchall()
            for row in res:
                equipement = row[0]
                nature     = row[1]
                if equipement not in r:
                    r[equipement]={}
                r[equipement][nature] = row[2]
        ro = OrderedDict(sorted(r.items()))

        #** Calcul des totaux **************************************************
        total={}
        total_general=0
        for line in ro:
            for n in _NATURE:
                nature = n[0]
                tps = ro[line].get(nature,'')
                if nature not in total:
                    total[nature] = 0
                if tps!='':
                    total[nature]+=tps
                    total_general+=tps
        #***********************************************************************


        #** Résultat HTML ******************************************************
        res=[]
        for line in ro:
            tr='<tr><td style="text-align:left">'+line+'</td>'
            total_ligne=0
            curatif = 0
            for n in _NATURE:
                nature = n[0]
                tps = ro[line].get(nature,'')
                if tps!='':
                    x='%.2f'%tps
                else:
                    x=''
                tr+='<td>'+x+'</td>'
                if tps!='':
                    total_ligne+=tps
                    if nature == 'curatif':
                        curatif+=tps
            pourcent=''
            if total_general>0:
                pourcent=round(100*total_ligne/total_general,1);
            tr+='<td style="text-align:right"><b>'+'%.2f'%total_ligne+'</b></td>'
            if affiche_total:
                tr+='<td style="text-align:right"><b>'+'%.1f'%pourcent+'%</b></td>'
            pourcentage_preventif = 0
            if total_ligne>0:
                pourcentage_preventif = 100*(1 - curatif / total_ligne)
                tr+='<td style="text-align:right"><b>'+'%.1f'%pourcentage_preventif+'%</b></td>'
            tr+='</tr>'
            res.append(tr)

        if affiche_total and res:
            tr='<tr><th style="text-align:left">Total : </th>'
            curatif = 0
            for n in _NATURE:
                nature = n[0]
                tps=total.get(nature,0)
                if nature == 'curatif':
                    curatif=tps
                tr+='<th>'+str(tps)+'</th>'
            tr+='<th>'+str(round(total_general,1))+'</th>'
            tr+='<th>100%</th>'
            pourcentage_preventif = 0
            if total_general>0:
                pourcentage_preventif = 100*(1 - curatif / total_general)
            tr+='<th>'+'%.1f'%pourcentage_preventif+'%</th>'
            tr+='</tr>'
            res.append(tr)

        if affiche_pourcentage and res:
            tr='<tr><td style="text-align:left"></td>'
            for n in _NATURE:
                nature = n[0]
                tps=total.get(nature,0)
                pourcent=0
                if total_general>0:
                    pourcent=round(100*tps/total_general,1);
                tr+='<td>'+str(pourcent)+'%</td>'
            tr+='<td></td>'
            if affiche_total:
                tr+='<td></td>'
                tr+='<td></td>'
            tr+='</tr>'
            res.append(tr)
        return res
        #***********************************************************************




