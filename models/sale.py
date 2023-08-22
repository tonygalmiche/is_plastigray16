# -*- coding: utf-8 -*-
from odoo import models,fields,api
from odoo.exceptions import ValidationError
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
        uid=self.uid
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
            pdf = self.env['ir.actions.report']._render_qweb_pdf('is_plastigray16.report_ar_commande',[obj.id])[0]
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

            obj.message_post(u'Commande envoyée par mail à '+ email_contact)
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
                'view_type': 'form',
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
                'view_type': 'form',
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


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._verif_existe(vals)
            self._verif_tarif(vals)
        res = super().create(vals_list)

        self._client_order_ref(res)
        self._verif_article_livrable(res)
        return res


    def write(self, vals):
        obj=super().write(vals)
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



    # Le 22/06/2020 à 12:02, Caroline CHEVALLIER a écrit :
    # Date de livraison - délai de transport = date d'expédition.
    # Il faut ensuite comparer la date d'expédition au calendrier usine. 
    # Si la la date d'expédition se situe un jour où l'entreprise est fermée, il faut ramener la date d'expédition au 1er jour ouvré.

    # J'ai aussi une autre demande qui concerne le calendrier usine : nous avons besoin de 2 calendriers usine : un calendrier pour la production 
    # et qui sert au calcul de besoin et un calendrier pour les expéditions qui sert au calcul de la date d'expédition. 
    # La plupart du temps, ces 2 calendriers sont identiques mais en période estivale, ces calendriers sont différents 
    # car nous avons besoin d'avoir une permanence logistique et nous avons besoin de pouvoir expédier des produits.

    # Date de livraison = 31/07/2020
    # Nous avons fermé le calendrier de la société les 29/30/31 juillet : 
    # le temps de transport est inchangé : 2 jours : le 29/07 étant fermé, 
    # le système devrait positionné la commande au 28/07 : premier jour ouvert dans le calendrier.

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
                    num_day = new_date.strftime('%w')

                    if (num_day in jours_fermes or new_date in leave_dates):
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
                'view_type': 'form',
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
                'view_type': 'form',
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
                'view_type': 'form',
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


    # @api.onchange('product_id')
    # def product_id_change(self):
    #     #** Recherche et mise à jour prix et justification dans liste de prix pour date qt
    #     self.set_price_justification()


    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_price_unit(self):
        #** Arrondir au lot et au multiple du lot *****************************
        qty = self.env['product.template'].get_arrondi_lot_livraison(self.product_id, self.order_id.partner_id, self.product_uom_qty)
        self.product_uom_qty = qty
        #** Recherche et mise à jour prix et justification dans liste de prix pour date qt
        self.set_price_justification()



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
