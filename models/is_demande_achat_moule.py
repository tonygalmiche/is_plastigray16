# -*- coding: utf-8 -*-
from odoo import models,fields,api
from odoo.exceptions import ValidationError
import datetime


class is_imputation_investissement(models.Model):
    _name='is.imputation.investissement'
    _description="Imputation investissement"
    _order='name'

    name   = fields.Char("Imputation investissement", required=True)
    active = fields.Boolean("Active", default=True, copy=False)


class is_demande_achat_moule(models.Model):
    _name='is.demande.achat.moule'
    _description="Demande d'achat moule"
    _inherit=['mail.thread']
    _order='name desc'

    @api.depends('line_ids')
    def _compute(self):
        uid=self._uid
        for obj in self:
            montant_total = 0
            for line in obj.line_ids:
                montant_total+=line.montant
            obj.montant_total = montant_total


    @api.depends('line_ids')
    def _compute_vsb(self):
        uid=self._uid
        for obj in self:
            vsb=False
            if obj.state!='brouillon' and (uid==obj.chef_service_id.id or uid==obj.direction_id.id or uid==obj.acheteur_id.id):
                vsb=True
            obj.vers_brouillon_vsb=vsb
            if obj.state=='annule' and (uid==obj.createur_id.id or uid==obj.chef_service_id.id or uid==obj.direction_id.id or uid==obj.acheteur_id.id):
                vsb=True
            obj.vers_brouillon_vsb=vsb
            vsb=False
            if obj.state=='brouillon' and uid==obj.createur_id.id:
                vsb=True
            obj.vers_validation_rsp_vsb=vsb
            vsb=False
            if obj.state=='validation_rsp' and uid==obj.chef_service_id.id:
                vsb=True
            obj.vers_validation_direction_vsb=vsb
            vsb=False
            if obj.state=='validation_direction' and uid==obj.direction_id.id:
                vsb=True
            obj.vers_transmis_achat_vsb=vsb
            vsb=False
            if obj.state=='transmis_achat' and uid==obj.acheteur_id.id:
                vsb=True
            obj.vers_solde_vsb=vsb
            vsb=False
            if obj.state=='brouillon' and uid==obj.createur_id.id:
                vsb=True
            if obj.state=='validation_rsp' and uid==obj.chef_service_id.id:
                vsb=True
            if obj.state=='transmis_achat' and uid==obj.acheteur_id.id:
                vsb=True
            if obj.state=='validation_direction' and uid==obj.direction_id.id:
                vsb=True
            obj.vers_annule_vsb=vsb


    @api.depends('line_ids')
    def _compute_num_chantier(self):
        for obj in self:
            for line in obj.line_ids:
                obj.num_chantier=line.num_chantier


    name                 = fields.Char("N°DA-M", tracking=True, readonly=True)
    createur_id          = fields.Many2one('res.users', 'Demandeur', tracking=True, required=True, default=lambda self: self.env.uid,copy=False)
    chef_service_id      = fields.Many2one('res.users', 'Chef de projet', tracking=True, required=True)
    direction_id         = fields.Many2one('res.users', 'Directeur technique', tracking=True, readonly=True, default=lambda self: self._dirigeant_id())
    date_creation        = fields.Date("Date de création", copy=False, tracking=True, required=True, default=lambda *a: fields.datetime.now())
    acheteur_id          = fields.Many2one('res.users', 'Acheteur', tracking=True, required=True)
    fournisseur_id       = fields.Many2one('res.partner', 'Fournisseur', tracking=True, domain=[('is_company','=',True),('is_segment_achat.name','=',u'Fournisseurs de Moules')])
    pricelist_id         = fields.Many2one('product.pricelist', "Liste de prix", tracking=True, related='fournisseur_id.pricelist_purchase_id', readonly=True)
    fournisseur_autre    = fields.Char("Fournisseur autre", tracking=True)
    delai_livraison      = fields.Date("Délai de livraison", tracking=True, required=True)
    lieu_livraison_id    = fields.Many2one('res.partner', 'Lieu de livraison', tracking=True, domain=[('is_company','=',True)], required=True, default=lambda self: self._lieu_livraison_id())
    lieu_autre           = fields.Char("Lieu autre", tracking=True)
    is_incoterm          = fields.Many2one(string="Incoterm  / Conditions de livraison", related='fournisseur_id.is_incoterm', readonly=True)
    is_lieu              = fields.Char("Lieu", related='fournisseur_id.is_lieu', tracking=True, readonly=True)
    num_devis            = fields.Char("N° du devis", tracking=True)
    date_devis           = fields.Date("Date du devis", tracking=True)
    commentaire          = fields.Text("Commentaire", tracking=True)
    state                = fields.Selection([
        ('brouillon'           , 'Brouillon'),
        ('validation_rsp'      , 'Validation chef de projet'),
        ('validation_direction', 'Validation directeur technique'),
        ('transmis_achat'      , 'Transmis achat'),
        ('solde'               , 'Soldé'),
        ('annule'              , 'Annulé'),
    ], "Etat", default="brouillon", tracking=True)
    line_ids                      = fields.One2many('is.demande.achat.moule.line'  , 'da_id', u"Lignes", copy=True)
    montant_total                 = fields.Float("Montant Total", compute='_compute', readonly=True, store=True, tracking=True)
    order_id                      = fields.Many2one('purchase.order', 'Commande générée', readonly=True, copy=False, tracking=True)
    num_chantier                  = fields.Char("N° du chantier", compute='_compute_num_chantier', tracking=True, readonly=True, store=True)
    vers_brouillon_vsb            = fields.Boolean('Champ technique vers_brouillon_vsb', compute='_compute_vsb', readonly=True, store=False)
    vers_validation_rsp_vsb       = fields.Boolean('Champ technique vers_validation_rsp_vsb', compute='_compute_vsb', readonly=True, store=False)
    vers_validation_direction_vsb = fields.Boolean('Champ technique vers_validation_direction_vsb', compute='_compute_vsb', readonly=True, store=False)
    vers_transmis_achat_vsb       = fields.Boolean('Champ technique vers_transmis_achat_vsb', compute='_compute_vsb', readonly=True, store=False)
    vers_solde_vsb                = fields.Boolean('Champ technique vers_solde_vsb', compute='_compute_vsb', readonly=True, store=False)
    vers_annule_vsb               = fields.Boolean('Champ technique vers_annule_vsb', compute='_compute_vsb', readonly=True, store=False)


    def _lieu_livraison_id(self):
        user = self.env['res.users'].browse(self._uid)
        partner_id = user.company_id.partner_id.id
        return partner_id


    def _dirigeant_id(self):
        user    = self.env["res.users"].browse(self._uid)
        company = user.company_id
        return company.is_directeur_technique_id.id


    def fournisseur_id_on_change(self,fournisseur_id):
        res={}
        if fournisseur_id:
            res['value']={}
            partner = self.env['res.partner'].browse(fournisseur_id)
            lieu_livraison_id=partner.is_livre_a_id.id
            if lieu_livraison_id:
                res['value']['lieu_livraison_id']=lieu_livraison_id
        return res


    # def create(self, vals):
    #     data_obj = self.env['ir.model.data']
    #     sequence_ids = data_obj.search([('name','=','is_demande_achat_moule_seq')])
    #     if sequence_ids:
    #         sequence_id = data_obj.browse(sequence_ids[0].id).res_id
    #         vals['name'] = self.env['ir.sequence'].get_id(sequence_id, 'id')
    #     obj = super(is_demande_achat_moule, self).create(vals)
    #     return obj


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('is.demande.achat.moule')
        return super().create(vals_list)



    def vers_brouillon_action(self):
        for obj in self:
            obj.sudo().state="brouillon"


    def vers_validation_rsp_action(self):
        for obj in self:
            subject=u'['+obj.name+u'] Validation chef de projet'
            email_to=obj.chef_service_id.email
            user  = self.env['res.users'].browse(self._uid)
            email_from = user.email
            nom   = user.name
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url=base_url+u'/web#id='+str(obj.id)+u'&view_type=form&model=is.demande.achat.moule'
            body_html=u"""
                <p>Bonjour,</p>
                <p>"""+nom+""" vient de passer la demande d'achat moule <a href='"""+url+"""'>"""+obj.name+"""</a> à l'état 'Validation chef de projet'.</p>
                <p>Merci d'en prendre connaissance.</p>
            """
            self.envoi_mail(email_from,email_to,subject,body_html)
            obj.state="validation_rsp"


    def vers_validation_direction_action(self):
        for obj in self:
            subject=u'['+obj.name+u'] Validation directeur technique'
            email_to=obj.direction_id.email
            user  = self.env['res.users'].browse(self._uid)
            email_from = user.email
            nom   = user.name
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url=base_url+u'/web#id='+str(obj.id)+u'&view_type=form&model=is.demande.achat.moule'
            body_html=u"""
                <p>Bonjour,</p>
                <p>"""+nom+""" vient de passer la demande d'achat moule <a href='"""+url+"""'>"""+obj.name+"""</a> à l'état 'Validation directeur technique'.</p>
                <p>Merci d'en prendre connaissance.</p>
            """
            self.envoi_mail(email_from,email_to,subject,body_html)
            obj.state="validation_direction"


    def vers_transmis_achat_action(self):
        for obj in self:
            subject=u'['+obj.name+u'] Transmis achat'
            email_to=obj.acheteur_id.email
            user  = self.env['res.users'].browse(self._uid)
            email_from = user.email
            nom   = user.name
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url=base_url+u'/web#id='+str(obj.id)+u'&view_type=form&model=is.demande.achat.moule'
            body_html=u"""
                <p>Bonjour,</p>
                <p>"""+nom+""" vient de passer la demande d'achat moule <a href='"""+url+"""'>"""+obj.name+"""</a> à l'état 'Transmis achat'.</p>
                <p>Merci d'en prendre connaissance.</p>
            """
            self.envoi_mail(email_from,email_to,subject,body_html)
            obj.state="transmis_achat"


    def vers_solde_action(self):
        for obj in self:
            order_obj      = self.env['purchase.order']
            order_line_obj = self.env['purchase.order.line']
            partner=obj.fournisseur_id
            if partner.id==False:
                raise ValidationError('Fournisseur obligatoire pour générer la commande !')
            for line in obj.line_ids:
                if line.num_chantier==False:
                    raise ValidationError('N° du chantier obligatoire sur toutes les lignes de la commande !')
                else:
                    if len(line.num_chantier)!=11 and len(line.num_chantier)!=12:
                        raise ValidationError('Le numéro du chantier doit-être sur 11 ou 12 caractères (ex : M0000/123456)')
                    

            if partner.pricelist_purchase_id==False:
                raise ValidationError('Liste de prix non renseignée pour ce fournisseur')
            else:
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
                obj.order_id=order.id
                if order:
                    for line in obj.line_ids:
                        vals={}
                        # res=order_line_obj.onchange_product_id(
                        #     order.pricelist_id.id, 
                        #     line.product_id.id, 
                        #     line.quantite, 
                        #     line.uom_id.id, 
                        #     partner.id, 
                        #     date_order         = False, 
                        #     fiscal_position_id = partner.property_account_position.id, 
                        #     date_planned       = False, 
                        #     name               = False, 
                        #     price_unit         = line.prix, 
                        #     state              = 'draft'
                        # )
                        # vals=res['value']
                        vals['order_id']        = order.id
                        vals['date_planned']    = obj.delai_livraison
                        vals['product_id']      = line.product_id.id
                        vals['product_qty']  = line.quantite
                        vals['price_unit']   = line.prix
                        vals['is_num_chantier'] = line.num_chantier
                        name=[]
                        if line.product_id.id:
                            name.append(line.product_id.is_code+u' - '+line.product_id.name)
                        if line.designation1:
                            name.append(line.designation1)
                        if line.designation2:
                            name.append(line.designation2)
                        vals['name']='\n'.join(name)
                        #if 'taxes_id' in vals:
                        #    vals.update({'taxes_id': [[6, False, vals['taxes_id']]]})
                        order_line=order_line_obj.create(vals)
                    #order.wkf_bid_received() 
                    #res=order.wkf_confirm_order()
                    #order.action_picking_create() 
                    #order.wkf_approve_order()
                    order.button_confirm()
                    obj.sudo().state="solde"


    def vers_annule_action(self):
        for obj in self:
            uid = self._uid
            if obj.createur_id.id==uid or obj.acheteur_id.id==uid or obj.direction_id.id==uid or obj.chef_service_id.id==uid:
                obj.sudo().state="annule"


    def envoi_mail(self, email_from,email_to,subject,body_html):
        for obj in self:
            vals={
                'email_from'    : email_from, 
                'email_to'      : email_to, 
                'email_cc'      : email_from,
                'subject'       : subject,
                'body_html'     : body_html, 
            }
            email=self.env['mail.mail'].sudo().create(vals)
            if email:
                self.env['mail.mail'].send(email)


