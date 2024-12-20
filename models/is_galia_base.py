# -*- coding: utf-8 -*-
from odoo import models,fields,api
import datetime
import pytz
import os
import logging
_logger = logging.getLogger(__name__)

_MIXTE=[
    ('oui', 'Oui'),
    ('non', 'Non'),
]

class is_galia_base(models.Model):
    _name='is.galia.base'
    _description="Etiquettes Galia"
    _order='num_eti desc'
    _rec_name='num_eti'

    num_eti       = fields.Integer(u"N°Étiquette", index=True)
    soc           = fields.Integer(u"Société"    , index=True)
    type_eti      = fields.Char(u"Type étiquette", index=True)
    num_of        = fields.Char(u"N°OF"          , index=True)
    num_carton    = fields.Integer(u"N°Carton"   , index=True)
    qt_pieces     = fields.Integer(u"Qt Pièces")
    date_creation = fields.Datetime(u"Date de création")
    login         = fields.Char(u"Login")


class is_galia_base_um(models.Model):
    _name='is.galia.base.um'
    _description="Etiquettes Galia UM"
    _order='name desc'
    _sql_constraints = [('name_uniq','UNIQUE(name)', u'Cette étiquette UM existe déjà')]

    @api.depends('uc_ids')
    def _compute(self):
        for obj in self:
            qt_pieces  = 0
            product_id = False
            if obj.mixte=='non':
                for line in obj.uc_ids:
                    qt_pieces += line.qt_pieces
                    product_id = line.product_id
            obj.product_id = product_id
            obj.qt_pieces  = qt_pieces

    name             = fields.Char("N°Étiquette UM", readonly=True             , index=True)
    mixte            = fields.Selection(_MIXTE, "UM mixte", default='non', required=True)
    liste_servir_id  = fields.Many2one('is.liste.servir', 'Liste à servir'     , index=True)
    bon_transfert_id = fields.Many2one('is.bon.transfert', 'Bon de transfert'  , index=True)
    production_id    = fields.Many2one('mrp.production', 'Ordre de fabrication', index=True)
    location_id      = fields.Many2one('stock.location', 'Emplacement'         , index=True, domain=[("usage","=","internal")], default=lambda self: self._get_location_id())
    uc_ids           = fields.One2many('is.galia.base.uc'  , 'um_id', "UCs")
    product_id       = fields.Many2one('product.product', 'Article', readonly=True, compute='_compute', store=False)
    qt_pieces        = fields.Integer("Qt Pièces"                 , readonly=True, compute='_compute', store=False)
    employee_id      = fields.Many2one("hr.employee", "Employé")
    date_fin         = fields.Datetime("Date fin UM")
    active           = fields.Boolean("Active", default=True, copy=False, index=True)
    date_ctrl_rcp    = fields.Datetime("Date contrôle réception")


    def _get_location_id(self):
        filtre = [
            ('name' , '=', 'ATELIER'),
            ('usage', '=', 'internal'),
        ]
        lines = self.env["stock.location"].search(filtre)
        location_id = lines and lines[0].id or False
        return location_id
       

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # if 'production_id' in vals:
            #     production_id = vals['production_id']
            #     production = self.env['mrp.production'].browse(production_id)
            #     location_id = production.location_dest_id.id
            #     if location_id:
            #         vals['location_id'] = location_id
            vals['name'] = self.env['ir.sequence'].next_by_code('is.galia.base.um')
        return super().create(vals_list)


    @api.onchange('liste_servir_id')
    def onchange_liste_servir_id(self):
        location_id = self.liste_servir_id.is_source_location_id.id
        if location_id:
            self.location_id = location_id


    @api.onchange('bon_transfert_id')
    def onchange_bon_transfert_id(self):
        location_id = self.bon_transfert_id.location_id.id
        if location_id:
            self.location_id = location_id


    @api.onchange('production_id')
    def onchange_production_id(self):
        location_id = self.production_id.location_dest_id.id
        if location_id:
            self.location_id = location_id


    def acceder_um_action(self):
        view_id = self.env.ref('is_plastigray16.is_galia_base_um_form_view').id
        for obj in self:
            return {
                'name': "Etiquettes UM",
                'view_mode': 'form',
                'view_id': view_id,
                'res_model': 'is.galia.base.um',
                'type': 'ir.actions.act_window',
                'res_id': obj.id,
                'domain': '[]',
            }


    def voir_uc_action(self):
        for obj in self:
            res= {
                'name': obj.name,
                'view_mode': 'tree,form',
                'res_model': 'is.galia.base.uc',
                'type': 'ir.actions.act_window',
                'domain': [('um_id','=',obj.id)],
            }
            return res


    def imprimer_etiquette_um_action(self):
        for obj in self : 
            cdes = self.env['is.commande.externe'].search([('name','=',"imprimer-etiquette-um")])
            for cde in cdes:
                model=self._name
                uid=self._uid
                user=self.env['res.users'].browse(uid)
                soc=user.company_id.partner_id.is_code
                x = cde.commande
                x = x.replace("#soc"  , soc)
                x = x.replace("#um_id", str(obj.id))
                x = x.replace("#uid"  , str(uid))
                _logger.info(x)
                lines=os.popen(x).readlines()
                for line in lines:
                    _logger.info(line.strip())
 

class is_galia_base_uc(models.Model):
    _name='is.galia.base.uc'
    _description="Etiquettes Galia UC"
    _order='num_eti desc'
    _rec_name='num_eti'
    _sql_constraints = [('num_eti_uniq','UNIQUE(num_eti,um_id)', u'Cette étiquette existe déjà dans cette UM')]

    um_id         = fields.Many2one('is.galia.base.um', 'UM', required=True, ondelete='cascade')
    um_mixte      = fields.Selection(related="um_id.mixte")
    um_active     = fields.Boolean(related="um_id.active")
    num_eti       = fields.Integer("N°Étiquette UC", required=True, index=True)
    type_eti      = fields.Char("Type étiquette", required=True   , index=True)
    num_carton    = fields.Integer("N°Carton", required=True      , index=True)
    qt_pieces     = fields.Integer("Qt Pièces", required=True)
    date_creation = fields.Datetime("Date de création", required=True)
    production_id = fields.Many2one('mrp.production', 'Ordre de fabrication')
    production    = fields.Char('Fabrication')
    product_id    = fields.Many2one('product.product', 'Article', required=True , index=True)
    employee_id   = fields.Many2one("hr.employee", "Employé")
    liste_servir_id   = fields.Many2one('is.liste.servir' , 'Liste à servir'  , related='um_id.liste_servir_id')
    bon_transfert_id  = fields.Many2one('is.bon.transfert', 'Bon de transfert', related='um_id.bon_transfert_id')
    ls_line_id        = fields.Many2one('is.liste.servir.line' , 'Ligne liste à servir')
    bt_line_id        = fields.Many2one('is.bon.transfert.line', 'Ligne bon de transfert')
    stock_move_id     = fields.Many2one('stock.move', 'Ligne livraison')
    stock_move_rcp_id = fields.Many2one('stock.move', 'Ligne réception')
    reception_inter_site_id = fields.Many2one('is.reception.inter.site', 'Réception inter-site')


    def acceder_uc_action(self):
        #view_id = self.env.ref('is_plastigray16.is_galia_base_um_form_view').id
        for obj in self:
            return {
                'name': "Etiquettes UC",
                'view_mode': 'form',
                #'view_id': view_id,
                'res_model': 'is.galia.base.uc',
                'type': 'ir.actions.act_window',
                'res_id': obj.id,
                'domain': '[]',
            }

