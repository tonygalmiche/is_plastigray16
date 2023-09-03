# -*- coding: utf-8 -*-
from odoo import models,fields,api
from odoo.tools import float_compare, float_round, format_datetime


class mrp_bom(models.Model):
    _name     = 'mrp.bom'
    _inherit  = 'mrp.bom'
    _order    = 'product_tmpl_id'
    _rec_name = 'product_tmpl_id'

    is_gamme_generique_id = fields.Many2one('mrp.routing', 'Gamme générique', help="Gamme générique utilisée dans le plan directeur")
    is_sous_traitance     = fields.Boolean('Nomenclature de sous-traitance')
    is_negoce             = fields.Boolean('Nomenclature de négoce')
    is_inactive           = fields.Boolean('Nomenclature inactive')
    is_qt_uc              = fields.Integer("Qt par UC", compute='_compute')
    is_qt_um              = fields.Integer("Qt par UM", compute='_compute')
    segment_id            = fields.Many2one('is.product.segment', 'Segment'  , related='product_tmpl_id.segment_id'        , readonly=True)
    is_gestionnaire_id    = fields.Many2one('is.gestionnaire', 'Gestionnaire', related='product_tmpl_id.is_gestionnaire_id', readonly=True)
    routing_id            = fields.Many2one('mrp.routing', 'Gamme', index=True) # Ce champ n'existait plus dans Odoo 16
 

    @api.depends('product_tmpl_id')
    def _compute(self):
        for obj in self:
            obj.is_qt_uc = obj.product_tmpl_id.get_uc()
            obj.is_qt_um = obj.product_tmpl_id.get_um()

    # def explode_phantom(self, qty=1, lines=[]):
    #     for obj in self:
    #         for line in obj.bom_line_ids:
    #             #print(line.product_id.is_code)
    #             if line.type == 'phantom':
    #                 #print("phantom")
    #                 lines=line.child_bom_id.explode_phantom(qty=line.product_qty*qty, lines=lines)
    #             else: 
    #                 vals={
    #                     "product_id"    : line.product_id.id,
    #                     "product_uom_id": line.product_uom_id.id,
    #                     "product_qty"   : line.product_qty*qty,
    #                 }
    #                 lines.append(vals)
    #         print("len=",len(lines))
    #         return lines


    def explode_phantom(self, qty=1):
        def explode(bom, qty=1, lines=[]):
            for line in bom.bom_line_ids:
                #print(line.product_id.is_code)
                if line.type == 'phantom':
                    #print("phantom")
                    lines=explode(line.child_bom_id, qty=line.product_qty*qty, lines=lines)
                else: 
                    vals={
                        "product_id"    : line.product_id.id,
                        "product_uom_id": line.product_uom_id.id,
                        "product_qty"   : line.product_qty*qty,
                        "line"          : line,
                        "qty"           : qty,
                    }
                    lines.append(vals)
            return lines
        for obj in self:
            lines = explode(obj,qty=qty)
            return lines





class mrp_bom_line(models.Model):
    _name = 'mrp.bom.line'
    _inherit = 'mrp.bom.line'
    _order = "sequence, id"


    #Si la catégorie est 'Fantôme', tous les liens des nomenclatures doivent passer en 'Fantôme'
    @api.depends("product_id", "product_id.product_tmpl_id.is_category_id", "product_id.product_tmpl_id.is_category_id.fantome")
    def _type(self):
        for obj in self:
            type='normal'
            if obj.product_id:
                if obj.product_id.product_tmpl_id:
                    if obj.product_id.product_tmpl_id.is_category_id:
                        if obj.product_id.product_tmpl_id.is_category_id.fantome==True:
                            type='phantom'
            obj.type=type
    type = fields.Selection([('normal', 'Normal'), ('phantom', 'Fantôme')], 'Type', required=True, compute='_type')

    is_article_fourni = fields.Selection([('oui', 'Oui'), ('non', 'Non')], 'Article fourni', default="non")
    is_qt_uc          = fields.Float("Qt par UC", digits=(12, 2), compute='_compute')
    is_qt_um          = fields.Float("Qt par UM", digits=(12, 2), compute='_compute')
    is_bom            = fields.Boolean('Nomenclature existante' , compute='_compute')


    @api.depends('bom_id.product_tmpl_id', 'product_qty')
    def _compute(self):
        for obj in self:
            obj.is_qt_uc = obj.product_qty*obj.bom_id.product_tmpl_id.get_uc()
            obj.is_qt_um = obj.product_qty*obj.bom_id.product_tmpl_id.get_um()
            product_tmpl_id=obj.product_id.product_tmpl_id.id
            nomenclatures=self.env['mrp.bom'].search([['product_tmpl_id', '=', product_tmpl_id]])
            is_bom=False
            if len(nomenclatures)>0:
                is_bom=True
            obj.is_bom=is_bom


    def action_acces_nomenclature(self):
        for obj in self:
            product_tmpl_id=obj.product_id.product_tmpl_id.id
            nomenclatures=self.env['mrp.bom'].search([['product_tmpl_id', '=', product_tmpl_id]])
            if len(nomenclatures)>0:
                res_id=nomenclatures[0].id
                view_id=self.env.ref('is_plastigray16.is_mrp_bom_form_view')
                return {
                    'name': obj.product_id.name,
                    'view_mode': 'form',
                    'view_type': 'form',
                    'res_model': 'mrp.bom',
                    'type': 'ir.actions.act_window',
                    'view_id': view_id.id,
                    'res_id': res_id,
                }


