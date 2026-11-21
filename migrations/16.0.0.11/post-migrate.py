# -*- coding: utf-8 -*-
"""
Migration 16.0.0.10 -> 16.0.0.11 (demande 2172 : 1 liste à servir = 1 BL)

Initialisation du nouveau champ client is_decoupage_bl à partir des deux anciens
champs is_caracteristique_liste_a_servir et is_caracteristique_bl, sans changer
le résultat actuel.

« 1 commande Odoo = 1 BL » n'avait aucun effet (un seul BL pour toutes les
commandes) : il n'est pas repris (1 BL par client à livrer, ou 1 BL par point de
déchargement s'il était associé au point de chargement).

En SQL et non par l'ORM : un write() sur res.partner dans odoo0 déclencherait la
synchronisation des clients vers les autres bases (copy_other_database).
"""


def migrate(cr, version):
    if not version:
        return

    cr.execute(
        """
        UPDATE res_partner
        SET is_decoupage_bl = CASE
            WHEN is_caracteristique_liste_a_servir = 'point_de_chargement_et_status_aqp' THEN 'point_dechargement_statut_aqp'
            WHEN is_caracteristique_liste_a_servir = 'point_de_chargement' AND is_caracteristique_bl = 'cde_client' THEN 'point_dechargement_cde_client'
            WHEN is_caracteristique_liste_a_servir = 'point_de_chargement' THEN 'point_dechargement'
            WHEN is_caracteristique_liste_a_servir = 'status_aqp' AND is_caracteristique_bl = 'cde_client' THEN 'statut_aqp_cde_client'
            WHEN is_caracteristique_liste_a_servir = 'status_aqp' THEN 'statut_aqp'
            WHEN is_caracteristique_bl = 'cde_client' THEN 'cde_client'
            WHEN is_caracteristique_bl = 'ref_article' THEN 'ref_client'
            ELSE 'client_a_livrer'
        END
        WHERE is_decoupage_bl IS NULL
          AND (
                (is_company = true AND customer = true)
                OR is_caracteristique_liste_a_servir IS NOT NULL
                OR is_caracteristique_bl IS NOT NULL
          )
        """
    )
