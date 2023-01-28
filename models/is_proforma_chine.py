# -*- coding: utf-8 -*-

from odoo import models, fields, api
import datetime
import math


class is_proforma_chine(models.Model):
    _name = 'is.proforma.chine'
    _description="is_proforma_chine"
    _order = 'name desc'

    name               = fields.Char("N°invoice", readonly=True)
    date_creation      = fields.Date(u"Date", required=True, copy=False, default=fields.Date.context_today)
    partner_id         = fields.Many2one("res.partner", "Partner", required=True, domain=[('is_company', '=', True)])
    pallet_size        = fields.Char("Pallet size")
    transport_costs    = fields.Float("Transport costs", digits=(14, 2))
    incoterm_id        = fields.Many2one("account.incoterms", "Incoterm")
    place              = fields.Char("Place")
    line_ids           = fields.One2many('is.proforma.chine.line', 'proforma_id', u"Lignes")
    total_net_weight   = fields.Float("Total net weight"  , digits=(14, 2), compute="_compute_total_net_weight", store=True, readonly=True)
    total_gross_weight = fields.Float("Total gross weight", digits=(14, 2))
    total_amount       = fields.Float("Total amount"      , digits=(14, 2), compute="_compute_total_net_weight", store=True, readonly=True)


    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.incoterm_id = self.partner_id.is_incoterm.id
        self.place       = self.partner_id.is_lieu


    @api.depends('line_ids')
    def _compute_total_net_weight(self):
        for obj in self:
            total_net_weight = 0
            total_amount     = 0
            for line in obj.line_ids:
                total_net_weight+=line.net_weight
                total_amount+=line.total_price
            obj.total_net_weight = total_net_weight
            obj.total_amount     = total_amount


    # def create(self, vals):
    #     vals['name'] = self.env['ir.sequence'].get('is.proforma.chine') or ''
    #     return super(is_proforma_chine, self).create(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('is.proforma.chine')


        print(vals_list)
        return super().create(vals_list)





class is_proforma_chine_line(models.Model):
    _name = 'is.proforma.chine.line'
    _description="is_proforma_chine_line"

    proforma_id  = fields.Many2one("is.proforma.chine", "Invoice",required=True, ondelete='cascade', readonly=True)
    type_material = fields.Selection([
            ("raw material plastic", "Raw material plastic"),
            ("masterbatch"         , "Masterbatch"),
            ("components"          , "Components"),
        ], "Type material")
    mold_ids       = fields.Many2many('is.mold'        ,'is_proforma_chine_mold_rel','proforma_id','mold_id', string="Project number")
    product_id     = fields.Many2one("product.product", "Part number")
    designation    = fields.Char("Designation", required=True)
    custom_code    = fields.Char("Custom Code")
    country_origin = fields.Char("Country of origin")
    uom_id         = fields.Many2one("uom.uom", "Unit")
    quantity       = fields.Float("Quantity"         , digits=(14, 2))
    packaging      = fields.Selection([
            ("bag", "Bag"),
            ("box", "Box"),
        ], "Packaging")
    qty_per_pack   = fields.Float("Qty per packaging", digits=(14, 2))
    qty_of_pack    = fields.Float("Qty of packaging" , digits=(14, 2), compute="_compute_qty_of_pack", store=True, readonly=True)
    net_weight     = fields.Float("Net weight", digits=(14, 2))
    price_unit     = fields.Float("Price unit"       , digits=(14, 2))
    total_price    = fields.Float("Total Price"      , digits=(14, 2), compute="_compute_price_unit", store=True, readonly=True)


    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.designation    = self.product_id.name
        self.custom_code    = self.product_id.is_nomenclature_douaniere
        self.country_origin = self.product_id.is_origine_produit_id.code
        self.uom_id         = self.product_id.uom_id.id
        price_unit = 0
        if self.product_id:
            couts = self.env['is.cout'].search([('name', '=', self.product_id.id)])
            for cout in couts:
                price_unit = cout.cout_act_total
        self.price_unit = price_unit


    @api.depends('price_unit','quantity')
    def _compute_price_unit(self):
        for obj in self:
            obj.total_price = obj.price_unit*obj.quantity


    @api.depends('quantity','qty_per_pack')
    def _compute_qty_of_pack(self):
        for obj in self:
            qty_of_pack = 0
            if obj.qty_per_pack>0:
                qty_of_pack = obj.quantity/obj.qty_per_pack
            obj.qty_of_pack = qty_of_pack

    def getQtyOfPack(self):
        for obj in self:
            return int(math.ceil(obj.qty_of_pack))



