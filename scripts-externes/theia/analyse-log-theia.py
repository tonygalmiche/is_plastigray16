#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyse des démarrages/arrêts du Raspberry Pi THEIA.

Pour chaque cycle de fonctionnement (boot), détermine :
  - la température CPU relevée juste avant l'arrêt
  - si l'arrêt est propre (commande shutdown/reboot) ou brutal
  - une cause probable (coupure secteur, surchauffe, plantage noyau, OOM...)

À exécuter directement sur le Raspberry Pi (utilise journalctl / vcgencmd en local).
Usage :
    ./analyse-log-theia.py                 # 7 derniers jours
    ./analyse-log-theia.py --jours 15      # 15 derniers jours
    ./analyse-log-theia.py --depuis 2026-07-10
"""

import argparse
import re
import subprocess
from datetime import datetime, timedelta


SEUIL_TEMP_SURCHAUFFE = 75.0          # °C : au-delà, on suspecte une surchauffe au moment de l'arrêt
SEUIL_TEMP_CHRONIQUE = 70.0           # °C : moyenne sur tout un cycle au-delà de laquelle on parle de chauffe chronique
DELAI_REDEMARRAGE_IMMEDIAT_SEC = 30   # en dessous, redémarrage quasi instantané -> coupure secteur probable

MARQUEURS_ARRET_PROPRE = (
    "Reached target Reboot",
    "Reached target Power-Off",
    "Reached target System Halt",
    "Started Reboot",
    "Started Power-Off",
    "Started System Halt",
    "systemd-shutdown[1]: Syncing filesystems",
)


def run(cmd):
    return subprocess.run(
        cmd, shell=True, capture_output=True, text=True, errors="replace"
    ).stdout


def parse_dt(texte):
    m = re.search(r"(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})", texte)
    if not m:
        return None
    return datetime.strptime(f"{m.group(1)} {m.group(2)}", "%Y-%m-%d %H:%M:%S")


def lister_boots():
    """Retourne la liste des boots (id, début, fin) via `journalctl --list-boots`."""
    sortie = run("journalctl --list-boots -o short-iso 2>/dev/null")
    boots = []
    for ligne in sortie.splitlines():
        m = re.match(r"^\s*(-?\d+)\s+([0-9a-f]+)\s+(.+)$", ligne)
        if not m:
            continue
        offset, boot_id, reste = m.groups()
        if "—" in reste:
            debut_brut, fin_brut = reste.split("—", 1)
        elif "--" in reste:
            debut_brut, fin_brut = reste.split("--", 1)
        else:
            continue
        boots.append(
            {
                "offset": int(offset),
                "id": boot_id,
                "debut": parse_dt(debut_brut),
                "fin": parse_dt(fin_brut),
            }
        )
    boots.sort(key=lambda b: b["offset"])
    return boots


def dernieres_lignes_boot(boot_id, n=20):
    return run(f"journalctl -b {boot_id} -n {n} --no-pager -o short-iso 2>/dev/null")


def journal_complet_boot(boot_id):
    return run(f"journalctl -b {boot_id} --no-pager -o short-iso 2>/dev/null")


def derniere_temperature(journal_boot):
    temps = re.findall(r"temp cpu=([\d.]+)", journal_boot)
    return float(temps[-1]) if temps else None


def est_arret_propre(dernieres_lignes):
    return any(marqueur in dernieres_lignes for marqueur in MARQUEURS_ARRET_PROPRE)


def detecter_incident(journal_boot):
    """Cherche dans le journal du boot des traces explicites d'incident matériel/noyau."""
    if re.search(r"under-voltage detected", journal_boot, re.I):
        return "sous_tension"
    if re.search(r"kernel panic|Oops[: ]|hung task|soft lockup|rcu_sched detected|BUG: |Call Trace", journal_boot, re.I):
        return "crash"
    if re.search(r"oom-killer|Out of memory", journal_boot, re.I):
        return "oom"
    if re.search(r"EXT4-fs error|I/O error|mmc.*error|blk_update_request", journal_boot, re.I):
        return "erreur_disque"
    return None


