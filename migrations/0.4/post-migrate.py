# -*- coding: utf-8 -*-
"""
Migration 0.3 -> 0.4

Repare le mapping ir_model_data <-> uom.uom / uom.category, constate
identique sur les 4 bases pg-odoo16-0, pg-odoo16-1, pg-odoo16-3 et
pg-odoo16-4 : les xmlids standards uom.* pointent vers les ids
"installation fraiche" (1, 2, 3... dans l'ordre d'apparition du fichier
odoo/addons/uom/data/uom_data.xml), au lieu des vrais ids de ces bases
(remplies au fil des annees avec de nombreuses unites "maison" type
"ROULEAU DE 50M", ce qui a decale toute la numerotation reelle par
rapport a celle d'une installation fraiche).

Constate en tentant d'installer uom_unece (module OCA requis par
is_facturation_electronique) : erreur
"Cannot update missing record 'uom.product_uom_dozen'".

Verifie ligne a ligne (categorie/type/facteur) sur les 4 bases, dont la
table uom_uom est identique sur la plage d'ids concernee (1-26) :
- 13 xmlids uom.uom + la categorie "Volume" pointent vers le mauvais id
  alors que la bonne ligne existe deja sous un autre id => remappage
  simple de ir_model_data.res_id.
- 12 xmlids uom.uom + la categorie "Surface" n'ont plus aucun
  enregistrement correspondant (supprime au fil du temps, ou jamais cree)
  => creation, comme deja fait pour Odoo 18 par is_coheliance18 (meme
  defaut de migration, cf. son migrations/18.0.1.0.1/post-migrate.py).

Ne touche que ir_model_data (+ creation des uom/categorie physiquement
absentes) : aucune donnee metier n'est modifiee, puisque produits/lignes
de facture referencent une unite par son id concret, jamais par xmlid.
"""
from odoo import api, SUPERUSER_ID


# xmlid -> id reel verifie (categorie deja correcte, simple remappage de
# ir_model_data.res_id)
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

# xmlid -> valeurs a creer (aucune ligne correspondante sur les 4 bases),
# reprises telles quelles depuis uom_data.xml (branche 16.0). categ=None
# pour uom_square_meter/uom_square_foot : categorie "Surface" creee plus
# bas (absente des 4 bases), renseignee dynamiquement.
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


def _matches(row, vals):
    if not row.exists() or row.uom_type != vals["uom_type"]:
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

    # --- Unites : doublon "reference" dans la categorie "Unite" -----------
    # Sur certaines bases, une unite "maison" (ex. "rouleau") a ete creee en
    # tant que 2e unite de reference dans la categorie "Unite", en plus de
    # celle du xmlid uom.product_uom_unit. Odoo l'accepte a la creation mais
    # _check_category_reference_uniqueness() refuse ensuite toute creation
    # ulterieure dans cette categorie (bloque la creation de
    # product_uom_dozen ci-dessous). Comme ces doublons ne sont reference
    # nulle part (produits/lignes de commande/mouvements), on les repasse en
    # "bigger" pour lever le blocage sans toucher aux donnees metier.
    unit_categ_imd = imd_for("uom.category", "product_uom_categ_unit")
    unit_uom_imd = imd_for("uom.uom", "product_uom_unit")
    if unit_categ_imd and unit_uom_imd:
        duplicate_refs = uom_model.search([
            ("category_id", "=", unit_categ_imd.res_id),
            ("uom_type", "=", "reference"),
            ("id", "!=", unit_uom_imd.res_id),
        ])
        if duplicate_refs:
            duplicate_refs.write({"uom_type": "bigger"})

    surface_imd = imd_for("uom.category", "uom_categ_surface")
    surface_categ = env["uom.category"]
    if surface_imd:
        current = categ_model.browse(surface_imd.res_id)
        if current.exists() and current.name == "Surface":
            surface_categ = current  # deja corrige (script relance)
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
        current = uom_model.browse(imd.res_id)
        if _matches(current, vals):
            continue  # deja corrige (script relance)
        categ_id = vals["categ"] or surface_categ.id
        create_vals = {"name": vals["name"], "category_id": categ_id, "uom_type": vals["uom_type"]}
        if "factor" in vals:
            create_vals["factor"] = vals["factor"]
        else:
            create_vals["factor_inv"] = vals["factor_inv"]
        new_uom = uom_model.create(create_vals)
        imd.write({"res_id": new_uom.id})
