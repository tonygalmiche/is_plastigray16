# -*- coding: utf-8 -*-
from odoo import models,fields,api
from odoo.exceptions import ValidationError
from math import ceil
from datetime import datetime
import base64


class purchase_order_line(models.Model):
    _inherit = "purchase.order.line"

    is_justification = fields.Char("Justification" , help="Ce champ est obligatoire si l'article n'est pas renseigné ou le prix à 0")
    is_num_chantier  = fields.Char("N° du chantier", help="Champ utilisé pour la gestion des investissements sous la forme Mxxxx/xxxxx")
    #date_planned     = fields.Date("Date prévue") #TODO : Pour remplacer Datetime par Date


    @api.depends('product_qty', 'product_uom')
    def _compute_price_unit_and_date_planned_and_name(self):
        'Désactivation de cette fonction le 20/01/2024'
        print("## _compute_price_unit_and_date_planned_and_name",self, self.product_qty)
        return


    # @api.depends('product_packaging_qty')
    # def _compute_product_qty(self):
    #     'Désactivation de cette fonction le 18/02/2024'
    #     print("## _compute_product_qty",self, self.product_qty, self.product_uom_qty)
    #     return
 

    # @api.depends('product_uom', 'product_qty', 'product_id.uom_id')
    # def _compute_product_uom_qty(self):
    #     'Désactivation de cette fonction le 18/02/2024'
    #     print("## _compute_product_uom_qty",self, self.product_qty, self.product_uom_qty)
    #     return


    def set_price_justification(self):
        """Recherche prix et justifcation dans liste de prix pour date et qt et mise à jour"""
        price = 0
        justifcation = False
        if self.order_id.pricelist_id and self.date_planned:
            price, justifcation = self.order_id.pricelist_id.price_get(
                product = self.product_id,
                qty     = self.product_qty, 
                date    = self.date_planned.date()
            )
        self.price_unit = price
        self.is_justification = justifcation


    def _suggest_quantity(self):
        "La quantité par défaut est mise au lot (en unité d'achat)"
        if not self.product_id:
            return
        if self.product_qty>0:
            return
        if not self.product_uom:
            self.product_uom = self.product_id.uom_po_id.id
        lot = self.product_id.lot_mini
        # Convertir lot en unité d'achat
        qty = self.product_id.uom_id._compute_quantity(lot, self.product_uom, round=True, rounding_method='UP', raise_if_failure=True)
        self.product_qty = round(qty,6)
        # Le prix est initialisé au début avec le lot est n'est plus calculé ensuite même si la quanité ou la date changent
        self.set_price_justification()


    @api.onchange('product_qty','product_uom')
    def is_onchange_product_id(self):
        "Si la quantité est modifiée, il faut l'arrondir au lot et au multiple du lot"
        if not self.product_uom:
            self.product_uom = self.product_id.uom_po_id.id
        qty      = self.product_qty 
        lot      = self.product_id.lot_mini
        multiple = self.product_id.multiple
        if multiple==0:
            multiple=1
        # Convertir qty en unité de stock pour pouvoir la comparer au lot
        qty = self.product_uom._compute_quantity(qty, self.product_id.uom_id, round=True, rounding_method='UP', raise_if_failure=True)
        if qty<lot:
            qty=lot
        else:
            delta=round(qty-lot,8)
            qty=lot+multiple*ceil(delta/multiple)
        # Convertir qty en unité d'achat
        qty = self.product_id.uom_id._compute_quantity(qty, self.product_uom, round=True, rounding_method='UP', raise_if_failure=True)
        self.product_qty = round(qty,6)
        # Le prix est calculé uniquement si il n'est pas déja renseigné
        if not self.price_unit and not self.is_justification:
            self.set_price_justification()
        self._compute_tax_id()


    @api.onchange('date_planned')
    def onchange_date_planned(self):
        #Le prix est actualisé uniquement si il n'est pas déjà renseigné"
        if not self.price_unit and not self.is_justification:
            self.set_price_justification()

        res=True
        #** Recherche si le partner est ouvert cette journée avec les jours fériés du pays
        partner=self.order_id.partner_id
        if partner:
            res = partner.test_date_dispo(self.date_planned, partner, avec_jours_feries=True)

        #** Recherche si plastigray est ouvert cette journée sans les jours fériés du pays
        partner_company = self.env.user.company_id.partner_id
        if partner_company and res:
            date=self.date_planned
            res = partner_company.test_date_dispo(date, partner, avec_jours_feries=False)
        if res==False:
            warning = {
                'title'  : 'Attention!',
                'message': 'La date prévue tombe pendant la fermeture du fournisseur ou de plastigray !'
            }
            return {'warning': warning}


