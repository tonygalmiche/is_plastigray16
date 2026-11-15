# -*- coding: utf-8 -*-
from odoo import api, fields, models # type: ignore
from odoo.exceptions import ValidationError # type: ignore


class SaleOrderLineBasculerWizard(models.TransientModel):
    _name = 'sale.order.line.basculer.wizard'
    _description = "Assistant de basculement des lignes d'une commande ouverte sur un autre article (changement d'indice)"

    line_ids       = fields.Many2many('sale.order.line', string="Lignes à basculer", readonly=True)
    nb_lignes      = fields.Integer("Nombre de lignes", compute='_compute_nb_lignes')
    order_src_id   = fields.Many2one('sale.order', "Commande d'origine", readonly=True)
    partner_id     = fields.Many2one('res.partner', "Client", related='order_src_id.partner_id')
    product_src_id = fields.Many2one('product.product', "Article d'origine", readonly=True)
    segment_id     = fields.Many2one('is.product.segment', "Segment", related='product_src_id.segment_id')
    product_id     = fields.Many2one('product.product', "Nouvel article", required=True,
        domain="[('segment_id','=',segment_id),('id','!=',product_src_id)]",
        help="Articles du même segment que l'article d'origine")
    order_id       = fields.Many2one('sale.order', "Nouvelle commande ouverte", compute='_compute_order_id',
        help="Commande ouverte du nouvel article pour le même client (à créer avant par l'ADV)")


    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('active_model')=='sale.order.line':
            lines = self.env['sale.order.line'].browse(self.env.context.get('active_ids') or [])
            self._controle_lignes(lines)
            res['line_ids']       = [(6,0,lines.ids)]
            res['order_src_id']   = lines[0].order_id.id
            res['product_src_id'] = lines[0].product_id.id
        return res


    @api.depends('line_ids')
    def _compute_nb_lignes(self):
        for obj in self:
            obj.nb_lignes = len(obj.line_ids)


    @api.depends('product_id','order_src_id')
    def _compute_order_id(self):
        for obj in self:
            obj.order_id = obj._get_commande_ouverte()


    def _get_commande_ouverte(self):
        "Commande ouverte (devis) du nouvel article pour le même client"
        if not self.product_id or not self.order_src_id:
            return self.env['sale.order']
        return self.env['sale.order'].search([
            ('partner_id'            , '=', self.order_src_id.partner_id.id),
            ('is_article_commande_id', '=', self.product_id.id),
            ('is_type_commande'      , '=', 'ouverte'),
            ('state'                 , '=', 'draft'),
        ], limit=1)


    def _controle_lignes(self, lines):
        "Lignes à l'état devis d'une même commande ouverte, toutes du même article"
        if not lines:
            raise ValidationError("Aucune ligne sélectionnée")
        if len(lines.mapped('order_id'))>1:
            raise ValidationError("Les lignes sélectionnées doivent toutes être de la même commande")
        order = lines[0].order_id
        if order.is_type_commande!='ouverte':
            raise ValidationError("Seules les lignes des commandes ouvertes peuvent être basculées (commande %s)"%order.name)
        if any(l.state!='draft' for l in lines):
            raise ValidationError("Seules les lignes à l'état Devis peuvent être basculées")
        if len(lines.mapped('product_id'))>1:
            raise ValidationError("Les lignes sélectionnées doivent toutes être du même article")


    def action_basculer(self):
        self.ensure_one()
        self._controle_lignes(self.line_ids)
        if self.product_id==self.product_src_id:
            raise ValidationError("Le nouvel article doit être différent de l'article d'origine")
        order = self._get_commande_ouverte()
        if not order:
            raise ValidationError("Il n'existe pas de commande ouverte (devis) pour l'article %s et le client %s.\nElle doit d'abord être créée par l'ADV."%(
                self.product_id.is_code, self.order_src_id.partner_id.display_name))
        order_src = self.order_src_id
        lines     = self.line_ids.sorted('is_date_livraison')
        # Tarif obligatoire pour le nouvel article (même contrôle qu'à la création d'une commande ouverte)
        tarifs = {}
        for line in lines:
            price, justification = order.pricelist_id.price_get(self.product_id, line.product_uom_qty, line.is_date_livraison)
            if price==0 and not justification:
                raise ValidationError("Il n'existe pas de tarif (liste de prix %s) pour l'article %s / qt=%s / date=%s.\nAucune ligne n'a été basculée."%(
                    order.pricelist_id.display_name, self.product_id.is_code, line.product_uom_qty, line.is_date_livraison and line.is_date_livraison.strftime('%d/%m/%Y')))
            tarifs[line.id] = (price, justification)
        # Déplacement sur la nouvelle commande : article remplacé, quantités et dates gardées,
        # prix recalculé avec la liste de prix de la nouvelle commande.
        # Justification du tarif seulement si elle existe, sinon celle de la ligne est gardée
        # (champ « Justif. » utilisé par certains clients pour la destination, ex : EXOTEC)
        for line in lines:
            price, justification = tarifs[line.id]
            line.write({
                'order_id'           : order.id,
                'product_id'         : self.product_id.id,
                'product_uom_qty'    : line.product_uom_qty,   # Gardée (champs recalculés au changement d'article)
                'is_date_livraison'  : line.is_date_livraison,
                'is_client_order_ref': order.client_order_ref,
                'price_unit'         : price,
                'is_justification'   : justification or line.is_justification,
            })
        order._verif_article_livrable(order)
        details = ", ".join("%s (%s)"%(fields.Date.to_string(l.is_date_livraison) or '', l.product_uom_qty) for l in lines)
        order_src.message_post(body="%s ligne(s) de %s basculée(s) sur %s (%s) : %s"%(
            len(lines), self.product_src_id.is_code, order.name, self.product_id.is_code, details))
        order.message_post(body="%s ligne(s) reçue(s) de %s (%s) : %s"%(
            len(lines), order_src.name, self.product_src_id.is_code, details))
        return {
            'name'     : order.name,
            'view_mode': 'form',
            'res_model': 'sale.order',
            'res_id'   : order.id,
            'type'     : 'ir.actions.act_window',
        }
