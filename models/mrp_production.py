# -*- coding: utf-8 -*-

from odoo import models, fields, api, Command
from odoo.tools import float_compare, float_round
from odoo.exceptions import AccessError, ValidationError, UserError
import time
from datetime import datetime, timedelta
import logging
_logger = logging.getLogger(__name__)


class IsMrpProductionWizardLine(models.TransientModel):
    _name = "is.mrp.production.wizard.line"
    _description = "Lignes du Wizard de déclaration de production"

    wizard_id   = fields.Many2one('is.mrp.production.wizard', 'Wizard', required=True, ondelete='cascade')
    product_id  = fields.Many2one("product.product", "Article", required=True)
    qt          = fields.Float("Quantité", required=1, digits='Product Unit of Measure')
    bom_line_id = fields.Many2one("mrp.bom.line", "Ligne")


class IsMrpProductionWizard(models.TransientModel):
    _name = "is.mrp.production.wizard"
    _description = "Wizard de déclaration de production"

    product_id       = fields.Many2one("product.product", "Article", readonly=True)
    bom_id           = fields.Many2one("mrp.bom", "Nomenclature", readonly=True)
    ul_id            = fields.Many2one("is.product.ul", "Conditionnement (UC)", readonly=True)
    package_qty      = fields.Float("Quantité par UC", readonly=True)
    nb_uc            = fields.Float("Nombre d'UC à déclarer", required=1)
    product_qty      = fields.Float("Quantité à déclarer"   , required=1)
    location_dest_id = fields.Many2one("stock.location", "Emplacement des produits finis", required=1)
    line_ids         = fields.One2many('is.mrp.production.wizard.line', 'wizard_id', "Lignes")


    def ok_action(self,is_employee_theia_id=False):
        active_id = self.env.context.get("active_id")
        if active_id:
            production       = self.env['mrp.production'].browse(active_id)
            name             = production.name
            product_id       = self.product_id.id
            product_qty      = self.product_qty
            production_id    = production.id

            #** Sorties des composants ****************************************
            location_id      = production.location_src_id.id
            location_dest_id = self.product_id.property_stock_production.id
            if product_qty<0:
                location_id      = self.product_id.property_stock_production.id
                location_dest_id = production.location_src_id.id
            for line in self.line_ids:
                qty = float_round(line.qt, precision_rounding=line.product_id.uom_id.rounding)
                move_vals={
                    "raw_material_production_id": production_id,
                    "location_id"     : location_id,
                    "location_dest_id": location_dest_id,
                    "product_uom_qty" : abs(qty),
                    "product_id"      : line.product_id.id,
                    "name"            : name,
                    "is_employee_theia_id": is_employee_theia_id,
                }
                move=self.env['stock.move'].with_context({}).create(move_vals) # Il faut effacer le context, sinon erreur avec le champ product_qty
                move._action_confirm()
                if product_qty<0:
                    move.location_dest_id = location_dest_id # Il faut forcer location_dest_id, sinon il met la même chose que location_id
                    move_lines = self.env['stock.move.line'].search([('product_id','=',line.product_id.id),('lot_id','!=', False)], limit=1, order="id desc")
                    if len(move_lines)>0:
                        lot=move_lines[0].lot_id
                        for l in move.move_line_ids:
                            l.lot_id = lot.id
                            l.location_dest_id = location_dest_id
                move.quantity_done = move.product_uom_qty
                move._action_done()
            #******************************************************************

            qty              = product_qty
            location_id      = self.product_id.property_stock_production.id
            location_dest_id = self.location_dest_id.id
            if product_qty<0:
                location_id      = self.location_dest_id.id
                location_dest_id = self.product_id.property_stock_production.id
                qty = - qty

            #** Création lot **************************************************
            lots = self.env['stock.lot'].search([('name','=',name),('product_id','=',product_id)])
            if len(lots)>0:
                lot=lots[0]
            else:
                vals={
                    "name"      : name,
                    "product_id": product_id,
                }
                lot = self.env["stock.lot"].create(vals)
            production.lot_producing_id = lot.id
            #******************************************************************

            #** Création stock.move et stock.move.line ************************
            line_vals={
                "location_id"     : location_id,
                "location_dest_id": location_dest_id,
                "lot_id"          : lot.id,
                "qty_done"        : qty,
                "product_id"      : product_id,
            }
            move_vals={
                #"production_id"   : production_id, # Si j'indique ce champ avant la création du lot, j'ai message => La quantité de xxx débloquée ne peut pas être supérieure à la quantité en stock
                "location_id"     : location_id,
                "location_dest_id": location_dest_id,
                "product_uom_qty" : qty,
                "product_id"      : product_id,
                "name"            : name,
                "is_employee_theia_id": is_employee_theia_id,
                "move_line_ids"   : [[0,False,line_vals]],
            }
            move=self.env['stock.move'].with_context({}).create(move_vals) # Il faut effacer le context, sinon erreur avec le champ product_qty
            move._action_done()
            move.production_id = production_id # Permet d'associer le mouvement à l'ordre de fabrication après sa création
            move.production_id._compute_qt_reste()
            move.create_pg_stock_move_action() # Permet de remettre le lien avec production_id
            #******************************************************************


    @api.onchange('nb_uc')
    def onchange_nb_uc(self):
        self.product_qty = self.nb_uc *  self.package_qty


    @api.onchange('product_qty')
    def onchange_qt(self):
        nb_uc = 0
        if self.package_qty>0:
            nb_uc = self.product_qty/self.package_qty
        self.nb_uc = nb_uc
        lines = self._get_bom_lines()
        self.line_ids = False
        if lines:
            self.line_ids = lines


    def _get_bom_lines(self):
        bom_lines = []
        active_id = self.env.context.get("active_id")
        if active_id:
            production = self.env['mrp.production'].browse(active_id)
            if not production.is_bom_line_ids:
                production._compute_is_bom_line_ids()
            if production.is_bom_line_ids and self.bom_id:
                for line in production.is_bom_line_ids:
                    qt = float_round(line.product_qty * self.product_qty, precision_rounding=line.product_id.uom_id.rounding)
                    vals={
                        "product_id" : line.product_id.id,
                        "qt"         : round(qt,6),
                    }
                    bom_lines.append([0, False, vals])
        return bom_lines


