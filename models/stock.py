# -*- coding: utf-8 -*-
from odoo import models,fields,api,tools,SUPERUSER_ID
from odoo.exceptions import ValidationError
import string
import time
from datetime import datetime, date, timedelta
from subprocess import PIPE, Popen
import logging
_logger = logging.getLogger(__name__)


class stock_location(models.Model):
    _inherit = 'stock.location'

    control_quality = fields.Boolean(u'Contrôle qualité', default=False)

    def name_get(self):
        res = []
        for obj in self:
            name = obj.name
            res.append((obj.id,name))
        return res


class is_commentaire_mouvement_stock(models.Model):
    _name = 'is.commentaire.mouvement.stock'
    _description = 'Comentaires sur les mouvements'

    name = fields.Char('Description', required=True)


class stock_lot(models.Model):
    _inherit = "stock.lot"
    _order="id desc"

    is_date_peremption = fields.Date("Date de péremption")
    is_lot_fournisseur = fields.Char("Lot fournisseur")
    company_id = fields.Many2one('res.company', 'Company', required=True, store=True, index=True, default=1) #J'ai ajouté default=1, sinon, impossible de créer des lots


    def _domain_product_id(self):
        "Modification de la fonction par défaut pour autoriser tous les articles dans un lot"
        domain = [
            #"('tracking', '!=', 'none')",
            "('type', '=', 'product')",
            "'|'",
                "('company_id', '=', False)",
                "('company_id', '=', company_id)"
        ]
        if self.env.context.get('default_product_tmpl_id'):
            domain.insert(0,
                ("('product_tmpl_id', '=', %s)" % self.env.context['default_product_tmpl_id'])
            )
        res='[' + ', '.join(domain) + ']'
        return res


class stock_quant(models.Model):
    _inherit = "stock.quant"
    _order   = "product_id, location_id"

    is_mold_id          = fields.Many2one('is.mold'    , 'Moule'            , related='product_id.is_mold_id'         , readonly=True)


    @api.onchange('location_id', 'product_id', 'lot_id', 'package_id', 'owner_id')
    def _onchange_location_or_product_id(self):
        vals = {}

        # Once the new line is complete, fetch the new theoretical values.
        if self.product_id and self.location_id:
            # Sanity check if a lot has been set.
            #if self.lot_id:
            #    if self.tracking == 'none' or self.product_id != self.lot_id.product_id:
            #        vals['lot_id'] = None

            quant = self._gather(
                self.product_id, self.location_id, lot_id=self.lot_id,
                package_id=self.package_id, owner_id=self.owner_id, strict=True)
            if quant:
                self.quantity = quant.quantity

            # Special case: directly set the quantity to one for serial numbers,
            # it'll trigger `inventory_quantity` compute.
            if self.lot_id and self.tracking == 'serial':
                vals['inventory_quantity'] = 1
                vals['inventory_quantity_auto_apply'] = 1

        if vals:
            self.update(vals)





