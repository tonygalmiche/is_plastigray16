# -*- coding: utf-8 -*-
from odoo import models,fields,api               # type: ignore
from odoo.exceptions import ValidationError      # type: ignore
from datetime import datetime, timedelta
from subprocess import PIPE, Popen
import pytz
import logging
_logger = logging.getLogger(__name__)


#TODO : 
#- Action plannifié la nuit


class is_gestion_portail(models.Model):
    _name='is.gestion.portail'
    _inherit=['mail.thread']
    _description="Gestion du portail"
    _order='ordre'

    name       = fields.Char("Description de l’horaire", help="ex : Le matin du lundi au vendredi", required=True, tracking=True)
    ordre      = fields.Integer("Ordre", default=0, help="Ordre de prise en compte. Le premier est pris en compte", tracking=True)
    date_debut = fields.Date("Date de début", tracking=True)
    date_fin   = fields.Date("Date de fin", tracking=True)
    date_ids   = fields.One2many('is.gestion.portail.date', 'gestion_id', "Dates ")
    dates      = fields.Text("Dates", store=True, compute='_compute_dates', tracking=True)
    jour_1     = fields.Boolean("Lundi"   , default=False, tracking=True)
    jour_2     = fields.Boolean("Mardi"   , default=False, tracking=True)
    jour_3     = fields.Boolean("Mercredi", default=False, tracking=True)
    jour_4     = fields.Boolean("Jeudi"   , default=False, tracking=True)
    jour_5     = fields.Boolean("Vendredi", default=False, tracking=True)
    jour_6     = fields.Boolean("Samedi"  , default=False, tracking=True)
    jour_7     = fields.Boolean("Dimanche", default=False, tracking=True)
    heure_ouverture = fields.Float("Heure d’ouverture" , required=True, tracking=True)
    heure_fermeture = fields.Float("Heure de fermeture", required=True, tracking=True)
    state = fields.Selection([
        ('ouvert'     , 'Ouvert'),
        ('ferme'      , 'Fermé'),
        ('indetermine', 'Indéterminé'),
    ], "État du portail", default="indetermine", tracking=True)
    calendar_ids = fields.One2many('is.gestion.portail.calendar', 'gestion_id', 'Calendar')


    @api.depends('date_ids','date_ids.name')
    def _compute_dates(self):
        for obj in self:
            dates=[]
            for line in obj.date_ids:
                if line.name:
                    dates.append(line.name.strftime('%d/%m/%Y'))
            dates = ', '.join(dates)
            obj.dates = dates


    def _utc_offset(self,date):
        offset = int(pytz.timezone('Europe/Paris').localize(date).utcoffset().total_seconds()/3600)
        return offset
 

    def _get_date_heure(self,date,heure):
        hour   = int(heure)
        minute = round(60*(heure - hour))
        date_heure = date.replace(hour=hour, minute=minute)
        offset = self._utc_offset(date_heure)
        date_heure = date_heure -  timedelta(hours=offset) 
        return date_heure


    def actualiser_action(self):
        #** Renuméroter les lignes ********************************************
        lines = self.env['is.gestion.portail'].search([],order="ordre,id")
        ordre=10
        for line in lines:
            line.ordre = ordre
            ordre+=10
        #**********************************************************************

        self.env['is.gestion.portail.calendar'].search([('gestion_id','!=',False)]).unlink()
        lines = self.env['is.gestion.portail'].search([],order="ordre,id")
        date=datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        #Pour chaque jour rechercher la première ligne correspondante
        for i in range(0,100):
            jour_semaine = date.weekday()+1 # Jour de la semaine entre 1 et 7
            test=False
            heure_ouverture = heure_fermeture = False
            for line in lines:
                field_name="jour_%s"%jour_semaine
                jour_coche = getattr(line, field_name)

                #** Si le jour est coché, test date début et fin **************
                if jour_coche:
                    if not test and not line.date_debut and not line.date_fin:
                        test=True
                    if not test and line.date_debut and line.date_debut<=date.date() and not line.date_fin:
                        test=True
                    if not test and not line.date_debut and line.date_fin and line.date_fin>=date.date():
                        test=True
                    if not test and line.date_debut and line.date_debut<=date.date()  and line.date_fin and line.date_fin>=date.date():
                        test=True
                #**************************************************************

                #** Liste de dates ********************************************
                if not test:
                    for line_date in line.date_ids:
                        if line_date.name==date.date():
                            test=True
                #**************************************************************

                if test:
                    date_debut = self._get_date_heure(date,line.heure_ouverture)
                    date_fin   = self._get_date_heure(date,line.heure_fermeture)
                    vals={
                        'gestion_id': line.id,
                        'date_debut': date_debut,
                        'date_fin'  : date_fin,
                    }
                    self.env['is.gestion.portail.calendar'].create(vals)
                    break
            date = date + timedelta(days=1)
        now = datetime.now(pytz.timezone('Europe/Paris')).strftime('%H:%M:%S')
        return {
            'name': u'Agenda actualisé à '+str(now),
            'view_mode': 'calendar,tree,form',
            'res_model': 'is.gestion.portail.calendar',
            'type': 'ir.actions.act_window',
        }


    def gestion_portail(self, param):
        name='gestion-portail'
        cdes = self.env['is.commande.externe'].search([('name','=',name)])
        if (len(cdes)==0):
            raise ValidationError("Commande externe '%s' non trouvée"%name)
        res=''
        for cde in cdes:
            cmd = cde.commande.replace("#param", param)
            p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
            stdout, stderr = p.communicate()
            res=stdout.decode("utf-8").strip()
            _logger.info("%s => %s"%(cmd,res))
            if stderr:
                raise ValidationError("Erreur dans commande externe '%s' => %s"%(cmd,stderr.decode("utf-8")))
        if res in ('indetermine','ouvert','ferme'):
            self.state=res
        else:
            raise ValidationError("La réponse de la commande doit-être 'indetermine','ouvert' ou 'ferme' : '%s' => %s"%(cmd,res))


    def etat_portail_action(self):
        for obj in self:
            obj.gestion_portail('etat')
            

    def ouvrir_portail_action(self):
        for obj in self:
            obj.gestion_portail('ouvrir')


    def fermer_portail_action(self):
        for obj in self:
            obj.gestion_portail('fermer')


class is_gestion_portail_date(models.Model):
    _name='is.gestion.portail.date'
    _description="Gestion du portail - Dates"
    _order='name'

    gestion_id = fields.Many2one('is.gestion.portail', 'Gestion portail', required=True, ondelete="cascade")
    name       = fields.Date("Date")


class is_gestion_portail_calendar(models.Model):
    _name='is.gestion.portail.calendar'
    _description="Gestion du portail - Calendar"
    _order='date_debut'
    _rec_name = 'gestion_id'


    # move_id                = fields.Many2one('account.move', 'Facture', required=True, ondelete="cascade")

    gestion_id = fields.Many2one('is.gestion.portail', 'Gestion portail', ondelete="cascade")
    date_debut = fields.Datetime("Date de début", required=True)
    date_fin   = fields.Datetime("Date de fin", required=True)
