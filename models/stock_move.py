# -*- coding: utf-8 -*-
from odoo import models,fields,api
from odoo.osv import expression
import string
import re
import logging
_logger = logging.getLogger(__name__)


class stock_move(models.Model):
    _inherit = "stock.move"
    _order   = "date desc, id"


    @api.depends('product_id','product_uom_qty','picking_id.state')
    def _compute_lots(self):
        cr = self._cr
        for obj in self:
            lots = False
            if obj.picking_id.sale_id.is_liste_servir_id.galia_um_ids:
                liste_servir_id = obj.picking_id.sale_id.is_liste_servir_id.id
                # SQL="""
                #     select uc.production, sum(uc.qt_pieces)
                #     from is_galia_base_uc uc inner join is_galia_base_um um on uc.um_id=um.id
                #                             inner join is_liste_servir ls on um.liste_servir_id=ls.id
                #                             inner join product_product pp on uc.product_id=pp.id 
                #                             inner join product_template pt on pp.product_tmpl_id=pt.id
                #     where ls.id=%s and uc.product_id=%s
                #     group by uc.production
                #     order by uc.production
                # """
                # cr.execute(SQL,[liste_servir_id, obj.product_id.id])
                # result = cr.fetchall()
                # lots=[]
                # for row in result:
                #     lots.append("Lot "+(row[0] or '')+" : "+str(row[1]))
                # lots = u"\n".join(lots)

                #TODO : modification du 20/05/2025
                mydict={}
                for uc in obj.is_uc_ids:
                    lot = uc.production
                    if lot not in mydict:
                        mydict[lot]=0
                    mydict[lot]+=uc.qt_pieces
                if len(mydict):
                    lots=[]
                    sorted_dict = dict(sorted(mydict.items())) 
                    for lot in sorted_dict:
                        lots.append("Lot %s : %s"%(lot, sorted_dict[lot]))
                    lots = u"\n".join(lots)

            if obj.is_uc_rcp_ids:
                res={}
                for uc in obj.is_uc_rcp_ids:
                    if uc.production not in res:
                        res[uc.production]=0
                    res[uc.production]+=uc.qt_pieces
                if len(res)>0:
                    lots=[]
                    for k in res:
                        lots.append("Lot "+(k or '')+" : "+str(res[k]))
                    lots = u"\n".join(lots)
            obj.is_lots = lots


    @api.depends('product_id','product_uom_qty')
    def _compute_is_point_dechargement(self):
        for obj in self:
            obj.is_point_dechargement = obj.picking_id.sale_id.is_point_dechargement
            # x = False
            # if obj.picking_id.partner_id.is_traitement_edi:
            #     filtre = [
            #         ('partner_id'            , '=', obj.picking_id.partner_id.id),
            #         ('is_article_commande_id', '=', obj.product_id.id),
            #         ('is_type_commande'      , '=', 'ouverte'),
            #         ('state'                 , '=', 'draft'),
            #     ]
            #     orders = self.env['sale.order'].search(filtre)
            #     for order in orders:
            #         x = order.is_point_dechargement
            # obj.is_point_dechargement = x


    is_sale_line_id               = fields.Many2one('sale.order.line', 'Ligne de commande (Champ désactivé dans Odoo 16 et remplacé par sale_line_id)', index=True)  #Le champ sale_line_id existe par défaut dans Odoo 16
    is_lot_id                     = fields.Many2one('stock.lot', 'Lot', domain="[('product_id','=',product_id)]", help="Lot forcé pour les mouvements créés manuellement")
    is_lots                       = fields.Text('Lots', compute='_compute_lots', store=True, readonly=True, copy=False)
    is_dosmat_ctrl_qual           = fields.Char('Contrôle qualité', readonly=True)
    is_dosmat_conditions_stockage = fields.Char('Conditions de stockage', readonly=True)
    is_point_dechargement         = fields.Char('Point de déchargement', compute='_compute_is_point_dechargement', store=False, readonly=True)
    is_employee_theia_id          = fields.Many2one('hr.employee', 'Employé Theia')

    is_amortissement_moule  = fields.Float('Amt client négocié'        , digits=(14,4))
    is_amt_interne          = fields.Float('Amt interne'               , digits=(14,4))
    is_cagnotage            = fields.Float('Cagnotage'                 , digits=(14,4))
    is_montant_amt_moule    = fields.Float('Montant amt client négocié', digits=(14,2))
    is_montant_amt_interne  = fields.Float('Montant amt interne'       , digits=(14,2))
    is_montant_cagnotage    = fields.Float('Montant cagnotage'         , digits=(14,2))
    is_montant_matiere      = fields.Float('Montant matière livrée'    , digits=(14,2))
    is_account_move_line_id = fields.Many2one("account.move.line", "Ligne de facture" )     # Champ ajouté pour Odoo 16 pour faire le lien entre les lignes des factures et les livraisons
    inventory_id            = fields.Many2one("stock.inventory", "Inventaire", index=True ) # Champ dans Odoo 8 et supprimé dans Odoo 16
    is_location_dest_prevu_id = fields.Many2one('stock.location', 'Emplacement prévu', compute='_compute_is_location_dest_prevu_id', store=False, readonly=True)
    is_unit_coef            = fields.Float('US/UA', help="Unité de réception / Unité d'achat", digits=(14,6), compute='_compute_montant_reception', store=True, readonly=True)
    is_montant_reception    = fields.Float('Montant réception'                 , digits=(14,2), compute='_compute_montant_reception', store=True, readonly=True)
    is_uc_ids               = fields.One2many('is.galia.base.uc', 'stock_move_id', "UCs")
    is_uc_rcp_ids           = fields.One2many('is.galia.base.uc', 'stock_move_rcp_id', "UCs Réception")
    is_qt_uc                = fields.Float('Qt UC'    , readonly=True, copy=False, digits=(14,4), help="Total de la quantité des UC scannées")
    is_uc_galia             = fields.Text('UC (Galia)', readonly=True, copy=False)
    is_um_galia             = fields.Text('UM (Galia)', readonly=True, copy=False)
    is_uc                   = fields.Text('UC'        , readonly=True, copy=False, help="UC sans indiquer le lot pour Stellantis")


    def compute_is_uc_galia(self):
        for obj in self:
            um_ids=[]
            qt_uc=0
            lines_uc=[] 
            lines_um=[]
            uc_ids=False
            if obj.is_uc_ids:
                uc_ids=obj.is_uc_ids
            if obj.is_uc_rcp_ids:
                uc_ids=obj.is_uc_rcp_ids
            if uc_ids:
                for uc in uc_ids:
                    if uc.um_id.id not in um_ids:
                        um_ids.append(uc.um_id.id)
                ums = self.env['is.galia.base.um'].search([('id', 'in', um_ids)],order="name")
                for um in ums: 
                    first=False
                    def set_num_uc(first,last,lot):
                        if first==last:
                            num = "%s [%s]"%(str(first),lot)
                        else:
                            num = "%s à %s [%s]"%(str(first),str(last)[-3:],lot)
                        return num
                    def set_num_um(uc,um,ct):
                        if ct==0:
                            if uc.product_id.is_um_egale_uc:
                                num=str(uc.num_eti)
                            else:
                                num = um.name
                        else:
                            num='.'
                        return num
                    ucs = self.env['is.galia.base.uc'].search([('um_id', '=', um.id)],order="num_eti")
                    ct=0
                    for uc in ucs:
                        if uc.product_id==obj.product_id and (uc.stock_move_id==obj or uc.stock_move_rcp_id==obj):
                            qt_uc+=uc.qt_pieces
                            lot = uc.production
                            num = int(uc.num_eti)
                            if not first:
                                first = last = suivant = num
                            if num==suivant:
                                last=num
                            else:
                                lines_uc.append(set_num_uc(first,last,lot))
                                lines_um.append(set_num_um(uc,um,ct))
                                ct+=1
                                first=last=num
                            suivant = num+1
                    if first:
                        lines_uc.append(set_num_uc(first,last,lot))
                        lines_um.append(set_num_um(uc,um,ct))
                        ct+=1
            lines_uc_sans_lot=[]
            for line in lines_uc:
                uc=''
                x = re.search("(.*) (\[.*\])", line) 
                if x:
                    v = x.groups()
                    if len(v)>0:
                        uc=v[0]
                lines_uc_sans_lot.append(uc)
            obj.is_uc       = "\n".join(lines_uc_sans_lot)
            obj.is_uc_galia = "\n".join(lines_uc)
            obj.is_um_galia = "\n".join(lines_um)
            obj.is_qt_uc = qt_uc


    @api.depends('purchase_line_id','state','product_uom','product_uom_qty')
    def _compute_montant_reception(self):
        for obj in self:
            coef = 1
            montant_reception=0
            if obj.purchase_line_id:
                try:
                    coef = round(obj.purchase_line_id.product_uom._compute_quantity(1, obj.product_uom),6)
                except Exception:
                    coef = 1
                if coef>0:
                    montant_reception = round(obj.product_uom_qty*obj.purchase_line_id.price_unit/coef,6)
                _logger.info("_compute_montant_reception (move_id=%s, article=%s, montant=%s)"%(obj.id, obj.product_id.is_code, montant_reception))
            obj.is_unit_coef         = coef
            obj.is_montant_reception = montant_reception


    @api.depends('location_dest_id')
    def _compute_is_location_dest_prevu_id(self):
        for obj in self:
            location_id = obj.location_dest_id
            if  obj.picking_id.is_purchase_order_id:
                location_id = obj.picking_id.is_purchase_order_id.location_id.id
                if obj.product_id.is_ctrl_rcp=='bloque':
                    locations = self.env['stock.location'].search([('name','=','Q2')])
                    for location in locations:
                        location_id=location.id
            obj.is_location_dest_prevu_id = location_id


    #TODO Ce champ  a disparru dans Odoo 16 => Je l'ai remis pour conserver le même principe de facturation des réceptions
    invoice_state = fields.Selection([
        ('2binvoiced', u'à Facturer'),
        ('none'      , u'Annulé'),
        ('invoiced'  , u'Facturé'),
    ], u"État facturation", index=True)


    def name_get(self):
        res=[]
        for obj in self:
            name=obj.product_id.is_code+u' / '+ u'qt='+str(obj.product_uom_qty) 
            if obj.picking_id:
                name=name + u' / bl='+str(obj.picking_id.name)
            if obj.origin:
                name=name + u' / '+str(obj.origin)
            name=name+u' / id='+str(obj.id)
            res.append((obj.id, name))
        return res


    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            try:
                id = int(name)
            except ValueError:
                id = 0
            if id>1000000:
                domain=[('id','=', name)]
            else:
                if id>0:
                    domain=['|','|','|',('product_id','ilike', name),('reference','ilike', name),('origin','ilike', name),('id','=', name)]
                else:
                    domain=['|','|',('product_id.is_code','ilike', name),('reference','ilike', name),('origin','ilike', name)]
        res = self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
        return res


    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for obj in res:
            vals=obj.update_amortissement_moule()
            obj.write(vals)
            if obj.purchase_line_id and obj.picking_id:
                obj.picking_id.is_purchase_order_id=obj.purchase_line_id.order_id.id
        return res


    def write(self, vals):
        v=self.update_amortissement_moule()
        if v:
            vals.update(v)
        res=super().write(vals)
        return res


    def _action_done(self, cancel_backorder=False):
        res = super(stock_move, self)._action_done(cancel_backorder=cancel_backorder)
        self.create_pg_stock_move()
        return res


    def create_pg_stock_move_action(self):
        for obj in self:
            self.env['pg.stock.move'].search([('move_id', '=', obj.id)]).unlink()
        self.create_pg_stock_move()
        return True


    #TODO : A revoir => Ne pas mettre de lien vers pg_stock_move depuis stock_move
    #@api.depends('product_id','quantity_done', 'state', 'picking_id')
    def create_pg_stock_move(self):
        for obj in self:
            move_id=False
            if obj.state=='done':
                #** Regroupement des lignes identiques + somme qty ************
                dict={}
                for line in obj.move_line_ids:
                    key = "%s-%s-%s"%(line.lot_id,line.location_id,line.location_dest_id)
                    if key not in dict:
                        dict[key]={}
                        dict[key]["line"]=line
                        dict[key]["qty"]=0
                    qty = line.product_uom_id._compute_quantity(line.qty_done, line.product_id.uom_id) #, round=True, rounding_method='UP', raise_if_failure=True):
                    dict[key]["qty"]+=qty
                #**************************************************************
                for key in dict:
                    line = dict[key]["line"]
                    qty  = dict[key]["qty"]
                    location_dest_id = line.location_dest_id
                    if line.location_id.usage=="internal" and line.location_dest_id.usage!="internal":
                        location_dest_id = line.location_id
                        qty=-qty
                    if qty!=0:
                        vals={
                            "move_id": obj.id,
                            "date": obj.date,
                            "product_id": obj.product_id.id,
                            "name": obj.name,
                            "origin": obj.origin,
                            "category": obj.product_id.is_category_id.name,
                            "mold": obj.product_id.is_mold_dossierf,
                            "picking_type_id": obj.picking_type_id.id,
                            "picking_id": obj.picking_id.id,
                            "lot_id": line.lot_id.id,
                            "lot_fournisseur": line.lot_id.is_lot_fournisseur,
                            "qty": qty,
                            "product_uom": obj.product_id.uom_id.id,
                            "location_dest_id": location_dest_id.id,
                            "login": obj.write_uid.partner_id.name,
                            "is_employee_theia_id": obj.is_employee_theia_id.id,
                            "purchase_line_id": obj.purchase_line_id.id,
                            "production_id": obj.production_id.id or obj.raw_material_production_id.id,
                            "sale_line_id": obj.sale_line_id.id,
                        }
                        self._create_pg_stock_move(vals)
                        if line.location_id.usage=="internal" and line.location_dest_id.usage=="internal":
                            vals["location_dest_id"] = line.location_id.id
                            vals["qty"]              = -qty
                            self._create_pg_stock_move(vals)
        return True


    def _create_pg_stock_move(self, vals):
        self.env['pg.stock.move'].create(vals)




    def access_stock_move_action(self):
        for obj in self:
            res= {
                'name': 'Mouvement',
                'view_mode': 'form',
                'res_model': 'stock.move',
                'res_id': obj.id,
                'type': 'ir.actions.act_window',
            }
            return res


    def is_valider_action(self):
        for obj in self:
            line_vals={
                "location_id"     : obj.location_id.id,
                "location_dest_id": obj.location_dest_id.id,
                "lot_id"          : obj.is_lot_id.id,
                "qty_done"        : obj.product_uom_qty,
                "product_id"      : obj.product_id.id,
                "move_id"         : obj.id,
            }
            filtre=[('code', '=', 'internal')]
            picking_type_id = self.env['stock.picking.type'].search(filtre)[0]
            picking_vals={
                "picking_type_id" : picking_type_id.id,
                "location_id"     : obj.location_id.id,
                "location_dest_id": obj.location_dest_id.id,
                'move_line_ids'   : [[0,False,line_vals]],
            }
            picking=self.env['stock.picking'].create(picking_vals)
            obj.picking_id=picking.id
            picking.action_confirm()
            picking._action_done()


    def is_raz_action(self):
        for obj in self:
            obj.move_line_ids.unlink()


    def is_confirm_action(self):
        for obj in self:
            obj._action_confirm()
            obj.quantity_done = obj.product_uom_qty


    def is_assign_action(self):
        for obj in self:
            obj._action_assign()


    def is_fait_reserve_action(self):
        for obj in self:
            for line in obj.move_line_ids:
                line.qty_done = line.reserved_uom_qty


    def is_creer_lot_action(self):
        for obj in self:
            name=obj.name
            lots = self.env['stock.lot'].search([('name','=',name),('product_id','=',obj.product_id.id)])
            if len(lots)>0:
                lot=lots[0]
            else:
                vals={
                    "name"      : name,
                    "product_id": obj.product_id.id,
                }
                lot = self.env["stock.lot"].create(vals)
            vals = obj._prepare_move_line_vals(1)
            line=self.env['stock.move.line'].create(vals)
            obj.production_id.lot_producing_id = lot.id


    def is_done_action(self):
        for obj in self:
            obj._action_done()
            for line in obj.move_line_ids:
                line._action_done()
 

    def update_amortissement_moule(self):
        cr = self._cr
        for obj in self:
            amortissement_moule = 0
            amt_interne = 0
            cagnotage = 0
            montant_amt_moule = 0
            montant_amt_interne = 0
            montant_cagnotage = 0
            montant_matiere = 0
            if obj.picking_id and obj.product_id and obj.product_uom_qty and obj.picking_id.is_date_expedition:
                SQL="""
                    SELECT
                        get_amortissement_moule_a_date(rp.is_code, pt.id, sp.is_date_expedition) as is_amortissement_moule,
                        get_amt_interne_a_date(rp.is_code, pt.id,  sp.is_date_expedition) as is_amt_interne,
                        get_cagnotage_a_date(rp.is_code, pt.id,  sp.is_date_expedition) as is_cagnotage,
                        get_amortissement_moule_a_date(rp.is_code, pt.id,  sp.is_date_expedition)*sm.product_uom_qty as is_montant_amt_moule,
                        get_amt_interne_a_date(rp.is_code, pt.id,  sp.is_date_expedition)*sm.product_uom_qty as is_montant_amt_interne,
                        get_cagnotage_a_date(rp.is_code, pt.id,  sp.is_date_expedition)*sm.product_uom_qty as is_montant_cagnotage,
                        get_cout_act_matiere_st(pp.id)*sm.product_uom_qty as is_montant_matiere,
                        sp.is_date_expedition,
                        sm.state
                    from stock_picking sp inner join stock_move        sm on sm.picking_id=sp.id
                                          inner join product_product   pp on sm.product_id=pp.id
                                          inner join product_template  pt on pp.product_tmpl_id=pt.id
                                          inner join res_partner       rp on sp.partner_id=rp.id
                    where sm.id=%s
                """
                cr.execute(SQL,[obj.id])
                res_ids = cr.fetchall()
                for res in res_ids:
                    amortissement_moule = res[0]
                    amt_interne         = res[1]
                    cagnotage           = res[2]
                    montant_amt_moule   = res[3]
                    montant_amt_interne = res[4]
                    montant_cagnotage   = res[5]
                    montant_matiere     = res[6]
            vals={
                "is_amortissement_moule": amortissement_moule,
                "is_amt_interne"        : amt_interne,
                "is_cagnotage"          : cagnotage,
                "is_montant_amt_moule"  : montant_amt_moule,
                "is_montant_amt_interne": montant_amt_interne,
                "is_montant_cagnotage"  : montant_cagnotage,
                "is_montant_matiere"    : montant_matiere,
            }
            return vals


    def _create_invoice_line_from_vals(self, cr, uid, move, invoice_line_vals, context=None):
        """
        Permet d'ajouter le lien avec la livraison et la section analytique sur
        les lignes des factures
        """
        if move:
            is_section_analytique_id=move.product_id.is_section_analytique_id.id
            invoice_line_vals['is_move_id']=move.id
            invoice_line_vals['is_section_analytique_id']=is_section_analytique_id
        res = super(stock_move, self)._create_invoice_line_from_vals(cr, uid, move, invoice_line_vals, context)
        return res


    def action_acceder_mouvement_stock(self):
        view_id = self.env.ref('stock.view_move_form').id
        for obj in self:
            return {
                'name': "Mouvement de stock",
                'view_mode': 'form',
                'view_id': view_id,
                'res_model': 'stock.move',
                'type': 'ir.actions.act_window',
                'res_id': obj.id,
                'domain': '[]',
            }


    def get_working_day(self, date, num_day, jours_fermes, leave_dates):
        """ Déterminer la date de livraison en fonction des jours de fermeture ou des jours de congés
        """
        if int(num_day) not in jours_fermes and date not in leave_dates:
            return date
        else:
            date = datetime.datetime.strptime(date, '%Y-%m-%d') + datetime.timedelta(days=1)
            date = date.strftime('%Y-%m-%d')
            num_day = time.strftime('%w', time.strptime(date, '%Y-%m-%d'))
            return self.get_working_day(date, num_day, jours_fermes, leave_dates)


    def _get_date_livraison(self,date_expedition):
        date_livraison=date_expedition
        for obj in self:
            date_livraison= self.env['res.partner'].get_date_livraison(obj.company_id, obj.partner_id, date_expedition)
        return date_livraison






