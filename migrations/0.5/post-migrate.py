# -*- coding: utf-8 -*-
"""
Migration 0.4 -> 0.5

Corrige un bug de la migration 0.4 (migrations/0.4/post-migrate.py) :
sa fonction _matches(), utilisee pour savoir si une unite a deja ete
corrigee (script relance) et donc s'il faut la (re)creer, ne comparait
que (uom_type, factor), pas la categorie. Or la ligne "kg" (categorie
Poids, reference, facteur 1.0) que product_uom_day visait encore a tort
a exactement la meme signature (reference, facteur 1.0) que "Days"
attendu (categorie Temps de travail) : la creation de "Days" a donc ete
sautee par erreur, laissant la categorie "Temps de travail" sans unite
de reference (contrainte Odoo violee, constate a l'installation de
uom_unece : "La categorie d'UdM Temps de travail doit avoir une unite de
mesure de reference").

Ce script reprend exactement la meme logique que la 0.4, avec _matches()
corrige (categorie comparee en plus de uom_type/factor). Idempotent et
sans effet sur les xmlids deja correctement corriges par la 0.4 : safe a
rejouer aussi bien sur les bases ou la 0.4 est deja passee (ne fera que
creer "Days", qui manquait) que sur celles ou elle ne l'est pas encore.
"""
from odoo import api, SUPERUSER_ID


UOM_REMAP = {
    "product_uom_kgm": 3,
    "product_uom_gram": 4,
    "product_uom_hour": 5,
    "product_uom_ton": 7,
    "product_uom_meter": 8,
    "product_uom_km": 9,
    "product_uom_litre": 11,
    "product_uom_lb": 12,
    "product_uom_oz": 13,
    "product_uom_inch": 14,
    "product_uom_mile": 16,
    "product_uom_qt": 18,
    "product_uom_gal": 19,
}
CATEG_REMAP = {
    "product_uom_categ_vol": 5,
}

UOM_CREATE = {
    "product_uom_dozen": {"name": "Dozens", "categ": 1, "uom_type": "bigger", "factor_inv": 12},
    "product_uom_day": {"name": "Days", "categ": 3, "uom_type": "reference", "factor": 1.0},
    "product_uom_millimeter": {"name": "mm", "categ": 4, "uom_type": "smaller", "factor": 1000},
    "product_uom_cm": {"name": "cm", "categ": 4, "uom_type": "smaller", "factor": 100},
    "product_uom_foot": {"name": "ft", "categ": 4, "uom_type": "smaller", "factor": 3.28084},
    "product_uom_yard": {"name": "yd", "categ": 4, "uom_type": "smaller", "factor": 1.09361},
    "product_uom_cubic_meter": {"name": "m³", "categ": 5, "uom_type": "bigger", "factor_inv": 1000},
    "product_uom_floz": {"name": "fl oz (US)", "categ": 5, "uom_type": "smaller", "factor": 33.814},
    "product_uom_cubic_inch": {"name": "in³", "categ": 5, "uom_type": "smaller", "factor": 61.0237},
    "product_uom_cubic_foot": {"name": "ft³", "categ": 5, "uom_type": "bigger", "factor_inv": 28.3168},
    "uom_square_meter": {"name": "m²", "categ": None, "uom_type": "reference", "factor": 1.0},
    "uom_square_foot": {"name": "ft²", "categ": None, "uom_type": "smaller", "factor": 10.76391},
}

TOLERANCE = 1e-4


def _matches(row, vals, categ_id):
    if not row.exists() or row.uom_type != vals["uom_type"]:
        return False
    if row.category_id.id != categ_id:
        return False
    expected = vals["factor"] if "factor" in vals else 1.0 / vals["factor_inv"]
    return abs(row.factor - expected) < TOLERANCE


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    imd_model = env["ir.model.data"]
    uom_model = env["uom.uom"]
    categ_model = env["uom.category"]

    def imd_for(model, name):
        return imd_model.search(
            [("module", "=", "uom"), ("model", "=", model), ("name", "=", name)],
            limit=1,
        )

    # --- Categories : remap + creation de "Surface" ----------------------
    for xmlid_name, res_id in CATEG_REMAP.items():
        imd = imd_for("uom.category", xmlid_name)
        if imd and imd.res_id != res_id and categ_model.browse(res_id).exists():
            imd.write({"res_id": res_id})

    surface_imd = imd_for("uom.category", "uom_categ_surface")
    surface_categ = env["uom.category"]
    if surface_imd:
        current = categ_model.browse(surface_imd.res_id)
        if current.exists() and current.name == "Surface":
            surface_categ = current  # deja corrige
        else:
            surface_categ = categ_model.create({"name": "Surface"})
            surface_imd.write({"res_id": surface_categ.id})

    # --- Unites : remap ---------------------------------------------------
    for xmlid_name, res_id in UOM_REMAP.items():
        imd = imd_for("uom.uom", xmlid_name)
        if imd and imd.res_id != res_id and uom_model.browse(res_id).exists():
            imd.write({"res_id": res_id})

    # --- Unites : creation --------------------------------------------------
    for xmlid_name, vals in UOM_CREATE.items():
        imd = imd_for("uom.uom", xmlid_name)
        if not imd:
            continue
        categ_id = vals["categ"] or surface_categ.id
        current = uom_model.browse(imd.res_id)
        if _matches(current, vals, categ_id):
            continue  # deja corrige
        create_vals = {"name": vals["name"], "category_id": categ_id, "uom_type": vals["uom_type"]}
        if "factor" in vals:
            create_vals["factor"] = vals["factor"]
        else:
            create_vals["factor_inv"] = vals["factor_inv"]
        new_uom = uom_model.create(create_vals)
        imd.write({"res_id": new_uom.id})
