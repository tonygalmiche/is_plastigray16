#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Envoi quotidien du rapport PDF d'heures théoriques M.O. pour la journée précédente.

Le rapport est envoyé aux destinataires définis dans le groupe
« Mail Heures Théoriques M.O. » (modèle is.theia.validation.groupe),
via le serveur de messagerie sortant d'Odoo (XML-RPC).
"""

import sys
import os
import ssl
import xmlrpc.client
import base64
from datetime import date, timedelta


# --- chemin vers config.py (répertoire parent du script) ---
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import ODOO_USER, ODOO_PASSWORD, DATABASES, ROBOT_EMAIL, MAIL_TEST, MAIL_TEST_CC


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Nombre de jours à traiter (1 = veille, 30 = 30 derniers jours révolus, etc.)
# Note: Ne traite jamais le jour actuel (toujours des jours passés)
NB_JOURS = 1 #30


# ---------------------------------------------------------------------------
# Connexion XML-RPC
# ---------------------------------------------------------------------------

def get_connection_for_db(db_key):
    """Établit une connexion XML-RPC pour une database donnée"""
    cfg = DATABASES[db_key]
    url = cfg["url"]
    db  = cfg["db"]

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common", context=ctx, allow_none=True)
    uid = common.authenticate(db, ODOO_USER, ODOO_PASSWORD, {})
    if not uid:
        print(f"    [ERREUR] Échec d'authentification sur {db}")
        return None, None, None

    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object", context=ctx, allow_none=True)
    return db, uid, models


# ---------------------------------------------------------------------------
# Récupération des destinataires
# ---------------------------------------------------------------------------

def get_destinataires(db, uid, models):
    """Récupère les destinataires du groupe 'Mail Heures Théoriques M.O.'"""
    
    # Recherche du groupe
    groupe_ids = models.execute_kw(
        db, uid, ODOO_PASSWORD,
        "is.theia.validation.groupe", "search",
        [[("name", "=", "Mail Heures Théoriques M.O.")]],
    )
    
    if not groupe_ids:
        print("  [ATTENTION] Groupe 'Mail Heures Théoriques M.O.' non trouvé.")
        return []
    
    groupe_id = groupe_ids[0]
    groupe = models.execute_kw(
        db, uid, ODOO_PASSWORD,
        "is.theia.validation.groupe", "read",
        [groupe_id],
        {"fields": ["employee_ids"]},
    )
    
    if not groupe:
        return []
    
    employee_ids = groupe[0].get("employee_ids", [])
    
    if not employee_ids:
        print("  [ATTENTION] Aucun employé dans le groupe.")
        return []
    
    # Récupère les utilisateurs associés aux employés
    employees = models.execute_kw(
        db, uid, ODOO_PASSWORD,
        "hr.employee", "read",
        [employee_ids],
        {"fields": ["user_id"]},
    )
    
    user_ids = [e.get("user_id")[0] for e in employees if e.get("user_id")]
    
    if not user_ids:
        print("  [ATTENTION] Aucun utilisateur associé aux employés du groupe.")
        return []
    
    # Récupère les emails des utilisateurs
    users = models.execute_kw(
        db, uid, ODOO_PASSWORD,
        "res.users", "read",
        [user_ids],
        {"fields": ["email"]},
    )
    
    emails = [u.get("email") for u in users if u.get("email")]
    return emails


# ---------------------------------------------------------------------------
# Récupération/Création des données et calcul
# ---------------------------------------------------------------------------

def get_or_create_heures_theoriques(db, uid, models):
    """Crée/met à jour et calcule les heures théoriques pour la plage de dates configurée"""
    
    if NB_JOURS == 1:
        # Si 1 jour, on traite la veille
        start_date = date.today() - timedelta(days=1)
        end_date = date.today() - timedelta(days=1)
    else:
        # Sinon, on traite les NB_JOURS derniers jours révolus (en excluant aujourd'hui)
        start_date = date.today() - timedelta(days=NB_JOURS)
        end_date = date.today() - timedelta(days=1)
    
    # Cherche une fiche existante pour l'utilisateur (admin)
    existing_ids = models.execute_kw(
        db, uid, ODOO_PASSWORD,
        "is.heures.theoriques", "search",
        [[("user_id", "=", uid)]],
    )
    
    if existing_ids:
        # Réutilise la fiche existante
        record_id = existing_ids[0]
        print(f"    Mise à jour de la fiche existante (ID {record_id}) pour la période du {start_date} au {end_date}...")
        
        # Met à jour les dates de la fiche
        models.execute_kw(
            db, uid, ODOO_PASSWORD,
            "is.heures.theoriques", "write",
            [[record_id], {
                "date_debut": start_date.isoformat(),
                "date_fin": end_date.isoformat(),
            }],
        )
    else:
        # Crée une nouvelle fiche
        print(f"    Création d'une nouvelle fiche pour la période du {start_date} au {end_date}...")
        
        # Récupère le type de picking "Fabrication" pour la configuration par défaut
        picking_type_ids = models.execute_kw(
            db, uid, ODOO_PASSWORD,
            "stock.picking.type", "search",
            [[["name", "ilike", "Fabrication"], ["active", "=", True]]],
            {"limit": 1},
        )
        
        picking_type_id = picking_type_ids[0] if picking_type_ids else False
        
        record_id = models.execute_kw(
            db, uid, ODOO_PASSWORD,
            "is.heures.theoriques", "create",
            [{
                "user_id": uid,
                "type_tps": "user",
                "date_debut": start_date.isoformat(),
                "date_fin": end_date.isoformat(),
                "picking_type_id": picking_type_id,
            }],
        )
    
    # Appelle action_calculer pour générer les lignes
    print(f"  Calcul des heures théoriques...")
    models.execute_kw(
        db, uid, ODOO_PASSWORD,
        "is.heures.theoriques", "action_calculer",
        [[record_id]],
    )
    
    return [record_id], start_date.isoformat(), end_date.isoformat()


# ---------------------------------------------------------------------------
# Génération du rapport PDF
# ---------------------------------------------------------------------------

def generate_pdf_report(db, uid, models, record_ids, period_start, period_end):
    """Génère le rapport PDF pour les enregistrements via la méthode Odoo"""
    
    try:
        # Appelle la méthode get_report_pdf_base64 du modèle
        pdf_base64 = models.execute_kw(
            db, uid, ODOO_PASSWORD,
            "is.heures.theoriques", "get_report_pdf_base64",
            [record_ids],
        )
        
        # Décode le base64 en bytes
        pdf_bytes = base64.b64decode(pdf_base64)
        
        return pdf_bytes
        
    except Exception as e:
        print(f"  [ERREUR] Génération du PDF : {e}")
        return None


# ---------------------------------------------------------------------------
# Envoi de l'e-mail
# ---------------------------------------------------------------------------

def send_email_with_pdf(db, uid, models, emails, pdf_bytes, period_start, period_end):
    """Envoie le mail avec le rapport PDF en pièce jointe"""
    
    dest_email = MAIL_TEST if MAIL_TEST else ", ".join(emails)
    
    if not dest_email:
        print("  [IGNORÉ] Aucun destinataire configuré.")
        return False
    
    # Format des dates pour l'affichage
    start_display = date.fromisoformat(period_start).strftime("%d/%m/%Y")
    end_display = date.fromisoformat(period_end).strftime("%d/%m/%Y")
    
    # Formater le sujet et le corps selon le nombre de jours
    if NB_JOURS == 1:
        subject = f"Rapport heures théoriques M.O. - {start_display}"
        period_text = f"pour la journée du <strong>{start_display}</strong>"
    else:
        subject = f"Rapport heures théoriques M.O. - du {start_display} au {end_display}"
        period_text = f"pour la période du <strong>{start_display}</strong> au <strong>{end_display}</strong>"
    
    body = f"""
