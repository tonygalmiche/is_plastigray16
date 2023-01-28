# -*- coding: utf-8 -*-
from odoo import models,fields,api
from odoo.exceptions import ValidationError
import datetime


class IsModeOperatoireMenu(models.Model):
    _name='is.mode.operatoire.menu'
    _description="IsModeOperatoireMenu"
    _order='ordre'

    name    = fields.Char("Menu Mode opératoire", required=True)
    ordre   = fields.Integer("Ordre")
    menu_id = fields.Many2one('ir.ui.menu', 'Menu')



    # @api.model_create_multi
    # def create(self, vals_list):
    #     for vals in vals_list:
    #         vals['name'] = self.env['ir.sequence'].next_by_code('is.bl.manuel')
    #     return super().create(vals_list)



    @api.model_create_multi
    def create(self, vals_list):
        vals=vals_list[0]
        parent=self.env.ref('is_plastigray16.is_mode_operatoire_main_menu')
        v={
            'name'     : vals['name'], 
            'parent_id': parent.id, 
            'sequence' : vals['ordre'], 
         }
        menu=self.env['ir.ui.menu'].sudo().create(v)
        vals_list[0]["menu_id"]=menu.id
        v={
            'name'     : vals['name'], 
            'res_model': 'is.mode.operatoire', 
            'view_mode': 'tree,form',
        }
        action=self.env['ir.actions.act_window'].sudo().create(v)
        menu.action="ir.actions.act_window,%s"%(action.id)
        res = super().create(vals_list)
        action.domain=[('menu_id','=',res.id)] 
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

