# -*- coding: utf-8 -*-
from email.policy import default
from odoo import models,fields,api


class is_bl_manuel(models.Model):
    _name='is.bl.manuel'
    _description="BL manuel"
    _order='name desc'


    @api.depends('emetteur_id')
    def _compute(self):
        for obj in self:
            initiales=''
            if obj.emetteur_id:
                initiales=obj.emetteur_id.login.upper()
            obj.initiales=initiales


    name                 = fields.Char("N° de BL", readonly=True)
    emetteur_id          = fields.Many2one('res.users', 'Émetteur', required=True, default=lambda self: self.env.uid)
    initiales            = fields.Char("Initiales émetteur", compute='_compute', readonly=True, store=True)
    date_bl              = fields.Date("Date", required=True, default=lambda *a: fields.datetime.now())
    destinataire_id      = fields.Many2one('res.partner', 'Destinataire', domain=[('is_company','=',True)])
    raison_sociale       = fields.Char("Raison Sociale", required=True)
    adresse1             = fields.Char("Ligne adresse 1")
    adresse2             = fields.Char("Ligne adresse 2")
    code_postal          = fields.Char("Code postal")
    ville                = fields.Char("Ville")
    pays_id              = fields.Many2one('res.country', 'Pays')
    contact              = fields.Char("Contact")
    incoterm_id          = fields.Many2one('account.incoterms', 'Incoterm')
    motif_expedition     = fields.Char("Motif Expédition")
    transporteur_id      = fields.Many2one('res.partner', 'Transporteur', domain=[('is_company','=',True),('supplier','=',True)])
    demande_transport_id = fields.Many2one('is.demande.transport', 'Demande de transport', readonly=True)
    colisage             = fields.Char("Colisage (dimensions)")
    state                = fields.Selection([('brouillon', 'Brouillon'),('termine', 'Terminé')], "Etat", default='brouillon')
    line_ids             = fields.One2many('is.bl.manuel.line'  , 'bl_id', u"Lignes")


    def creation_facture_proforma_action(self):
        for obj in self:
            vals={
                'adresse_liv_id': obj.destinataire_id.id,
                'bl_manuel_id'  : obj.id,
                'packaging'     : obj.colisage,
                'informations'  : obj.motif_expedition,
            }
            proforma=self.env['is.facture.proforma'].create(vals)
            poids_net = poids_brut = 0
            for line in obj.line_ids:
                poids_net  += line.poids_net
                poids_brut += line.poids_brut
                vals={
                    'proforma_id': proforma.id,
                    'sequence': line.sequence,
                    'product_id': line.product_id.id,
                    'designation': line.description,
                    'uom_id': line.uom_id.id,
                    'quantite': line.qt_livree,
                }
                res=self.env['is.facture.proforma.line'].create(vals)
                res._onchange_product_id()
            proforma.poids_net  = poids_net
            proforma.poids_brut = poids_brut
            proforma._compute()
            return {
                'name': "Facture proforma",
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'is.facture.proforma',
                'type': 'ir.actions.act_window',
                'res_id': proforma.id,
                'domain': '[]',
            }


    def destinataire_id_change(self, destinataire_id):
        values = {}
        if destinataire_id:
            partner = self.env['res.partner'].browse(destinataire_id)
            values['raison_sociale'] = partner.name
            values['adresse1']       = partner.street
            values['adresse2']       = partner.street2
            values['code_postal']    = partner.zip
            values['ville']          = partner.city
            values['pays_id']        = partner.country_id.id
        return {'value': values}


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('is.bl.manuel')
        return super().create(vals_list)


    def vers_brouillon_action(self):
        for obj in self:
            obj.state="brouillon"


    def vers_termine_action(self):
        for obj in self:
            obj.state="termine"


    def creation_demande_transport_action(self):
        for obj in self:
            if obj.demande_transport_id.id==False:
                poids_net=0
                poids_brut=0
                for line in obj.line_ids:
                    poids_net=poids_net+line.poids_net
                    poids_brut=poids_brut+line.poids_brut
                vals={
                    'type_demande'       : 'transport',
                    'demandeur_id'       : obj.emetteur_id.id,
                    'date_demande'       : obj.date_bl,
                    'dest_raison_sociale': obj.raison_sociale,
                    'dest_adresse1'      : obj.adresse1,
                    'dest_adresse2'      : obj.adresse2,
                    'dest_code_postal'   : obj.code_postal,
                    'dest_ville'         : obj.ville,
                    'dest_pays_id'       : obj.pays_id.id,
                    'contact'            : obj.contact,
                    'poids_net'          : poids_net,
                    'poids_brut'         : poids_brut,
                    'colisage'           : obj.colisage,
                    'bl_id'              : obj.id,
                }
                new_id=self.env['is.demande.transport'].create(vals)
                obj.demande_transport_id=new_id.id

                res= {
                    'name': 'Demande de transport',
                    'view_mode': 'form',
                    'view_type': 'form',
                    'res_model': 'is.demande.transport',
                    'res_id': new_id.id,
                    'type': 'ir.actions.act_window',
                }
                return res


class is_bl_manuel_line(models.Model):
    _name='is.bl.manuel.line'
    _description="Lignes BL manuel"
    _order='bl_id,sequence'

    bl_id                  = fields.Many2one('is.bl.manuel', 'BL manuel', required=True, ondelete='cascade', readonly=True)
    sequence               = fields.Integer('Ordre')
    num_commande           = fields.Char("N°commande")
    product_id             = fields.Many2one('product.product', 'Article',
                                domain=[('is_category_id.name','<','70')])
    description            = fields.Char("Description")
    ref_client             = fields.Char("Référence client")
    origine_id             = fields.Many2one('res.country', 'Origine')
    nomenclature_douaniere = fields.Char("Nomenclature douanière")
    qt_livree              = fields.Float("Quantité livrée")
    uom_id                 = fields.Many2one('uom.uom', 'Unité')
    qt_par_colis           = fields.Integer("Qt/Colis")
    nb_colis               = fields.Float("Nb Colis")
    poids_net              = fields.Float("Poids net")
    poids_brut             = fields.Float("Poids brut")


    def product_id_change(self, product_id):
        values = {}
        if product_id:
            product = self.env['product.product'].browse(product_id)
            values['description']            = product.name
            values['ref_client']             = product.is_ref_client
            values['origine_id']             = product.is_origine_produit_id.id
            values['nomenclature_douaniere'] = product.is_nomenclature_douaniere
            values['qt_par_colis']           = product.is_uc_qt
            values['uom_id']                 = product.uom_id.id
        return {'value': values}


    def qt_change(self, product_id,qt_livree,qt_par_colis):
        values = {}
        if product_id:
            product = self.env['product.product'].browse(product_id)
            values['poids_net']  = product.weight_net*qt_livree
            values['poids_brut'] = product.weight*qt_livree
        nb_colis=0
        if qt_par_colis>0:
            nb_colis=qt_livree/qt_par_colis
        values['nb_colis'] = nb_colis
        return {'value': values}






