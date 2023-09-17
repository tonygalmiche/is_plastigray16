# -*- coding: utf-8 -*-

import string
from odoo import models,fields,api
from odoo.exceptions import ValidationError

#from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
import time
from datetime import datetime, date
#from xml.dom.minidom import parseString
#import re
#import os
#from collections import OrderedDict
import logging
_logger = logging.getLogger(__name__)

#from odoo.addons.is_plastigray16.report.is_stock_move import _SELECT_STOCK_MOVE
# class stock_pack_operation(models.Model):
#     _inherit = "stock.pack.operation"
  
#     move_id = fields.Many2one('stock.move', 'Stock Move')


class stock_location(models.Model):
    _inherit = 'stock.location'

    control_quality = fields.Boolean(u'Contrôle qualité', default=False)


    def name_get(self):
        res = []
        for obj in self:
            name = obj.name
            #name = "%s (%s)"%(obj.name,(obj.is_matricule or ''))
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


class stock_picking_type(models.Model):
    _inherit = "stock.picking.type"


    def name_get(self):
        res = []
        for picking_type in self:
            name = picking_type.name
            res.append((picking_type.id, name))
        return res


class stock_picking(models.Model):
    _inherit = "stock.picking"
    _order   = "date desc, name desc"
    
    is_sale_order_id       = fields.Many2one('sale.order', 'Commande Client (champ obsolète dans Odoo 16 car remplacé par sale_id)')
    is_purchase_order_id   = fields.Many2one('purchase.order', 'Commande Fournisseur')
    is_transporteur_id     = fields.Many2one('res.partner', 'Transporteur', compute='_compute_transporteur_dates', store=True, readonly=False)
    is_date_expedition     = fields.Date("Date d'expédition"            , compute='_compute_transporteur_dates', store=True, readonly=False)
    is_date_livraison      = fields.Date("Date d'arrivée chez le client", compute='_compute_transporteur_dates', store=True, readonly=False)
    is_date_livraison_vsb  = fields.Boolean('Avertissement VSB', store=False, compute='_compute_is_date_livraison_vsb', readonly=True)
    is_date_livraison_msg  = fields.Char("Avertissement"       , store=False, compute='_compute_is_date_livraison_vsb', readonly=True)
    is_num_bl              = fields.Char("N° BL fournisseur")
    is_date_reception      = fields.Date('Date de réception')
    is_facture_pk_id       = fields.Many2one('is.facture.pk', 'Facture PK')
    is_piece_jointe        = fields.Boolean(u"Pièce jointe", store=False, readonly=True, compute='_compute_is_piece_jointe')
    is_galia_um            = fields.Boolean(u"Test si étiquettes scannées sur Liste à servir", store=False, readonly=True, compute='_compute_is_galia_um')
    is_mode_envoi_facture  = fields.Selection(related="partner_id.is_mode_envoi_facture", string="Mode d'envoi des factures")
    is_traitement_edi      = fields.Selection(related='partner_id.is_traitement_edi', string='Traitement EDI', readonly=True)
    is_date_traitement_edi = fields.Datetime("Date traitement EDI")
    invoice_state = fields.Selection([
            ('none'      , 'Non applicable'),
            ('2binvoiced', "À facturer"),
            ('invoiced'  , "Facturé"),
        ], "Facturation", default="2binvoiced", compute="_compute_invoice_state", store=True)


    @api.depends('state', 'move_ids_without_package')
    def _compute_invoice_state(self):
        for obj in self:
            if obj.state=="cancel":
                invoice_state="none"
            else:
                invoice_state="invoiced"
                for line in obj.move_ids_without_package:
                    if line.invoice_state!="invoiced":
                        invoice_state="2binvoiced"
                        break
            obj.invoice_state = invoice_state


    @api.depends('sale_id', 'partner_id')
    def _compute_transporteur_dates(self):
        date_expedition = time.strftime('%Y-%m-%d')
        #date_livraison  = self.env['stock.move']._get_date_livraison(date_expedition)
        date_livraison= self.env['res.partner'].get_date_livraison( self.company_id, self.partner_id, date_expedition)
        for obj in self:
            is_transporteur_id=False
            if obj.sale_id:
                is_transporteur_id = obj.sale_id.is_transporteur_id.id
            obj.is_transporteur_id = is_transporteur_id
            obj.is_date_expedition = date_expedition
            obj.is_date_livraison  = date_livraison
            if obj.sale_id.is_source_location_id:
                obj.location_id = obj.sale_id.is_source_location_id.id


    @api.onchange('is_date_expedition')
    def onchange_date_expedition(self):
        date_livraison = self.is_date_expedition
        if self.partner_id and self.company_id:
            date_livraison= self.env['res.partner'].get_date_livraison( self.company_id, self.partner_id, self.is_date_expedition)
        self.is_date_livraison = date_livraison




    def creer_factures_action(self):
        ids=[]
        for obj in self:
            id = obj.sale_id.id
            if id and id not in ids:
                ids.append(id)
        self.env['sale.order'].search([('id','in',ids)])._create_invoices() #  def _create_invoices(self, grouped=False, final=False, date=None)







    def transfert_action(self):
        for obj in self:
            print(obj)


    def pj_action(self):
        for obj in self:
            print(obj)


    def _compute_is_piece_jointe(self):
        for obj in self:
            attachments = self.env['ir.attachment'].search([('res_model','=',self._name),('res_id','=',obj.id)])
            pj=False
            if attachments:
                pj=True
            obj.is_piece_jointe=pj


    @api.depends('is_date_livraison', 'partner_id', 'company_id')
    def _compute_is_date_livraison_vsb(self):
        for obj in self:
            vsb = self.check_date_livraison(obj.is_date_livraison, obj.partner_id.id)
            obj.is_date_livraison_vsb=vsb
            msg=''
            if not vsb:
                msg='La date de livraison tombe pendant la fermeture du client !'
            obj.is_date_livraison_msg=msg


    def _compute_is_galia_um(self):
        for obj in self:
            test=False
            if obj.sale_id.is_liste_servir_id.galia_um_ids:
                test=True
            obj.is_galia_um = test


    def get_is_code_rowspan(self,product_id):
        cr = self._cr
        for obj in self:
            liste_servir = obj.sale_id.is_liste_servir_id
            SQL="""
                select count(*)
                from is_galia_base_uc uc inner join is_galia_base_um um on uc.um_id=um.id
                                         inner join is_liste_servir ls on um.liste_servir_id=ls.id
                                         inner join product_product pp on uc.product_id=pp.id 
                where 
                    ls.id="""+str(liste_servir.id)+""" and 
                    uc.product_id="""+str(product_id)+""" 
            """
            cr.execute(SQL)
            result = cr.fetchall()
            nb=0
            for row in result:
                nb=row[0]
            return nb


    def get_um_rowspan(self,product_id,um_id):
        cr = self._cr
        for obj in self:
            liste_servir = obj.sale_id.is_liste_servir_id
            SQL="""
                select count(*)
                from is_galia_base_uc uc inner join is_galia_base_um um on uc.um_id=um.id
                                         inner join is_liste_servir ls on um.liste_servir_id=ls.id
                                         inner join product_product pp on uc.product_id=pp.id 
                where 
                    ls.id="""+str(liste_servir.id)+""" and 
                    uc.product_id="""+str(product_id)+""" and
                    um.id="""+str(um_id)+""" 
            """
            cr.execute(SQL)
            result = cr.fetchall()
            nb=0
            for row in result:
                nb=row[0]
            return nb


    def get_etiquettes(self):
        cr = self._cr
        res=[]
        for obj in self:
            #** Recherche des articles du BL **********************************
            product_ids=[]
            for line in obj.move_lines:
                if line.state=="done":
                    product_id = line.product_id.id
                    if product_id not in product_ids:
                        product_ids.append(str(product_id))
            product_ids = ",".join(product_ids)
            #******************************************************************

            liste_servir = obj.sale_id.is_liste_servir_id
            SQL="""
                select 
                    pt.is_code,
                    um.name,
                    uc.num_eti,
                    uc.qt_pieces,
                    pp.id,
                    um.id,
                    uc.production
                from is_galia_base_uc uc inner join is_galia_base_um um on uc.um_id=um.id
                                         inner join is_liste_servir ls on um.liste_servir_id=ls.id
                                         inner join product_product pp on uc.product_id=pp.id 
                                         inner join product_template pt on pp.product_tmpl_id=pt.id
                where 
                    ls.id="""+str(liste_servir.id)+""" and 
                    pp.id in ("""+product_ids+""") 
                order by pt.is_code, um.name, uc.num_eti
            """
            cr.execute(SQL)
            result = cr.fetchall()
            ct_code = 0
            ct_um   = 0
            is_code_rowspan = 0
            um_rowspan = 0
            mem_code = ''
            mem_um   = ''
            for row in result:
                is_code_rowspan=0
                um_rowspan=0
                if row[0]!=mem_code:
                    mem_code=row[0]
                    is_code_rowspan=self.get_is_code_rowspan(row[4])
                    ct_code=0

                is_code_um = (row[0]+row[1])
                if is_code_um!=mem_um:
                    mem_um=is_code_um
                    um_rowspan=self.get_um_rowspan(row[4],row[5])
                    ct_um=0

                ct_code+=1
                ct_um+=1

                vals={
                    'is_code'  : row[0],
                    'um'       : row[1],
                    'uc'       : row[2],
                    'qt_pieces': row[3],
                    'lot'      : row[6],
                    'is_code_rowspan': is_code_rowspan,
                    'um_rowspan': um_rowspan,
                }
                res.append(vals)
        return res



    def check_date_livraison(self, date_livraison,  partner_id, context=None):
        res_partner = self.env['res.partner']
        if partner_id and date_livraison:
            partner = self.env['res.partner'].browse(partner_id)
            # jours de fermeture de la société
            jours_fermes = res_partner.num_closing_days(partner)
            # Jours de congé de la société
            leave_dates = res_partner.get_leave_dates(partner,avec_jours_feries=True)
            # num de jour dans la semaine de la date de livraison
            if type(date_livraison) is str:
                date_livraison = datetime.strptime(date_livraison, '%Y-%m-%d')
            #num_day = time.strftime('%w', time.strptime(date_livraison, '%Y-%m-%d'))
            num_day = date_livraison.strftime('%Y%m%d')
            if int(num_day) in jours_fermes or date_livraison in leave_dates:
                return False
        return True




    # def onchange_date_expedition(self, date_expedition, partner_id, company_id):
    #     date_livraison=date_expedition
    #     if partner_id and company_id:
    #         partner = self.env['res.partner'].browse(partner_id)
    #         company = self.env['res.company'].browse(company_id)
    #         date_livraison= self.env['res.partner'].get_date_livraison(company, partner, date_expedition)
    #     v = {}
    #     warning = {}
    #     v['is_date_livraison'] = date_livraison
    #     return {'value': v,
    #             'warning': warning}







    def action_imprimer_etiquette_reception(self):
        for obj in self:
            uid=self._uid
            user=self.env['res.users'].browse(uid)
            soc=user.company_id.partner_id.is_code
            return {
                'type' : 'ir.actions.act_url',
                'url': 'http://odoo16/odoo-erp/reception/Impression_Etiquette_Reception.php?Soc='+str(soc)+'&&zzCode='+str(obj.name),
                'target': '_blank',
            }


    def action_annuler_reception(self):
        cr = self._cr
        for obj in self:
            if obj.state!='done':
                raise ValidationError("Cette réception n'est pas à l'état 'Fait' !")

            #** Recherche si les lignes de cette réception son facturées ******
            for line in obj.move_ids_without_package:
                if line.invoice_state=='invoiced':
                    raise ValidationError('Annulation impossible car la réception est déjà facturée !')
                line.invoice_state="none"
            obj.invoice_state='none'
            #******************************************************************

            #** Copie de la réception pour pouvoir la réfaire *****************
            retour=obj.copy()
            retour.location_id = obj.location_dest_id.id
            retour.location_dest_id = obj.location_id.id

            #******************************************************************

            #** Création des mouvements inverses pour annuler la réception ****
            for move in obj.move_ids_without_package:
                #move.location_id = move.location_dest_id.id
                #move.location_dest_id = move.location_id.id
                for line in move.move_line_ids:
                    vals={
                        "picking_id"      : retour.id,
                        "location_id"     : line.location_dest_id.id,
                        "location_dest_id": line.location_id.id,
                        "lot_id"          : line.lot_id.id,
                        "qty_done"        : line.qty_done,
                        "product_id"      : line.product_id.id,
                    }
                    res=self.env['stock.move.line'].create(vals)
                #action_confirm
            #******************************************************************


            # #** Création des mouvements inverses pour annuler la réception ****
            # for move in obj.move_ids_without_package:
            #     copy = move.copy()
            #     copy.location_id      = move.location_dest_id.id
            #     copy.location_dest_id = move.location_id.id
            #     copy.origin_returned_move_id = move.id
            #     for line in move.move_line_ids:
            #         vals={
            #             "move_id"         : copy.id,
            #             "picking_id"      : obj.id,
            #             "location_id"     : line.location_dest_id.id,
            #             "location_dest_id": line.location_id.id,
            #             "lot_id"          : line.lot_id.id,
            #             "qty_done"        : line.qty_done,
            #             "product_id"      : line.product_id.id,
            #         }
            #         res=self.env['stock.move.line'].create(vals)
            #         #print(res, res.location_id.name, res.location_dest_id.name)
            #     copy._action_confirm()
            #     move.state = 'cancel'
            #     copy.state = 'cancel'
            # #******************************************************************


            #**Validation des mouvements et annulation des receptions *********
            retour.action_confirm()
            retour._action_done()
            #******************************************************************

            #** Annulation du picking d'origigne, du retour et des mouvements *
            for move in obj.move_ids_without_package:
                move.state="cancel"
            for move in retour.move_ids_without_package:
                move.state="cancel"
            #******************************************************************

            new_picking=obj.copy()
            return {
                'name': "Réception annullée",
                'view_mode': 'form',
                'res_model': 'stock.picking',
                'type': 'ir.actions.act_window',
                'res_id': new_picking.id,
                'domain': '[]',
            }




    def action_invoice_create(self, cr, uid, ids, journal_id, group=False, type='out_invoice', context=None):
        """
            Permet de fixer la date de la facture à la date de la livraison lors 
            de la création des factures à partir des livraisons
        """
        context = context or {}
        todo = {}
        for picking in self.browse(cr, uid, ids, context=context):
            partner = self._get_partner_to_invoice(cr, uid, picking, dict(context, type=type))
            if group:
                key = partner
            else:
                key = picking.id
            for move in picking.move_lines:
                if move.invoice_state == '2binvoiced':
                    if (move.state != 'cancel') and not move.scrapped:
                        todo.setdefault(key, [])
                        todo[key].append(move)
        invoices = []
        for moves in todo.values():
            date_inv=False
            for move in moves:
                date_inv=move.picking_id.is_date_expedition
            context['date_inv']=date_inv
            invoices += self._invoice_create_line(cr, uid, moves, journal_id, type, context=context)
        return invoices




    def desadv_action(self):
        for obj in self : 
            cdes = self.env['is.commande.externe'].search([('name','=',"edi-tenor-desadv")])
            for cde in cdes:
                model=self._name
                uid=self._uid
                user=self.env['res.users'].browse(uid)
                soc=user.company_id.partner_id.is_code
                x = cde.commande
                x = x.replace("#soc"   , soc)
                x = x.replace("#model" , model)
                x = x.replace("#res_id", str(obj.id))
                x = x.replace("#uid"   , str(uid))
                _logger.info(x)
                lines=os.popen(x).readlines()
                for line in lines:
                    _logger.info(line.strip())
                now = datetime.now()
                obj.is_date_traitement_edi = now
                body = u"<b>DESADV envoyé</b><br>"+"<br>".join(lines)
                vals={
                    'author_id': user.partner_id.id,
                    'type'     : "notification",
                    'body'     : body,
                    'model'    : model,
                    'res_id'   : obj.id
                }
                res=self.env['mail.message'].create(vals)


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








    # #TODO : Fonction reprise complètement par Hiren pour pouvoir gérer les recéptions avec plusieurs lignes du même article
    # @api.cr_uid_ids_context
    # def do_prepare_partial(self, cr, uid, picking_ids, context=None):
    #     context = context or {}
    #     pack_operation_obj = self.pool.get('stock.pack.operation')
    #     #used to avoid recomputing the remaining quantities at each new pack operation created
    #     ctx = context.copy()
    #     ctx['no_recompute'] = True

    #     #get list of existing operations and delete them
    #     existing_package_ids = pack_operation_obj.search(cr, uid, [('picking_id', 'in', picking_ids)], context=context)
    #     if existing_package_ids:
    #         pack_operation_obj.unlink(cr, uid, existing_package_ids, context)
    #     for picking in self.browse(cr, uid, picking_ids, context=context):
    #         forced_qties = {}  # Quantity remaining after calculating reserved quants
    #         picking_quants = []
    #         #Calculate packages, reserved quants, qtys of this picking's moves
    #         for move in picking.move_lines:
    #             if move.state not in ('assigned', 'confirmed', 'waiting'):
    #                 continue
    #             move_quants = move.reserved_quant_ids
    #             picking_quants += move_quants
    #             forced_qty = (move.state == 'assigned') and move.product_qty - sum([x.qty for x in move_quants]) or 0
    #             #if we used force_assign() on the move, or if the move is incoming, forced_qty > 0
    #             if float_compare(forced_qty, 0, precision_rounding=move.product_id.uom_id.rounding) > 0:
    #                 if forced_qties.get(move):
    #                     forced_qties[move] += forced_qty
    #                 else:
    #                     forced_qties[move] = forced_qty
    #         for vals in self._prepare_pack_ops(cr, uid, picking, picking_quants, forced_qties, context=context):
    #             pack_operation_obj.create(cr, uid, vals, context=ctx)
    #     #recompute the remaining quantities all at once
    #     self.do_recompute_remaining_quantities(cr, uid, picking_ids, context=context)
    #     self.write(cr, uid, picking_ids, {'recompute_pack_op': False}, context=context)
 

    # #TODO : Fonction reprise complètement le 18/12/2018 pour gérer l'emplacement de destination
    # @api.multi
    # def do_enter_transfer_details(self):
    #     for picking in self:
    #         if picking.is_purchase_order_id:
    #             location_id=picking.is_purchase_order_id.location_id.id
    #             for move in [x for x in picking.move_lines if x.state not in ('done', 'cancel')]:
    #                 if move.product_id.is_ctrl_rcp=='bloque':
    #                     res = self.pool.get('stock.location').search(cr, uid, [
    #                             ('name','=', 'Q2'),
    #                         ], context=context)
    #                     if res:
    #                         location_id=res[0]
    #                 move.location_dest_id=location_id
    #         if not context:
    #             context = {}
    #         else:
    #             context = context.copy()
    #         context.update({
    #             'active_model': self._name,
    #             'active_ids': [picking.id],
    #             'active_id': picking.id
    #         })
    #         created_id = self.pool['stock.transfer_details'].create(cr, uid, {'picking_id': picking.id}, context)
    #         return self.pool['stock.transfer_details'].wizard_view(cr, uid, created_id, context)


    # #TODO : Fonction reprise complètement par Hiren pour pouvoir gérer les recéptions avec plusieurs lignes du même article
    # def _prepare_pack_ops(self, cr, uid, picking, quants, forced_qties, context=None):
    #     """ returns a list of dict, ready to be used in create() of stock.pack.operation.

    #     :param picking: browse record (stock.picking)
    #     :param quants: browse record list (stock.quant). List of quants associated to the picking
    #     :param forced_qties: dictionary showing for each product (keys) its corresponding quantity (value) that is not covered by the quants associated to the picking
    #     """
    #     def _picking_putaway_apply(product):
    #         location = False
    #         # Search putaway strategy
    #         if product_putaway_strats.get(product.id):
    #             location = product_putaway_strats[product.id]
    #         else:
    #             location = self.pool.get('stock.location').get_putaway_strategy(cr, uid, picking.location_dest_id, product, context=context)
    #             product_putaway_strats[product.id] = location
    #         return location or picking.location_dest_id.id

    #     # If we encounter an UoM that is smaller than the default UoM or the one already chosen, use the new one instead.
    #     product_uom = {} # Determines UoM used in pack operations
    #     location_dest_id = None
    #     location_id = None
    #     for move in [x for x in picking.move_lines if x.state not in ('done', 'cancel')]:

    #         if not product_uom.get(move.product_id.id):
    #             product_uom[move.product_id.id] = move.product_id.uom_id
    #         if move.product_uom.id != move.product_id.uom_id.id and move.product_uom.factor > product_uom[move.product_id.id].factor:
    #             product_uom[move.product_id.id] = move.product_uom

    #         if not move.scrapped:
    #             if location_dest_id and move.location_dest_id.id != location_dest_id:
    #                 raise ValidationError(_('The destination location must be the same for all the moves of the picking.'))
    #             location_dest_id = move.location_dest_id.id
    #             if location_id and move.location_id.id != location_id:
    #                 raise ValidationError(_('The source location must be the same for all the moves of the picking.'))
    #             location_id = move.location_id.id

    #     pack_obj = self.pool.get("stock.quant.package")
    #     quant_obj = self.pool.get("stock.quant")
    #     vals = []
    #     qtys_grouped = {}
    #     #for each quant of the picking, find the suggested location
    #     quants_suggested_locations = {}
    #     product_putaway_strats = {}
    #     for quant in quants:
    #         if quant.qty <= 0:
    #             continue
    #         suggested_location_id = _picking_putaway_apply(quant.product_id)
    #         quants_suggested_locations[quant] = suggested_location_id

    #     #find the packages we can movei as a whole
    #     top_lvl_packages = self._get_top_level_packages(cr, uid, quants_suggested_locations, context=context)
    #     # and then create pack operations for the top-level packages found
    #     for pack in top_lvl_packages:
    #         pack_quant_ids = pack_obj.get_content(cr, uid, [pack.id], context=context)
    #         pack_quants = quant_obj.browse(cr, uid, pack_quant_ids, context=context)
    #         vals.append({
    #                 'picking_id': picking.id,
    #                 'package_id': pack.id,
    #                 'product_qty': 1.0,
    #                 'location_id': pack.location_id.id,
    #                 'location_dest_id': quants_suggested_locations[pack_quants[0]],
    #                 'owner_id': pack.owner_id.id,
    #             })
    #         #remove the quants inside the package so that they are excluded from the rest of the computation
    #         for quant in pack_quants:
    #             del quants_suggested_locations[quant]

    #     # Go through all remaining reserved quants and group by product, package, lot, owner, source location and dest location
    #     for quant, dest_location_id in quants_suggested_locations.items():
    #         key = (quant.product_id.id, quant.package_id.id, quant.lot_id.id, quant.owner_id.id, quant.location_id.id, dest_location_id,quant.reservation_id.id)
    #         if qtys_grouped.get(key):
    #             qtys_grouped[key] += quant.qty
    #         else:
    #             qtys_grouped[key] = quant.qty

    #     # Do the same for the forced quantities (in cases of force_assign or incomming shipment for example)
    #     for move, qty in forced_qties.items():
    #         if qty <= 0:
    #             continue
    #         suggested_location_id = _picking_putaway_apply(move.product_id)
    #         key = (move.product_id.id, False, False, picking.owner_id.id, picking.location_id.id, suggested_location_id,move.id)
    #         if qtys_grouped.get(key):
    #             qtys_grouped[key] += qty
    #         else:
    #             qtys_grouped[key] = qty
    #     # Create the necessary operations for the grouped quants and remaining qtys
    #     uom_obj = self.pool.get('product.uom')
    #     prevals = {}
    #     for key, qty in qtys_grouped.items():
    #         product = self.pool.get("product.product").browse(cr, uid, key[0], context=context)
    #         uom_id = product.uom_id.id
    #         qty_uom = qty
    #         if product_uom.get(key[0]):
    #             uom_id = product_uom[key[0]].id
    #             qty_uom = uom_obj._compute_qty(cr, uid, product.uom_id.id, qty, uom_id)
    #         val_dict = {
    #             'picking_id': picking.id,
    #             'product_qty': qty_uom,
    #             'product_id': key[0],
    #             'package_id': key[1],
    #             'lot_id': key[2],
    #             'owner_id': key[3],
    #             'location_id': key[4],
    #             'location_dest_id': key[5],
    #             'product_uom_id': uom_id,
    #             'move_id':key[6],
    #         }
    #         if key[6] in prevals:
    #             prevals[key[6]].append(val_dict)
    #         else:
    #             prevals[key[6]] = [val_dict]
    #     # prevals var holds the operations in order to create them in the same order than the picking stock moves if possible
    #     processed_products = set()
    #     for move in [x for x in picking.move_lines if x.state not in ('done', 'cancel')]:
    #         if move.id not in processed_products:
    #             vals += prevals.get(move.id, [])
    #             processed_products.add(move.id)
    #     return vals
    

    # #TODO : Fonction reprise complètement par Hiren pour pouvoir gérer les recéptions avec plusieurs lignes du même article
    # def recompute_remaining_qty(self, cr, uid, picking, context=None):
    #     def _create_link_for_index(operation_id, index, product_id, qty_to_assign, move_id, quant_id=False):
    #         move_dict = prod2move_ids[move_id][index]
    #         qty_on_link = min(move_dict['remaining_qty'], qty_to_assign)
    #         self.pool.get('stock.move.operation.link').create(cr, uid, {'move_id': move_dict['move'].id, 'operation_id': operation_id, 'qty': qty_on_link, 'reserved_quant_id': quant_id}, context=context)
    #         if move_dict['remaining_qty'] == qty_on_link:
    #             prod2move_ids[move_id].pop(index)
    #         else:
    #             move_dict['remaining_qty'] -= qty_on_link
    #         return qty_on_link

    #     def _create_link_for_quant(operation_id, quant, qty, move_id):
    #         """create a link for given operation and reserved move of given quant, for the max quantity possible, and returns this quantity"""
    #         if not quant.reservation_id.id:
    #             return _create_link_for_product(operation_id, quant.product_id.id, qty, move_id)
    #         qty_on_link = 0
    #         for i in range(0, len(prod2move_ids[move_id])):
    #             if prod2move_ids[move_id][i]['move'].id != quant.reservation_id.id:
    #                 continue
    #             qty_on_link = _create_link_for_index(operation_id, i, quant.product_id.id, qty, move_id,quant_id=quant.id)
    #             break
    #         return qty_on_link

    #     def _create_link_for_product(operation_id, product_id, qty, move_id):
    #         '''method that creates the link between a given operation and move(s) of given product, for the given quantity.
    #         Returns True if it was possible to create links for the requested quantity (False if there was not enough quantity on stock moves)'''
    #         qty_to_assign = qty
    #         prod_obj = self.pool.get("product.product")
    #         product = prod_obj.browse(cr, uid, product_id)
    #         rounding = product.uom_id.rounding
    #         qtyassign_cmp = float_compare(qty_to_assign, 0.0, precision_rounding=rounding)
    #         if prod2move_ids.get(move_id):
    #             while prod2move_ids[move_id] and qtyassign_cmp > 0:
    #                 qty_on_link = _create_link_for_index(operation_id, 0, product_id, qty_to_assign, move_id, quant_id=False)
    #                 qty_to_assign -= qty_on_link
    #                 qtyassign_cmp = float_compare(qty_to_assign, 0.0, precision_rounding=rounding)
    #         return qtyassign_cmp == 0

    #     uom_obj = self.pool.get('product.uom')
    #     package_obj = self.pool.get('stock.quant.package')
    #     quant_obj = self.pool.get('stock.quant')
    #     link_obj = self.pool.get('stock.move.operation.link')
    #     quants_in_package_done = set()
    #     prod2move_ids = {}
    #     still_to_do = []
    #     #make a dictionary giving for each product, the moves and related quantity that can be used in operation links
    #     for move in [x for x in picking.move_lines if x.state not in ('done', 'cancel')]:
    #         if not prod2move_ids.get(move.id):
    #             prod2move_ids[move.id] = [{'move': move, 'remaining_qty': move.product_qty}]
    #         else:
    #             prod2move_ids[move.id].append({'move': move, 'remaining_qty': move.product_qty})
    #     need_rereserve = False
    #     #sort the operations in order to give higher priority to those with a package, then a serial number
    #     operations = picking.pack_operation_ids
    #     operations = sorted(operations, key=lambda x: ((x.package_id and not x.product_id) and -4 or 0) + (x.package_id and -2 or 0) + (x.lot_id and -1 or 0))
    #     #delete existing operations to start again from scratch
    #     links = link_obj.search(cr, uid, [('operation_id', 'in', [x.id for x in operations])], context=context)
    #     if links:
    #         link_obj.unlink(cr, uid, links, context=context)
    #     #1) first, try to create links when quants can be identified without any doubt
    #     for ops in operations:
    #         #for each operation, create the links with the stock move by seeking on the matching reserved quants,
    #         #and deffer the operation if there is some ambiguity on the move to select
    #         if ops.package_id and not ops.product_id:
    #             #entire package
    #             quant_ids = package_obj.get_content(cr, uid, [ops.package_id.id], context=context)
    #             for quant in quant_obj.browse(cr, uid, quant_ids, context=context):
    #                 remaining_qty_on_quant = quant.qty
    #                 if quant.reservation_id:
    #                     #avoid quants being counted twice
    #                     quants_in_package_done.add(quant.id)
    #                     qty_on_link = _create_link_for_quant(ops.id, quant, quant.qty, ops.move_id.id)
    #                     remaining_qty_on_quant -= qty_on_link
    #                 if remaining_qty_on_quant:
    #                     still_to_do.append((ops, quant.product_id.id, remaining_qty_on_quant))
    #                     need_rereserve = True
    #         elif ops.product_id.id:
    #             #Check moves with same product
    #             qty_to_assign = uom_obj._compute_qty_obj(cr, uid, ops.product_uom_id, ops.product_qty, ops.product_id.uom_id, context=context)
    #             for move_dict in prod2move_ids.get(ops.move_id.id, []):
    #                 move = move_dict['move']
    #                 for quant in move.reserved_quant_ids:
    #                     if not qty_to_assign > 0:
    #                         break
    #                     if quant.id in quants_in_package_done:
    #                         continue

    #                     #check if the quant is matching the operation details
    #                     if ops.package_id:
    #                         flag = quant.package_id and bool(package_obj.search(cr, uid, [('id', 'child_of', [ops.package_id.id])], context=context)) or False
    #                     else:
    #                         flag = not quant.package_id.id
    #                     flag = flag and ((ops.lot_id and ops.lot_id.id == quant.lot_id.id) or not ops.lot_id)
    #                     flag = flag and (ops.owner_id.id == quant.owner_id.id)
    #                     if flag:
    #                         max_qty_on_link = min(quant.qty, qty_to_assign)
    #                         qty_on_link = _create_link_for_quant(ops.id, quant, max_qty_on_link, ops.move_id.id)
    #                         qty_to_assign -= qty_on_link
    #             qty_assign_cmp = float_compare(qty_to_assign, 0, precision_rounding=ops.product_id.uom_id.rounding)
    #             if qty_assign_cmp > 0:
    #                 #qty reserved is less than qty put in operations. We need to create a link but it's deferred after we processed
    #                 #all the quants (because they leave no choice on their related move and needs to be processed with higher priority)
    #                 still_to_do += [(ops, ops.product_id.id, qty_to_assign)]
    #                 need_rereserve = True

    #     #2) then, process the remaining part
    #     all_op_processed = True
    #     for ops, product_id, remaining_qty in still_to_do:
    #         all_op_processed = _create_link_for_product(ops.id, product_id, remaining_qty,ops.move_id.id) and all_op_processed
    #     return (need_rereserve, all_op_processed)


    # @api.onchange('location_id')
    # def onchange_location(self):
    #     for move in self.move_lines:
    #         move.location_id = self.location_id