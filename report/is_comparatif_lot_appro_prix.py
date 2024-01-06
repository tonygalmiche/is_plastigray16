# -*- coding: utf-8 -*-
from odoo import tools,models,fields

class is_comparatif_lot_appro_prix(models.Model):
    _name='is.comparatif.lot.appro.prix'
    _description='is_comparatif_lot_appro_prix'
    _order='product_id'
    _auto = False

    product_id             = fields.Many2one('product.template', 'Article')
    is_category_id         = fields.Many2one('is.category', 'Catégorie')
    is_gestionnaire_id     = fields.Many2one('is.gestionnaire', 'Gestionnaire')
    partner_id             = fields.Many2one('res.partner', 'Fournisseur')
    pricelist_id           = fields.Many2one('product.pricelist', 'Liste de prix')
    uom_id                 = fields.Many2one('uom.uom', 'US')
    uom_po_id              = fields.Many2one('uom.uom', 'UA')
    coef                   = fields.Float('US/UA')
    lot_mini_product       = fields.Float("Lot d'appro.")
    min_quantity_pricelist = fields.Float("Mini liste de prix")
    prix_lot               = fields.Float("Prix d'achat pour le lot")


    def init(self):
        cr = self._cr

        # TODO Cette fonction n'est plus necessaire car la liste de prix est dans un champ et non plus dans une property
        #    CREATE OR REPLACE FUNCTION get_product_pricelist_purchase(partner_id integer) RETURNS integer AS $$
        #     BEGIN
        #         RETURN (
        #             select substring(value_reference, 19)::int pricelist_id
        #             from ir_property ip 
        #             where ip.name='property_product_pricelist_purchase' and res_id=concat('res.partner,',partner_id)
        #             limit 1
        #         );
        #     END;
        #     $$ LANGUAGE plpgsql;

        tools.drop_view_if_exists(cr, 'is_comparatif_lot_appro_prix')
        cr.execute("""
             CREATE OR REPLACE view is_comparatif_lot_appro_prix AS (
                select
                    pt.id         id,
                    pt.id         product_id,
                    ic.id         is_category_id,
                    pt.is_gestionnaire_id,
                    -- pt_tmp2.partner_id,
                    -- get_product_pricelist_purchase(pt_tmp2.pricelist_purchase_id) pricelist_id,
                    pt.uom_id,
                    pt.uom_po_id,
                    is_unit_coef(pt.uom_id, pt.uom_po_id) coef,
                    pt.lot_mini lot_mini_product,
                    pt.is_fournisseur_id partner_id,
                    rp.pricelist_purchase_id pricelist_id,
                    is_mini_liste_prix(pp.id, rp.pricelist_purchase_id)*is_unit_coef(pt.uom_id, pt.uom_po_id) min_quantity_pricelist,
                    is_prix_achat(rp.pricelist_purchase_id,pp.id, pt.lot_mini/is_unit_coef(pt.uom_id, pt.uom_po_id),CURRENT_DATE) prix_lot
                from product_template pt join product_product                pp on pp.product_tmpl_id=pt.id
                                        join res_partner                    rp on pt.is_fournisseur_id=rp.id
                                        left outer join is_category         ic on pt.is_category_id=ic.id
                                        left outer join is_gestionnaire     ig on pt.is_gestionnaire_id=ig.id
                                        left outer join is_product_famille ipf on pt.family_id=ipf.id
                                        left outer join is_product_segment ips on pt.segment_id=ips.id
                where 
                    pt.purchase_ok='t' and 
                    ic.name::int<70 and 
                    pt.active='t' and
                    is_prix_achat(rp.pricelist_purchase_id,pp.id, pt.lot_mini/is_unit_coef(pt.uom_id, pt.uom_po_id),CURRENT_DATE) is null
            )
        """)


#                    round(is_mini_liste_prix(pp.id, get_product_pricelist_purchase(pt_tmp2.partner_id))*is_unit_coef(pt.uom_id, pt.uom_po_id))<>pt.lot_mini
#                    is_mini_liste_prix(pp.id, get_product_pricelist_purchase(pt_tmp2.partner_id)) is not null and






