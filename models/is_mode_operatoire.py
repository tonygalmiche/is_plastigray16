# -*- coding: utf-8 -*-
from odoo import models,fields,api           # type: ignore
from odoo.exceptions import ValidationError  # type: ignore
import datetime


class IsModeOperatoireMenu(models.Model):
    _name='is.mode.operatoire.menu'
    _description="IsModeOperatoireMenu"
    _order='ordre'

    name    = fields.Char("Menu Mode opératoire", required=True)
    ordre   = fields.Integer("Ordre")
    menu_id = fields.Many2one('ir.ui.menu', 'Menu', copy=False)


    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res.creer_menu_action()
        return res


    def write(self,vals):
        res = super(IsModeOperatoireMenu, self).write(vals)
        if 'name' in vals:
            self.sudo().menu_id.name=vals["name"]
        if 'ordre' in vals:
            self.sudo().menu_id.sequence=vals["ordre"]
        return res


    def unlink(self):
        self.sudo().menu_id.unlink()
        return super(IsModeOperatoireMenu, self).unlink()


    def creer_menu_action(self):
        parent=self.env.ref('is_plastigray16.is_mode_operatoire_main_menu')
        for obj in self:
            if not obj.menu_id:
                v={
                    'name'     : obj.name, 
                    'parent_id': parent.id, 
                    'sequence' : obj.ordre, 
                }
                menu=self.env['ir.ui.menu'].sudo().create(v)
                obj.menu_id = menu.id
                v={
                    'name'     : obj.name, 
                    'res_model': 'is.mode.operatoire', 
                    'view_mode': 'tree,form',
                    'domain'  : [('menu_id','=',obj.id)] 
                }
                action=self.env['ir.actions.act_window'].sudo().create(v)
                menu.action="ir.actions.act_window,%s"%(action.id)


        # #** Création des menus ************************************************
        # lines = self.env['is.mode.operatoire.menu'].search([],order='ordre,id', limit=100)
        # for line in lines:
        #     if not line.menu_id:
        #         vals={
        #             'name'     : line.name, 
        #             'parent_id': parent.id, 
        #             'sequence' : line.ordre, 
        #         }
        #         menu=self.env['ir.ui.menu'].sudo().create(vals)
        #         line.menu_id = menu.id
        # #**********************************************************************


        # #** Ajout des actions aux menus


        # #** Suppression des anciens menus *************************************
        # if parent.id:
        #     domain =[
        #         ('parent_id','=',parent.id),
        #         ('name','!=', 'Modes opératoires')
        #     ]
        #     menus = self.env['ir.ui.menu'].search(domain,order='sequence,id', limit=100)
        #     for menu in menus:
        #         # domain =[
        #         #     ('menu_id','=',menu.id),
        #         # ]
        #         # lines = self.env['is.mode.operatoire.menu'].search(domain, limit=1)
        #         print(menu.id,menu.sequence,menu.name,menu.action)











class IsModeOperatoire(models.Model):
    _name='is.mode.operatoire'
    _description="IsModeOperatoire"
    _inherit=['mail.thread']
    _order='name'

    name           = fields.Char("Mode opératoire", required=True)
    menu_id        = fields.Many2one('is.mode.operatoire.menu', 'Menu', required=True)
    createur_id    = fields.Many2one("res.users", "Createur", required=True, default=lambda self: self.env.user)
    date_demande   = fields.Date("Date de la demande"       , required=True, default=lambda *a: fields.datetime.now())
    attachment_ids = fields.Many2many('ir.attachment', 'is_mode_operatoire_attachment_rel', 'doc_id', 'file_id', u'Pièces jointes')

