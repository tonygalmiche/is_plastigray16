# -*- coding: utf-8 -*-
from odoo import models, fields, api
from lxml import etree


class Model(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        res = super().get_view(view_id=view_id, view_type=view_type, options=options)
        if view_type == "form":
            doc = etree.XML(res["arch"])
            sheet = doc.xpath("//sheet")
            if sheet:
                model_id = self.env['ir.model'].sudo().search([('model', '=', 'is.head.model.form.view')])
                if model_id:
                    is_head_id = self.env['is.head.model.form.view'].search([('model_id.model', '=', self._name)], limit=1)
                    if is_head_id:
                        img_src = ""
                        if is_head_id.picture:
                            img_src = "<img src='data:image/gif;base64," + str(is_head_id.picture,
                                                                               'utf-8') + "' height='42' width='42' />"
                        new_add = "<div height='60px' width='100%' style='padding: 10px;margin-bottom:20px;font-size:18px;background-color: " + is_head_id.color + ";'> " + img_src + " " + is_head_id.name + "</div>"
                        name_field = sheet[0].xpath('//sheet')
                        if name_field:
                            sheet[0].insert(0, etree.fromstring(new_add))
                        else:
                            sheet[0].insert(0, etree.fromstring(new_add))
                        res["arch"] = etree.tostring(doc)
        return res


class is_head_model_form_view(models.Model):
    _name        = "is.head.model.form.view"
    _description = "Is head model form view"

    model_id = fields.Many2one("ir.model", string="Modèle", required=True, ondelete='cascade')
    name     = fields.Char(string="Nom du modèle", required=True)
    picture  = fields.Binary(string="Image", type="binary")
    color    = fields.Char(string="Couleur", required=True, default="#E1E1E1")
