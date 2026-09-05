# -*- coding: utf-8 -*-
"""
Migration 0.9 -> 16.0.0.10

La séquence "is.facture.pk" (Factures PK) passe de l'implémentation
"standard" à "no_gap" pour éviter les trous de numérotation quand le
create() échoue après le tirage du numéro (ex: erreur de droit d'accès
sur la commande/le BL liée à la facture).

En implémentation "standard", le champ number_next de ir_sequence n'est
jamais tenu à jour : le vrai compteur vit dans une séquence PostgreSQL
séparée. En passant en "no_gap", Odoo se met à utiliser ce champ
number_next comme compteur réel, alors qu'il était resté figé à sa
valeur d'origine (bien en dessous du dernier numéro de facture PK
réellement utilisé) -> sans ce correctif, les premières factures créées
après la mise à jour reprendraient d'anciens numéros déjà utilisés
(doublons).

Recale number_next sur le dernier numéro de facture PK réellement
utilisé + 1.
"""


def migrate(cr, version):
    if not version:
        return

    cr.execute(
        """
        SELECT COALESCE(MAX((substring(num_facture from '^PK-(\\d+)$'))::int), 0)
        FROM is_facture_pk
        WHERE num_facture ~ '^PK-\\d+$'
        """
    )
    dernier_numero = cr.fetchone()[0]

    cr.execute(
        """
        UPDATE ir_sequence
        SET number_next = %s
        WHERE code = 'is.facture.pk'
        """,
        (dernier_numero + 1,),
    )
