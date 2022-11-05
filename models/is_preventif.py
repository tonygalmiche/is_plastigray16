# -*- coding: utf-8 -*-

from odoo import models, fields, api
import time
import datetime


class is_mold(models.Model):
    _inherit = 'is.mold'

    def vers_nouveau_preventif_mold(self):
        for data in self:
            context = dict(self.env.context or {})
            context['moule'] = data.id
            return {
                'name': u"Préventif Moule",
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'is.preventif.moule',
                'type': 'ir.actions.act_window',
                'domain': '[]',
                'context': context,
            }
        return True


    def default_get(self, default_fields):
        res = super(is_mold, self).default_get(default_fields)
        res['is_base_check'] = False
        user_obj = self.env['res.users']
        user_data = user_obj.browse(self._uid)
        if user_data and user_data.company_id.is_base_principale:
            res['is_base_check'] = True
        systematique_obj = self.env['is.mold.operation.systematique']
        systematique_ids = systematique_obj.search([('active', '=', True)])
        systematique_lst = []
        for num in systematique_ids:
            systematique_lst.append((0,0, {
                'operation_systematique_id': num.id,
                'activer'                  : True,
            }))
        res['systematique_ids'] = systematique_lst
        specifique_obj = self.env['is.mold.operation.specifique']
        specifique_ids = specifique_obj.search([('active', '=', True)])
        specifique_lst = []
        for num in specifique_ids:
            specifique_lst.append((0,0, {
                'operation_specifique_id': num.id,
                'activer'                : False,
            }))
        res['specifique_ids'] = specifique_lst
        specification_obj = self.env['is.mold.specification.particuliere']
        specification_ids = specification_obj.search([('active', '=', True)])
        specification_lst = []
        for num in specification_ids:
            specification_lst.append((0,0, {
                'specification_particuliere_id': num.id,
                'activer'                      : False,
            }))
        res['specification_ids'] = specification_lst
        return res

    @api.depends()
    def _check_base_db(self):
        for obj in self:
            user_obj = self.env['res.users']
            user_data = user_obj.browse(self._uid)
            if user_data and user_data.company_id.is_base_principale:
                obj.is_base_check = True


    date_dernier_preventif        = fields.Date(u"Date dernier préventif")
    nb_cycles_dernier_preventif   = fields.Integer(u"Nb cycles dernier préventif")
    nb_cycles_actuel              = fields.Integer(u"Nb cycles actuel")
    nb_cycles_avant_preventif     = fields.Integer(u"Nb cycles avant préventif")
    periodicite_maintenance_moule = fields.Integer(u"Périodicité maintenance moule (nb cycles)")
    gamme_preventif_ids           = fields.Many2many('ir.attachment', 'is_mold_attachment_rel', 'mold_id', 'file_id', u"Gamme préventif")
    preventif_inactif             = fields.Boolean(u"Préventif inactif suite FDV", default=False)
    is_base_check                 = fields.Boolean(string="Is Base", compute="_check_base_db")
    is_preventif_moule            = fields.One2many('is.preventif.moule', 'moule', u'Préventif Moule')
    systematique_ids              = fields.One2many('is.mold.systematique.array', 'mold_id',  u'Opérations systématiques')
    specifique_ids                = fields.One2many('is.mold.specifique.array', 'mold_id',  u'Opérations spécifiques')
    specification_ids             = fields.One2many('is.mold.specification.array', 'mold_id',  u'Spécifications particulières')
    piece_specifique_ids          = fields.Many2many('is.mold.piece.specifique', 'is_mold_piece_specifique_rel', 'mold_id', 'piece_spec_id', u"Pièces spécifiques de rechange en stock")
    surface_aspect_id             = fields.Many2one('is.mold.surface.aspect', u"Surface d'aspect")
    reference_grain               = fields.Char(string=u'Référence du grain utilisé')
    graineur_id                   = fields.Many2one('res.partner', string='Graineur', domain="[('supplier','=',True)]")
    diametre_seuil                = fields.Char(string=u'Diamètre seuil')
    fournisseur_bloc_chaud_id     = fields.Many2one('res.partner', string='Fournisseur du bloc chaud', domain="[('supplier','=',True)]")
    num_systeme                   = fields.Char(string=u'N° du système')
    garantie_outillage            = fields.Char(string=u"Garantie de l'outillage (en nombre de cycles)")
    indice_creation_fiche         = fields.Char(string='Indice Fiche', default='A')
    createur_fiche_id             = fields.Many2one("res.users", string=u'Créateur Fiche')
    date_creation_fiche           = fields.Date(string=u'Date Création Fiche')
    date_modification_fiche       = fields.Date(string='Date Modfication Fiche')


    def write(self, vals):
        if 'periodicite_maintenance_moule' in vals:
            nb = self.nb_cycles_dernier_preventif+vals['periodicite_maintenance_moule']-self.nb_cycles_actuel
            vals['nb_cycles_avant_preventif'] = nb
        res = super(is_mold, self).write(vals)
        return res


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


    def create(self, vals):
        obj = super(is_preventif_moule, self).create(vals)
        if obj and 'moule' in vals:
                obj.moule.nb_cycles_dernier_preventif = obj.nb_cycles
                obj.moule.nb_cycles_actuel            = obj.nb_cycles
                obj.moule.date_dernier_preventif      = obj.date_preventif
                obj.moule.nb_cycles_avant_preventif   = obj.periodicite
        return obj


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

