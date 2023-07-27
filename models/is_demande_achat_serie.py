# -*- coding: utf-8 -*-
from odoo import models,fields,api
from odoo.exceptions import ValidationError
import datetime


class is_demande_achat_serie(models.Model):
    _name='is.demande.achat.serie'
    _description="Demande d'achat série"
    _inherit=['mail.thread']
    _order='name desc'


    @api.depends('line_ids')
    def _compute(self):
        uid=self._uid
        for obj in self:
            montant_total = 0
            for line in obj.line_ids:
                obj.product_id=line.product_id.id
                montant_total+=line.montant
            nb_lignes=len(obj.line_ids)
            if nb_lignes>1:
                raise ValidationError('Une seule ligne autorisée !')
            obj.nb_lignes     = nb_lignes
            obj.montant_total = montant_total

 
    @api.depends('line_ids')
    def _compute_vsb(self):
        uid=self._uid
        for obj in self:
            vsb=False
            if obj.state!='brouillon' and uid==obj.acheteur_id.id:
                vsb=True
            obj.vers_brouillon_vsb=vsb
            vsb=False
            if obj.state=='brouillon':
                vsb=True
            obj.vers_transmis_achat_vsb=vsb
            vsb=False
            if obj.state=='transmis_achat' and uid==obj.acheteur_id.id:
                vsb=True
            obj.vers_solde_vsb=vsb
            vsb=False
            if obj.state=='brouillon' and uid==obj.createur_id.id:
                vsb=True
            if obj.state=='transmis_achat' and uid==obj.acheteur_id.id:
                vsb=True
            obj.vers_annule_vsb=vsb


    name                 = fields.Char("N° demande achat série", readonly=True)
    createur_id          = fields.Many2one('res.users', 'Demandeur', required=True, default=lambda self: self.env.uid)
    date_creation        = fields.Date("Date de création", required=True, default=lambda *a: fields.datetime.now())
    acheteur_id          = fields.Many2one('res.users', 'Acheteur', required=True)
    fournisseur_id       = fields.Many2one('res.partner', 'Fournisseur', domain=[('is_company','=',True)], required=True)
    pricelist_id         = fields.Many2one('product.pricelist', "Liste de prix", related='fournisseur_id.pricelist_purchase_id', readonly=True)
    is_type_cde_fournisseur = fields.Selection(string="Type commande fourniseur", related='fournisseur_id.is_type_cde_fournisseur', readonly=True)
    delai_livraison      = fields.Date("Délai de livraison", required=True)
    lieu_livraison_id    = fields.Many2one('res.partner', 'Lieu de livraison', domain=[('is_company','=',True)], required=True, default=lambda self: self._lieu_livraison_id())
    is_incoterm          = fields.Many2one(string="Incoterm  / Conditions de livraison", related='fournisseur_id.is_incoterm', readonly=True)
    is_lieu              = fields.Char("Lieu", related='fournisseur_id.is_lieu', readonly=True)
    motif                = fields.Selection([
        ('pas_tarif'    , "Pas de tarif de créé"),
        ('fin_vie'      , "Produit en fin de vie (Lot trop important)"),
        ('inf_lot_appro', "Besoin inférieur au lot d'appro"),
        ('gest_18'      , "Gest 18 = Achat réalisé par le service achat"),
    ], "Motif")
    commentaire          = fields.Text("Commentaire")
    state                = fields.Selection([
        ('brouillon'     , 'Brouillon'),
        ('transmis_achat', 'Transmis achat'),
        ('solde'         , 'Soldé'),
        ('annule'        , 'Annulé'),
    ], "Etat", default="brouillon")
    order_id                = fields.Many2one('purchase.order', 'Commande générée', readonly=True, copy=False)
    line_ids                = fields.One2many('is.demande.achat.serie.line'  , 'da_id', u"Lignes", copy=True)
    montant_total           = fields.Float("Montant Total"                            , compute='_compute', readonly=True, store=True)
    nb_lignes               = fields.Integer("Nombre de lignes"                       , compute='_compute', readonly=True, store=True)
    product_id              = fields.Many2one('product.product', 'Article'            , compute='_compute', readonly=True, store=True)

    vers_brouillon_vsb      = fields.Boolean('Champ technique vers_brouillon_vsb'     , compute='_compute_vsb', readonly=True, store=False)
    vers_transmis_achat_vsb = fields.Boolean('Champ technique vers_transmis_achat_vsb', compute='_compute_vsb', readonly=True, store=False)
    vers_solde_vsb          = fields.Boolean('Champ technique vers_solde_vsb'         , compute='_compute_vsb', readonly=True, store=False)
    vers_annule_vsb         = fields.Boolean('Champ technique vers_annule_vsb'        , compute='_compute_vsb', readonly=True, store=False)


    def _lieu_livraison_id(self):
        user = self.env['res.users'].browse(self._uid)
        partner_id = user.company_id.partner_id.id
        return partner_id


    def fournisseur_id_on_change(self,fournisseur_id):
        res={}
        if fournisseur_id:
            res['value']={}
            partner = self.env['res.partner'].browse(fournisseur_id)
            lieu_livraison_id=partner.is_livre_a_id.id
            if lieu_livraison_id:
                res['value']['lieu_livraison_id']=lieu_livraison_id
        return res


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('is.demande.achat.serie')
        return super().create(vals_list)


    def vers_brouillon_action(self):
        for obj in self:
            if obj.acheteur_id.id==self._uid or self._uid==1:
                obj.sudo().state="brouillon"


    def vers_transmis_achat_action(self):
        for obj in self:
            article=u''
            for line in obj.line_ids:
                article=u' ('+line.product_id.is_code+u' / '+line.product_id.name+u')'
            subject=u'['+obj.name+u'] Transmis achat'+article
            email_to=obj.acheteur_id.email
            user  = self.env['res.users'].browse(self._uid)
            email_from = user.email
            email_cc   = email_from
            nom   = user.name
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url=base_url+u'/web#id='+str(obj.id)+u'&view_type=form&model=is.demande.achat.serie'
            body_html=u"""
                <p>Bonjour,</p>
                <p>"""+nom+""" vient de passer la demande d'achat série <a href='"""+url+"""'>"""+obj.name+"""</a> à l'état 'Transmis achat'.</p>
                <p>Merci d'en prendre connaissance.</p>
            """
            self.envoi_mail(email_from,email_to,email_cc,subject,body_html)
            obj.state="transmis_achat"


    def vers_solde_action(self):
        for obj in self:
            order_obj      = self.env['purchase.order']
            order_line_obj = self.env['purchase.order.line']
            partner=obj.fournisseur_id
            if partner.pricelist_purchase_id:
                vals={
                    'partner_id'      : partner.id,
                    'is_livre_a_id'   : obj.lieu_livraison_id.id,
                    'location_id'     : partner.is_source_location_id.id,
                    'fiscal_position_id': partner.property_account_position_id.id,
                    'payment_term_id' : partner.property_supplier_payment_term_id.id,
                    'pricelist_id'    : partner.pricelist_purchase_id.id,
                    'currency_id'     : partner.pricelist_purchase_id.currency_id.id,
                    'is_num_da'       : obj.name,
                    'is_demandeur_id' : obj.createur_id.id,
                    'incoterm_id'     : partner.is_incoterm.id,
                    'is_lieu'         : partner.is_lieu,
                }
                order=order_obj.create(vals)
                print(order,vals)
                obj.order_id=order.id
                line=False
                if len(obj.line_ids)==1:
                    line=obj.line_ids[0]
                test=True
                if order and line:
                    vals={}
                    vals['product_qty']  = line.quantite
                    vals['price_unit']   = line.prix
                    vals['order_id']     = order.id
                    vals['date_planned'] = obj.delai_livraison
                    vals['product_id']   = line.product_id.id
                    order_line=order_line_obj.create(vals)
                    order.button_confirm()
                    obj.state="solde"
                    subject=u'['+obj.name+u'] Soldé ('+line.product_id.is_code+u' / '+line.product_id.name+u')'
                    email_to=obj.createur_id.email
                    user  = self.env['res.users'].browse(self._uid)
                    email_from = user.email
                    nom   = user.name
                    base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                    url=base_url+u'/web#id='+str(obj.id)+u'&view_type=form&model=is.demande.achat.serie'
                    body_html=u"""
                        <p>Bonjour,</p>
                        <p>"""+nom+""" vient de passer la demande d'achat série <a href='"""+url+"""'>"""+obj.name+"""</a> à l'état 'Soldé'.</p>
                        <p>Merci d'en prendre connaissance.</p>
                    """
                    self.envoi_mail(email_from,email_to,'',subject,body_html)


    def vers_annule_action(self):
        for obj in self:
            if obj.createur_id.id==self._uid or obj.acheteur_id.id==self._uid:
                obj.sudo().state="annule"


    def envoi_mail(self, email_from,email_to,email_cc,subject,body_html):
        for obj in self:
            vals={
                'email_from'    : email_from, 
                'email_to'      : email_to, 
                'email_cc'      : email_cc,
                'subject'       : subject,
                'body_html'     : body_html, 
            }
            email=self.env['mail.mail'].sudo().create(vals)
            if email:
                self.env['mail.mail'].send(email)


