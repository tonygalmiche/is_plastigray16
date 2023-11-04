# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools
from odoo.exceptions import ValidationError
import time
from datetime import date,datetime,timedelta
import base64
import os
#from pyPdf import PdfFileWriter, PdfFileReader
#from PyPDF2 import PdfFileWriter, PdfFileReader, PdfFileMerger
from shutil import copy
import magic


#                data_dir=odoo.tools.config['data_dir']


TYPE_PREVENTIF_EQUIPEMENT = [
    ('niveau2'       , u'Niveau 2'),
    ('niveau3'       , u'Niveau 3'),
    ('plastification', u'Plastification'),
    ('constructeur'  , u'Constructeur'),
]


class is_preventif_equipement_zone(models.Model):
    _name = 'is.preventif.equipement.zone'
    _description="is_preventif_equipement_zone"
    _order = "name"

    def pgcd(self,a,b):
        """pgcd(a,b): calcul du 'Plus Grand Commun Diviseur' entre les 2 nombres entiers a et b"""
        while b!=0:
            a,b=b,a%b
        return a

    def pgcdn(self,n):
        """Calcul du 'Plus Grand Commun Diviseur' de n valeurs entières (Euclide)"""
        if len(n)==0:
            return 0
        if len(n)==1:
            return n[0]
        p = self.pgcd(n[0], n[1])
        for x in n[2:]:
            p = self.pgcd(p, x)
        return p

    @api.depends('preventif_ids')
    def _compute_frequence(self):
        for obj in self:
            frequences = []
            try:
                for line in obj.preventif_ids:
                    if line.frequence>0:
                        frequences.append(line.frequence)
            except:
                print("## BUG ###")
            pgcdn = self.pgcdn(frequences)
            obj.frequence = pgcdn

    name                 = fields.Char(u"Nom de la zone", required=True, index=True)
    description          = fields.Text(u"Description de la zone")
    equipement_ids       = fields.One2many('is.equipement', 'zone_id', u"Equipements de cette zone")
    equipement_pilote_id = fields.Many2one('is.equipement', u"Equipement pilote du préventif")
    preventif_ids        = fields.One2many('is.preventif.equipement', 'zone_id', u"Préventifs")
    frequence            = fields.Integer(u"Fréquence préventif zone (H)", compute='_compute_frequence', store=True, readonly=True)
    active               = fields.Boolean(u"Active", default=True)


    def imprimer_gammes_action(self):
        uid=self._uid
        for obj in self:
            db = self._cr.dbname
            path="/tmp/gamme_preventif-" + str(uid)
            cde="rm -Rf " + path
            os.popen(cde).readlines()
            if not os.path.exists(path):
                os.makedirs(path)
            paths=[]

            # ** Ajout du rapport *********************************************
            #result = self.env['report'].get_pdf(obj, 'is_plastigray16.preventif_equipement_zone_report')
            result = self.env['ir.actions.report']._render_qweb_pdf('is_plastigray16.preventif_equipement_zone_report',[obj.id])[0]
            file_name = path + '/zone.pdf'
            fd = os.open(file_name,os.O_RDWR|os.O_CREAT)
            try:
                os.write(fd, result)
            finally:
                os.close(fd)
            paths.append(file_name)
            #******************************************************************

            # ** Ajout des gammes *********************************************
            #filestore = os.environ.get('HOME')+"/.local/share/Odoo/filestore/"+db+"/"
            data_dir=tools.config['data_dir']
            filestore = "%s/filestore/%s/"%(data_dir,db)
            for line in obj.preventif_ids:
                if line.nb_heures_avant_preventif<=0:
                    for gamme in line.gamme_ids:
                        src = filestore+gamme.store_fname
                        dst = path+"/"+str(gamme.id)+".pdf"
                        filetype = magic.from_file(src, mime=True)
                        if filetype=="application/pdf":
                            copy(src, dst)
                            paths.append(dst)
            # ******************************************************************

            # ** Merge des PDF *************************************************
            try:
                path_merged=self.env['stock.picking']._merge_pdf(paths)
            except:
                raise ValidationError("Impossible de générer le PDF => Les gammes doivent être au format PDF")
            #pdfs = open(path_merged,'rb').read().encode('base64')
            pdfs = open(path_merged,'rb').read()
            # ******************************************************************

            # ** Recherche si une pièce jointe est déja associèe ***************
            attachment_obj = self.env['ir.attachment']
            name = 'zone.pdf'
            attachments = attachment_obj.search([('name','=',name)],limit=1)
            # ******************************************************************

            # ** Creation ou modification de la pièce jointe *******************
            vals = {
                'name':        name,
                #'datas_fname': name,
                'type':        'binary',
                #'datas':       pdfs,
                'datas':       base64.b64encode(pdfs),
            }
            if attachments:
                for attachment in attachments:
                    attachment.write(vals)
                    attachment_id=attachment.id
            else:
                attachment = attachment_obj.create(vals)
                attachment_id=attachment.id
            #******************************************************************

            #** Envoi du PDF mergé dans le navigateur *************************
            if attachment_id:
                return {
                    'type' : 'ir.actions.act_url',
                    'url': '/web/content/%s?download=true'%(attachment_id),
                    #'url': '/web/binary/saveas?model=ir.attachment&field=datas&id='+str(attachment_id)+'&filename_field=name',
                    #'target': 'new',
                }
            #******************************************************************


