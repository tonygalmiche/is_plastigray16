# -*- coding: utf-8 -*-

from odoo import tools, models, fields


class is_comparatif_gamme_standard_generique(models.Model):
    _name='is.comparatif.gamme.standard.generique'
    _description='is.comparatif.gamme.standard.generique'
    _order='product_id'
    _auto = False

    product_id                 = fields.Many2one('product.template', 'Article')
    bom_id                     = fields.Many2one('mrp.bom', 'Nomenclature')
    standard_routing_id        = fields.Many2one('mrp.routing', 'Gamme standard')
    standard_sequence          = fields.Integer('Sequence standard')
    standard_name              = fields.Char('Nom standard')
    standard_workcenter_id     = fields.Many2one('mrp.workcenter', 'Poste de charge standard')
    standard_nb_secondes       = fields.Float('Nb secondes standard')

    generique_routing_id        = fields.Many2one('mrp.routing', 'Gamme générique')
    generique_sequence          = fields.Integer('Sequence générique')
    generique_name              = fields.Char('Nom générique')
    generique_workcenter_id     = fields.Many2one('mrp.workcenter', 'Poste de charge générique')
    generique_nb_secondes       = fields.Float('Nb secondes générique')
    delta_nb_secondes           = fields.Float('Delta Nb secondes')


    def init(self):
        cr = self._cr
        tools.drop_view_if_exists(cr, 'is_comparatif_gamme_standard_generique')
        cr.execute("""
            CREATE OR REPLACE view is_comparatif_gamme_standard_generique AS (
                SELECT 
                    mb.id,
                    mb.product_tmpl_id  as product_id,
                    mb.id               as bom_id,
                    mr1.id              as standard_routing_id,
                    mrw1.sequence       as standard_sequence,
                    mrw1.name           as standard_name,
                    mrw1.workcenter_id  as standard_workcenter_id,
                    mrw1.is_nb_secondes as standard_nb_secondes,

                    mr2.id              as generique_routing_id,
                    mrw2.sequence       as generique_sequence,
                    mrw2.name           as generique_name,
                    mrw2.workcenter_id  as generique_workcenter_id,
                    mrw2.is_nb_secondes as generique_nb_secondes,

                    (mrw1.is_nb_secondes-mrw2.is_nb_secondes) as delta_nb_secondes


                FROM mrp_bom mb inner join mrp_routing mr1             on mb.routing_id=mr1.id
                                inner join mrp_routing_workcenter mrw1 on mr1.id=mrw1.routing_id

                                inner join mrp_routing mr2             on mb.is_gamme_generique_id=mr2.id
                                inner join mrp_routing_workcenter mrw2 on mr2.id=mrw2.routing_id

                WHERE mb.id>0 and mrw1.sequence=mrw2.sequence
            )
        """)

#routing_id
#sequence name is_nb_secondes
#                                inner join mrp_routing mr2             on mb.is_gamme_generique_id=mr2.id
#                                inner join mrp_routing_workcenter mrw2 on mr2.id=mrw2.routing_id
#                    mr2.id             as routing_generique_id,
#                    mrw2.workcenter_id as workcenter_generique_id