class is_demande_achat_serie_line(models.Model):
    _name='is.demande.achat.serie.line'
    _description="Lignes demande d'achat série"
    _order='da_id,sequence'


    @api.depends('product_id','quantite','prix')
    def _compute(self):
        for obj in self:
            if obj.product_id:
                obj.uom_id=obj.product_id.uom_po_id
            obj.montant=obj.quantite*obj.prix

    da_id                  = fields.Many2one('is.demande.achat.serie', "Demande d'achat", required=True, ondelete='cascade', readonly=True)
    sequence               = fields.Integer('Ordre')
    product_id             = fields.Many2one('product.product', 'Article', domain=[('is_category_id.name','<','62')], required=True)
    uom_id                 = fields.Many2one('uom.uom', "Unité d'achat", compute='_compute', readonly=True, store=True)
    quantite               = fields.Float("Quantité", digits=(14,4), required=True)
    prix                   = fields.Float("Prix"    , digits=(14,4))
    montant                = fields.Float("Montant", compute='_compute', readonly=True, store=True)


    def product_id_on_change(self,parent,product_id,quantite):
        cr=self._cr
        res={}
        fournisseur_id=parent.fournisseur_id
        if fournisseur_id:
            partner = self.env['res.partner'].browse(fournisseur_id)
            pricelist_id=partner.property_product_pricelist_purchase.id
            if product_id:
                res['value']={}
                product = self.env['product.product'].browse(product_id)
                now=datetime.datetime.now().strftime('%Y-%m-%d')
                sql="""
                    select 
                        is_prix_achat("""+str(pricelist_id)+""", """+str(product_id)+""", """+str(quantite)+""", '"""+now+"""') 
                    from product_product
                    where id="""+str(product_id)+"""
                """
                cr.execute(sql)
                prix=0
                for row in cr.fetchall():
                    prix=row[0]
                res['value']['prix']=prix
        return res