class is_preventif_equipement_heure(models.Model):
    _name = 'is.preventif.equipement.heure'
    _description = u"Nombre d'heures par équipement et par mois"
    _order = "mois desc, equipement_id"

    soc            = fields.Integer(u"Société"                     , required=True, index=True)
    equipement_id  = fields.Many2one('is.equipement', u"Equipement", required=True, index=True)
    mois           = fields.Char(u"Mois"                           , required=True, index=True)
    nb_heures      = fields.Integer(u"Nb heures")


class is_preventif_equipement(models.Model):
    _name = 'is.preventif.equipement'
    _description="is_preventif_equipement"
    _order = "zone_id, equipement_id, type_preventif"
    _sql_constraints = [('name_uniq','UNIQUE(equipement_id,type_preventif)', u'Ce type de préventif existe déjà pour cet équipement')]


    @api.depends('equipement_id')
    def _compute(self):
        for obj in self:
            obj.zone_id = obj.equipement_id.zone_id.id


    @api.depends('date_dernier_preventif','frequence','frequence_semaine')
    def _compute_date_prochain_preventif(self):
        for obj in self:
            date_prochain_preventif = False
            nb_heures_avant_preventif = obj.nb_heures_avant_preventif
            if obj.date_dernier_preventif and obj.frequence_semaine:
                d =  obj.date_dernier_preventif
                date_prochain_preventif = d + timedelta(days=obj.frequence_semaine*7)
                if not obj.frequence:
                    now = datetime.now()
                    nb  = (date_prochain_preventif - now).days*8
                    nb_heures_avant_preventif = nb
            obj.nb_heures_avant_preventif = nb_heures_avant_preventif
            obj.date_prochain_preventif = date_prochain_preventif

    zone_id                     = fields.Many2one('is.preventif.equipement.zone', u"Zone", ondelete='cascade', readonly=True, compute="_compute", store=True)
    equipement_id               = fields.Many2one('is.equipement', u"Equipement",required=True)
    type_preventif              = fields.Selection(TYPE_PREVENTIF_EQUIPEMENT, u"Type de préventif",required=True)
    frequence                   = fields.Integer(u"Fréquence préventif (Heure)"  , help="Dans ce cas le préventif se base sur le temps réellement pas passé dans THEIA")
    frequence_semaine           = fields.Integer(u"Fréquence préventif (Semaine)", help="Dans ce cas le préventif se base sur la date du dernier préventif")
    date_dernier_preventif      = fields.Date(u"Date du dernier préventif"       , readonly=True)
    date_prochain_preventif      = fields.Date(u"Date du prochain préventif"     , compute='_compute_date_prochain_preventif', store=True, readonly=True)
    nb_heures_dernier_preventif = fields.Integer(u"Nb heures dernier préventif"  , readonly=True)
    nb_heures_actuel            = fields.Integer(u"Nb heures actuel"             , readonly=True)
    nb_heures_avant_preventif   = fields.Integer(u"Nb heures avant préventif"    , compute='_compute_date_prochain_preventif', store=True, readonly=True)
    gamme_ids                   = fields.Many2many('ir.attachment', 'is_preventif_equipement_gamme_rel', 'preventif_id', 'gamme_id', u'Gamme')

    def saisie_preventif_action(self):
        for obj in self:
            context = dict(self.env.context or {})
            context['equipement_id']  = obj.equipement_id.id
            context['type_preventif'] = obj.type_preventif
            return {
                'name': u"Saisie préventif équipement",
                'view_mode': 'form',
                'res_model': 'is.preventif.equipement.saisie',
                'type': 'ir.actions.act_window',
                'domain': '[]',
                'context': context,
            }
        return True


