#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Met à jour les champs is_cout_budget_matiere et is_ecart_budget
dans account_move_line en allant chercher les coûts dans is_cout
par code article (product_id).

  is_cout_budget_matiere = is_cout.cout_budget_matiere
  is_ecart_budget        = price_unit - is_cout.cout_budget_matiere
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import psycopg2
from config import DATABASES, PG_HOST, PG_PORT, PG_USER, PG_PASSWORD, NB_JOURS_CREATION_FACTURE


SQL_UPDATE = """
    UPDATE account_move_line ail
    SET
        is_cout_budget_matiere = ic.cout_budget_matiere * uom_from.factor / uom_to.factor,
        is_ecart_budget        = (ic.cout_budget_matiere * uom_from.factor / uom_to.factor) - ail.price_unit 
    FROM is_cout ic,
         product_product  pp,
         product_template pt,
         uom_uom          uom_from,
         uom_uom          uom_to
    WHERE ail.product_id       = ic.name
      AND pp.id                = ail.product_id
      AND pt.id                = pp.product_tmpl_id
      AND uom_from.id          = pt.uom_id
      AND uom_to.id            = ail.product_uom_id
      AND ail.display_type     = 'product'
      AND uom_to.factor       != 0
      {filtre_date}
"""

SQL_NULL_TO_ZERO = """
    UPDATE account_move_line
    SET is_cout_budget_matiere = 0,
        is_ecart_budget        = 0
    WHERE display_type = 'product'
      AND (is_cout_budget_matiere IS NULL OR is_ecart_budget IS NULL)
"""


def update_database(dbname):
    print(f"\n=== Base : {dbname} ===")
    conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        user=PG_USER,
        password=PG_PASSWORD,
        dbname=dbname,
    )
    try:
        with conn:
            with conn.cursor() as cr:
                filtre_date = f"AND ail.create_date >= NOW() - INTERVAL '{NB_JOURS_CREATION_FACTURE} days'" if NB_JOURS_CREATION_FACTURE else ""
                cr.execute(SQL_UPDATE.format(filtre_date=filtre_date))
                print(f"  {cr.rowcount} ligne(s) mise(s) à jour avec les coûts")
                cr.execute(SQL_NULL_TO_ZERO)
                print(f"  {cr.rowcount} ligne(s) NULL remise(s) à 0")
    finally:
        conn.close()


if __name__ == '__main__':
    for db in DATABASES:
        try:
            update_database(db)
        except Exception as e:
            print(f"  ERREUR sur {db} : {e}")
    print("\nTerminé.")
