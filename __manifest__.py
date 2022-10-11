# -*- coding: utf-8 -*-
{
    "name"     : "Module Odoo 16 pour Plastigray",
    "version"  : "0.1",
    "author"   : "InfoSaône",
    "category" : "InfoSaône",
    "description": """
Module Odoo 16 pour Plastigray
===================================================
""",
    "maintainer" : "InfoSaône",
    "website"    : "http://www.infosaone.com",
    "depends"    : [
        "base",
        "sale_management",
        "purchase",
        "account",
        "l10n_fr",
        "l10n_fr_fec",
    ],
    "data" : [
        "security/ir.model.access.csv",
        "views/is_mold_view.xml",
        "views/is_mold_project_view.xml",
        "views/is_dossierf_view.xml",
        "views/product_view.xml",
        "views/menu.xml",


    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
