# -*- coding: utf-8 -*-
from odoo import api, fields, models


class IsGaliaBaseUcReintegrerCiWizard(models.TransientModel):
    _name = 'is.galia.base.uc.reintegrer.ci.wizard'
    _description = "Assistant de réintégration d'une UC CI dans une UC"

    uc_id       = fields.Many2one('is.galia.base.uc', "Nouvelle UC", required=True, readonly=True)
    product_id  = fields.Many2one('product.product', "Article", related='uc_id.product_id')
    qt_pieces   = fields.Integer("Qt pièces nouvelle UC", related='uc_id.qt_pieces')
    uc_ci_id    = fields.Many2one('is.galia.base.uc', "UC CI", required=True,
        domain="[('product_id','=',product_id),('id','!=',uc_id),('um_id.location_id.name','=','CI'),('um_id.location_id.usage','=','internal')]")
    qt_ci       = fields.Integer("Qt pièces UC CI", related='uc_ci_id.qt_pieces')
    lot_ci      = fields.Char("Fabrication UC CI", related='uc_ci_id.production')
    employee_id = fields.Many2one('hr.employee', "Employé", help="Utilisateur Odoo de cet employé indiqué comme auteur des modifications (Administrateur s'il n'en a pas)")


    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        uc = self.env['is.galia.base.uc'].browse(self.env.context.get('active_id'))
        if uc.exists():
            res['uc_id']       = uc.id
            res['employee_id'] = uc.employee_id.id
        return res


    def action_confirmer(self):
        for obj in self:
            obj.uc_id.reintegrer_ci_dans_uc(obj.uc_ci_id.id, obj.qt_ci, obj.employee_id.id)
        return True
