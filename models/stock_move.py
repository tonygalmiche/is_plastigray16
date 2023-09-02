# -*- coding: utf-8 -*-
import string
from odoo import models,fields,api


class stock_move(models.Model):
    _inherit = "stock.move"
    _order   = "date desc, id"


    @api.depends('product_id','product_uom_qty')
    def _compute_lots(self):
        cr = self._cr
        for obj in self:
            lots = False
            if obj.picking_id.sale_id.is_liste_servir_id.galia_um_ids:
                liste_servir_id = obj.picking_id.sale_id.is_liste_servir_id.id
                SQL="""
                    select uc.production, sum(uc.qt_pieces)
                    from is_galia_base_uc uc inner join is_galia_base_um um on uc.um_id=um.id
                                            inner join is_liste_servir ls on um.liste_servir_id=ls.id
                                            inner join product_product pp on uc.product_id=pp.id 
                                            inner join product_template pt on pp.product_tmpl_id=pt.id
                    where ls.id=%s and uc.product_id=%s
                    group by uc.production
                    order by uc.production
                """
                cr.execute(SQL,[liste_servir_id, obj.product_id.id])
                result = cr.fetchall()
                lots=[]
                for row in result:
                    lots.append(u"Lot "+row[0]+u" : "+str(row[1]))
                lots = u"\n".join(lots)
            obj.is_lots = lots


    @api.depends('product_id','product_uom_qty')
    def _compute_is_point_dechargement(self):
        for obj in self:
            x = False
            if obj.picking_id.partner_id.is_traitement_edi:
                filtre = [
                    ('partner_id'            , '=', obj.picking_id.partner_id.id),
                    ('is_article_commande_id', '=', obj.product_id.id),
                    ('is_type_commande'      , '=', 'ouverte'),
                    ('state'                 , '=', 'draft'),
                ]
                orders = self.env['sale.order'].search(filtre)
                for order in orders:
                    x = order.is_point_dechargement
            obj.is_point_dechargement = x


    #is_pg_stock_move_id           = fields.Many2one('pg.stock.move', 'Mouvement PG', compute='_compute_is_pg_stock_move_id', store=True, readonly=True)
    is_sale_line_id               = fields.Many2one('sale.order.line', 'Ligne de commande (Champ désactivé dans Odoo 16 et remplacé par sale_line_id)', index=True)  #Le champ sale_line_id existe par défaut dans Odoo 16
    is_lot_id                     = fields.Many2one('stock.lot', 'Lot', domain="[('product_id','=',product_id)]", help="Lot forcé pour les mouvements créés manuellement")
    is_lots                       = fields.Text(u'Lots', compute='_compute_lots', store=False, readonly=True)
    is_dosmat_ctrl_qual           = fields.Char(u'Contrôle qualité', readonly=True)
    is_dosmat_conditions_stockage = fields.Char(u'Conditions de stockage', readonly=True)
    is_point_dechargement         = fields.Char(u'Point de déchargement', compute='_compute_is_point_dechargement', store=False, readonly=True)
    is_employee_theia_id          = fields.Many2one('hr.employee', 'Employé Theia')

    is_amortissement_moule = fields.Float('Amt client négocié'        , digits=(14,4))
    is_amt_interne         = fields.Float('Amt interne'               , digits=(14,4))
    is_cagnotage           = fields.Float('Cagnotage'                 , digits=(14,4))
    is_montant_amt_moule   = fields.Float('Montant amt client négocié', digits=(14,2))
    is_montant_amt_interne = fields.Float('Montant amt interne'       , digits=(14,2))
    is_montant_cagnotage   = fields.Float('Montant cagnotage'         , digits=(14,2))
    is_montant_matiere     = fields.Float('Montant matière livrée'    , digits=(14,2))

    #TODO Ce champ  a disparru dans Odoo 16 => Je l'ai remis pour conserver le même principe de facturation des réceptions
    invoice_state = fields.Selection([
        ('2binvoiced', u'à Facturer'),
        ('none'      , u'Annulé'),
        ('invoiced'  , u'Facturé'),
    ], u"État facturation", readonly=True, index=True)


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


    def name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        if not args:
            args = []
        if name:
            try:
                id = int(name)
            except ValueError:
                id = 0
            if id>0:
                filtre=['|','|','|',('product_id.is_code','ilike', name),('picking_id.name','ilike', name),('origin','ilike', name),('id','=', name)]
            else:
                filtre=['|','|',('product_id.is_code','ilike', name),('picking_id.name','ilike', name),('origin','ilike', name)]
            ids = list(self._search(filtre + args, limit=limit))
        else:
            ids = list(self._search(filtre + args, limit=limit))
        return ids


    # def create(self, vals):
    #     obj = super(stock_move, self).create(vals)
    #     if obj.purchase_line_id and obj.picking_id:
    #         obj.picking_id.is_purchase_order_id=obj.purchase_line_id.order_id.id

    #     obj.update_pg_stock_move()
    #     vals=obj.update_amortissement_moule()
    #     obj.write(vals)

    #     return obj


    # def write(self, vals):
    #     v=self.update_amortissement_moule()
    #     if v:
    #         vals.update(v)

    #     res=super(stock_move, self).write(vals)
    #     for obj in self:
    #         obj.update_pg_stock_move()
    #     return res


    # def _action_confirm(self, merge=True, merge_into=False):
    #     res = super(stock_move, self)._action_confirm(merge=merge, merge_into=merge_into)
    #     self.create_pg_stock_move()
    #     return res


    def _action_done(self, cancel_backorder=False):
        res = super(stock_move, self)._action_done(cancel_backorder=cancel_backorder)
        self.create_pg_stock_move()
        return res


    def create_pg_stock_move_action(self):
        for obj in self:
            self.env['pg.stock.move'].search([('move_id', '=', obj.id)]).unlink()
        self.create_pg_stock_move()
        return True


    # def create_pg_stock_move_all(self):
    #     #self.env['stock.move'].search([('state', '=', 'done')], order="date", limit=100).create_pg_stock_move()
    #     self.env['stock.move'].search([('state', '=', 'done')], order="date").create_pg_stock_move()
    #     return True


    #TODO : A revoir => Ne pas mettre de lien vers pg_stock_move depuis stock_move
    #@api.depends('product_id','quantity_done', 'state', 'picking_id')
    def create_pg_stock_move(self):
        for obj in self:
            print(obj.date)

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
                    dict[key]["qty"]+=line.qty_done
                #**************************************************************
                for key in dict:
                    line = dict[key]["line"]
                    qty  = dict[key]["qty"]
                    location_dest_id = line.location_dest_id
                    if line.location_id.usage=="internal" and line.location_dest_id.usage!="internal":
                        location_dest_id = line.location_id
                        qty=-qty
                    #** Convertire la qty dans l'unité de stock ***************
                    product_uom = obj.product_id.uom_id
                    if obj.product_uom!=obj.product_id.uom_id:
                        if obj.product_uom.category_id==obj.product_id.uom_id.category_id:
                            qty = obj.product_uom._compute_quantity(qty, product_uom) #, round=True, rounding_method='UP', raise_if_failure=True):
                    #**********************************************************

                    vals={
                        "move_id": obj.id,
                        "date": obj.date,
                        "product_id": obj.product_id.id,
                        "name": obj.name,
                        "category": obj.product_id.is_category_id.name,
                        "mold": obj.product_id.is_mold_dossierf,
                        "picking_type_id": obj.picking_type_id.id,
                        "picking_id": obj.picking_id.id,
                        "lot_id": line.lot_id.id,
                        "lot_fournisseur": line.lot_id.is_lot_fournisseur,
                        "qty": qty,
                        "product_uom": product_uom.id,
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
                #'move_ids'        : [[0,False,move_vals]],
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
            # vals.update({
            #     "lot_id"   : lot.id,
            #     #"reserved_uom_qty": 0,
            # })
            line=self.env['stock.move.line'].create(vals)
            obj.production_id.lot_producing_id = lot.id


    def is_done_action(self):
        for obj in self:
            obj._action_done()
            for line in obj.move_line_ids:
                line._action_done()
            #obj._action_assign(force_qty=True)
            # # obj._action_confirm()
            # # obj._action_assign(force_qty=True)
            # obj.move_line_ids.unlink()
            # obj._action_confirm()
            # for line in obj.move_line_ids:
            #     line.qty_done = line.reserved_uom_qty
            #obj._action_done()

    #def _action_assign(self, force_qty=False):


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


    def update_pg_stock_move(self):
        cr = self._cr
        for obj in self:
            SQL=_SELECT_STOCK_MOVE+" WHERE sm2.id=%s"
            cr.execute(SQL, [obj.id])
            rows = cr.fetchall()
            for row in rows:
                SQL="delete from pg_stock_move where move_id=%s"
                cr.execute(SQL,[row[1]])
                SQL="""
                    INSERT INTO pg_stock_move (
                        move_id,
                        date,
                        product_id,
                        category,
                        mold,
                        type_mv,
                        name,
                        picking_id,
                        purchase_line_id,
                        raw_material_production_id,
                        production_id,
                        sale_line_id,
                        lot_id,
                        lot_fournisseur,
                        qty,
                        product_uom,
                        location_dest,
                        is_employee_theia_id,
                        login
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);
                """
                cr.execute(SQL,[
                    row[1],
                    row[2],
                    row[3],
                    row[4],
                    row[5],
                    row[6],
                    row[7],
                    row[8],
                    row[9],
                    row[10],
                    row[11],
                    row[12],
                    row[13],
                    row[14],
                    row[15],
                    row[16],
                    row[17],
                    row[18],
                    row[19],
                ])


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
                'view_type': 'form',
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


    # def _picking_assign(self, procurement_group, location_from, location_to):
    #     """Assign a picking on the given move_ids, which is a list of move supposed to share the same procurement_group, location_from and location_to
    #     (and company). Those attributes are also given as parameters.
    #     """
    #     cr       = self._cr
    #     uid      = self._uid
    #     context  = self._context
    #     move_ids = self._ids
    #     pick_obj = self.env["stock.picking"]
    #     # Use a SQL query as doing with the ORM will split it in different queries with id IN (,,)
    #     # In the next version, the locations on the picking should be stored again.
    #     query = """
    #         SELECT stock_picking.id FROM stock_picking, stock_move
    #         WHERE
    #             stock_picking.state in ('draft', 'confirmed', 'waiting') AND
    #             stock_move.picking_id = stock_picking.id AND
    #             stock_move.location_id = %s AND
    #             stock_move.location_dest_id = %s AND
    #     """
    #     params = (location_from, location_to)
    #     if not procurement_group:
    #         query += "stock_picking.group_id IS NULL LIMIT 1"
    #     else:
    #         query += "stock_picking.group_id = %s LIMIT 1"
    #         params += (procurement_group,)
    #     cr.execute(query, params)
    #     [pick] = cr.fetchone() or [None]
    #     if not pick:
    #         move = self.browse(move_ids)[0]
    #         if move.origin:
    #             sale_obj = self.env['sale.order']
    #             sales = sale_obj.search([('name','=',move.origin)])
    #             for sale_data in sales:
    #                 date_expedition = time.strftime('%Y-%m-%d')
    #                 date_livraison  = self._get_date_livraison(date_expedition)
    #                 values = {
    #                     'origin'             : move.origin,
    #                     'company_id'         : move.company_id and move.company_id.id or False,
    #                     'move_type'          : move.group_id and move.group_id.move_type or 'direct',
    #                     'partner_id'         : move.partner_id.id or False,
    #                     'picking_type_id'    : move.picking_type_id and move.picking_type_id.id or False,
    #                     'sale_id'   : sale_data and sale_data.id or False,
    #                     'is_transporteur_id' : sale_data and sale_data.is_transporteur_id.id or False,
    #                     'is_date_expedition' : date_expedition,
    #                     'is_date_livraison'  : date_livraison,
    #                 }
    #                 pick = pick_obj.create(values)
    #     if pick:
    #         self.write({'picking_id': pick.id})
    #     return
    

    # def action_consume(self, cr, uid, ids, product_qty, location_id=False, restrict_lot_id=False, restrict_partner_id=False,
    #                    consumed_for=False, context=None):
    #     """ Consumed product with specific quantity from specific source location.
    #     @param product_qty: Consumed/produced product quantity (= in quantity of UoM of product)
    #     @param location_id: Source location
    #     @param restrict_lot_id: optionnal parameter that allows to restrict the choice of quants on this specific lot
    #     @param restrict_partner_id: optionnal parameter that allows to restrict the choice of quants to this specific partner
    #     @param consumed_for: optionnal parameter given to this function to make the link between raw material consumed and produced product, for a better traceability
    #     @return: New lines created if not everything was consumed for this line
    #     """

    #     if context is None:
    #         context = {}
    #     res = []
    #     production_obj = self.pool.get('mrp.production')

    #     #** Test si la quantité est négative pour inverser les emplacements ****
    #     inverse=False
    #     if product_qty <= 0:
    #         inverse=True
    #         product_qty=-product_qty

    #     ids2 = []
    #     for move in self.browse(cr, uid, ids, context=context):
    #         if move.state == 'draft':
    #             ids2.extend(self.action_confirm(cr, uid, [move.id], context=context))
    #         else:
    #             ids2.append(move.id)
    #     prod_orders = set()

    #     for move in self.browse(cr, uid, ids2, context=context):
    #         prod_orders.add(move.raw_material_production_id.id or move.production_id.id)
    #         move_qty = move.product_qty

    #         #** Si la quantité est négative, il faut augmenter le reste à produire
    #         if inverse:
    #             quantity_rest = move_qty + product_qty
    #         else:
    #             quantity_rest = move_qty - product_qty
            
    #         # Compare with numbers of move uom as we want to avoid a split with 0 qty
    #         quantity_rest_uom = move.product_uom_qty - self.pool.get("product.uom")._compute_qty_obj(cr, uid, move.product_id.uom_id, product_qty, move.product_uom)

    #         #** Si la quantité est négative, ajout de 2 fois la quantité déclarée sur le mouvement en attente
    #         #** La fonction slit ci-dessous enlevera fois la quantité => Du coup, nous seront bien à +1 comme souhaité
    #         if inverse and product_qty>0:
    #             move.product_uom_qty=move.product_uom_qty+2*product_qty

    #         #Si la quantité restante est à 0 , mettre 0.00001 pour ne pas solder le mouvement
    #         #if float_compare(quantity_rest_uom, 0, precision_rounding=move.product_uom.rounding) == 0:
    #         #    quantity_rest=move.product_uom.rounding
    #         #TODO : Modif du 09/09/17 pour corriger un pb de division par 0
    #         if abs(quantity_rest)<0.00001:
    #             quantity_rest=0.00001
                
    #         #** Invertion des emplacements pour faire un mouvement négatif
    #         if inverse:
    #             mem_location_id           = move.location_id.id
    #             mem_location_dest_id      = move.location_dest_id.id
    #             move.location_dest_id     = mem_location_id
    #             move.location_id          = mem_location_dest_id

    #         #** Création d'un nouveau mouvement qui contiendra le reste à fabriquer. Le mouvement en cours contiendra la quantité déclarée

    #         new_mov = self.split(cr, uid, move, quantity_rest, context=context)

    #         if move.production_id:
    #             self.write(cr, uid, [new_mov], {'production_id': move.production_id.id}, context=context)

    #         #** Sur le nouveau mouvement qui correspond au reste à produire, il faut remettre les emplacements dans l'ordre (nouvelle invertion)
    #         if inverse:
    #             v={
    #                 'location_id'     : mem_location_id,
    #                 'location_dest_id': mem_location_dest_id,
    #             }
    #             self.write(cr, uid, [new_mov], v, context)
    #         res.append(new_mov)

    #         vals = {'restrict_lot_id': restrict_lot_id,
    #                 'restrict_partner_id': restrict_partner_id,
    #                 'consumed_for': consumed_for}
    #         self.write(cr, uid, [move.id], vals, context=context)


    #     # Original moves will be the quantities consumed, so they need to be done
    #     self.action_done(cr, uid, ids2, context=context)


    #     #TODO : J'ai commenté ces lignes le 26/12/2017 pour ne pas réserver le stock sur les OF
    #     #if res:
    #     #    self.action_assign(cr, uid, res, context=context)


    #     #TODO : J'ai désactivé ce code car cela bloquait les homes flux
    #     #if prod_orders:
    #     #    production_obj.signal_workflow(cr, uid, list(prod_orders), 'button_produce')
    #     return res







