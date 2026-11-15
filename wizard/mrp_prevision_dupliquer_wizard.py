# -*- coding: utf-8 -*-
from odoo import api, fields, models # type: ignore
from odoo.exceptions import ValidationError # type: ignore


class MrpPrevisionDupliquerWizard(models.TransientModel):
    _name = 'mrp.prevision.dupliquer.wizard'
    _description = "Assistant de duplication des FS / SA sur un autre article (changement d'indice)"

    prevision_ids  = fields.Many2many('mrp.prevision', string="FS / SA à dupliquer", readonly=True)
    type           = fields.Selection([('fs', "FS"),('sa', "SA")], "Type", readonly=True)
    nb_previsions  = fields.Integer("Nombre de lignes", compute='_compute_nb_previsions')
    product_src_id = fields.Many2one('product.product', "Article d'origine", readonly=True)
    segment_id     = fields.Many2one('is.product.segment', "Segment", related='product_src_id.segment_id')
    product_id     = fields.Many2one('product.product', "Nouvel article", required=True,
        domain="[('segment_id','=',segment_id),('id','!=',product_src_id)]",
        help="Articles du même segment que l'article d'origine")


    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('active_model')=='mrp.prevision':
            previsions = self.env['mrp.prevision'].browse(self.env.context.get('active_ids') or [])
            self._controle_previsions(previsions)
            res['prevision_ids']  = [(6,0,previsions.ids)]
            res['type']           = previsions[0].type
            res['product_src_id'] = previsions[0].product_id.id
        return res


    @api.depends('prevision_ids')
    def _compute_nb_previsions(self):
        for obj in self:
            obj.nb_previsions = len(obj.prevision_ids)


    def _controle_previsions(self, previsions):
        "FS ou SA seulement, toutes du même type et du même article"
        if not previsions:
            raise ValidationError("Aucune ligne sélectionnée")
        if any(p.type not in ('fs','sa') for p in previsions):
            raise ValidationError("Seules les FS et les SA peuvent être dupliquées (pas les FT)")
        if len(set(previsions.mapped('type')))>1:
            raise ValidationError("Les lignes sélectionnées doivent être toutes des FS ou toutes des SA")
        if len(previsions.mapped('product_id'))>1:
            raise ValidationError("Les lignes sélectionnées doivent toutes être du même article")


    def action_dupliquer(self):
        self.ensure_one()
        self._controle_previsions(self.prevision_ids)
        if self.product_id==self.product_src_id:
            raise ValidationError("Le nouvel article doit être différent de l'article d'origine")
        # Création une par une (le create des FS ne gère qu'une FS à la fois pour créer ses FT).
        # Quantité arrondie au lot et date de début recalculée avec le nouvel article.
        news = self.env['mrp.prevision']
        for prevision in self.prevision_ids.sorted('start_date'):
            vals = {
                'type'      : prevision.type,
                'product_id': self.product_id.id,
                'quantity'  : prevision.quantity,
                'note'      : prevision.note,
            }
            if prevision.type=='fs':
                # FS : même date de fin, FT recréées avec la nomenclature du nouvel article
                vals['end_date'] = fields.Date.to_string(prevision.end_date)
            else:
                # SA : même date de réception
                vals['start_date_cq'] = fields.Date.to_string(prevision.start_date_cq)
            news |= self.env['mrp.prevision'].create(vals)
        return {
            'name'     : "%s dupliquées sur %s"%(self.type.upper(), self.product_id.is_code or self.product_id.display_name),
            'view_mode': 'tree,form',
            'res_model': 'mrp.prevision',
            'domain'   : [('id','in',news.ids)],
            'type'     : 'ir.actions.act_window',
        }
