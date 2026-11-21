# -*- coding: utf-8 -*-
"""
Migration 16.0.0.11 -> 16.0.0.12 (demande 2172)

Initialisation du champ decoupage_bl des listes à servir existantes avec le découpage
actuel du client (champ renseigné à la création des nouvelles listes à servir).
"""


def migrate(cr, version):
    if not version:
        return

    cr.execute(
        """
        UPDATE is_liste_servir ls
        SET decoupage_bl = coalesce(p.is_decoupage_bl, 'client_a_livrer')
        FROM res_partner p
        WHERE p.id = ls.partner_id
          AND ls.decoupage_bl IS NULL
        """
    )