class IsMrpProductionBom(models.Model):
    _name = "is.mrp.production.bom"
    _description = "Nomenclature de l'ordre de production"

    production_id   = fields.Many2one('mrp.production', 'Ordre de production', required=True, ondelete='cascade')
    sequence        = fields.Integer("Séquence")
    product_id      = fields.Many2one("product.product", "Article", required=True)
    product_qty     = fields.Float("Qt nomenclature", required=True, digits='Product Unit of Measure')
    product_uom_id  = fields.Many2one("uom.uom", "Unité", required=True)
    qt_reste        = fields.Float("Qt reste", digits='Product Unit of Measure', compute="_compute_qt_reste")
    is_cbn          = fields.Boolean('CBN', default=True, help="Prise en compte de cette linge dans le CBN")


    @api.depends('product_qty')
    def _compute_qt_reste(self):
        for obj in self:
            qt=obj.production_id.is_qt_reste_uom*obj.product_qty
            obj.qt_reste=qt


    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.product_uom_id = self.product_id.uom_id.id
       

class MrpProduction(models.Model):
    _inherit = "mrp.production"
    _order="name desc"


    @api.depends('bom_id', 'product_id', 'product_qty', 'product_uom_id')
    def _compute_qt_reste(self):
        for obj in self:
            is_qt_rebut=0
            package_qty=0
            is_qt_fabriquee = 0
            is_qt_prevue = 0
            for line in obj.move_lines_produits_finis:
                if line.location_dest_id.scrap_location and line.state=='done':
                    is_qt_rebut=is_qt_rebut+line.product_uom_qty
                else:
                    if line.location_dest_id.usage=='internal' and line.state=='done':
                        is_qt_fabriquee=is_qt_fabriquee+line.product_uom_qty
            for line in obj.move_lines_produits_finis:

                if line.location_id.scrap_location and line.state=='done':
                    is_qt_rebut=is_qt_rebut-line.product_uom_qty
                else:
                    if line.location_id.usage=='internal' and line.state=='done':
                        is_qt_fabriquee=is_qt_fabriquee-line.product_uom_qty
                # if line.location_id.usage=='internal' and line.state=='done':
                #     is_qt_fabriquee=is_qt_fabriquee-line.product_uom_qty
            product_package = False
            if obj.product_id and obj.product_id.packaging_ids:
                pack_brw        = obj.product_id.packaging_ids[0]
                product_package = pack_brw.ul and pack_brw.ul.id or False
                package_qty     = pack_brw.qty
                is_qt_prevue    = obj.product_qty 
            if package_qty==0:
                package_qty=1
            obj.product_package     = product_package
            obj.package_qty         = package_qty
            obj.is_qt_fabriquee_uom = is_qt_fabriquee 
            obj.is_qt_rebut_uom     = is_qt_rebut
            obj.is_qt_reste_uom     = obj.product_qty - obj.is_qt_fabriquee_uom
            obj.is_qt_prevue        = is_qt_prevue / package_qty
            obj.is_qt_fabriquee     = is_qt_fabriquee / package_qty
            obj.is_qt_rebut         = is_qt_rebut / package_qty
            obj.is_qt_reste         = obj.is_qt_prevue - obj.is_qt_fabriquee


    @api.onchange('product_id')
    def _compute_is_bom_line_ids(self):
        for obj in self:
            obj.is_bom_line_ids = False
            bom_lines = []
            if obj.bom_id:
                res = obj.bom_id.explode_phantom()
                for line in res:
                    vals={
                            "product_id"    : line["line"].product_id.id,
                            "product_uom_id": line["line"].product_uom_id.id,
                            "product_qty"   : line["product_qty"],
                            "is_cbn"        : line["line"].is_cbn,
                    }
                    bom_lines.append([0, False, vals])
            obj.is_bom_line_ids = bom_lines


    @api.depends('picking_type_id')
    def _compute_locations(self):
        res=super(MrpProduction, self)._compute_locations()
        #Permet de mettre l'emplacement indiqué dans la fiche article
        for obj in self:
            location_dest_id = obj.product_id.is_emplacement_declaration_prod_id
            if location_dest_id.usage=='internal':
                obj.location_dest_id = location_dest_id.id
        return res


    product_qty = fields.Float('Qt à fabriquer', required=True, readonly=False)  #digits_compute=dp.get_precision('Product Unit of Measure')
    state       = fields.Selection(compute=False, default="draft") #Desactive la fonction compute pour gérer cela autrement
    is_qt_fabriquee_uom       = fields.Float(string="Qt fabriquée"     , compute="_compute_qt_reste", store=True)
    is_qt_rebut_uom           = fields.Float(string="Qt rebut"         , compute="_compute_qt_reste", store=True)
    is_qt_reste_uom           = fields.Float(string="Qt reste"         , compute="_compute_qt_reste", store=True)
    product_package           = fields.Many2one('is.product.ul'        , compute="_compute_qt_reste", store=True, string="Unité de conditionnement")
    package_qty               = fields.Float(string='Qt par UC'        , compute="_compute_qt_reste", store=True)
    is_qt_prevue              = fields.Float(string="Qt prévue (UC)"   , compute="_compute_qt_reste", store=True)
    is_qt_fabriquee           = fields.Float(string="Qt fabriquée (UC)", compute="_compute_qt_reste", store=True)
    is_qt_rebut               = fields.Float(string="Qt rebut (UC)"    , compute="_compute_qt_reste", store=True)
    is_qt_reste               = fields.Float(string="Qt reste (UC)"    , compute="_compute_qt_reste", store=True)
    is_done                   = fields.Boolean(string="Is done ?", default=False)
    mrp_product_suggestion_id = fields.Many2one('mrp.prevision','MRP Product Suggestion')
    is_mold_dossierf          = fields.Char("Moule", help='Moule ou Dossier F', related='product_id.is_mold_dossierf', readonly=True)
    is_num_essai              = fields.Char("N°Essai")
    is_prioritaire            = fields.Boolean("Prioritaire", help="Ordre de fabrication prioritaire")
    move_lines_composants_consommes = fields.One2many('stock.move', 'raw_material_production_id', 'Composants consommés', domain=[('state', 'in', ['done'])]              , readonly=True)
    move_lines_produits_finis       = fields.One2many('stock.move', 'production_id', 'Produits finis', domain=[('state', 'in', ['done'])]                                 , readonly=True)
    is_bom_line_ids                 = fields.One2many('is.mrp.production.bom', 'production_id', "Composants à consommer", copy=False, states={'done': [('readonly', True)]})
    

    @api.ondelete(at_uninstall=False)
    def _unlink_except_done(self):
        if any(production.state == 'done' for production in self):
            raise UserError('Impossible de supprimer un OF terminé')
        if any(production.move_lines_produits_finis for production in self):
            raise UserError('Impossible de supprimer un OF démarré')


    @api.depends('product_id', 'bom_id', 'product_qty', 'product_uom_id', 'location_dest_id', 'date_planned_finished')
    def _compute_move_finished_ids(self):
        "Désactive cette fonction standard, car il n'est pas utile de mettre à jour le champ move_finished_ids"
        return True


    @api.depends('company_id', 'bom_id', 'product_id', 'product_qty', 'product_uom_id', 'location_src_id', 'date_planned_start')
    def _compute_move_raw_ids(self):
        "Désactive cette fonction standard, car il n'est pas utile de générer des mouvements de stock de réservation"
        return True


    @api.onchange('product_id')
    def onchange_product_id_pg(self):
        self.product_qty = self.product_id.lot_mini


    @api.depends('bom_id', 'product_id', 'product_qty', 'product_uom_id')
    def _compute_workorder_ids(self):
        for production in self:
            if production.state != 'draft' or len(production.workorder_ids)>0:
                continue
            workorders_list = [Command.link(wo.id) for wo in production.workorder_ids.filtered(lambda wo: not wo.operation_id)]
            if not production.bom_id and not production._origin.product_id:
                production.workorder_ids = workorders_list
            if production.product_id != production._origin.product_id:
                production.workorder_ids = [Command.clear()]
            if production.bom_id and production.product_id and production.product_qty > 0:
                # keep manual entries
                workorders_values = []
                product_qty = production.product_uom_id._compute_quantity(production.product_qty, production.bom_id.product_uom_id)
                exploded_boms, dummy = production.bom_id.explode(production.product_id, product_qty / production.bom_id.product_qty, picking_type=production.bom_id.picking_type_id)
                for bom, bom_data in exploded_boms:
                    # If the operations of the parent BoM and phantom BoM are the same, don't recreate work orders.
                    #if not (bom.operation_ids and (not bom_data['parent_line'] or bom_data['parent_line'].bom_id.operation_ids != bom.operation_ids)):
                    #    continue
                    for operation in bom.routing_id.workcenter_lines:
                        if operation._skip_operation_line(bom_data['product']):
                            continue
                        workorders_values += [{
                            'sequence': operation.sequence,
                            'name': operation.name,
                            'production_id': production.id,
                            'workcenter_id': operation.workcenter_id.id,
                            'product_uom_id': production.product_uom_id.id,
                            'operation_id': operation.id,
                            'state': 'pending',
                        }]
                workorders_dict = {wo.operation_id.id: wo for wo in production.workorder_ids.filtered(lambda wo: wo.operation_id)}
                for workorder_values in workorders_values:
                    if workorder_values['operation_id'] in workorders_dict:
                        # update existing entries
                        workorders_list += [Command.update(workorders_dict[workorder_values['operation_id']].id, workorder_values)]
                    else:
                        # add new entries
                        workorders_list += [Command.create(workorder_values)]                    
                production.workorder_ids = workorders_list
            else:
                production.workorder_ids = [Command.delete(wo.id) for wo in production.workorder_ids.filtered(lambda wo: wo.operation_id)]


    def init_nomenclature_action(self):
        for obj in self:
            if obj.state=='draft' and not obj.is_bom_line_ids:
                obj._compute_is_bom_line_ids()
        return True


    def init_qt_reste_action(self):
        for obj in self:
            obj._compute_qt_reste()
        return True


    def init_operation_id_action(self):
        for obj in self:
            for line in obj.bom_id.routing_id.workcenter_lines:
                for operation in obj.workorder_ids:
                    if line.sequence==operation.sequence and line.workcenter_id==operation.workcenter_id and not operation.operation_id:
                        operation.operation_id = line.id
        return True


    def voir_composants_consommes_action(self):
        for obj in self:
            tree_view=self.env.ref('is_plastigray16.is_mouvements_termines_tree')
            return {
                'name': "Composants consommés %s"%(obj.name),
                'view_mode': 'tree,form',
                'views': [[tree_view.id, "list"], [False, "form"]],
                'res_model': 'stock.move',
                'type': 'ir.actions.act_window',
                'domain': [('raw_material_production_id','=',obj.id),('state', 'in', ['done'])],
                'limit': 1000,
            }
        

    def voir_produits_finis_action(self):
        for obj in self:
            tree_view=self.env.ref('is_plastigray16.is_mouvements_termines_tree')
            return {
                'name': "Composants consommés %s"%(obj.name),
                'view_mode': 'tree,form',
                'views': [[tree_view.id, "list"], [False, "form"]],
                'res_model': 'stock.move',
                'type': 'ir.actions.act_window',
                'domain': [('production_id','=',obj.id),('state', 'in', ['done'])],
                'limit': 1000,
            }


    def liste_mouvements_action(self):
        for obj in self:
            tree_view=self.env.ref('is_plastigray16.is_mouvements_termines_tree')
            return {
                'name': "Mouvements %s"%(obj.name),
                'view_mode': 'tree,form',
                'views': [[tree_view.id, "list"], [False, "form"]],
                'res_model': 'stock.move',
                'type': 'ir.actions.act_window',
                #'domain': ['|',('production_id','=',obj.id),('raw_material_production_id','=',obj.id),('state','!=','draft')],
                'domain': ['|',('production_id','=',obj.id),('raw_material_production_id','=',obj.id)],
                'limit': 1000,
            }


    def vers_done_action(self):
        for obj in self:
            obj.move_raw_ids.filtered(lambda wo: wo.state=='draft').unlink()
            obj.move_finished_ids.filtered(lambda wo: wo.state=='draft').unlink()
            obj.state="done"


    def _get_fabrication_context(self):
        for obj in self:
            new_context = dict(self.env.context).copy()
            new_context.update({
                "default_product_id"      : obj.product_id.id,
                "default_bom_id"          : obj.bom_id.id,
                "default_ul_id"           : obj.product_package.id,
                "default_location_dest_id": obj.location_dest_id.id,
                "default_package_qty"     : obj.package_qty,
                "default_product_qty"     : obj.package_qty,
            })
            return new_context


    def fabriquer_action(self):
        for obj in self:
            new_context = obj._get_fabrication_context()
            return {
                'name': "Déclaration de production %s"%(obj.name),
                'view_mode': 'form',
                'res_model': 'is.mrp.production.wizard',
                'type': 'ir.actions.act_window',
                "context": new_context,
                'target': 'new',
            }


    def test_declaration_theia_uc_action(self):
        "TEST Déclaration THEIA 1 UC"
        for obj in self:
            employe_id = 560 # Tony
            obj.declaration_production_theia_action(obj.package_qty,0,employe_id)


    def test_declaration_theia_rebut_action(self):
        "TEST Déclaration THEIA 10 rebuts"
        for obj in self:
            employe_id = 560 # Tony
            obj.declaration_production_theia_action(0,10,employe_id)


    def declaration_production_theia_action(self,qt_bonne, qt_rebut, is_employee_theia_id=False):
        err=""
        for obj in self:
            qt=0
            err=""
            location_id = False
            if qt_bonne>0:
                qt=qt_bonne
                location_id = obj.location_dest_id.id
                # filtre = [
                #     ('name' , '=', 'ATELIER'),
                #     ('usage', '=', 'internal'),
                # ]
            if qt_rebut>0:
                qt=qt_rebut
                filtre = [
                    ('name' , '=', 'Rebuts'),
                    ('usage', '=', 'inventory'),
                ]
                lines = self.env["stock.location"].search(filtre)
                location_id = lines and lines[0].id or False
                if location_id==False:
                    err="Emplacement non trouve"


            if qt==0:
                err="Qt = 0"
            if err=="":
                #** Création du wizard ****************************************
                wiz_obj = self.env['is.mrp.production.wizard']
                vals = {
                    'product_id'      : obj.product_id.id,
                    'bom_id'          : obj.bom_id.id,
                    'ul_id'           : obj.product_package.id,
                    'location_dest_id': location_id,
                    'package_qty'     : obj.package_qty,
                    'product_qty'     : qt,
                    'nb_uc'           : 0,
                }
                wiz = wiz_obj.create(vals)
                wiz.onchange_qt()
                lines = wiz.with_context(active_id=obj.id)._get_bom_lines()
                wiz.line_ids = lines
                if qt_rebut>0:
                    for line in wiz.line_ids:
                        code = line.product_id.is_code
                        if code[:1]!="5":
                            line.unlink()
                res = wiz.with_context(active_id=obj.id).ok_action(is_employee_theia_id=is_employee_theia_id)
                #**************************************************************
        res=True
        if err!="":
            res={"err": err}
        return res
    

    def get_wizard(self, production):
        #wiz_obj = self.env['mrp.product.produce']
        wiz_obj = self.env['is.mrp.production.wizard']
        vals = {
            'product_id': production.product_id.id,
            'nb_uc': 1.0,
        }
        wiz = wiz_obj.create(vals)
        return wiz


    def envoi_mail(self, email_from,email_to,email_cc,subject,body_html):
        for obj in self:
            vals={
                'email_from'    : email_from, 
                'email_to'      : email_to, 
                'email_cc'      : email_cc,
                'subject'       : subject,
                'body_html'     : body_html, 
                'model'         : self._name,
                'res_id'        : obj.id,
            }
            email=self.env['mail.mail'].create(vals)
            if email:
                self.env['mail.mail'].send(email)


    def mail_quantite_modifiee(self, qt1, qt2):
        for obj in self:
            test=False
            date_planned = obj.date_planned_start
            now = datetime.now()
            date_fin = now + timedelta(days=1)
            if date_planned<=date_fin:
                test=True
            if test==False:
                ofs = self.env["is.of"].search([('name', '=', obj.name),('heure_debut','!=',False),('heure_fin','=',False)])
                if len(ofs)>0:
                    test=True
            if test:
                groupes = self.env["is.theia.validation.groupe"].search([('name', '=', "Mail modification quantité OF")])
                email_to=[]
                for groupe in groupes:
                    for employe in groupe.employee_ids:
                        if employe.is_courriel:
                            email_to.append(employe.is_courriel)
                        else:
                            if employe.user_id.partner_id.email:
                                email_to.append(employe.user_id.partner_id.email)
                if email_to:
                    subject=u"["+obj.name+u"] Quantité modifiée de %s vers %s"%(int(qt1), qt2)
                    email_to = u','.join(email_to)
                    _logger.info(subject+u" (%s)"%(email_to))
                    user  = self.env['res.users'].browse(self._uid)
                    email_from = user.email
                    email_cc   = False
                    nom   = user.name
                    base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                    url=base_url+u'/web#id='+str(obj.id)+u'&view_type=form&model=mrp.production'
                    body_html=u"""
                        <p>Bonjour,</p>
                        <p>"""+nom+""" vient de modifier la quantité de <a href='"""+url+"""'>"""+obj.name+"""</a>.</p>
                        <p>Merci d'en prendre connaissance.</p>
                    """
                    self.envoi_mail(email_from,email_to,email_cc,subject,body_html)


    def write(self, vals):
        vals = vals or {}
        if 'product_qty' in vals:
            for obj in self:
                obj.mail_quantite_modifiee(obj.product_qty,  vals["product_qty"])
        res=super(MrpProduction, self).write(vals)
        return res


