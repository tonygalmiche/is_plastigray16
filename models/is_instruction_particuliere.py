# -*- coding: utf-8 -*-

from odoo import models, fields, api


class is_instruction_particuliere(models.Model):
    _name = 'is.instruction.particuliere'
    _description="Instructions particulières"
    _order = 'name desc'

    name          = fields.Char("N°", required=False, readonly=True, index=True)
    createur_id   = fields.Many2one('res.users', 'Créateur', readonly=True, default=lambda self: self.env.uid)
    date_creation = fields.Date('Date de création', readonly=True, default=lambda *a: fields.datetime.now())
    mold_ids      = fields.Many2many('is.mold'        ,'is_instruction_particuliere_mold_rel'    ,'ip_id','mold_id'    , string="Moules")
    dossierf_ids  = fields.Many2many('is.dossierf'    ,'is_instruction_particuliere_dossierf_rel','ip_id','dossierf_id', string="Dossiers F")
    product_ids   = fields.Many2many('product.product','is_instruction_particuliere_product_rel' ,'ip_id','product_id' , string="Articles")
    date_validite = fields.Date("Date de validité", required=True)
    commentaire   = fields.Text("Commentaire")
    contenu       = fields.Binary("Image du contenu")

 
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('is.instruction.particuliere')
        return super().create(vals_list)