class is_demande_achat_moule_line(models.Model):
    _name='is.demande.achat.moule.line'
    _description="Lignes demande achat moule"
    _order='da_id,sequence'


    @api.depends('product_id','quantite','prix')
    def _compute(self):
        for obj in self:
            if obj.product_id:
                obj.uom_id=obj.product_id.uom_po_id
            obj.montant=obj.quantite*obj.prix

    da_id         = fields.Many2one('is.demande.achat.moule', "Demande d'achat", required=True, ondelete='cascade', readonly=True)
    sequence      = fields.Integer('Ordre')
    product_id    = fields.Many2one('product.product', 'Article', required=True, domain=[('is_code','=','607000MOUL')], default=lambda self: self._product_id())
    imputation_id = fields.Many2one('is.imputation.investissement', 'Imputation')
    designation1  = fields.Char("Désignation 1")
    designation2  = fields.Char("Désignation 2")
    num_dfn       = fields.Char("N°de DFN")
    uom_id        = fields.Many2one('uom.uom', "Unité d'achat")
    quantite      = fields.Float("Quantité", digits=(14,4), required=True)
    prix          = fields.Float("Prix"    , digits=(14,4))
    montant       = fields.Float("Montant", compute='_compute', readonly=True, store=True)
    num_chantier  = fields.Char("N° du chantier", required=True, help="N° du chantier (M0000/12345)")


    def _product_id(self):
        products = self.env['product.product'].search([('is_code','=','607000MOUL')])
        for product in products:
            return product.id
        return False


    def product_id_on_change(self,parent,product_id,quantite):
        cr=self._cr
        res={}
        fournisseur_id=parent.fournisseur_id
        if fournisseur_id:
            partner = self.env['res.partner'].browse(fournisseur_id)
            pricelist_id=partner.property_product_pricelist_purchase.id
            if product_id and pricelist_id:
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
                if prix>0:
                    res['value']['prix']=prix
        return res


    def _test_num_chantier(self,vals):
        if 'num_chantier' in vals:
            num_chantier=vals.get('num_chantier')
            if len(num_chantier)!=11:
                raise ValidationError('Le numéro du chantier doit-être sur 11 caractères (ex : M0000/12345)')


    def create(self, vals):
        self._test_num_chantier(vals)
        obj = super(is_demande_achat_moule_line, self).create(vals)
        return obj


    def write(self,vals):
        self._test_num_chantier(vals)
        obj = super(is_demande_achat_moule_line, self).write(vals)
        return obj


