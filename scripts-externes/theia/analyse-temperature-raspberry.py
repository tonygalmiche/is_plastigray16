#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Relève la température CPU de tous les Raspberry Pi THEIA (modèle is.raspberry)
de chaque base de données Odoo définie dans DATABASES (config.py).

Pour chaque base :
  - récupère la liste des Raspberry (Adresse IP, Adresse MAC, Equipement)
  - se connecte en SSH sur chacun pour relever `vcgencmd measure_temp`
  - affiche un tableau récapitulatif, trié par température décroissante

Usage :
    ./analyse-temperature-raspberry.py                  # toutes les bases
    ./analyse-temperature-raspberry.py --db odoo1        # une seule base
    ./analyse-temperature-raspberry.py --seuil-temp 70   # seuil d'alerte (°C)
"""

import argparse
import re
import subprocess
import sys
import os
from concurrent.futures import ThreadPoolExecutor
import ssl
import xmlrpc.client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import ODOO_USER, ODOO_PASSWORD, DATABASES


SEUIL_TEMP_DEFAUT = 70.0   # °C : au-delà, la ligne est signalée dans le rapport
SSH_TIMEOUT_SEC = 3


# ---------------------------------------------------------------------------
# Connexion XML-RPC
# ---------------------------------------------------------------------------

def get_connection(cfg):
    """Établit une connexion XML-RPC pour une base donnée."""
    url = cfg["url"]
    db = cfg["db"]

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common", context=ctx, allow_none=True)
    uid = common.authenticate(db, ODOO_USER, ODOO_PASSWORD, {})
    if not uid:
        print(f"    [ERREUR] Échec d'authentification sur {db}")
        return None, None

    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object", context=ctx, allow_none=True)
    return uid, models


def lister_raspberry(db, uid, models):
    """Retourne la liste des Raspberry (name=IP, adresse_mac, equipement) d'une base."""
    ids = models.execute_kw(db, uid, ODOO_PASSWORD, "is.raspberry", "search", [[]])
    if not ids:
        return []
    return models.execute_kw(
        db, uid, ODOO_PASSWORD,
        "is.raspberry", "read",
        [ids],
        {"fields": ["name", "adresse_mac", "last_presse_id"]},
    )


# ---------------------------------------------------------------------------
# Relevé de température via SSH
# ---------------------------------------------------------------------------

def relever_temperature(ip):
    """Se connecte en SSH sur le Raspberry et relève sa température CPU (°C)."""
    cmd = (
        f"ssh -o ConnectTimeout={SSH_TIMEOUT_SEC} -o StrictHostKeyChecking=no "
        f"root@{ip} \"vcgencmd measure_temp\""
    )
    try:
        sortie = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=SSH_TIMEOUT_SEC + 5
        )
    except subprocess.TimeoutExpired:
        return None, "timeout"

    if sortie.returncode != 0:
        erreur = (sortie.stderr or sortie.stdout).strip().splitlines()
        return None, erreur[-1] if erreur else "erreur SSH"

    m = re.search(r"temp=([\d.]+)", sortie.stdout)
    if not m:
        return None, "réponse inattendue"
    return float(m.group(1)), None


# ---------------------------------------------------------------------------
# Rapport
# ---------------------------------------------------------------------------

def imprimer_rapport(nom_db, lignes, seuil_temp, seuil_actif):
    largeur = 90
    print("=" * largeur)
    print(f"TEMPÉRATURE CPU DES RASPBERRY - {nom_db}")
    print("=" * largeur)

    if seuil_actif:
        lignes = [l for l in lignes if l["temp"] is not None and l["temp"] >= seuil_temp]

    if not lignes:
        print("Aucun Raspberry trouvé.")
        return

    lignes.sort(key=lambda l: (l["temp"] is None, -(l["temp"] or 0)))

    entete = f"{'Base':10} {'Adresse IP':16} {'Adresse MAC':18} {'Equipement':20} {'Température'}"
    print(entete)
    print("-" * largeur)
    for l in lignes:
        equipement = l["equipement"] or "-"
        if l["temp"] is not None:
            temp_s = f"{l['temp']:.1f}°C"
            if l["temp"] >= seuil_temp:
                temp_s += "  /!\\"
        else:
            temp_s = f"injoignable ({l['erreur']})"
        print(f"{l['db_key']:10} {l['ip']:16} {l['mac'] or '-':18} {equipement:20} {temp_s}")
    print("-" * largeur)


def main():
    parser = argparse.ArgumentParser(description="Relevé de température des Raspberry Pi THEIA")
    parser.add_argument("--db", type=str, default=None, help="Clé de la base à traiter (défaut: toutes)")
    parser.add_argument("--seuil-temp", type=float, default=None,
                         help=f"Seuil en °C : si défini, n'affiche que les Raspberry à cette "
                              f"température ou plus (les injoignables sont alors masqués) "
                              f"(défaut: aucun filtre, marqueur /!\\ à partir de {SEUIL_TEMP_DEFAUT}°C)")
    args = parser.parse_args()

    seuil_actif = args.seuil_temp is not None
    seuil_temp = args.seuil_temp if seuil_actif else SEUIL_TEMP_DEFAUT

    bases = {args.db: DATABASES[args.db]} if args.db else DATABASES

    for db_key, cfg in bases.items():
        nom_db = cfg.get("name", db_key)
        uid, models = get_connection(cfg)
        if not uid:
            continue

        raspberries = lister_raspberry(cfg["db"], uid, models)
        if not raspberries:
            imprimer_rapport(nom_db, [], seuil_temp, seuil_actif)
            continue

        with ThreadPoolExecutor(max_workers=10) as executor:
            temperatures = list(executor.map(lambda r: relever_temperature(r["name"]), raspberries))

        lignes = []
        for r, (temp, erreur) in zip(raspberries, temperatures):
            lignes.append({
                "db_key": db_key,
                "ip": r["name"],
                "mac": r["adresse_mac"],
                "equipement": r["last_presse_id"][1] if r["last_presse_id"] else None,
                "temp": temp,
                "erreur": erreur,
            })

        imprimer_rapport(nom_db, lignes, seuil_temp, seuil_actif)
        print()


if __name__ == "__main__":
    main()