<p>Bonjour,</p>

<p>Veuillez trouver ci-joint le rapport d'heures théoriques M.O. {period_text}.</p>

<p>Cordialement,<br/>
<em>Système Automatisé</em></p>
"""
    
    mail_vals = {
        "subject":     subject,
        "body_html":   body,
        "email_from":  ROBOT_EMAIL,
        "email_to":    dest_email,
        "state":       "outgoing",
        "auto_delete": True,
    }
    
    if MAIL_TEST_CC:
        mail_vals["email_cc"] = MAIL_TEST_CC
    
    if pdf_bytes:
        # Crée d'abord l'attachment, puis le lie au mail via attachment_ids
        attachment_id = models.execute_kw(
            db, uid, ODOO_PASSWORD,
            "ir.attachment", "create",
            [{
                "name": f"heures_theoriques_{period_start}_to_{period_end}.pdf",
                "type": "binary",
                "datas": base64.b64encode(pdf_bytes).decode("utf-8"),
                "mimetype": "application/pdf",
            }],
        )
        mail_vals["attachment_ids"] = [(4, attachment_id)]
    
    mail_id = models.execute_kw(
        db, uid, ODOO_PASSWORD,
        "mail.mail", "create",
        [mail_vals],
    )
    
    # Le mail est créé avec state=outgoing, le scheduler Odoo l'enverra
    
    suffix = f" [TEST → {dest_email}]" if MAIL_TEST else ""
    print(f"  [OK] E-mail mis en file d'envoi{suffix}")
    return True


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def main():
    print("=" * 80)
    print("ENVOI DU RAPPORT HEURES THÉORIQUES M.O.")
    if NB_JOURS == 1:
        yesterday = (date.today() - timedelta(days=1)).strftime("%d/%m/%Y")
        print(f"Paramètre : 1 jour (veille) - {yesterday}")
    else:
        start = (date.today() - timedelta(days=NB_JOURS)).strftime("%d/%m/%Y")
        end = (date.today() - timedelta(days=1)).strftime("%d/%m/%Y")
        print(f"Paramètre : {NB_JOURS} derniers jours - du {start} au {end}")
    print("=" * 80)
    
    for db_key, db_cfg in DATABASES.items():
        print(f"\n{'='*80}")
        print(f"Traitement de la base '{db_key}' ({db_cfg['db']})...")
        print('='*80)
        
        # Connexion
        print(f"  Connexion...")
        db, uid, models = get_connection_for_db(db_key)
        if not db or not uid:
            print(f"  [ERREUR] Impossible de se connecter. Passage à la base suivante.")
            continue
        print(f"  [OK] Connexion établie.")
        
        # Récupération des destinataires
        print(f"  Récupération des destinataires...")
        emails = get_destinataires(db, uid, models)
        if not emails:
            print(f"  [ATTENTION] Aucun destinataire trouvé. Passage à la base suivante.")
            continue
        print(f"  [OK] {len(emails)} destinataire(s) : {', '.join(emails)}")
        
        # Création/Récupération et calcul des données des X derniers jours
        print(f"  Création/Récupération et calcul des heures théoriques...")
        try:
            record_ids, period_start, period_end = get_or_create_heures_theoriques(db, uid, models)
            
            # Formater l'affichage selon le nombre de jours
            start_display = date.fromisoformat(period_start).strftime("%d/%m/%Y")
            end_display = date.fromisoformat(period_end).strftime("%d/%m/%Y")
            
            if NB_JOURS == 1:
                date_info = f"du {start_display}"
            else:
                date_info = f"du {start_display} au {end_display}"
            
            print(f"  [OK] {len(record_ids)} enregistrement(s) préparé(s) ({date_info})")
        except Exception as e:
            print(f"  [ERREUR] Impossible de préparer les données : {e}")
            continue
        
        # Génération du PDF
        print(f"  Génération du rapport PDF...")
        pdf_bytes = generate_pdf_report(db, uid, models, record_ids, period_start, period_end)
        if not pdf_bytes:
            print(f"  [ERREUR] Impossible de générer le PDF. Passage à la base suivante.")
            continue
        print(f"  [OK] PDF généré ({len(pdf_bytes)} bytes)")
        
        # Envoi de l'e-mail
        print(f"  Envoi de l'e-mail...")
        send_email_with_pdf(db, uid, models, emails, pdf_bytes, period_start, period_end)
    
    print(f"\n{'='*80}")
    print("Traitement de toutes les bases terminé.")
    print('='*80)


if __name__ == "__main__":
    main()
