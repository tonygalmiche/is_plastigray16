# -*- coding: utf-8 -*-
from odoo import models,fields,api
from odoo.exceptions import ValidationError
import datetime


class res_partner(models.Model):
    _inherit = 'res.partner'

    is_achat_ville = fields.Boolean(string=u"Achats en ville", help=u'Fournisseur autorisé pour les achats en ville', default=False)


class is_bon_achat_ville(models.Model):
    _name='is.bon.achat.ville'
    _description="is_bon_achat_ville"
    _inherit=['mail.thread']
    _order='name desc'


    @api.depends('line_ids')
    def _compute(self):
        uid=self._uid
        for obj in self:
            montant_total = 0
            for line in obj.line_ids:
                montant_total+=line.montant
            nb_lignes=len(obj.line_ids)
            obj.nb_lignes     = nb_lignes
            obj.montant_total = montant_total


    @api.depends('line_ids')
    def _compute_vsb(self):
        uid=self._uid
        for obj in self:
            vsb=False
            if obj.state!='brouillon' and (uid==obj.responsable_id.id or uid==1):
                vsb=True
            obj.vers_brouillon_vsb=vsb
            vsb=False
            if obj.state=='brouillon' and (uid==obj.createur_id.id or uid==obj.responsable_id.id or uid==1):
                vsb=True
            obj.vers_en_cours_vsb=vsb
            vsb=False
            if obj.state=='en_cours' and (uid==obj.responsable_id.id or uid==1):
                vsb=True
            obj.vers_valide_vsb=vsb
            vsb=False
            if obj.state=='en_cours' and (uid==obj.responsable_id.id or uid==1):
                vsb=True
            obj.vers_annule_vsb=vsb


    name                 = fields.Char("N° de bon d'achat en ville", readonly=True)
    createur_id          = fields.Many2one('res.users', 'Demandeur', required=True, default=lambda self: self.env.uid)
    date_demande         = fields.Date("Date de la demande", required=True        , default=lambda *a: fields.datetime.now())
    responsable_id       = fields.Many2one('res.users', 'Responsable', required=True, domain=lambda self: [( "groups_id", "=", self.env.ref("is_plastigray16.is_bon_achat_ville_grp").id)])
    fournisseur_id       = fields.Many2one('res.partner', 'Fournisseur', domain=[('is_achat_ville','=',True)], required=True)
    #pricelist_id         = fields.Many2one('product.pricelist', "Liste de prix", related='fournisseur_id.property_product_pricelist_purchase', readonly=True)
    objet                = fields.Char("Objet de la demande", required=True)
    state                = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('en_cours' , 'En cours de validation'),
        ('valide'   , 'Validé'),
        ('annule'   , 'Annulé'),
    ], "Etat", default='brouillon')
    line_ids           = fields.One2many('is.bon.achat.ville.line', 'bon_id', u"Lignes", copy=True)
    montant_total      = fields.Float("Montant Total"     , compute='_compute', readonly=True, store=True)
    nb_lignes          = fields.Integer("Nombre de lignes", compute='_compute', readonly=True, store=True)
    vers_brouillon_vsb = fields.Boolean('Champ technique vers_brouillon_vsb', compute='_compute_vsb', readonly=True, store=False)
    vers_en_cours_vsb  = fields.Boolean('Champ technique vers_en_cours_vsb' , compute='_compute_vsb', readonly=True, store=False)
    vers_valide_vsb    = fields.Boolean('Champ technique vers_valide_vsb'   , compute='_compute_vsb', readonly=True, store=False)
    vers_annule_vsb    = fields.Boolean('Champ technique vers_annule_vsb'   , compute='_compute_vsb', readonly=True, store=False)


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('is.bon.achat.ville')
        return super().create(vals_list)


    def vers_brouillon_action(self):
        for obj in self:
            if obj.createur_id.id==self._uid or obj.responsable_id.id==self._uid or self._uid==1:
                obj.sudo().state="brouillon"


    def vers_en_cours_action(self):
        for obj in self:
            subject=u"["+obj.name+u"][En cours de validation] Bon d'achat en ville"
            email_to=obj.responsable_id.email
            user  = self.env['res.users'].browse(self._uid)
            email_from = user.email
            email_cc   = email_from
            nom   = user.name
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url=base_url+u'/web#id='+str(obj.id)+u'&view_type=form&model=is.bon.achat.ville'
            body_html=u"""
                <p>Bonjour,</p>
                <p>"""+nom+""" vient de passer le bon d'achat en ville <a href='"""+url+"""'>"""+obj.name+"""</a> à l'état 'En cours de validation'.</p>
                <p>Merci d'en prendre connaissance.</p>
            """
            self.envoi_mail(email_from,email_to,email_cc,subject,body_html)
            obj.state="en_cours"


    def vers_valide_action(self):
        for obj in self:
            obj.state="valide"
            subject=u"["+obj.name+u"][Validé] Bon d'achat en ville"
            email_to=obj.createur_id.email
            user  = self.env['res.users'].browse(self._uid)
            email_from = user.email
            nom   = user.name
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url=base_url+u'/web#id='+str(obj.id)+u'&view_type=form&model=is.bon.achat.ville'
            body_html=u"""
                <p>Bonjour,</p>
                <p>"""+nom+""" vient de passer le bon d'achat en ville <a href='"""+url+"""'>"""+obj.name+"""</a> à l'état 'Validé'.</p>
                <p>Merci d'en prendre connaissance.</p>
            """
            self.envoi_mail(email_from,email_to,'',subject,body_html)


    def vers_annule_action(self):
        for obj in self:
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
            email=self.env['mail.mail'].create(vals)
            if email:
                self.env['mail.mail'].send(email)


class is_bon_achat_ville_line(models.Model):
    _name='is.bon.achat.ville.line'
    _description="is_bon_achat_ville_line"
    _order='bon_id,sequence'


    @api.depends('product_id','quantite','prix')
    def _compute(self):
        for obj in self:
            if obj.product_id:
                obj.uom_id=obj.product_id.uom_po_id
            obj.montant=obj.quantite*obj.prix

    bon_id      = fields.Many2one('is.bon.achat.ville', "Bon d'achat en ville", required=True, ondelete='cascade', readonly=True)
    sequence    = fields.Integer('Ordre')
    product_id  = fields.Many2one('product.product', 'Article', domain=[('segment_id.name','=','ARTICLES COMPTABLES FRAIS GENERAUX')], required=True)
    designation = fields.Char(u'Désignation', required=True)
    uom_id      = fields.Many2one('uom.uom', "Unité d'achat", compute='_compute', readonly=True, store=True)
    quantite    = fields.Float("Quantité", digits=(14,4), required=True)
    prix        = fields.Float("Prix"    , digits=(14,4))
    montant     = fields.Float("Montant", compute='_compute', readonly=True, store=True)
    chantier    = fields.Char(u'Chantier', help=u"Chantier sur 5 chiffres")



