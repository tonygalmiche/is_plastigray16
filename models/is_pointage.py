# -*- coding: utf-8 -*-

from odoo import models,fields,api,tools
from datetime import datetime
from dateutil.relativedelta import relativedelta 
import time
import pytz
from pytz import timezone


def utc2local(d):
    utc = pytz.utc
    d1=datetime.strptime(d, '%Y-%m-%d %H:%M:%S').replace(tzinfo=utc)
    europe = timezone('Europe/Paris')
    d2 = d1.astimezone(europe)
    d3=d2.strftime('%d/%m/%Y %H:%M:%S')
    return unicode(d3)


class is_badge(models.Model):
    _name='is.badge'
    _description="Badge"
    _order='employee'

    _sql_constraints = [('name_uniq','UNIQUE(name)', u'Ce badge existe déjà')]

    name       = fields.Char(u"Code",size=20,required=True, index=True)
    employee   = fields.Many2one('hr.employee', u'Employé', required=False, ondelete='set null', help=u"Sélectionnez un employé")
    code_theia = fields.Char(u"Code Lecteur RFID THEIA",size=20, index=True)
    nom_odalid = fields.Char(u"Nom ODALID", help=u"Pour faire la correspondance entre Odoo et Odalid")


class is_jour_ferie(models.Model):
    _name='is.jour.ferie'
    _description="Jout férié"
    _order='date'

    name      = fields.Char("Intitulé",size=100,help='Intitulé du jour férié (ex : Pâques)', required=True, index=True)
    date      = fields.Date("Date",required=True)
    jour_fixe = fields.Boolean('jour férié fixe',  help="Cocher pour préciser que ce jour férié est valable tous les ans")


    def get_jours_feries(self, ladate=False):
        dates=[]
        if ladate:
            year = ladate.year
        else:
            year = datetime.today().year
        lines = self.env['is.jour.ferie'].search([])
        for line in lines:
            ladate = line.date
            if line.jour_fixe:
                nb_years = year-line.date.year
                ladate = line.date + relativedelta(years=nb_years) 
            if ladate not in dates:
                dates.append(ladate)
        return dates


class is_pointage_commentaire(models.Model):
    _name='is.pointage.commentaire'
    _description="Commentaires des pointages"
    _order='name desc'

    name        = fields.Date("Date",required=True, default=lambda *a: fields.datetime.now())
    employee    = fields.Many2one('hr.employee', 'Employé', required=True, help="Sélectionnez un employé", index=True) #, ondelete='set null'
    commentaire = fields.Char('Commentaire', help="Mettre un commentaire court sur 40 caractères maximum") # , size=40
    demande_conges_id = fields.Many2one('is.demande.conges', 'Demande de congé')


class is_pointage(models.Model):
    _name='is.pointage'
    _description="Pointage"
    _order='name desc'

    name=fields.Datetime("Date Heure",required=True) #, default=lambda *a: time
    employee=fields.Many2one('hr.employee', 'Employé', required=True, help="Sélectionnez un employé", index=True) #, ondelete='set null'
    entree_sortie=fields.Selection([("E", "Entrée"), ("S", "Sortie")], "Entrée/Sortie", required=True)
    pointeuse=fields.Char('Pointeuse', help='Adresse IP du lecteur de badges', required=False)
    note=fields.Char('Commentaire', size=20, help="Mettre un commentaire court sur 20 caractères maximum")
    commentaire=fields.Text('Traçabilité')


    def id2employee(self):
        employee_obj = self.env['hr.employee']
        employee = employee_obj.browse(cr, uid, id)
        return employee.name


    # def write(self, vals):
    #     print(vals)
        # now = datetime.now(timezone('Europe/Berlin'))
        # user_obj = self.pool.get('res.users')
        # user = user_obj.browse(cr, uid, uid, context=context)
        # this = self.pool.get(str(self))
        # doc = this.browse(cr, uid, ids, context=context)
        # commentaire=[]
        # n=unicode(now.strftime('%d/%m/%Y'))+u" à "+unicode(now.strftime('%H:%M:%S'))
        # if 'name' in vals:
        #     d1=utc2local(doc.name)
        #     d2=utc2local(vals["name"])
        #     commentaire.append(u"le " + n + u" par " + user.name + u" : Date Heure " + d1 + u" => " + d2)
        # if 'employee' in vals:
        #     e1=doc.employee.name
        #     e2=self.id2employee(cr, uid, vals["employee"])
        #     commentaire.append(u"le " + n + u" par " + user.name + u" : Employé " + e1 + u" => " + e2)
        # if 'entree_sortie' in vals:
        #     es1=doc.entree_sortie
        #     es2=vals["entree_sortie"]
        #     commentaire.append(u"le " + n + u" par " + user.name + u" : Entrée/Sortie " + es1 + u" => " + es2)
        # if 'name' in vals or 'employee' in vals or 'entree_sortie' in vals :
        #     if doc.commentaire:
        #         commentaire.append(doc.commentaire)
        #     vals.update({'commentaire': '\n'.join(commentaire)})
        # return super(is_pointage, self).write(cr, uid, ids, vals, context=context)


