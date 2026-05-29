# -*- coding: utf-8 -*-
from odoo import models, fields, api
import datetime
import pytz
import logging
_logger = logging.getLogger(__name__)


class is_heures_theoriques(models.Model):
    _name        = 'is.heures.theoriques'
    _description = "Heures Théoriques M.O."
    _order       = 'user_id'
    _rec_name    = "id"


    user_id         = fields.Many2one('res.users', 'Utilisateur', required=True,
                                      default=lambda self: self.env.uid, index=True)
    code_pg         = fields.Char('Code PG (début)')
    moule           = fields.Char('Moule')
    of_name         = fields.Char('OF')
    picking_type_id = fields.Many2one('stock.picking.type', 'Type Mouvement',
                                      domain=[('active', '=', True)])
    type_tps        = fields.Selection([('user', 'M.O.'), ('material', 'Machine')],
                                       'Type Temps', required=True, default='user')
    workcenter_id   = fields.Many2one('mrp.workcenter', 'Poste de travail')
    date_debut      = fields.Date('Date Début', required=True)
    date_fin        = fields.Date('Date Fin', required=True)
    line_ids        = fields.One2many('is.heures.theoriques.line',
                                      'heures_theoriques_id', 'Lignes')
    nb_lignes       = fields.Integer('Nb lignes', compute='_compute_nb_lignes')

    _sql_constraints = [
        ('user_uniq', 'unique(user_id)', "Une seule fiche par utilisateur !"),
    ]

    @api.onchange('type_tps')
    def _onchange_type_tps(self):
        self.workcenter_id = False

    @api.depends('line_ids')
    def _compute_nb_lignes(self):
        for obj in self:
            obj.nb_lignes = len(obj.line_ids)

    @api.model
    def action_open_or_create(self):
        rec = self.search([('user_id', '=', self.env.uid)], limit=1)
        if not rec:
            today = fields.Date.today()
            fabrication = self.env['stock.picking.type'].search(
                [('name', 'ilike', 'Fabrication'), ('active', '=', True)], limit=1
            )
            rec = self.create({
                'user_id':          self.env.uid,
                'type_tps':         'M.O.',
                'date_debut':       today,
                'date_fin':         today,
                'picking_type_id':  fabrication.id if fabrication else False,
                'type_tps':         'user',
            })
        return {
            'type':      'ir.actions.act_window',
            'name':      'Heures Théoriques M.O.',
            'res_model': 'is.heures.theoriques',
            'res_id':    rec.id,
            'view_mode': 'form',
            'views':     [(False, 'form')],
            'target':    'current',
        }

    def action_afficher_lignes(self):
        for obj in self:
            return {
                'name':      'Heures Théoriques',
                'type':      'ir.actions.act_window',
                'res_model': 'is.heures.theoriques.line',
                'view_mode': 'tree,pivot,graph',
                'domain':    [('heures_theoriques_id', '=', obj.id)],
                'context':   {'default_heures_theoriques_id': obj.id},
                'limit':     200,
            }

    def action_calculer(self):
        for obj in self:
            obj.line_ids.unlink()

            cr = self._cr

            # ── Conversion des dates Paris → UTC ──────────────────────────────
            paris_tz = pytz.timezone('Europe/Paris')

            date_deb = obj.date_debut
            date_fin = obj.date_fin

            if date_deb != date_fin:
                # Si les dates sont différentes, la période va de 5H à 5H
                dt_deb_local = datetime.datetime.combine(date_deb, datetime.time(5, 0, 0))
                dt_fin_local = datetime.datetime.combine(date_fin, datetime.time(5, 0, 0))
            else:
                # Si même jour : de 0H à 24H
                dt_deb_local = datetime.datetime.combine(date_deb, datetime.time(0, 0, 0))
                dt_fin_local = datetime.datetime.combine(date_fin, datetime.time(23, 59, 59))

            dt_deb_utc = paris_tz.localize(dt_deb_local).astimezone(pytz.utc)
            dt_fin_utc = paris_tz.localize(dt_fin_local).astimezone(pytz.utc)

            date_deb_str = dt_deb_utc.strftime('%Y-%m-%d %H:%M:%S')
            date_fin_str = dt_fin_utc.strftime('%Y-%m-%d %H:%M:%S')

            # ── Type de ressource ─────────────────────────────────────────────
            resource_type = obj.type_tps

            # ── Requête principale ────────────────────────────────────────────
            params = [date_deb_str, date_fin_str]

            SQL = """
                SELECT
                    pt.is_code,
                    pt.name->>'fr_FR'  AS name,
                    sm.mold,
                    sm.product_id,
                    sm.qty,
                    pt.id              AS product_tmpl_id,
                    (
                        SELECT cout_act_total
                        FROM   is_cout ic
                        WHERE  ic.name = pp.id
                        LIMIT  1
                    ) AS cout
                FROM (
                    SELECT
                        move.product_id,
                        move.mold,
                        sum(move.qty) AS qty
                    FROM  pg_stock_move        move
                    JOIN  stock_picking_type   spt  ON move.picking_type_id = spt.id
                    WHERE move.date >= %s AND move.date <= %s
            """

            if obj.of_name:
                SQL += " AND move.name = %s"
                params.append(obj.of_name)

            if obj.picking_type_id:
                SQL += " AND move.picking_type_id = %s"
                params.append(obj.picking_type_id.id)
                # Conditions supplémentaires si type "Fabrication"
                if 'Fabrication' in (obj.picking_type_id.name or ''):
                    SQL += """
                        AND move.production_id IS NOT NULL
                        AND move.location_dest_id <> 4
                        AND move.origin IS NULL
                    """

            SQL += """
                    GROUP BY move.product_id, move.mold
                ) sm
                JOIN product_product  pp ON sm.product_id      = pp.id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                WHERE 1=1
            """

            if obj.code_pg:
                SQL += " AND pt.is_code LIKE %s"
                params.append(obj.code_pg + '%')

            SQL += " ORDER BY pt.is_code, sm.mold"

            cr.execute(SQL, params)
            rows = cr.dictfetchall()

            # ── Pour chaque article : recherche section + temps gamme générique
            vals_list = []
            for row in rows:
                is_code         = row['is_code']        or ''
                name            = row['name']           or ''
                mold            = row['mold']           or ''
                qty             = row['qty']            or 0.0
                product_tmpl_id = row['product_tmpl_id']
                cout            = row['cout']           or 0.0

                SQL2 = """
                    SELECT mrw.workcenter_id AS section, mrw.is_nb_secondes AS tps_s
                    FROM  mrp_bom                  mb
                    JOIN  mrp_routing              mr  ON mb.is_gamme_generique_id = mr.id
                    JOIN  mrp_routing_workcenter   mrw ON mr.id = mrw.routing_id
                    WHERE mb.product_tmpl_id = %s
                      AND mrw.workcenter_id IN (
                            SELECT id FROM mrp_workcenter WHERE resource_type = %s
                          )
                """
                params2 = [product_tmpl_id, resource_type]
                if obj.workcenter_id:
                    SQL2 += " AND mrw.workcenter_id = %s"
                    params2.append(obj.workcenter_id.id)
                cr.execute(SQL2, params2)
                rows2 = cr.dictfetchall()

                for row2 in rows2:
                    workcenter_id = row2['section']
                    tps_s         = row2['tps_s']   or 0.0
                    tps_tot_h     = tps_s * qty / 3600.0 if tps_s else 0.0
                    vals_list.append({
                        'heures_theoriques_id': obj.id,
                        'code_pg':       is_code,
                        'name':          name,
                        'mold':          mold,
                        'workcenter_id': workcenter_id,
                        'tps_s':      tps_s,
                        'qt_fab':     qty,
                        'tps_tot_h':  tps_tot_h,
                        'cout_unit':  cout,
                        'cout_total': cout * qty,
                    })

            if vals_list:
                self.env['is.heures.theoriques.line'].create(vals_list)

        return self.action_afficher_lignes()


class is_heures_theoriques_line(models.Model):
    _name        = 'is.heures.theoriques.line'
    _description = "Heures Théoriques M.O. - Lignes"
    _order       = 'code_pg, mold, workcenter_id'

    heures_theoriques_id = fields.Many2one('is.heures.theoriques', 'Entête',
                                            required=True, ondelete='cascade',
                                            index=True)
    code_pg    = fields.Char('CodePG')
    name       = fields.Char('Désignation')
    mold       = fields.Char('Moule')
    workcenter_id = fields.Many2one('mrp.workcenter', 'Poste de charge')
    tps_s      = fields.Float('Tps (s)',       digits=(14, 2))
    qt_fab     = fields.Float('Qt Fab',        digits=(14, 0))
    tps_tot_h  = fields.Float('Tps Tot (H)',   digits=(14, 2))
    cout_unit  = fields.Float('Coût Unit.',    digits=(14, 4))
    cout_total = fields.Float('Coût Total',    digits=(14, 0))