def etat_materiel_actuel():
    """Température CPU et flags de sous-tension/throttling actuels (vcgencmd)."""
    temp_txt = run("vcgencmd measure_temp 2>/dev/null")
    m = re.search(r"temp=([\d.]+)", temp_txt)
    temp_actuelle = float(m.group(1)) if m else None

    throttled_txt = run("vcgencmd get_throttled 2>/dev/null")
    m = re.search(r"throttled=(0x[0-9a-fA-F]+)", throttled_txt)
    throttled = m.group(1) if m else None

    return temp_actuelle, throttled


def watchdog_arme():
    """Le watchdog matériel/logiciel systemd est-il actif en fonctionnement normal ?
    S'il est désactivé, un plantage/gel du système ne peut pas être auto-résolu par
    un reset watchdog : le Pi resterait figé jusqu'à une intervention manuelle."""
    sortie = run("systemctl show -p RuntimeWatchdogUSec 2>/dev/null")
    m = re.search(r"RuntimeWatchdogUSec=(\S+)", sortie)
    valeur = m.group(1) if m else None
    return bool(valeur) and valeur not in ("0", "0us", "")


def formater_duree(debut, fin):
    if not debut or not fin:
        return "-"
    delta = fin - debut
    total_min = int(delta.total_seconds() // 60)
    h, m = divmod(total_min, 60)
    if h:
        return f"{h}h{m:02d}"
    return f"{m}min"


def analyser(boots, seuil_temp, seuil_temp_chronique):
    resultats = []
    diag = {
        "nb_boots_analyses": 0,
        "kernel_panic": 0,
        "hang": 0,
        "oom": 0,
        "erreur_disque": 0,
        "sous_tension": 0,
        "shutting_down": 0,
        "reached_target_reboot": 0,
        "temp_max_globale": None,
        "nb_cycles_chauffe_chronique": 0,
        "_somme_temps": 0.0,
        "_nb_temps": 0,
    }
    for i, boot in enumerate(boots):
        if boot["fin"] is None:
            # boot en cours (offset 0, toujours actif)
            continue

        journal = journal_complet_boot(boot["id"])
        dern_lignes = dernieres_lignes_boot(boot["id"])

        propre = est_arret_propre(dern_lignes)
        temp = derniere_temperature(journal)
        incident = detecter_incident(journal)

        diag["nb_boots_analyses"] += 1
        diag["kernel_panic"] += len(re.findall(r"kernel panic|Oops[: ]", journal, re.I))
        diag["hang"] += len(re.findall(r"hung task|soft lockup|rcu_sched detected|BUG: |Call Trace", journal, re.I))
        diag["oom"] += len(re.findall(r"oom-killer|Out of memory", journal, re.I))
        diag["erreur_disque"] += len(re.findall(r"EXT4-fs error|I/O error|mmc.*error|blk_update_request", journal, re.I))
        diag["sous_tension"] += len(re.findall(r"under-voltage detected", journal, re.I))
        diag["shutting_down"] += len(re.findall(r"Shutting down\.", journal))
        diag["reached_target_reboot"] += len(re.findall(r"Reached target (Reboot|Power-Off|System Halt)", journal))

        temps_boot = [float(t) for t in re.findall(r"temp cpu=([\d.]+)", journal)]
        if temps_boot:
            diag["temp_max_globale"] = max(temps_boot + ([diag["temp_max_globale"]] if diag["temp_max_globale"] else []))
            diag["_somme_temps"] += sum(temps_boot)
            diag["_nb_temps"] += len(temps_boot)
            if (sum(temps_boot) / len(temps_boot)) >= seuil_temp_chronique:
                diag["nb_cycles_chauffe_chronique"] += 1

        boot_suivant = boots[i + 1] if i + 1 < len(boots) else None
        delai_redemarrage = None
        if boot_suivant and boot_suivant["debut"]:
            delai_redemarrage = (boot_suivant["debut"] - boot["fin"]).total_seconds()

        # --- détermination de la cause probable (labels courts, détail en légende) ---
        if propre:
            cause = "Arrêt normal"
        elif incident == "sous_tension":
            cause = "Sous-tension détectée"
        elif incident == "crash":
            cause = "Plantage logiciel"
        elif incident == "oom":
            cause = "OOM (plantage logiciel)"
        elif incident == "erreur_disque":
            cause = "Erreur disque"
        elif temp is not None and temp >= seuil_temp:
            cause = f"Surchauffe (temp={temp:.1f}°C)"
        elif delai_redemarrage is not None and delai_redemarrage < DELAI_REDEMARRAGE_IMMEDIAT_SEC:
            cause = "Coupure secteur (instantané)"
        else:
            cause = "Coupure secteur"

        resultats.append(
            {
                "debut": boot["debut"],
                "fin": boot["fin"],
                "duree": formater_duree(boot["debut"], boot["fin"]),
                "brutal": not propre,
                "temp": temp,
                "cause": cause,
            }
        )

    diag["temp_moyenne_globale"] = (
        diag["_somme_temps"] / diag["_nb_temps"] if diag["_nb_temps"] else None
    )
    del diag["_somme_temps"], diag["_nb_temps"]
    return resultats, diag


def imprimer_rapport(resultats, diag, depuis, watchdog_actif, temp_actuelle, throttled):
    largeur = 108
    print("=" * largeur)
    print(f"RAPPORT D'ANALYSE DES ARRÊTS SYSTÈME - RASPBERRY PI THEIA - depuis le {depuis.strftime('%d/%m/%Y')}")
    print("=" * largeur)

    if not resultats:
        print("\nAucun arrêt trouvé sur la période demandée.")
        return

    print()
    entete = f"{'Démarrage':16} {'Arrêt':16} {'Durée':>8} {'Brutal':>7} {'Temp':>7}  Cause probable"
    print(entete)
    print("-" * largeur)
    for r in resultats:
        debut_s = r["debut"].strftime("%d/%m %H:%M") if r["debut"] else "-"
        fin_s = r["fin"].strftime("%d/%m %H:%M") if r["fin"] else "-"
        brutal_s = "OUI" if r["brutal"] else "non"
        temp_s = f"{r['temp']:.1f}°C" if r["temp"] is not None else "?"
        print(f"{debut_s:16} {fin_s:16} {r['duree']:>8} {brutal_s:>7} {temp_s:>7}  {r['cause']}")
    print("-" * largeur)

    causes = {r["cause"] for r in resultats}
    legende = []
    if any(r["brutal"] for r in resultats):
        legende.append("Brutal = OUI : le journal ne trace aucune extinction propre ('Shutting down'/'Reached target Reboot').")
    if "Arrêt normal" in causes:
        legende.append("Arrêt normal : extinction/redémarrage demandé proprement.")
    if "Coupure secteur" in causes:
        legende.append("Coupure secteur : arrêt brutal, aucune trace de plantage détectée.")
    if "Coupure secteur (instantané)" in causes:
        legende.append("Coupure secteur (instantané) : idem, redémarrage en moins de 30s (retour de courant).")
    if "Sous-tension détectée" in causes:
        legende.append("Sous-tension détectée : message noyau 'Under-voltage detected' trouvé.")
    if "Plantage logiciel" in causes:
        legende.append("Plantage logiciel : trace de kernel panic ou de gel système (hung task...).")
    if "OOM (plantage logiciel)" in causes:
        legende.append("OOM (plantage logiciel) : processus tué par manque de mémoire (OOM killer).")
    if "Erreur disque" in causes:
        legende.append("Erreur disque : erreur EXT4/carte SD détectée, plantage possible.")
    if any(c.startswith("Surchauffe") for c in causes):
        legende.append("Surchauffe : température élevée relevée juste avant l'arrêt.")
    if not watchdog_actif and any(c.startswith("Coupure secteur") for c in causes):
        legende.append("Watchdog inactif => un gel logiciel resterait figé (pas de reset auto) ; un")
        legende.append("redémarrage effectif sans trace de crash appuie la piste 'coupure secteur'.")

    print("\nLégende :")
    for ligne in legende:
        print(f"  {ligne}")

    print(f"\n{'=' * largeur}")
    print("DIAGNOSTICS EFFECTUÉS SUR LA PÉRIODE (pour confirmer/écarter un plantage logiciel)")
    print("=" * largeur)
    nb_brutaux = sum(1 for r in resultats if r["brutal"])
    nb_total = len(resultats)
    lignes_diag = [
        ("Cycles (boots) analysés",
         f"{nb_total}  (brutaux: {nb_brutaux}/{nb_total} - propres: {nb_total - nb_brutaux}/{nb_total})"),
        ("Arrêts propres tracés ('Shutting down' / 'Reached target Reboot...')",
         f"{diag['shutting_down']} / {diag['reached_target_reboot']}"),
        ("Occurrences 'kernel panic' / 'Oops'", str(diag["kernel_panic"])),
        ("Occurrences gel système (hung task / soft lockup / rcu stall)", str(diag["hang"])),
        ("Occurrences OOM killer (manque de mémoire)", str(diag["oom"])),
        ("Occurrences erreurs disque / carte SD (EXT4-fs, I/O error...)", str(diag["erreur_disque"])),
        ("Occurrences 'Under-voltage detected' (sous-tension)", str(diag["sous_tension"])),
        ("Température CPU max relevée sur toute la période",
         f"{diag['temp_max_globale']:.1f}°C" if diag["temp_max_globale"] is not None else "?"),
        ("Température CPU moyenne sur toute la période",
         f"{diag['temp_moyenne_globale']:.1f}°C" if diag["temp_moyenne_globale"] is not None else "?"),
        (f"Cycles en chauffe chronique (moyenne du cycle >= {SEUIL_TEMP_CHRONIQUE:.0f}°C)",
         f"{diag['nb_cycles_chauffe_chronique']}/{nb_total}"),
        ("Température CPU actuelle", f"{temp_actuelle:.1f}°C" if temp_actuelle is not None else "?"),
        ("Flags sous-tension/throttling actuels (vcgencmd get_throttled)",
         f"{throttled} (0x0 = aucun incident depuis le dernier reset matériel)" if throttled else "?"),
        ("Watchdog système armé (auto-reset en cas de gel)", "OUI" if watchdog_actif else "NON"),
    ]
    largeur_libelle = max(len(l) for l, _ in lignes_diag) + 2
    for libelle, valeur in lignes_diag:
        print(f"{libelle:<{largeur_libelle}} : {valeur}")

    total_incidents = diag["kernel_panic"] + diag["hang"] + diag["oom"] + diag["erreur_disque"] + diag["sous_tension"]
    print()
    if total_incidents == 0:
        print("=> Aucune trace de plantage logiciel, d'erreur disque ou de sous-tension n'a été")
        print("   trouvée sur la période. Les arrêts brutaux sont donc très probablement dus à")
        print("   des coupures de courant secteur, et non à un plantage du Raspberry Pi.")
    else:
        print(f"=> {total_incidents} indice(s) de plantage/incident matériel détecté(s) sur la période.")
        print("   Voir le détail dans la colonne 'Cause probable' du tableau des arrêts ci-dessus.")

    if diag["nb_cycles_chauffe_chronique"] > 0:
        print(f"=> {diag['nb_cycles_chauffe_chronique']}/{nb_total} cycle(s) ont tourné avec une température")
        print(f"   moyenne >= {SEUIL_TEMP_CHRONIQUE:.0f}°C sur toute leur durée (pas juste un pic ponctuel).")
        print("   Ce stress thermique chronique reste sous le seuil de throttling du Raspberry Pi")
        print("   (~80°C) et n'explique pas à lui seul un plantage, mais fragilise le matériel sur")
        print("   la durée : à surveiller (ventilation, dissipateur, emplacement du boîtier).")


def main():
    parser = argparse.ArgumentParser(description="Analyse des arrêts système du Raspberry Pi THEIA")
    parser.add_argument("--jours", type=int, default=7, help="Nombre de jours à analyser (défaut: 7)")
    parser.add_argument("--depuis", type=str, default=None, help="Date de début au format YYYY-MM-DD")
    parser.add_argument("--seuil-temp", type=float, default=SEUIL_TEMP_SURCHAUFFE,
                         help=f"Seuil de température (°C) au-delà duquel on suspecte une surchauffe (défaut: {SEUIL_TEMP_SURCHAUFFE})")
    parser.add_argument("--seuil-temp-chronique", type=float, default=SEUIL_TEMP_CHRONIQUE,
                         help=f"Seuil de température moyenne (°C) sur un cycle au-delà duquel on parle de chauffe chronique (défaut: {SEUIL_TEMP_CHRONIQUE})")
    args = parser.parse_args()

    if args.depuis:
        depuis = datetime.strptime(args.depuis, "%Y-%m-%d")
    else:
        depuis = datetime.now() - timedelta(days=args.jours)

    boots = lister_boots()
    boots = [b for b in boots if (b["fin"] or b["debut"] or depuis) and (b["fin"] is None or b["fin"] >= depuis)]

    resultats, diag = analyser(boots, args.seuil_temp, args.seuil_temp_chronique)
    temp_actuelle, throttled = etat_materiel_actuel()
    imprimer_rapport(resultats, diag, depuis, watchdog_arme(), temp_actuelle, throttled)


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# Procédure : activer le watchdog système (non appliqué automatiquement)
# ---------------------------------------------------------------------------
#
# But : si le Raspberry Pi se fige un jour (gel logiciel), il redémarre tout
# seul au bout de quelques secondes au lieu de rester planté indéfiniment.
# Ça permettra aussi, la prochaine fois, de confirmer avec certitude si un
# arrêt brutal est dû à un gel logiciel (reset watchdog tracé dans le
# journal) ou à une coupure secteur (rien à voir avec le watchdog).
#
# 1. Vérifier que le pilote watchdog matériel du Pi est actif (bcm2835_wdt,
#    compilé en dur dans le noyau -> n'apparaît pas dans lsmod) :
#      ls -la /dev/watchdog*
#    (confirmé présent : /dev/watchdog et /dev/watchdog0)
#
# 2. Éditer /etc/systemd/system.conf et décommenter/ajouter :
#      RuntimeWatchdogSec=30s
#      RebootWatchdogSec=10min
#    (RuntimeWatchdogSec = délai sans signe de vie avant reset ;
#     RebootWatchdogSec = filet de sécurité si un reboot reste bloqué)
#
# 3. Appliquer sans redémarrer :
#      systemctl daemon-reexec
#    (ou redémarrer le Pi pour que ce soit pris en compte proprement)
#
# 4. Vérifier que c'est bien actif :
#      systemctl show -p RuntimeWatchdogUSec
#      -> doit afficher RuntimeWatchdogUSec=30000000 (30s) au lieu de 0
#
# 5. À surveiller ensuite : si un reset watchdog se produit, le journal du
#    boot suivant contient une ligne explicite au démarrage, par ex. :
#      "Watchdog... last reset cause: WDOG_RESET" (ou équivalent selon la
#      version du noyau/firmware). Ce script pourra être complété pour
#      détecter automatiquement ce marqueur si besoin.
