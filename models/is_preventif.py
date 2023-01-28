# -*- coding: utf-8 -*-

from odoo import models, fields, api
import time
import datetime


class is_mold_cycle(models.Model):
    _name = 'is.mold.cycle'
    _description="is_mold_cycle"
    _rec_name = 'moule_id'
    _order = 'mois desc,moule_id'

    moule_id  = fields.Many2one('is.mold', string='Moule',index=True,required=True)
    mois      = fields.Char(u'Mois',index=True,required=True)
    nb_cycles = fields.Integer(u"Nb cycles")


class is_preventif_moule(models.Model):
    _name = 'is.preventif.moule'
    _description="is_preventif_moule"
    _rec_name = 'moule'
    _order = 'date_preventif desc,moule'


    def default_get(self, default_fields):
        res = super(is_preventif_moule, self).default_get(default_fields)
        if self._context and self._context.get('moule'):
            res['moule'] = self._context.get('moule')
        return res


    @api.depends('moule')
    def _compute(self):
        cr = self._cr
        for obj in self:
            if obj.moule.id:
                nb_cycles=0
                cr.execute("select sum(nb_cycles) from is_mold_cycle where moule_id = %s ",[obj.moule.id])
                res_ids = cr.fetchall()
                for res in res_ids:
                    nb_cycles = res[0]
                obj.nb_cycles = nb_cycles
                obj.periodicite = obj.moule.periodicite_maintenance_moule

    moule               = fields.Many2one('is.mold', string='Moule',index=True)
    date_preventif      = fields.Date(string=u'Date du préventif', default=fields.Date.context_today,index=True)
    nb_cycles           = fields.Integer(u"Nb cycles"            , compute="_compute", store=True, readonly=True)
    periodicite         = fields.Integer(u"Périodicité préventif", compute="_compute", store=True, readonly=True)
    fiche_preventif_ids = fields.Many2many('ir.attachment', 'is_preventif_moule_attachment_rel', 'preventif_id', 'file_id', u"Fiche de réalisation du préventif")


    @api.model_create_multi
    def create(self, vals_list):
        res=super().create(vals_list)

        print(res,vals_list)
        for obj in res:
            if obj and 'moule' in vals_list[0]:
                obj.moule.nb_cycles_dernier_preventif = obj.nb_cycles
                obj.moule.nb_cycles_actuel            = obj.nb_cycles
                obj.moule.date_dernier_preventif      = obj.date_preventif
                obj.moule.nb_cycles_avant_preventif   = obj.periodicite
        return res


class is_mold_operation_systematique(models.Model):
    _name = 'is.mold.operation.systematique'
    _description="is_mold_operation_systematique"

    name   = fields.Char(string=u'Opérations systématiques pour la maintenance préventive', required=True)
    active = fields.Boolean(string='Active', default=True)


class is_mold_operation_specifique(models.Model):
    _name = 'is.mold.operation.specifique'
    _description="is_mold_operation_specifique"

    name   = fields.Char(string=u'Opérations spécifique pour la maintenance préventive', required=True)
    active = fields.Boolean(string='Active', default=True)


class is_mold_specification_particuliere(models.Model):
    _name = 'is.mold.specification.particuliere'
    _description="is_mold_specification_particuliere"

    name   = fields.Char(string=u'Spécification particulière', required=True)
    active = fields.Boolean(string='Active', default=True)


class is_mold_frequence_preventif(models.Model):
    _name = 'is.mold.frequence.preventif'
    _description="is_mold_frequence_preventif"

    name   = fields.Char(string=u'Fréquence préventif moule', required=True)
    active = fields.Boolean(string='Active', default=True)


class is_mold_systematique_array(models.Model):
    _name = 'is.mold.systematique.array'
    _description="is_mold_systematique_array"

    operation_systematique_id     = fields.Many2one('is.mold.operation.systematique', string=u'Opérations systématiques pour la maintenance préventive', required=True)
    activer                       = fields.Boolean(string='Activer', default=False)
    frequence_preventif_id        = fields.Many2one('is.mold.frequence.preventif', string=u'Fréquence préventif')
    mold_id                       = fields.Many2one('is.mold', string='Moule')


class is_mold_specifique_array(models.Model):
    _name = 'is.mold.specifique.array'
    _description="is_mold_specifique_array"

    operation_specifique_id       = fields.Many2one('is.mold.operation.specifique', string=u'Opérations spécifiques pour la maintenance préventive', required=True)
    activer                       = fields.Boolean(string='Activer', default=False)
    frequence_preventif_id        = fields.Many2one('is.mold.frequence.preventif', string=u'Fréquence préventif')
    mold_id                       = fields.Many2one('is.mold', string='Moule')


class is_mold_specification_array(models.Model):
    _name = 'is.mold.specification.array'
    _description="is_mold_specification_array"

    specification_particuliere_id = fields.Many2one('is.mold.specification.particuliere', string=u'Spécifications particulières', required=True)
    activer                       = fields.Boolean(string='Activer', default=False)
    frequence_preventif_id        = fields.Many2one('is.mold.frequence.preventif', string=u'Fréquence préventif')
    mold_id                       = fields.Many2one('is.mold', string='Moule')


class is_mold_piece_specifique(models.Model):
    _name = 'is.mold.piece.specifique'
    _description="is_mold_piece_specifique"

    name = fields.Char(string=u'Pièces spécifiques de rechange en stock')


class is_mold_surface_aspect(models.Model):
    _name = 'is.mold.surface.aspect'
    _description="is_mold_surface_aspect"

    name = fields.Char(string=u"Surface d'aspect")

