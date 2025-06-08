# -*- coding: utf-8 -*-
from odoo import models,fields,api    # type: ignore
from odoo.fields import Command       # type: ignore
from odoo.exceptions import AccessError, ValidationError, UserError  # type: ignore
from itertools import groupby
import time
from  datetime import datetime, timedelta
from math import *
import base64


class sale_order(models.Model):
    _inherit = "sale.order"

    def _get_default_location(self):
        company_id = self.env.user.company_id.id
        warehouse_obj = self.env['stock.warehouse']
        warehouse_id = warehouse_obj.search([('company_id','=',company_id)])
        location = warehouse_id.out_type_id and  warehouse_id.out_type_id.default_location_src_id
        return location and location or False


    @api.depends('order_line')
    def _compute(self):
        for obj in self:
            obj.is_nb_lignes=len(obj.order_line)


    is_type_commande       = fields.Selection([
        ('standard', 'Ferme'),
        ('ouverte' , 'Ouverte'),
        ('cadence' , 'Cadencé'),
        ('ls'      , 'Liste à servir'),
        ('proforma', 'PROFORMA'),
    ], string="Type de commande", default="standard")
    is_article_commande_id = fields.Many2one('product.product', 'Article de la commande', help="Article pour les commandes ouvertes")
    is_ref_client          = fields.Char("Référence client", store=True, compute='_ref_client')
    is_source_location_id  = fields.Many2one('stock.location', 'Source Location', default=_get_default_location) 
    is_transporteur_id     = fields.Many2one('res.partner', 'Transporteur')
    is_liste_servir_id     = fields.Many2one('is.liste.servir', 'Liste à servir')
    is_info_client         = fields.Text("Information client complèmentaire")
    is_nb_lignes           = fields.Integer("Nb lignes", store=True, compute='_compute')
    is_date_envoi_mail     = fields.Datetime("Mail envoyé le", readonly=False)
    is_incoterm            = fields.Many2one('account.incoterms', 'Incoterm / Conditions de livraison', related='partner_id.is_incoterm', readonly=True)
    is_lieu                = fields.Char('Lieu', related='partner_id.is_lieu', readonly=True)
    is_ar_commentaire      = fields.Text("Commentaire AR de commande")
    is_message             = fields.Text("Message", compute='_compute_message')
    is_ar_contact_id       = fields.Many2many('res.partner', 'is_sale_ar_contact_id_rel', 'partner_id', 'contact_id', 'Destinataire AR de commande')
    is_point_dechargement  = fields.Char(u'Point de déchargement')
    client_order_ref       = fields.Char(string='N° de commande client') # Référence client => N° de commande client


    def _create_invoices(self, grouped=False, final=False, date=None):
        company = self.env.user.company_id
        if company.is_regrouper_ligne_commande:
            res = self._create_invoices_aves_regroupement(grouped=grouped, final=final, date=date)
        else:
            res = self._create_invoices_sans_regroupement(grouped=grouped, final=final, date=date)
        return res


    def _create_invoices_aves_regroupement(self, grouped=False, final=False, date=None):
        "Fonction remplacée le 31/05/2025 pour faire le lien entre les factures et les mouvements de stocks et regrouper les lignes des commandes"
        if not self.env['account.move'].check_access_rights('create', False):
            try:
                self.check_access_rights('write')
                self.check_access_rule('write')
            except AccessError:
                return self.env['account.move']

        invoice_vals_list = []
        invoice_item_sequence = 0 # Incremental sequencing to keep the lines order on the invoice.
        for order in self:
            order = order.with_company(order.company_id).with_context(lang=order.partner_invoice_id.lang)

            invoice_vals = order._prepare_invoice()
            invoiceable_lines = order._get_invoiceable_lines(final)

            if not any(not line.display_type for line in invoiceable_lines):
                continue

            #** Regroupement des lignes des commandes *************************
            invoiceable_lines_grouped={}
            pickings=[]
            for line in invoiceable_lines:
                key="%s-%s"%(line.is_client_order_ref,line.name)
                if key not in invoiceable_lines_grouped:
                    invoiceable_lines_grouped[key]={
                        'line': line,
                        'quantity':0,
                        'line_ids':[]    
                    }
                invoiceable_lines_grouped[key]['quantity']+=line.qty_to_invoice
                invoiceable_lines_grouped[key]['line_ids'].append(line)
            #******************************************************************

            #** Prépration des lignes des facture *****************************
            invoice_line_vals = []
            down_payment_section_added = False
            for key in invoiceable_lines_grouped:
                line     = invoiceable_lines_grouped[key]['line']
                quantity = invoiceable_lines_grouped[key]['quantity']
                line_ids = invoiceable_lines_grouped[key]['line_ids']
                # Create a dedicated section for the down payments (put at the end of the invoiceable_lines)
                if not down_payment_section_added and line.is_downpayment:
                    invoice_line_vals.append(
                        Command.create(
                            order._prepare_down_payment_section_line(sequence=invoice_item_sequence)
                        ),
                    )
                    down_payment_section_added = True
                    invoice_item_sequence += 1
                vals=line._prepare_invoice_line(sequence=invoice_item_sequence, quantity=quantity)
                vals['sale_line_ids']=[]
                for l in line_ids:
                    vals['sale_line_ids'].append(Command.link(l.id))
                invoice_line_vals.append(Command.create(vals))
                invoice_item_sequence += 1
            invoice_vals['invoice_line_ids'] += invoice_line_vals
            invoice_vals_list.append(invoice_vals)
            #******************************************************************

        if not invoice_vals_list and self._context.get('raise_if_nothing_to_invoice', True):
            raise UserError(self._nothing_to_invoice_error_message())

        #** Je désactive cette partie, car je pense qu'elle est inutile 
        # # 2) Manage 'grouped' parameter: group by (partner_id, currency_id).
        # if not grouped:
        #     new_invoice_vals_list = []
        #     invoice_grouping_keys = self._get_invoice_grouping_keys()
        #     invoice_vals_list = sorted(
        #         invoice_vals_list,
        #         key=lambda x: [
        #             x.get(grouping_key) for grouping_key in invoice_grouping_keys
        #         ]
        #     )
        #     for _grouping_keys, invoices in groupby(invoice_vals_list, key=lambda x: [x.get(grouping_key) for grouping_key in invoice_grouping_keys]):
        #         origins = set()
        #         payment_refs = set()
        #         refs = set()
        #         ref_invoice_vals = None
        #         for invoice_vals in invoices:
        #             if not ref_invoice_vals:
        #                 ref_invoice_vals = invoice_vals
        #             else:
        #                 ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
        #             origins.add(invoice_vals['invoice_origin'])
        #             payment_refs.add(invoice_vals['payment_reference'])
        #             refs.add(invoice_vals['ref'])
        #         ref_invoice_vals.update({
        #             'ref': ', '.join(refs)[:2000],
        #             'invoice_origin': ', '.join(origins),
        #             'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
        #         })
        #         new_invoice_vals_list.append(ref_invoice_vals)
        #     invoice_vals_list = new_invoice_vals_list

        #** Je ne sais pas à quoi sert cette partie ***************************
        if len(invoice_vals_list) < len(self):
            SaleOrderLine = self.env['sale.order.line']
            for invoice in invoice_vals_list:
                sequence = 1
                for line in invoice['invoice_line_ids']:
                    line[2]['sequence'] = SaleOrderLine._get_invoice_line_sequence(new=sequence, old=line[2]['sequence'])
                    sequence += 1
        #**********************************************************************

        #** Création des factures *********************************************
        moves = self.env['account.move'].sudo().with_context(default_move_type='out_invoice').create(invoice_vals_list)
        #**********************************************************************

        #** Transforme la facture en avoir si montant negatif *****************
        if final:
            moves.sudo().filtered(lambda m: m.amount_total < 0).action_switch_invoice_into_refund_credit_note()
        #**********************************************************************

        #** Ajout du message en bas des factures ******************************
        for move in moves:
            move.message_post_with_view(
                'mail.message_origin_link',
                values={'self': move, 'origin': move.line_ids.sale_line_ids.order_id},
                subtype_id=self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'))
        #**********************************************************************

        #** Facturation des mouvements de stocks ******************************
        invoices = moves
        for invoice in invoices:
            pickings=[]
            invoice.is_mode_envoi_facture   = invoice.partner_id.is_mode_envoi_facture
            invoice.invoice_payment_term_id = invoice.partner_id.property_payment_term_id.id
            for invoice_line in invoice.invoice_line_ids:
                invoice_line.is_section_analytique_id = invoice_line.product_id.is_section_analytique_id.id
                for sale_line in invoice_line.sale_line_ids:
                    for move in sale_line.move_ids:
                        if move.state!='cancel':
                            move.is_account_move_line_id = invoice_line.id
                            move.invoice_state='invoiced'
                            move.picking_id._compute_invoice_state()
                            invoice.invoice_date = move.picking_id.is_date_expedition
                            invoice_line.is_move_id = move.id
                            if move.picking_id.name not in pickings:
                                pickings.append(move.picking_id.name)
            invoice.invoice_origin=','.join(pickings)
        #**********************************************************************

        #** Mise à jour qty_invoiced de la ligne de commande ******************
        for order in self:
            order.is_compute_qty_invoiced()
        #**********************************************************************
        return invoices


    def is_compute_qty_invoiced(self):
        for obj in self:
            for line in obj.order_line:
                qty_invoiced = 0
                for move in line.move_ids:
                    if move.invoice_state=='invoiced' and move.is_account_move_line_id.move_id.state!='cancel':
                        qty = move.product_uom._compute_quantity(move.quantity_done, line.product_uom)
                        qty_invoiced+=qty
                line.qty_invoiced = qty_invoiced







    def _create_invoices_sans_regroupement(self, grouped=False, final=False, date=None):
        "Fonction surchargée pour faire le lien entre les factures et les mouvements de stocks"

        invoices = super()._create_invoices(grouped=grouped, final=final, date=date)
        for invoice in invoices:
            pickings=[]
            invoice.is_mode_envoi_facture   = invoice.partner_id.is_mode_envoi_facture
            invoice.invoice_payment_term_id = invoice.partner_id.property_payment_term_id.id

            #Modif du 02/08/2024 pour Céline => Position fiscale du client livré et non pas du client facturé
            #invoice.fiscal_position_id = invoice.partner_shipping_id.property_account_position_id.id
            #******************************************************************

            for line in invoice.line_ids:
                line.is_section_analytique_id = line.product_id.is_section_analytique_id.id

                #Modif du 02/08/2024 pour Céline => Position fiscale du client livré et non pas du client facturé
                #line._compute_account_id()
                # if line.display_type in ('line_section', 'line_note'):
                #     continue
                # if line.product_id or line.account_id.tax_ids or not line.tax_ids:
                #tax_ids = line._get_computed_taxes()
                #line.tax_ids = False
                #line._compute_tax_ids()
                #**************************************************************

                for sale_line in line.sale_line_ids:
                    for move in sale_line.move_ids:
                        #if not move.is_account_move_line_id and move.state=="done":
                        if move.state!="cancel":
                            move.is_account_move_line_id = line.id
                            move.invoice_state='invoiced'
                            move.picking_id._compute_invoice_state()
                            invoice.invoice_date = move.picking_id.is_date_expedition
                            line.is_move_id = move.id
                            if move.picking_id.name not in pickings:
                                pickings.append(move.picking_id.name)
            invoice.invoice_origin=','.join(pickings)
        return invoices













    def _message_auto_subscribe_notify(self, partner_ids, template):
        #Désactiver le message "Vous avez été assigné à"
        return


    def external_compute_delivery_status(self):
        "Permet d'appeller la méthode privée en XML-RPC pour la migration"
        orders=self.env['sale.order'].search([('is_type_commande','=', 'ls')]) #, order="id desc") #, limit=1000)
        for order in orders:
            for line in order.order_line:
                line._compute_qty_delivered()
                line._compute_qty_invoiced()
        self.env['sale.order'].search([('is_type_commande','=', 'ls')])._compute_delivery_status()
        self.env['sale.order'].search([('is_type_commande','=', 'ls')])._compute_invoice_status()
        return True


    @api.depends('partner_id')
    def _compute_message(self):
        for obj in self:
            #** Recherche messages *********************************************
            messages = ''
            where=['|',('name','=',obj.partner_id.id),('name','=',False)]
            for row in self.env['is.vente.message'].search(where):
                messages += row.message + '\n'
            #*******************************************************************
            obj.is_message = messages


    def onchange_client_order_ref(self, client_order_ref,partner_id):
        warning = {}
        if client_order_ref and partner_id:
            orders = self.env['sale.order'].search([('client_order_ref','=',client_order_ref),('partner_id','=',partner_id)],limit=1)
            if orders:
                warning = {
                    'title': _('ValidationError!'),
                    'message' : u"La commande "+orders[0].name+u" a déjà ce même numéro de commande client !"
                }
        return {
            'value'  : {},
            'warning': warning,
        }


    def fields_view_get(self, view_id=None, view_type='form', toolbar=False,submenu=False):
        res = super(sale_order, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,submenu=submenu)

        #** Suppression des rapports indiqués **********************************
        indexes=[]
        for idx, print_submenu in enumerate(res.get('toolbar', {}).get('print', [])):
            if print_submenu['display_name'] in ["Devis / Commande"]:
                indexes.append(idx)
        for idx in reversed(indexes):
            res['toolbar']['print'].pop(idx)
        #***********************************************************************

        return res


    def envoyer_ar_par_mail(self):
        uid=self._uid
        modele_mail = u"""
        <html>
            <head>
                <meta content="text/html; charset=UTF-8" http-equiv="Content-Type">
            </head>
            <body>
                <font>Bonjour, </font>
                <br><br>
                <font> Veuillez trouver ci-joint notre AR de commande.</font>
                <br><br>
                [commentaire]
                Cordialement <br><br>
                [from]<br>
            </body>
        </html>
        """
        for obj in self:
            mails=[]
            if obj.is_ar_contact_id:
                for c in obj.is_ar_contact_id:
                    mail = c.name + u' <' + c.email + u'>'
                    mails.append(mail)
            else:
                for c in obj.partner_id.child_ids:
                    if c.is_type_contact.name == 'Approvisionneur':
                        mail = c.name + u' <' + c.email + u'>'
                        mails.append(mail)
            if not mails:
                raise ValidationError(u"Aucun mail de type 'Approvisionneur' pour ce client !")
            email_contact = ','.join(mails)
            user  = self.env['res.users'].browse(uid)
            email = user.email
            nom   = user.name
            if email==False:
                raise ValidationError(u"Votre mail n'est pas renseigné !")

            #** Génération du PDF **********************************************
            name=u'ar_commande-' + obj.client_order_ref + u'.pdf'
            #pdf = self.env['report'].get_pdf(obj, 'is_plastigray16.report_ar_commande')
            pdf = self.env['ir.actions.report']._render_qweb_pdf('is_plastigray16.ar_commande_report',[obj.id])[0]
            #*******************************************************************

            # ** Recherche si une pièce jointe est déja associèe ***************
            model=self._name
            attachment_obj = self.env['ir.attachment']
            attachments = attachment_obj.search([('res_model','=',model),('res_id','=',obj.id),('name','=',name)])
            # ******************************************************************

            # ** Creation ou modification de la pièce jointe *******************
            vals = {
                'name':        name,
                #'datas_fname': name,
                'type':        'binary',
                'res_model':   model,
                'res_id':      obj.id,
                #'datas':       pdf.encode('base64'),
                'datas':       base64.b64encode(pdf),
            }
            attachment_id=False
            if attachments:
                for attachment in attachments:
                    attachment.write(vals)
                    attachment_id=attachment.id
            else:
                attachment = attachment_obj.create(vals)
                attachment_id=attachment.id
            #*******************************************************************

            email_cc      = nom + u' <'+email+u'>'

            email_from    = email_cc

            subject    = u'AR de commande Plastigray ' + obj.client_order_ref + ' pour ' + obj.partner_id.name
            #subject    = u'AR de commande Plastigray '+obj.client_order_ref+' pour '+obj.partner_id.name+u' (to='+email_contact+u')'

            email_to = email_contact
            #email_to = email_cc

            body_html = modele_mail.replace('[from]', user.name)
            if obj.is_ar_commentaire:
                commentaire = obj.is_ar_commentaire.replace('\n', '<br>') + '<br><br>'
            else:
                commentaire = ''
            if obj.is_message:
                commentaire += obj.is_message.replace('\n', '<br>') + '<br><br>'
            body_html = body_html.replace('[commentaire]', commentaire)
            email_vals = {
                'subject'       : subject,
                'email_to'      : email_to,
                'email_cc'      : email_cc,
                'email_from'    : email_from, 
                'body_html'     : body_html.encode('utf-8'), 
                'attachment_ids': [(6, 0, [attachment_id])] 
            }

            email_id = self.env['mail.mail'].create(email_vals)
            if email_id:
                self.env['mail.mail'].send(email_id)

            obj.message_post(body='Commande envoyée par mail à %s'%email_contact)
            obj.is_date_envoi_mail=datetime.now()


    def actualiser_prix_commande(self):
        for obj in self:
            for line in obj.order_line:
                line.set_price_justification()
            #     res=line.onchange_date_livraison(
            #         line.is_date_livraison, 
            #         line.product_id.id, 
            #         line.product_uom_qty, 
            #         line.product_uom.id, 
            #         obj.partner_id.id, 
            #         obj.pricelist_id.id, 
            #         obj.company_id.id, 
            #         obj.id)
            #     price=res['value']['price_unit']
            #     if price:
            #         line.price_unit=price


    def numeroter_lignes(self):
        for obj in self:
            lines = self.env['sale.order.line'].search([('order_id','=',obj.id)],order="is_date_expedition")
            sequence=0
            for line in lines:
                sequence=sequence+1
                line.sequence=sequence
        # return {
        #     #"type": "ir.actions.do_nothing",
        #     "type": "set_scrollTop",
        # }




    @api.onchange('partner_id')
    def pg_onchange_partner_id(self):
        if self.partner_id:
            partner = self.partner_id
            if partner.is_adr_facturation:
                self.partner_invoice_id = partner.is_adr_facturation.id
            if partner.is_source_location_id:
                self.is_source_location_id = partner.is_source_location_id.id
            if partner.is_transporteur_id:
                self.is_transporteur_id = partner.is_transporteur_id.id


    @api.depends('is_article_commande_id', 'is_article_commande_id.is_ref_client', 'is_article_commande_id.product_tmpl_id.is_ref_client')
    def _ref_client(self):
        for order in self:
            if order.is_article_commande_id:
                order.is_ref_client = order.is_article_commande_id.is_ref_client


    # def onchange_order_line(self, cr, uid, ids, type_commande, order_line, context=None):
    #     value = {}
    #     if len(order_line)>1:
    #         value.update({'is_type_commande_ro': True})
    #     else:
    #         value.update({'is_type_commande_ro': False})
    #     return {'value': value}


    def action_acceder_client(self):
        view_id = self.env.ref('base.view_partner_form').id
        for obj in self:
            return {
                'name': "Client",
                'view_mode': 'form',
                'view_id': view_id,
                'res_model': 'res.partner',
                'type': 'ir.actions.act_window',
                'res_id': obj.partner_id.id,
                'domain': '[]',
            }


    def action_acceder_commande(self):
        for obj in self:
            return {
                'name': "Commande",
                'view_mode': 'form',
                'res_model': 'sale.order',
                'type': 'ir.actions.act_window',
                'res_id': obj.id,
                'domain': '[]',
            }


    def _verif_tarif(self,vals):
        if 'is_type_commande' in vals and 'is_article_commande_id' in vals and 'pricelist_id' in vals :
            if vals['is_type_commande']=='ouverte':
                product_id=vals['is_article_commande_id']
                product   = self.env['product.product'].browse([product_id])
                partner   = self.env['res.partner'].browse(vals['partner_id'])
                pricelist_id=vals['pricelist_id']
                if pricelist_id:
                    pricelist=self.env['product.pricelist'].browse(pricelist_id)
                    qty = self.env['product.template'].get_lot_livraison(product.product_tmpl_id, partner)
                    if 'date_order' in vals:
                        date = vals['date_order']
                        if isinstance(date, str):
                            date = vals['date_order'][:10]
                            date = datetime.strptime(date, '%Y-%m-%d').date()
                        price, justification = pricelist.price_get(product, qty, date)
                        if price==0 and justification==False:
                            raise ValidationError("Il n'existe pas de tarif (liste de prix) pour l'article '"+str(product.is_code)+"' / qt="+str(qty)+ " / date="+str(date))


    def _verif_existe(self,vals):
        if 'is_article_commande_id' in vals:
            r=self.env['sale.order'].search([
                ['partner_id'            , '=', vals['partner_id']],
                ['is_article_commande_id', '=', vals['is_article_commande_id']],
                ['is_type_commande'      , '=', vals['is_type_commande']],
                ['state'                 , '=', 'draft'],
                ['is_type_commande'      , '=', 'ouverte'],
            ])
            if len(r)>1 :
                raise ValidationError("Il exite déjà une commande ouverte pour cet article et ce client")


    def _client_order_ref(self, obj):
        if obj.is_type_commande!='ls':
            for line in obj.order_line:
                line.is_client_order_ref=obj.client_order_ref


    def _verif_article_livrable(self, obj):
        for line in obj.order_line:
            ok=False
            for l in line.product_id.is_client_ids:
                if l.client_id.id==obj.partner_id.id:
                    ok=True
            if ok==False:
                raise ValidationError(u"L'article "+line.product_id.is_code+u" n'est pas livrable à ce client (cf fiche article) !")


    def _verif_champ_obligatoire(self,obj):
        champ_obligatoire = obj.partner_id.is_champ_obligatoire_id
        if champ_obligatoire:
            if champ_obligatoire.point_dechargement and not obj.is_point_dechargement:
                raise ValidationError("Le champ 'Point de déchargement' est obligatoire pour '%s'"%champ_obligatoire.name)


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._verif_existe(vals)
            self._verif_tarif(vals)
        res = super().create(vals_list)

        self._client_order_ref(res)
        self._verif_article_livrable(res)
        self._verif_champ_obligatoire(res)
        return res


    def write(self, vals):
        obj=super().write(vals)
        if "delivery_status" not in vals and "invoice_status" not in vals:
            for obj in self:
                vals2={
                    'is_type_commande'       : obj.is_type_commande,
                    'is_article_commande_id' : obj.is_article_commande_id.id,
                    'pricelist_id'           : obj.pricelist_id.id,
                    'partner_id'             : obj.partner_id.id,
                    'partner_invoice_id'     : obj.partner_invoice_id.id,
                    'date_order'             : obj.date_order.date(),
                }
                self._verif_tarif(vals2)
                self._verif_existe(vals2)
                self._client_order_ref(obj)
                self._verif_article_livrable(obj)
                self._verif_champ_obligatoire(obj)
                self.order_line._verif_champ_obligatoire()
        return obj


class sale_order_line(models.Model):
    _inherit = "sale.order.line"
    _order = 'order_id desc, sequence, is_date_livraison, id'


    #TODO : J'ai du surcharger ce champ pour ajouter un index (index=true)
    product_id            = fields.Many2one('product.product', 'Product', domain=[('sale_ok', '=', True)], change_default=True, readonly=True, states={'draft': [('readonly', False)]}, ondelete='restrict',index=True)

    is_justification      = fields.Char("Justif.", help="Ce champ est obligatoire si l'article n'est pas renseigné ou le prix à 0")
    is_date_livraison     = fields.Date("Date de liv.",index=True)
    is_date_expedition    = fields.Date("Date d'expé.", store=True, compute='_date_expedition',index=True)
    is_type_commande      = fields.Selection([('ferme', 'Ferme'),('previsionnel', 'Prév.')], string="Type",index=True)
    is_client_order_ref   = fields.Char("Commande client")
    is_ref_client         = fields.Char('Réf. client', related='product_id.is_ref_client', readonly=True)
    is_date_confirmation  = fields.Date("Date de confirmation")
    is_comment_confirm    = fields.Char("Commentaire de confirmation")
    is_ref_plan           = fields.Char("Réf. plan", related='product_id.is_ref_plan', readonly=True)
    is_ind_plan           = fields.Char("Indice plan", related='product_id.is_ind_plan', readonly=True)

    is_date_heure_livraison_au_plus_tot = fields.Char('Liv au plus tôt'  , help="Champ 'DateHeurelivraisonAuPlusTot' pour EDI Weidplas")
    is_code_routage                     = fields.Char('Code routage'     , help="Champ 'CodeRoutage' pour EDI Weidplas")
    is_point_destination                = fields.Char('Point destination', help="Champ 'CodeIdentificationPointDestination' pour EDI Weidplas")
    is_numero_document                  = fields.Char('N°Document'       , help="Champ 'NumeroDocument' pour EDI Weidplas => N°UM de PSA")
    is_tg_number                        = fields.Char('TG Number'        , help="Champ 'TGNumber' pour EDI Weidplas => N°UM de Weidplas")
    is_caldel_number                    = fields.Char('Caldel Number'    , help="Champ 'CaldelNumber' pour EDI Weidplas")
    is_num_ran                          = fields.Char('NumRAN'                  , help="Champ 'NumRAN' pour EDI PO => N°UM de PO")
    is_identifiant_transport            = fields.Char("N° identifiant transport", help="Champ 'IdTransport' pour EDI Weidplas/PO à remettre sur le BL")


    def _verif_champ_obligatoire(self):
        anomalies=[]
        for obj in self:
            if obj.is_type_commande=='ferme':
                champ_obligatoire = obj.order_id.partner_id.is_champ_obligatoire_id
                if champ_obligatoire:
                    field_dict={
                        'numero_document'      : 'is_numero_document',
                        'caldel_number'        : 'is_caldel_number',
                        'num_ran'              : 'is_num_ran',
                        'identifiant_transport': 'is_identifiant_transport',
                        'tg_number'            : 'is_tg_number',
                        'code_routage'         : 'is_code_routage',
                        'point_destination'    : 'is_point_destination',
                    }
                    for key in field_dict:
                        field_name   = field_dict[key]
                        field_value  = obj[field_name]
                        field_string = obj._fields[field_name].string
                        if champ_obligatoire[key] and not field_value:
                            msg = "Le champ '%s' est obligatoire pour '%s' (Sequence=%s, Article=%s)"%(
                                    field_string,
                                    champ_obligatoire.name,
                                    obj.sequence,
                                    obj.product_id.is_code
                            )
                            anomalies.append(msg)
        if len(anomalies)>0:
            anomalies='\n'.join(anomalies)
            raise ValidationError(anomalies)


    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res._verif_champ_obligatoire()
        return res


    # Cela n'est pas utile, car le write des lignes est fait avec le write de la commande
    # def write(self, vals):
    #     res=super().write(vals)
    #     self._verif_champ_obligatoire()
    #     return res


    @api.depends('is_date_livraison')
    def _date_expedition(self):
        for order in self:
            if order.is_date_livraison:
                cr      = self._cr
                uid     = self._uid
                context = self._context
                res_partner = self.env['res.partner']
                delai_transport = order.order_id.partner_id.is_delai_transport
                date_expedition = order.is_date_livraison
                #date_expedition = datetime.datetime.strptime(date_expedition, '%Y-%m-%d')
                #Delai de transport en jour ouvrés (sans samedi et dimanches)
                if delai_transport:
                    while delai_transport>0:
                        date_expedition = date_expedition - timedelta(days=1)
                        weekday = date_expedition.weekday()
                        if weekday not in [5,6]:
                            delai_transport = delai_transport - 1
                # jours de fermeture de la société
                jours_fermes = res_partner.num_closing_days(order.order_id.company_id.is_calendrier_expedition_id)

                # Jours de congé de la société
                leave_dates = res_partner.get_leave_dates(order.order_id.company_id.is_calendrier_expedition_id)
                #date_expedition = date_expedition - datetime.timedelta(days=delai_transport)
                new_date = date_expedition
                while True:
                    #date_txt=new_date.strftime('%Y-%m-%d')
                    #num_day = int(time.strftime('%w', time.strptime( date_txt, '%Y-%m-%d')))
                    num_day = int(new_date.strftime('%w'))
                    if (num_day in jours_fermes or str(new_date) in leave_dates):
                        new_date = new_date - timedelta(days=1)
                    else:
                        break
                date_expedition = new_date.strftime('%Y-%m-%d')
                order.is_date_expedition=date_expedition


    def action_acceder_commande(self):
        view_id = self.env.ref('sale.view_order_form').id
        for obj in self:
            return {
                'name': "Commande",
                'view_mode': 'form',
                'view_id': view_id,
                'res_model': 'sale.order',
                'type': 'ir.actions.act_window',
                'res_id': obj.order_id.id,
                'domain': '[]',
            }

    def action_acceder_client(self):
        view_id = self.env.ref('base.view_partner_form').id
        for obj in self:
            return {
                'name': "Client",
                'view_mode': 'form',
                'view_id': view_id,
                'res_model': 'res.partner',
                'type': 'ir.actions.act_window',
                'res_id': obj.order_id.partner_id.id,
                'domain': '[]',
            }


    def action_acceder_article(self):
        view_id = self.env.ref('is_plastigray16.is_product_template_only_form_view').id
        for obj in self:
            return {
                'name': "Article",
                'view_mode': 'form',
                'view_id': view_id,
                'res_model': 'product.template',
                'type': 'ir.actions.act_window',
                'res_id': obj.product_id.product_tmpl_id.id,
                'domain': '[]',
            }


    def check_date_livraison(self, date_livraison,  partner):
        if partner and date_livraison:
            # jours de fermeture de la société
            jours_fermes = partner.num_closing_days(partner)
            # Jours de congé de la société
            leave_dates = partner.get_leave_dates(partner,avec_jours_feries=True)
            # num de jour dans la semaine de la date de livraison
            num_day = date_livraison.strftime("%w")            
            if int(num_day) in jours_fermes or date_livraison in leave_dates:
                return False
        return True


    def set_price_justification(self):
        """Recherche prix et justifcation dans liste de prix pour date et qt et mise à jour"""
        for obj in self:
            price = 0
            justifcation = False
            if obj.order_id.pricelist_id:
                price, justifcation = obj.order_id.pricelist_id.price_get(
                    product = obj.product_id,
                    qty     = obj.product_uom_qty, 
                    date    = obj.is_date_livraison
                )
            obj.price_unit = price
            obj.is_justification = justifcation


    @api.onchange('product_id')
    def onchange_product_id_qty(self):
        for obj in self:
            obj._compute_price_unit()


    @api.onchange('is_date_livraison')
    def onchange_date_livraison(self):
        if self.order_id:
            self.set_price_justification()
            partner=self.order_id.partner_id
            check_date = self.check_date_livraison(self.is_date_livraison, partner)
            if not check_date:
                warning = {
                    'title': 'Attention!',
                    'message' : 'La date de livraison tombe pendant la fermeture du client.'
                }
                return {'warning': warning}


    #TODO : Fonction créée le 03/02/2024 pour ne pas arrondir au lot la quantité depuis la liste à servir (uniquement en saisie directe)
    @api.onchange('product_id', 'product_uom', 'product_uom_qty')
    def _pg_onchange_product_uom_qty(self):
        qty = self.env['product.template'].get_arrondi_lot_livraison(self.product_id, self.order_id.partner_id, self.product_uom_qty)
        self.product_uom_qty = qty
        self.set_price_justification()


    #TODO : Fonction désactivée le 03/02/2024 pour ne pas arrondir au lot la quantité depuis la liste à servir (uniquement en saisie directe)
    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_price_unit(self):
        return
        # context=self.env.context 
        # if 'no_compute_price_unit' not in context:
        #     for obj in self:
                #** Arrondir au lot et au multiple du lot *****************************
                #qty = self.env['product.template'].get_arrondi_lot_livraison(obj.product_id, obj.order_id.partner_id, obj.product_uom_qty)
                #obj.product_uom_qty = qty
                #** Recherche et mise à jour prix et justification dans liste de prix pour date qt
                # obj.set_price_justification()


            # # check if there is already invoiced amount. if so, the price shouldn't change as it might have been
            # # manually edited
            # if line.qty_invoiced > 0:
            #     continue
            # if not line.product_uom or not line.product_id or not line.order_id.pricelist_id:
            #     line.price_unit = 0.0
            # else:
            #     price = line.with_company(line.company_id)._get_display_price()
            #     line.price_unit = line.product_id._get_tax_included_unit_price(
            #         line.company_id,
            #         line.order_id.currency_id,
            #         line.order_id.date_order,
            #         'sale',
            #         fiscal_position=line.order_id.fiscal_position_id,
            #         product_price_unit=price,
            #         product_currency=line.currency_id
            #     )


class is_vente_message(models.Model):
    _name='is.vente.message'
    _description="is_vente_message"
    _order='name'
    _sql_constraints = [('name_uniq','UNIQUE(name)', 'Un message pour ce client existe déjà')] 

    name    = fields.Many2one('res.partner', 'Client')
    message = fields.Text('Message')