class mrp_routing(models.Model):
    """Ce modele n'existe plus dans Odoo 16 => Il faut le recréer"""
    _name = 'mrp.routing'
    _description = "Gamme"
    _order = "name"
    
    @api.depends('name')
    def _compute(self):
        for obj in self:
            boms = self.env['mrp.bom'].search([('routing_id','=',obj.id)])
            val=False
            if len(boms)>0:
                val=True
            obj.is_presse_affectee=val
            boms = self.env['mrp.bom'].search([('is_gamme_generique_id','=',obj.id)])
            val=False
            if len(boms)>0:
                val=True
            obj.is_presse_generique=val

    name                = fields.Char("Nom", required=True)
    active              = fields.Boolean("Active", default=True)
    company_id          = fields.Many2one('res.company', 'Company' , default=1)
    workcenter_lines    = fields.One2many('mrp.routing.workcenter', 'routing_id', 'Opérations', copy=True)

    is_presse_affectee  = fields.Boolean("Presse affectée" , store=False, readonly=True, compute='_compute')
    is_presse_generique = fields.Boolean("Presse générique", store=False, readonly=True, compute='_compute')
    is_nb_empreintes    = fields.Integer("Nombre d'empreintes par pièce", default=1, help="Nombre d'empreintes pour cette pièce dans le moule")
    is_coef_theia       = fields.Float("Coefficient Theia"              , default=1, help="Nombre de pièces différentes dans le moule", digits=(14,2))
    is_reprise_humidite = fields.Boolean("Reprise d'humidité")



class mrp_routing_workcenter(models.Model):
    _inherit = 'mrp.routing.workcenter'
    _order   = 'routing_id,sequence'
    
    @api.depends('is_nb_secondes')
    def _hour_nbr(self):
        for obj in self:
            v = 0.0
            obj.hour_nbr=obj.is_nb_secondes/float(3600)
            obj.time_cycle_manual = obj.is_nb_secondes/float(60)

    routing_id = fields.Many2one('mrp.routing', 'Gamme'   , index=True, required=True)                 # Ce champ n'existait plus dans Odoo 16
    bom_id     = fields.Many2one('mrp.bom', 'Nomenclature', index=True, ondelete='set null', required=False, check_company=False) # Ce nouveau champ est obligatoire dans Odoo 16
    company_id = fields.Many2one('res.company', 'Company' , related='routing_id.company_id')

    # bom_id = fields.Many2one(
    #     'mrp.bom', 'Bill of Material',
    #     index=True, ondelete='cascade', required=True, check_company=True)

    hour_nbr         = fields.Float("Nombre d'heures"      , digits=(12,6), store=True, readonly=True, compute='_hour_nbr')
    is_nb_secondes   = fields.Float("Nombre de secondes"   , digits=(12,5), required=False, help="Nombre de secondes")
    is_nb_mod        = fields.Selection([
        ('0.25', '0.25'), 
        ('0.3' , '0.3'), 
        ('0.5' , '0.5'), 
        ('0.75', '0.75'), 
        ('1'   , '1'), 
        ('1.25', '1.25'), 
        ('1.5' , '1.5'), 
        ('1.75', '1.75'), 
        ('2'   , '2'),
        ('2.5' , '2.5'),
        ('3'   , '3'),
        ('4'   , '4'),
    ], 'Nombre de MOD', help='Donnée utilisée en particlier pour le planning')


class is_atelier(models.Model):
    _name='is.atelier'
    _description="is_atelier"
    _order='name'
    name = fields.Char("Atelier", required=True)


