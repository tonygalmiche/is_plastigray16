# -*- coding: utf-8 -*-
"""
Migration 0.5 -> 0.6

Corrige le "Pays fiscal" (account_fiscal_country_id) des sociétés, réglé
par erreur sur FO (Îles Féroé) au lieu du pays réel de la société (constat
identique sur pg-odoo16-1, pg-odoo16-3 et pg-odoo16-4 ; pg-odoo16-0 déjà
correct). Ce champ conditionne l'affichage de sections entières de
paramétrage (ex: "Facturation électronique France" dans is_facturation_electronique,
masquée tant que le pays fiscal n'est pas FR) : avec FO, ces sections
restent invisibles sans aucune erreur explicite.

Réaligne account_fiscal_country_id sur le country_id réel de la société
(FR pour la plupart, mais TN pour pg-odoo16-3, dont la société est
tunisienne) plutôt que de forcer FR partout.
"""


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        UPDATE res_company c
        SET account_fiscal_country_id = p.country_id
        FROM res_partner p
        WHERE p.id = c.partner_id
          AND c.account_fiscal_country_id != p.country_id
          AND c.account_fiscal_country_id IN (
              SELECT id FROM res_country WHERE code = 'FO'
          )
        """
    )