class purchase_order(models.Model):
    _inherit = "purchase.order"

    is_contact_id        = fields.Many2one('res.partner', 'Contact Logistique')
    is_livre_a_id        = fields.Many2one('res.partner', 'Livrer à', help="Indiquez l'adresse de livraison si celle-ci est différente de celle de la société")
    is_num_da            = fields.Char("N°Demande d'achat")
    is_document          = fields.Char("Document (N° de dossier)")
    is_demandeur_id      = fields.Many2one('res.users', 'Demandeur', default=lambda self: self.env.user)
    is_date_confirmation = fields.Date("Date de confirmation du fournisseur")
    is_commentaire       = fields.Text("Commentaire")
    is_acheteur_id       = fields.Many2one('res.users','Acheteur')
    is_date_envoi_mail   = fields.Datetime("Mail envoyé le", readonly=True)
    is_cfc_id            = fields.Many2one('is.cde.ferme.cadencee', 'Commande ferme cadencée', readonly=True)
    is_date_end_cfc      = fields.Date("Date de fin de la cde ferme cadencée", readonly=True)
    is_lieu              = fields.Char("Lieu")
    is_modified          = fields.Boolean('Commande modifiée')
    pricelist_id         = fields.Many2one('product.pricelist','Liste de prix')
    #date_planned         = fields.Date("Date prévue") #TODO : Pour remplacer Datetime par Date
    location_id          = fields.Many2one('stock.location', 'Destination') #TODO : Ce champ n'existait plus dans Odoo 16 
    is_type_cde_fournisseur  = fields.Selection(related='partner_id.is_type_cde_fournisseur')
    is_date_creation_picking = fields.Date("Date création picking", compute='_compute_is_date_creation_picking')

    is_dosmat_caracteristique_specifique = fields.Text("Caractéristiques spécifiques", compute='_compute_is_dosmat_caracteristique_specifique')


    def _compute_is_dosmat_caracteristique_specifique(self):
        for obj in self:
            val=False
            for line in obj.order_line:
                if line.product_id.is_dosmat_caracteristique_specifique:
                    val =  line.product_id.is_dosmat_caracteristique_specifique
                    break
            if val:
                val="Pour les matières premières, le certificat de conformité/d'analyse doit obligatoirement être fourni au moment de la livraison.\nVous devez assurer la conformité de la matière sur la (ou les) caractéristique(s) spécifique(s) suivante(s) :\n%s"%val
            obj.is_dosmat_caracteristique_specifique = val


    def _compute_is_date_creation_picking(self):
        for obj in self:
            d = False
            pickings = self.env['stock.picking'].search([('is_purchase_order_id','=',obj.id),('state','!=','cancel')])
            for picking in pickings:
                d = picking.create_date
            obj.is_date_creation_picking = d


    # def _message_auto_subscribe_notify(self, partner_ids, template):
    #     "Désactiver les notifications d'envoi des mails"
    #     print("_message_auto_subscribe_notify")
    #     return True


    def _add_supplier_to_product(self):
        # Désactivation de cette fonction qui ajoute automatiquement un fournisseur à la fiche article lors de la validation de la commande
        return True


    #TODO : Désactvié le 15/01/2024, car cela posait des problèmes d'emplacement lors de la modification des commandes
    # def button_confirm(self):
    #     res = super().button_confirm()
    #     if self.location_id:
    #         for picking in self.picking_ids:
    #             if picking.state=="assigned":
    #                 picking.location_dest_id = self.location_id.id
    #                 for move in picking.move_ids_without_package:
    #                     if move.state not in ('done','cancel'):
    #                         print(move, move.state,move.location_dest_id)
    #                         for line in move.move_line_ids:
    #                             if line.state not in ('done','cancel'):
    #                                 print(line, line.state, line.location_dest_id)
    #                                 line.location_dest_id=self.location_id.id
    #    return res


    def envoyer_par_mail(self):
        uid=self._uid
        modele_mail="""
        <html>
            <head>
                <meta content="text/html; charset=UTF-8" http-equiv="Content-Type">
            </head>
            <body>
                <font>Bonjour, </font>
                <br><br>
                <font> Veuillez trouver ci-joint notre commande.</font>
                <br><br>
                Cordialement <br><br>
                [from]<br>
            </body>
        </html>
        """

        for obj in self:
            email_contact=obj.is_contact_id.email
            if email_contact==False:
                raise ValidationError(u"Mail non renseigné pour ce contact !")
            user  = self.env['res.users'].browse(uid)
            email = user.email
            nom   = user.name
            if email==False:
                raise ValidationError(u"Votre mail n'est pas renseigné !")


            #** Génération du PDF **********************************************
            name=u'commande-'+obj.name+u'.pdf'
            #pdf = self.env['report'].get_pdf(obj, 'is_plastigray16.is_report_purchaseorder')
            pdf = self.env['ir.actions.report']._render_qweb_pdf('is_plastigray16.purchaseorder_report',[obj.id])[0]




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

            email_cc      = nom+u' <'+email+u'>'
            email_from    = email_cc

            #** Demandeur en copie *********************************************
            if obj.is_demandeur_id.email:
                email_cc = email_cc + ',' + obj.is_demandeur_id.name + u' <'+obj.is_demandeur_id.email+u'>'
            #*******************************************************************


            email_contact = obj.is_contact_id.name+u' <'+obj.is_contact_id.email+u'>'

            subject    = u'Commande Plastigray '+obj.name+' pour '+obj.partner_id.name
            #subject    = u'Commande Plastigray '+obj.name+' pour '+obj.partner_id.name+u' (to='+email_contact+u')'

            email_to = email_contact
            #email_to = email_cc

            email_vals = {}
            body_html=modele_mail.replace('[from]', user.name)
            email_vals.update({
                'subject'       : subject,
                'email_to'      : email_to,
                'email_cc'      : email_cc,
                'email_from'    : email_from, 
                'body_html'     : body_html.encode('utf-8'), 
                'attachment_ids': [(6, 0, [attachment_id])] 
            })

            email_id=self.env['mail.mail'].create(email_vals)
            if email_id:
                self.env['mail.mail'].send(email_id)

            obj.message_post(body='Commande envoyée par mail à %s'%email_contact)
            obj.is_date_envoi_mail=datetime.now()


    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            partner = self.partner_id
            self.pricelist_id  = partner.pricelist_purchase_id.id
            self.is_livre_a_id = partner.is_livre_a_id.id
            self.incoterm_id   = partner.is_incoterm.id
            self.is_lieu       = partner.is_lieu
            self.location_id   = partner.is_source_location_id.id

        #** Recherche du contact logistique ************************************
        cr = self._cr
        if self.partner_id:
            SQL="""
                select rp.id, rp.is_type_contact, itc.name
                from res_partner rp inner join is_type_contact itc on rp.is_type_contact=itc.id
                where 
                    rp.parent_id="""+str(self.partner_id.id)+""" and 
                    rp.active='t' and
                    itc.name ilike '%logistique%' 
                limit 1
            """
            cr.execute(SQL)
            result = cr.fetchall()
            for row in result:
                self.is_contact_id = row[0]
        #***********************************************************************


    def actualiser_prix_commande(self):
        for obj in self:
            for line in obj.order_line:
                line.set_price_justification()
                # res = line.onchange_product_id(
                #     obj.pricelist_id.id, 
                #     line.product_id.id, 
                #     line.product_qty, 
                #     line.product_uom.id,
                #     obj.partner_id.id, 
                #     date_order   = str(line.date_planned)+u' 12:00:00',
                #     date_planned = line.date_planned,
                # )
                # price=res['value']['price_unit']
                # if not price:
                #     raise ValidationError(u"Modification non éffectuée, car prix non trouvé")
                # line.price_unit=price


    def actualiser_taxes_commande(self):
        for obj in self:
            for line in obj.order_line:
                line._compute_tax_id()


    def test_prix0(self):
        for obj in self:
            for line in obj.order_line:
                if not line.is_justification and not line.price_unit:
                    raise ValidationError("Prix à 0 sans justification pour l'article "+str(line.product_id.is_code))


    def write(self,vals):
        res=super().write(vals)
        for obj in self:
            obj.test_prix0()
        return res


    @api.model_create_multi
    def create(self, vals_list):
        res=super().create(vals_list)
        self.test_prix0()
        return res


    def get_da(self):
        res=False
        for obj in self:
            if obj.is_num_da:
                type_da=obj.is_num_da[:4]
                model=False
                if type_da=='DAFG':
                    model = 'is.demande.achat.fg'
                if type_da=='DAI-':
                    model = 'is.demande.achat.invest'
                if type_da=='DAM-':
                    model = 'is.demande.achat.moule'
                if model:
                    das = self.env[model].search([('name','=',obj.is_num_da)])
                    for da in das:
                        date_devis=da.date_devis
                        if date_devis:
                            #d=datetime.strptime(date_devis,'%Y-%m-%d')
                            date_devis=date_devis.strftime('%d/%m/%Y')
                        res=''
                        if da.num_devis:
                            res=res+da.num_devis
                        if date_devis:
                            res=res+' du '+date_devis
        return res 