class is_preventif_equipement_saisie(models.Model):
    _name = 'is.preventif.equipement.saisie'
    _description="is_preventif_equipement_saisie"
    _rec_name = 'equipement_id'
    _order = 'date_preventif desc,equipement_id'

    def default_get(self, default_fields):
        res = super(is_preventif_equipement_saisie, self).default_get(default_fields)
        if self._context and self._context.get('equipement_id'):
            res['equipement_id'] = self._context.get('equipement_id')
        if self._context and self._context.get('type_preventif'):
            res['type_preventif'] = self._context.get('type_preventif')
        return res


    @api.depends('equipement_id','type_preventif')
    def _compute(self):
        cr = self._cr
        for obj in self:
            zone_id = obj.equipement_id.zone_id.id
            obj.zone_id   = zone_id
            preventifs = self.env['is.preventif.equipement'].search([('zone_id','=',zone_id),('equipement_id','=',obj.equipement_id.id),('type_preventif','=',obj.type_preventif)],limit=1)
            obj.preventif_id = (preventifs and preventifs[0].id) or False
            obj.frequence = obj._get_frequence()


    def _get_frequence(self):
        cr = self._cr
        equipement_id=type_preventif=zone_id=frequence=False
        if self._context and self._context.get('equipement_id'):
            equipement_id = self._context.get('equipement_id')
        else:
            equipement_id = self.equipement_id.id


        if self._context and self._context.get('type_preventif'):
            type_preventif = self._context.get('type_preventif')
        else:
            type_preventif = self.type_preventif


        if equipement_id and type_preventif:
            equipements = self.env['is.equipement'].search([('id','=',equipement_id)],limit=1)
            for equipement in equipements:
                zone_id = equipement.zone_id.id
                preventifs = self.env['is.preventif.equipement'].search([('zone_id','=',zone_id),('equipement_id','=',equipement_id),('type_preventif','=',type_preventif)],limit=1)
                frequence = (preventifs and preventifs[0].frequence) or False
        return frequence


    def _get_nb_heures(self):
        cr = self._cr
        nb_heures=False
        equipement_id=type_preventif=zone_id=frequence=False
        if self._context and self._context.get('equipement_id'):
            equipement_id = self._context.get('equipement_id')
        else:
            equipement_id = self.equipement_id.id

        if self._context and self._context.get('type_preventif'):
            type_preventif = self._context.get('type_preventif')
        else:
            type_preventif = self.type_preventif

        if equipement_id and type_preventif:
            equipements = self.env['is.equipement'].search([('id','=',equipement_id)],limit=1)
            for equipement in equipements:
                nb_heures = False
                equipement_pilote_id = equipement.zone_id.equipement_pilote_id.id
                if equipement_pilote_id:
                    SQL = "SELECT sum(nb_heures) FROM is_preventif_equipement_heure WHERE equipement_id=%s"
                    cr.execute(SQL,[equipement_pilote_id])
                    res = cr.fetchall()
                    nb_heures = (res and res[0][0]) or False
        return nb_heures


    @api.depends('nb_heures','frequence')
    def _compute_ro(self):
        for obj in self:
            ro = True
            if self.env.user.has_group('is_plastigray16.is_rsp_preventif_equipement_group'):
                ro=False
            obj.readonly = ro


    preventif_id        = fields.Many2one('is.preventif.equipement', u"Préventif", compute="_compute", store=True)
    zone_id             = fields.Many2one('is.preventif.equipement.zone', u"Zone", compute="_compute", store=True)
    equipement_id       = fields.Many2one('is.equipement', u"Equipement",required=True)
    type_preventif      = fields.Selection(TYPE_PREVENTIF_EQUIPEMENT, u"Type de préventif",required=True)
    readonly            = fields.Boolean('Champ technique', compute='_compute_ro', readonly=True, store=False)
    date_preventif      = fields.Date(string=u'Date du préventif', default=fields.Date.context_today,index=True, required=True)
    nb_heures           = fields.Integer(u"Nb heures actuel", default=_get_nb_heures)
    frequence           = fields.Integer(u"Fréquence du préventif (H)", compute="_compute", store=True)
    fiche_preventif_ids = fields.Many2many('ir.attachment', 'is_preventif_equipement_saisie_attachment_rel', 'saisie_id', 'file_id', u"Fiche de réalisation du préventif")


    @api.model_create_multi
    def create(self, vals_list):
        res=super().create(vals_list)
        res.preventif_id.date_dernier_preventif      = res.date_preventif
        res.preventif_id.nb_heures_dernier_preventif = res.nb_heures
        res.preventif_id.nb_heures_actuel            = res.nb_heures
        res.preventif_id.nb_heures_avant_preventif   = res.frequence
        return res


    @api.onchange('equipement_id','type_preventif')
    def on_change_equipement_id(self):
        self.nb_heures = self._get_nb_heures()