class is_ilot(models.Model):
    _name='is.ilot'
    _description="is_ilot"
    _order='name'
    name    = fields.Char("Ilot", required=True)
    atelier = fields.Selection([('Injection', 'Injection'), ('Assemblage', 'Assemblage')], 'Atelier')


class mrp_workcenter(models.Model):
    _inherit = 'mrp.workcenter'
    _order   = 'code,name'

    is_atelier_id  = fields.Many2one('is.atelier', 'Atelier')
    is_ilot_id     = fields.Many2one('is.ilot'   , 'Ilot')
    is_ordre       = fields.Integer("Ordre")
    is_cout_pk     = fields.Float("Coût horaire Plasti-ka")
    is_prioritaire = fields.Boolean("Prioritaire", help="Poste de charge prioritaire")
    resource_type  = fields.Selection([
            ('user'    , 'Humain'),
            ('material', "Matériel"),
        ], "Type de ressource", required=True, default="material")


#TODO : Le modele mrp_production_workcenter_line dans Odoo 8 est devenu mrp.workorder dans Odoo 16
class mrp_production_workcenter_line(models.Model):
    _inherit = 'mrp.workorder'

    sequence         = fields.Integer('Sequence')
    is_ordre         = fields.Integer("Ordre", help="Ordre sur le planning")
    is_qt_restante   = fields.Integer("Quantité restante", help="Quantité restante pour le planning")
    is_tps_restant   = fields.Float("Temps restant", help="Temps restant pour le planning")
    is_date_planning = fields.Datetime('Date planning', help="Date plannifiée sur le planning")
    is_date_tri      = fields.Datetime('Date tri', help="Date de tri du planning")


    def _get_duration_expected(self, alternative_workcenter=False, ratio=1):
        self.ensure_one()
        qty_production = self.production_id.product_uom_id._compute_quantity(self.qty_production, self.production_id.product_id.uom_id)
        capacity = self.workcenter_id._get_capacity(self.product_id)
        cycle_number = float_round(qty_production / capacity, precision_digits=0, rounding_method='UP')
        time_cycle = self.operation_id.time_cycle/60 # J'ai ajouté cette division par 60 sinon le résultat n'était pas en H
        duration = self.workcenter_id._get_expected_duration(self.product_id) + cycle_number * time_cycle * 100.0 / self.workcenter_id.time_efficiency
        return duration


# class mrp_production_workcenter_line(osv.osv):
#     _columns = {
#         'name': fields.char('Work Order', required=True),
#         'workcenter_id': fields.many2one('mrp.workcenter', 'Work Center', required=True),
#         'cycle': fields.float('Number of Cycles', digits=(16, 2)),
#         'hour': fields.float('Number of Hours', digits=(16, 2)),
#         'sequence': fields.integer('Sequence', required=True, help="Gives the sequence order when displaying a list of work orders."),
#         'production_id': fields.many2one('mrp.production', 'Manufacturing Order',
#             track_visibility='onchange', select=True, ondelete='cascade', required=True),
#     }

#     _columns = {
#        'state': fields.selection([('draft','Draft'),('cancel','Cancelled'),('pause','Pending'),('startworking', 'In Progress'),('done','Finished')],'Status', readonly=True, copy=False,
#                                  help="* When a work order is created it is set in 'Draft' status.\n" \
#                                        "* When user sets work order in start mode that time it will be set in 'In Progress' status.\n" \
#                                        "* When work order is in running mode, during that time if user wants to stop or to make changes in order then can set in 'Pending' status.\n" \
#                                        "* When the user cancels the work order it will be set in 'Canceled' status.\n" \
#                                        "* When order is completely processed that time it is set in 'Finished' status."),
#        'date_planned': fields.datetime('Scheduled Date', select=True),
#        'date_planned_end': fields.function(_get_date_end, string='End Date', type='datetime'),
#        'date_start': fields.datetime('Start Date'),
#        'date_finished': fields.datetime('End Date'),
#        'delay': fields.float('Working Hours',help="The elapsed time between operation start and stop in this Work Center",readonly=True),
#        'production_state':fields.related('production_id','state',
#             type='selection',
#             selection=[('draft','Draft'),('confirmed','Waiting Goods'),('ready','Ready to Produce'),('in_production','In Production'),('cancel','Canceled'),('done','Done')],
#             string='Production Status', readonly=True),
#        'product':fields.related('production_id','product_id',type='many2one',relation='product.product',string='Product',
#             readonly=True),
#        'qty':fields.related('production_id','product_qty',type='float',string='Qty',readonly=True, store=True),
#        'uom':fields.related('production_id','product_uom',type='many2one',relation='product.uom',string='Unit of Measure',readonly=True),
#     }

