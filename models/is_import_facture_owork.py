# -*- coding: utf-8 -*-
from odoo import models, fields, api         # type: ignore
from odoo.exceptions import ValidationError  # type: ignore
from xmlrpc import client as xmlrpclib
from datetime import datetime
from urllib import request
from urllib.error import HTTPError, URLError
from socket import timeout
from subprocess import PIPE, Popen
import pytz
import csv
import base64
import sys
import logging
_logger = logging.getLogger(__name__)



class is_import_facture_owork(models.Model):
    _name = "is.import.facture.owork"
    _description = "Importation factures O'Work"
    _order='name desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    active                = fields.Boolean("Actif", default=True, tracking=True)
    name                  = fields.Char("N°", readonly=True, tracking=True)
    attachment_ids        = fields.Many2many('ir.attachment', 'is_import_facture_owork_attachment_rel', 'import_id', 'attachment_id', 'Fichiers à importer')
    nb_lignes             = fields.Integer("Nombre de lignes"  , readonly=True, tracking=True)
    nb_factures_a_traiter = fields.Integer("Nombre de factures à traiter", readonly=True, tracking=True)
    nb_avoirs             = fields.Integer("Nombre d'avoirs", readonly=True, tracking=True)
    nb_factures           = fields.Integer("Nombre de factures générées", readonly=True, tracking=True, compute='_compute_nb_factures', store=True)
    nb_anomalies          = fields.Integer("Nombre d'anomalies", readonly=True, tracking=True, compute='_compute_nb_anomalies', store=True)
    line_ids              = fields.One2many('is.import.facture.owork.line', 'import_id', "Lignes", copy=True)
    invoice_ids           = fields.One2many('account.move', 'is_owork_id', "Factures Odoo")
    state                 = fields.Selection([('analyse', 'Analyse'),('traite', 'Traité')], "État", index=True, default="analyse", tracking=True)
    factures              = fields.Text("Factures", readonly=True, tracking=True)
    id_owork_list         = fields.Text("Liste des ID O'Work", readonly=True, tracking=True, compute='_compute_id_owork_list', store=True)


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('is.import.facture.owork')
        return super().create(vals_list)


    @api.depends('invoice_ids')
    def _compute_nb_factures(self):
        for obj in self:
            obj.nb_factures = len(obj.invoice_ids)


    @api.depends('line_ids','line_ids.anomalies')
    def _compute_nb_anomalies(self):
        for obj in self:
            nb_anomalies = 0
            for line in obj.line_ids:
                if line.anomalies:
                    nb_anomalies+=1
            obj.nb_anomalies = nb_anomalies


    @api.depends('line_ids','line_ids.id_owork')
    def _compute_id_owork_list(self):
        for obj in self:
            id_owork_list = []
            for line in obj.line_ids:
                if line.id_owork and str(line.id_owork) not in id_owork_list:
                    id_owork_list.append(str(line.id_owork))
            obj.id_owork_list = ','.join(sorted(id_owork_list)) if id_owork_list else False


    def actualiser_lignes(self):
        for obj in self:
            obj.line_ids.actualiser_ligne()
            obj._compute_id_owork_list()

            #** Statistiques **************************************************
            obj.nb_lignes = len(obj.line_ids)
            factures = []
            avoirs = []
            for line in obj.line_ids:
                if line.numfac not in factures and line.numfac not in avoirs:
                    # Si le montant TTC est négatif, c'est un avoir
                    if line.montanttc < 0:
                        avoirs.append(line.numfac)
                    else:
                        factures.append(line.numfac)
            
            obj.nb_factures_a_traiter = len(factures)
            obj.nb_avoirs = len(avoirs)
            
            # Texte pour l'affichage
            texte_factures = []
            if len(factures) > 0:
                texte_factures.extend(factures)
            if len(avoirs) > 0:
                texte_factures.extend(['AVOIR: ' + avoir for avoir in avoirs])
            
            if len(texte_factures) > 0:
                obj.factures = '\n'.join(texte_factures)
            else:
                obj.factures = False
            #******************************************************************
        return []



    def voir_les_lignes(self):
        for obj in self:
            ctx={
                'default_import_id': obj.id,
            }
            return {
                'name'     : obj.name,
                'view_mode': 'tree,form',
                'res_model': 'is.import.facture.owork.line',
                'domain'   : [('import_id' ,'=',obj.id)],
                'type'     : 'ir.actions.act_window',
                'context'  : ctx,
                'limit'    : 1000,
            }



    def get_destinataires(self):
        "Recherche de la liste de diffusion pour l'envoi des mails"
        for obj in self:
            company = self.env.company
            DB        = company.is_nom_base_odoo0
            USERID    = 2
            USERPASS  = company.is_mdp_admin
            URL       = company.is_url_odoo0 
            sock = xmlrpclib.ServerProxy('%s/xmlrpc/2/object'%URL)
            domain=[('code','=','import-facture-owork')]
            users=False
            try:
                lines=sock.execute_kw(DB, USERID, USERPASS, 'is.liste.diffusion.mail', 'search_read', [domain], {'fields': ['user_ids'], 'limit': 1, 'order': 'id desc'})
                user_ids=[]
                for line in lines:
                    user_ids=line['user_ids']
                    domain=[('id','in',user_ids)]
                    users=sock.execute_kw(DB, USERID, USERPASS, 'res.users', 'search_read', [domain], {'fields': ['name','email']})
            except:
                msg="Problème de connexion sur %s ou sur la base %s"%(URL,DB)
                _logger.warning(msg)
            return(users)


    def creation_factures(self):
        for obj in self:
            users_mail = obj.get_destinataires()
            
            #** Liste de toutes les factures à traiter (hors avoirs) **********
            factures_a_traiter = []
            avoirs_list = []
            for line in obj.line_ids:
                if line.numfac:
                    # Si le montant TTC est négatif, c'est un avoir
                    if line.montanttc < 0:
                        if line.numfac not in avoirs_list:
                            avoirs_list.append(line.numfac)
                    else:
                        if line.numfac not in factures_a_traiter:
                            factures_a_traiter.append(line.numfac)
            #******************************************************************
            
            #** Liste des factures à créer (hors avoirs) **********************
            factures={}
            factures_non_creees = {}  # Dictionnaire pour stocker les raisons de non-création
            for line in obj.line_ids:
                numfac = line.numfac
                
                # Ne pas créer de facture si c'est un avoir (montant négatif)
                if line.montanttc < 0:
                    if numfac not in factures_non_creees:
                        factures_non_creees[numfac] = "Avoir - Traitement non supporté (montant TTC négatif)"
                    continue
                
                if numfac not in factures:
                    bon_a_payer = True
                    if line.litige=='L':
                        bon_a_payer = False
                    if line.partner_id and line.datefact and line.numfac:
                        vals = {
                            'partner_id'      : line.partner_id.id,
                            'journal_id'      : 2,
                            'move_type'       : 'in_invoice',
                            'invoice_date'    : line.datefact,
                            'date'            : line.datefact,
                            'invoice_date_due': line.datefact,
                            'is_bon_a_payer'  : bon_a_payer,
                            'supplier_invoice_number': line.numfac,
                            'is_owork_id'     : obj.id,
                            'is_id_owork'     : line.id_owork,
                        }
                        factures[numfac]=vals
                    else:
                        # Enregistrer la raison de non-création
                        if numfac not in factures_non_creees:
                            raisons = []
                            if not line.partner_id:
                                raisons.append("Fournisseur manquant")
                            if not line.datefact:
                                raisons.append("Date de facture manquante")
                            if not line.numfac:
                                raisons.append("Numéro de facture manquant")
                            factures_non_creees[numfac] = ', '.join(raisons)
            #******************************************************************

            for facture in factures:
                lines = []
                invoice_line_tax_id=[]
                for line in obj.line_ids:
                    if line.numfac==facture:
                        product_id = line.product_id.id
                        if product_id:
                            description     = line.descriparticle
                            quantite        = line.qtefact
                            invoice_line_tax_id=[]
                            if line.tax_id:
                                invoice_line_tax_id.append(line.tax_id.id)
                                #** Ajout tax déductible pour Intracom ********
                                if line.tax_id.description=='ACH_UE_due-20.0':
                                    taxs = self.env['account.tax'].search([('description','=',"ACH_UE_ded.-20.0")])
                                    for tax in taxs:
                                        invoice_line_tax_id.append(tax.id)
                                #**********************************************
                            # Garder une liste vide au lieu de False pour éviter l'erreur "bool is not iterable"
                            product_uom_id = line.product_id.uom_po_id.id
                            if line.stock_move_id.id:
                                product_uom_id = line.stock_move_id.purchase_line_id.product_uom.id

                            v = {
                                'product_id'      : product_id,
                                'name'            : description or line.product_id.name,
                                'quantity'        : line.qtefact,
                                'product_uom_id'  : product_uom_id,
                                'price_unit'      : line.prixfact,
                                'tax_ids'         : [(6,0,invoice_line_tax_id)],
                                'is_move_id'      : line.stock_move_id.id,
                                'purchase_line_id': line.stock_move_id.purchase_line_id.id,
                                'is_section_analytique_id': line.product_id.is_section_analytique_ha_id.id,
                                'is_document'     : line.num_chantier_fact or line.num_chantier_rcp or False,
                            }
                            lines.append([0,False,v]) 
                vals=factures[facture]
                vals.update({
                    'invoice_line_ids': lines,
                })

                new_invoice=self.env['account.move'].create(vals)
                for line in obj.line_ids:
                    if line.numfac==facture:
                        line.invoice_id = new_invoice.id
                for line in new_invoice.invoice_line_ids:
                    if line.is_move_id:
                        line.is_move_id.invoice_state='invoiced'
                        line.is_move_id.picking_id._compute_invoice_state()

                #** Récupérer le montant HT O'Work pour cette facture **********
                montantht_owork = 0
                for line in obj.line_ids:
                    if line.numfac == facture:
                        montantht_owork = line.montantht
                        break
                #**************************************************************

                #** Correction automatique des petits écarts *******************
                # Récupérer les montants O'Work pour cette facture
                montanttva_owork = 0
                montanttc_owork = 0
                for line in obj.line_ids:
                    if line.numfac == facture:
                        montanttva_owork = line.montanttva
                        montanttc_owork = line.montanttc
                        break
                
                ecart_ht_corrige = obj._corriger_ecart_montant_ht(new_invoice, montantht_owork)
                ecart_tva_corrige = obj._corriger_ecart_montant_tva(new_invoice, montanttva_owork)
                
                # Stocker les corrections dans un champ technique sur la facture
                if ecart_ht_corrige != 0 or ecart_tva_corrige != 0:
                    corrections_msg = []
                    if ecart_ht_corrige != 0:
                        corrections_msg.append("Correction HT: %+.4f€" % ecart_ht_corrige)
                    if ecart_tva_corrige != 0:
                        corrections_msg.append("Correction TVA: %+.2f€" % ecart_tva_corrige)
                    
                    new_invoice.narration = (new_invoice.narration or '') + "\n\n🔧 Corrections automatiques d'arrondis:\n" + "\n".join(corrections_msg)
                #**************************************************************

                #** Calcul des anomalies ***************************************
                obj._calculer_anomalies_facture(new_invoice)
                #**************************************************************

                #** Valider la facture si pas d'anomalie et pas de doublon ***
                if not new_invoice.is_anomalies_owork and not new_invoice.is_doublon_facture:
                    new_invoice.action_post()
                #**************************************************************


            # Envoi des mails pour chaque facture créée
            obj._envoyer_mails_factures(users_mail)
            
            # Traiter les factures non créées
            if factures_non_creees:
                obj._traiter_factures_non_creees(factures_non_creees, users_mail)
            
            obj.state='traite'
        return []


    def _calculer_anomalies_facture(self, invoice):
        """
        Calcule les anomalies d'une facture en comparant avec les données O'Work
        Utilise 4 décimales pour la comparaison HT pour plus de précision
        """
        if not invoice:
            return
        
        anomalies = []
        
        # Rechercher les lignes O'Work correspondant à cette facture
        for line in self.line_ids:
            if line.invoice_id and line.invoice_id.id == invoice.id:
                # Comparaison HT avec 4 décimales pour plus de précision
                if round(invoice.amount_untaxed, 4) != round(line.montantht, 4):
                    anomalies.append("Le montant HT de la facture O'Work (%s) est différent de cette facture Odoo (%s)" % (round(line.montantht, 2), round(invoice.amount_untaxed, 2)))
                if round(invoice.amount_tax, 2) != round(line.montanttva, 2):
                    anomalies.append("Le montant de la TVA de la facture O'Work (%s) est différent de cette facture Odoo (%s)" % (round(line.montanttva, 2), round(invoice.amount_tax, 2)))
                if round(invoice.amount_total, 2) != round(line.montanttc, 2):
                    anomalies.append("Le montant TTC de la facture O'Work (%s) est différent de cette facture Odoo (%s)" % (round(line.montanttc, 2), round(invoice.amount_total, 2)))
                break
        
        if len(anomalies) > 0:
            invoice.is_anomalies_owork = '\n'.join(anomalies)
        else:
            invoice.is_anomalies_owork = False


    def _corriger_ecart_montant_ht(self, invoice, montantht_owork):
        """
        Corrige automatiquement les petits écarts de montant HT (≤ 0.02€)
        en ajoutant une ligne d'ajustement basée sur la ligne avec le montant le plus élevé
        La ligne d'ajustement est placée à la fin de la facture
        L'écart est calculé pour corriger le HT sans impacter le TTC
        Retourne l'écart corrigé ou 0 si aucune correction
        """
        if not invoice or not montantht_owork:
            return 0
        
        # Calculer l'écart HT avec 4 décimales
        ecart_ht = round(montantht_owork - invoice.amount_untaxed, 4)

        # Si l'écart est inférieur ou égal à 0.02€ en valeur absolue
        if abs(ecart_ht) > 0 and abs(ecart_ht) <= 0.02:
            _logger.info("Correction automatique de l'écart de %.4f€ HT pour la facture %s" % (ecart_ht, invoice.name or invoice.id))
            
            # Trouver la ligne avec le montant le plus élevé
            ligne_max = None
            montant_max = 0
            sequence_max = 0
            
            for line in invoice.invoice_line_ids:
                montant_ligne = abs(line.price_subtotal)
                if montant_ligne > montant_max:
                    montant_max = montant_ligne
                    ligne_max = line
                # Récupérer la séquence maximale pour placer la ligne à la fin
                if line.sequence and line.sequence > sequence_max:
                    sequence_max = line.sequence
            
            if ligne_max:
                # Calculer le taux de TVA de la ligne de référence
                taux_tva = 0
                if ligne_max.tax_ids:
                    for tax in ligne_max.tax_ids:
                        taux_tva += tax.amount
                
                # Calculer l'écart HT ajusté pour que le TTC soit correct
                # Si on ajoute ecart_ht, la TVA sera de ecart_ht * (taux_tva/100)
                # Donc le TTC sera de ecart_ht * (1 + taux_tva/100)
                # On veut que cela compense exactement l'écart
                if taux_tva != 0:
                    # Ajuster l'écart pour tenir compte de la TVA
                    ecart_ht_ajuste = round(ecart_ht, 4)
                else:
                    ecart_ht_ajuste = round(ecart_ht, 4)
                
                # Préparer la description avec l'information sur l'écart
                description_ajustement = "Ajustement d'arrondi (écart de %.4f€ HT) - %s" % (ecart_ht_ajuste, ligne_max.name or '')
                
                # Créer une nouvelle ligne d'ajustement à la fin
                vals_ajustement = {
                    'move_id': invoice.id,
                    'product_id': ligne_max.product_id.id if ligne_max.product_id else False,
                    'name': description_ajustement,
                    'quantity': 1,
                    'product_uom_id': ligne_max.product_uom_id.id if ligne_max.product_uom_id else False,
                    'price_unit': ecart_ht_ajuste,
                    'tax_ids': [(6, 0, ligne_max.tax_ids.ids)] if ligne_max.tax_ids else False,
                    'is_section_analytique_id': ligne_max.is_section_analytique_id.id if ligne_max.is_section_analytique_id else False,
                    'is_document': ligne_max.is_document if ligne_max.is_document else False,
                    'sequence': sequence_max + 10,  # Placer à la fin avec un écart de 10
                }
                
                try:
                    self.env['account.move.line'].create(vals_ajustement)
                    _logger.info("Ligne d'ajustement créée avec succès à la fin de la facture %s (écart: %.4f€ HT)" % (invoice.name or invoice.id, ecart_ht_ajuste))
                    return ecart_ht_ajuste
                except Exception as e:
                    _logger.error("Erreur lors de la création de la ligne d'ajustement pour la facture %s: %s" % (invoice.name or invoice.id, str(e)))
        
        return 0


    def _corriger_ecart_montant_tva(self, invoice, montanttva_owork):
        """
        Corrige automatiquement les petits écarts de montant de TVA (≤ 0.02€)
        en ajustant directement les lignes de taxes de la facture
        Cette méthode doit être appelée APRÈS _corriger_ecart_montant_ht
        Retourne l'écart corrigé ou 0 si aucune correction
        """
        if not invoice or not montanttva_owork:
            return 0
        
        # Forcer le recalcul des montants après l'ajout de la ligne d'ajustement HT
        # Invalider le cache pour forcer le recalcul
        invoice.invalidate_recordset(['amount_untaxed', 'amount_tax', 'amount_total'])
        
        # Calculer l'écart TVA avec 2 décimales (montant affiché)
        ecart_tva = round(montanttva_owork - invoice.amount_tax, 2)
        
        # Si l'écart est inférieur ou égal à 0.02€ en valeur absolue
        if abs(ecart_tva) > 0 and abs(ecart_tva) <= 0.02:
            _logger.info("Correction automatique de l'écart de %.2f€ TVA pour la facture %s" % (ecart_tva, invoice.name or invoice.id))
            
            # Trouver la ligne de taxe avec le montant le plus élevé
            tax_lines = invoice.line_ids.filtered(lambda line: line.display_type == 'tax')
            
            if tax_lines:
                # Prendre la première ligne de taxe (ou celle avec le montant le plus élevé)
                ligne_tax_max = None
                montant_max = 0
                
                for tax_line in tax_lines:
                    montant_tax = abs(tax_line.amount_currency)
                    if montant_tax > montant_max:
                        montant_max = montant_tax
                        ligne_tax_max = tax_line
                
                if ligne_tax_max:
                    # Déterminer le signe selon le type de facture
                    sign = -1 if invoice.is_inbound() else 1
                    
                    # Ajuster le montant de la ligne de taxe
                    try:
                        ligne_tax_max.with_context(check_move_validity=False).write({
                            'amount_currency': ligne_tax_max.amount_currency + (ecart_tva * sign)
                        })
                        _logger.info("Ligne de taxe ajustée avec succès pour la facture %s (écart: %.2f€ TVA)" % (invoice.name or invoice.id, ecart_tva))
                        
                        # Recalculer les totaux après ajustement
                        invoice._compute_amount()
                        
                        return ecart_tva
                        
                    except Exception as e:
                        _logger.error("Erreur lors de l'ajustement de la ligne de taxe pour la facture %s: %s" % (invoice.name or invoice.id, str(e)))
                else:
                    _logger.warning("Aucune ligne de taxe trouvée pour ajuster la TVA de la facture %s" % (invoice.name or invoice.id))
            else:
                _logger.warning("Aucune ligne de taxe trouvée pour la facture %s" % (invoice.name or invoice.id))
        
        return 0


    def _envoyer_mails_factures(self, users_mail):
        """Envoie un mail pour chaque facture créée avec indication des anomalies"""
        for obj in self:
            if not users_mail:
                _logger.warning("Aucun destinataire trouvé pour l'envoi des mails")
                return
            
            # Récupération des emails des destinataires
            emails = []
            for user in users_mail:
                if user.get('email'):
                    emails.append(user['email'])
            
            if not emails:
                _logger.warning("Aucune adresse email valide trouvée dans la liste de diffusion")
                return
            
            # Envoi d'un mail pour chaque facture
            factures_traitees = {}
            for line in obj.line_ids:
                if line.invoice_id and line.numfac not in factures_traitees:
                    factures_traitees[line.numfac] = line.invoice_id
            
            for numfac, invoice in factures_traitees.items():
                # Vérifier s'il y a des anomalies
                has_anomalie = False
                anomalies_details = []
                
                # Vérifier les anomalies sur les lignes
                for line in obj.line_ids:
                    if line.numfac == numfac and line.anomalies:
                        has_anomalie = True
                        anomalies_details.append("Ligne %s: %s" % (line.id, line.anomalies))
                
                # Vérifier les anomalies sur la facture elle-même
                if invoice.is_anomalies_owork:
                    has_anomalie = True
                    anomalies_details.append("Facture: %s" % invoice.is_anomalies_owork)
                
                # Vérifier s'il y a un doublon
                if invoice.is_doublon_facture:
                    has_anomalie = True
                    anomalies_details.append("Doublon: %s" % invoice.is_doublon_facture)
                
                # Vérifier s'il y a eu des corrections automatiques
                has_corrections = False
                corrections_details = []
                if invoice.narration and "🔧 Corrections automatiques" in invoice.narration:
                    has_corrections = True
                    # Extraire les corrections depuis la narration
                    narration_lines = invoice.narration.split('\n')
                    for line in narration_lines:
                        if 'Correction' in line:
                            corrections_details.append(line.strip())
                
                # Définir le sujet avec icône selon le statut
                if invoice.is_doublon_facture:
                    sujet = "🔴 Facture O'Work %s - DOUBLON DÉTECTÉ" % numfac
                elif has_anomalie:
                    sujet = "🟠 Facture O'Work %s - Anomalies détectées" % numfac
                elif has_corrections:
                    sujet = "🟠 Facture O'Work %s - Corrections automatiques appliquées" % numfac
                else:
                    sujet = "✅ Facture O'Work %s - Import OK" % numfac
                
                # Construire le corps du mail
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                invoice_url = "%s/web#id=%s&model=account.move&view_type=form" % (base_url, invoice.id)
                
                body_html = """
                    <p>Bonjour,</p>
                    <p>La facture <a href="%s">%s</a> a été importée depuis O'Work.</p>
                    <p><strong>Fournisseur:</strong> %s</p>
                    <p><strong>Date:</strong> %s</p>
                    <p><strong>Montant HT:</strong> %.2f €</p>
                    <p><strong>Montant TTC:</strong> %.2f €</p>
                """ % (
                    invoice_url,
                    numfac,
                    invoice.partner_id.name,
                    invoice.invoice_date,
                    invoice.amount_untaxed,
                    invoice.amount_total
                )
                
                # Ajouter les corrections automatiques si présentes
                if has_corrections:
                    body_html += """
                        <p><strong style="color: orange;">🟠 Corrections automatiques d'arrondis appliquées:</strong></p>
                        <ul>
                    """
                    for correction in corrections_details:
                        body_html += "<li>%s</li>" % correction
                    body_html += "</ul>"
                
                if has_anomalie:
                    body_html += """
                        <p><strong style="color: red;">🟠 Anomalies détectées:</strong></p>
                        <ul>
                    """
                    for anomalie in anomalies_details:
                        body_html += "<li>%s</li>" % anomalie
                    body_html += "</ul>"
                
                if not has_anomalie and not has_corrections:
                    body_html += """
                        <p><strong style="color: green;">✅ Aucune anomalie détectée</strong></p>
                    """
                # Préparer le message pour le chatter
                chatter_body = "<p><strong>%s</strong></p>" % sujet
                
                # Ajouter les destinataires dans le message
                if users_mail:
                    destinataires = []
                    for user in users_mail:
                        name = user.get('name', 'Inconnu')
                        email = user.get('email', '')
                        if email:
                            destinataires.append("%s (%s)" % (name, email))
                        else:
                            destinataires.append(name)
                    if destinataires:
                        chatter_body += "<p><em>Notification envoyée à: %s</em></p>" % ', '.join(destinataires)
                
                # Ajouter les détails des corrections et anomalies dans le chatter
                if has_corrections or has_anomalie:
                    chatter_body += body_html
                
                # Poster le message dans le chatter de la facture
                try:
                    invoice.message_post(
                        body=chatter_body,
                        subject=sujet,
                        message_type='comment',
                        subtype_xmlid='mail.mt_comment',
                    )
                    _logger.info("Message posté dans le chatter de la facture %s" % numfac)
                except Exception as e:
                    _logger.error("Erreur lors du post du message pour la facture %s: %s" % (numfac, str(e)))
                
                # Envoi du mail aux destinataires
                mail_values = {
                    'subject': sujet,
                    'body_html': body_html,
                    'email_to': ','.join(emails),
                    'email_from': self.env.user.email or 'noreply@plastigray.com',
                    'auto_delete': False,
                }
                
                try:
                    mail = self.env['mail.mail'].create(mail_values)
                    mail.send()
                    _logger.info("Mail envoyé pour la facture %s à %s" % (numfac, ','.join(emails)))
                except Exception as e:
                    _logger.error("Erreur lors de l'envoi du mail pour la facture %s: %s" % (numfac, str(e)))


    def _traiter_factures_non_creees(self, factures_non_creees, users_mail):
        """Traite les factures qui n'ont pas pu être créées"""
        for obj in self:
            if not factures_non_creees:
                return
            
            # Récupération des emails des destinataires
            emails = []
            if users_mail:
                for user in users_mail:
                    if user.get('email'):
                        emails.append(user['email'])
            
            # Construire le message pour le chatter de l'import
            chatter_body = "<p><strong>🟠 Factures O'Work non créées</strong></p>"
            chatter_body += "<p>Les factures suivantes n'ont pas pu être importées :</p><ul>"
            
            for numfac, raison in factures_non_creees.items():
                chatter_body += "<li><strong>%s</strong> : %s</li>" % (numfac, raison)
            
            chatter_body += "</ul>"
            
            # Ajouter les destinataires dans le message
            if users_mail:
                destinataires = []
                for user in users_mail:
                    name = user.get('name', 'Inconnu')
                    email = user.get('email', '')
                    if email:
                        destinataires.append("%s (%s)" % (name, email))
                    else:
                        destinataires.append(name)
                if destinataires:
                    chatter_body += "<p><em>Notification envoyée à: %s</em></p>" % ', '.join(destinataires)
            
            # Poster le message dans le chatter de l'import O'Work
            try:
                obj.message_post(
                    body=chatter_body,
                    subject="🟠 Factures O'Work non créées",
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                )
                _logger.info("Message posté dans le chatter de l'import %s pour les factures non créées" % obj.name)
            except Exception as e:
                _logger.error("Erreur lors du post du message pour l'import %s: %s" % (obj.name, str(e)))
            
            # Envoyer un mail si des destinataires sont disponibles
            if emails:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                import_url = "%s/web#id=%s&model=is.import.facture.owork&view_type=form" % (base_url, obj.id)
                
                body_html = """
                    <p>Bonjour,</p>
                    <p>Lors de l'import O'Work <a href="%s">%s</a>, certaines factures n'ont pas pu être créées :</p>
                    <ul>
                """ % (import_url, obj.name)
                
                for numfac, raison in factures_non_creees.items():
                    body_html += "<li><strong>Facture %s</strong> : %s</li>" % (numfac, raison)
                
                
                mail_values = {
                    'subject': "🟠 Import O'Work %s - Factures non créées" % obj.name,
                    'body_html': body_html,
                    'email_to': ','.join(emails),
                    'email_from': self.env.user.email or 'noreply@plastigray.com',
                    'auto_delete': False,
                }
                
                try:
                    mail = self.env['mail.mail'].create(mail_values)
                    mail.send()
                    _logger.info("Mail envoyé pour les factures non créées de l'import %s à %s" % (obj.name, ','.join(emails)))
                except Exception as e:
                    _logger.error("Erreur lors de l'envoi du mail pour l'import %s: %s" % (obj.name, str(e)))

   
    def voir_les_factures(self):
        for obj in self:
            ids=[]
            for invoice in obj.invoice_ids:
                ids.append(invoice.id)
            tree_view_id=self.env.ref('is_plastigray16.is_view_invoice_tree')
            res= {
                'name': obj.name,
                'view_mode': 'tree,form',
                'res_model': 'account.move',
                'views': [[tree_view_id.id, "list"], [False, "form"]],
                'type': 'ir.actions.act_window',
                'context': {'default_move_type':'in_invoice', 'move_type':'in_invoice'},
                'domain': [('move_type','=','in_invoice'),('id','in',ids)],
            }
            return res


    def exporter_receptions_owork_action(self):
        name = "exporter-receptions-owork"
        cdes = self.env['is.commande.externe'].search([('name','=',name)])
        if len(cdes)==0:
            raise ValidationError("Commande externe '%s' non trouvée !"%name)
        for cde in cdes:
            p = Popen(cde.commande, shell=True, stdout=PIPE, stderr=PIPE)
            stdout, stderr = p.communicate()
            _logger.info("%s => %s"%(cde.commande,stdout))
            if stderr:
                raise ValidationError("Erreur dans commande externe '%s' => %s"%(cde.commande,stderr))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': "Exportation vers O'Work éffectutée",
                #'message': "Exportation vers O'Work éffectutée",
                'type': 'success',
                'sticky': False,
            }
        }


class is_import_facture_owork_line(models.Model):
    _name = "is.import.facture.owork.line"
    _description = "Lignes importation factures O'Work"
    _rec_name = 'id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    active         = fields.Boolean("Actif", default=True, tracking=True)
    import_id      = fields.Many2one('is.import.facture.owork', "Import O'Work", required=True, ondelete='cascade', tracking=True)
    codeetab       = fields.Char("Code etab", tracking=True)
    codefour       = fields.Char("Code Four fact", tracking=True)
    codefourrcp    = fields.Char("Code Four Rcp", tracking=True)
    codeadrfour    = fields.Char("Code adr four", tracking=True)
    numbl          = fields.Char("Num BL", tracking=True)
    numrecept      = fields.Char("Num rcp", tracking=True)
    daterecpt      = fields.Date("Date rcp", tracking=True)
    numcde         = fields.Char("Num Cde", tracking=True)
    num_chantier_rcp  = fields.Char("N°Chantier Rcp", tracking=True)
    num_chantier_fact = fields.Char("N°Chantier Fact", tracking=True)
    sec_ana_origine = fields.Char("Section Rcp", tracking=True)
    sec_ana_fact    = fields.Char("Section Fact", tracking=True)
    cpte_origine    = fields.Char("Compte Rcp", tracking=True)
    cpte_fact       = fields.Char("Compte Fact", tracking=True)
    article        = fields.Char("Code Article", tracking=True)
    descriparticle = fields.Char("Description article", tracking=True)
    qterestefac    = fields.Float("Qt reste fac", digits=(12, 6), tracking=True)
    prixorigine    = fields.Float("Prix Origine", digits=(12, 6), tracking=True)
    total          = fields.Float("Total ligne HT", digits=(12, 4), tracking=True)
    codetvaorigine = fields.Char("Code TVA Origine", tracking=True)
    codetvafact    = fields.Char("Code TVA Fac", tracking=True)
    prixfact       = fields.Float("Prix Fac", digits=(12, 6), tracking=True)
    qtefact        = fields.Float("Qt fac"  , digits=(12, 6), tracking=True)
    datefact       = fields.Date("Date Fac", tracking=True)
    numfac         = fields.Char("Num Fac", tracking=True)
    montantht      = fields.Float("Montant HT Facture", tracking=True)
    montanttva     = fields.Float("Montant TVA Facture", tracking=True)
    montanttc      = fields.Float("Montant TTC Facture", tracking=True)
    numidodoo      = fields.Char("Id Odoo", tracking=True)
    id_owork       = fields.Integer("id O'Work", tracking=True)
    totalfacture   = fields.Float("Total ligne facture", tracking=True)
    litige         = fields.Char("Litige", tracking=True)
    picking_id     = fields.Many2one('stock.picking', "Réception", tracking=True, copy=False)
    stock_move_id  = fields.Many2one('stock.move', "Ligne de réception", tracking=True, copy=False, ondelete='set null')
    partner_id     = fields.Many2one('res.partner', "Fournisseur", tracking=True, copy=False)
    product_id     = fields.Many2one('product.product', "Article", tracking=True, copy=False)
    tax_id         = fields.Many2one('account.tax', "TVA", tracking=True, copy=False)
    invoice_id     = fields.Many2one('account.move', "Facture", tracking=True, copy=False)
    fichier        = fields.Char("Fichier", tracking=True)
    anomalies      = fields.Text("Anomalies", tracking=True, copy=False, compute='actualiser_ligne', store=True, readonly=True)
 

    @api.depends('numrecept','codefour','codefourrcp','numidodoo','codetvafact','prixorigine','prixfact','qtefact','totalfacture','total','montantht','article')
    def actualiser_ligne(self):
        cr=self._cr
        for obj in self:
            anomalies=[]
            #** Recherche article *********************************************
            if obj.article:
                domain=[
                    ('is_code'    ,'=', obj.article),
                ]
                products = self.env['product.product'].search(domain)
                product_id = False
                for product in products:
                    product_id = product.id
                obj.product_id = product_id
                if not product_id:
                    anomalies.append("Code article '%s' non trouvé dans Odoo"%(obj.article))
            #******************************************************************

            #** Recherche fournisseur *****************************************
            partner_id = False
            codefour = obj.codefour or obj.codefourrcp
            if codefour:
                is_code = codefour.lstrip("0")
                domain=[
                    ('is_code'    ,'=', is_code),
                    ('is_adr_code','=', '0')
                ]
                partners = self.env['res.partner'].search(domain)
                for partner in partners:
                    partner_id = partner.id
            obj.partner_id = partner_id
            #******************************************************************

            numrecept = obj.numrecept or ''
            if numrecept!='':
                #** stock_move_id, product_id et picking_id ************************
                stock_move_id = product_id = picking_id = False
                t = (obj.numidodoo or '').split('-')
                stock_move_id = obj.numidodoo
                if len(t)==3:
                    stock_move_id = t[1]
                try:
                    stock_move_id = int(stock_move_id)
                except ValueError:
                    anomalies.append("stock_move_id non valide (numidodoo=%s et stock_move_id=%s)" % (obj.numidodoo, stock_move_id))
                    stock_move_id=0
                if not stock_move_id:
                    anomalies.append("stock_move_id non trouvé (numidodoo=%s) "%(obj.numidodoo))
                if stock_move_id:
                    SQL="""
                        select sm.id, sm.picking_id, sm.product_id, sp.partner_id
                        from stock_move sm join stock_picking sp on sm.picking_id=sp.id
                        where sm.id=%s
                    """
                    cr.execute(SQL,[stock_move_id])
                    rows = cr.dictfetchall()
                    stock_move_id = False
                    for row in rows:
                        stock_move_id = row['id']
                        picking_id = row['picking_id']
                        product_id = row['product_id']
                        if not partner_id:
                            partner_id = row['partner_id']
                    if not stock_move_id:
                        anomalies.append("stock_move_id non trouvé (stock_move_id=%s) "%(obj.numidodoo))
                    if not picking_id:
                        anomalies.append("picking_id non trouvé (stock_move_id=%s) "%(stock_move_id))
                    if not product_id:
                        anomalies.append("product_id non trouvé (stock_move_id=%s) "%(stock_move_id))
                    if not partner_id:
                        anomalies.append("partner_id non trouvé (stock_move_id=%s) "%(stock_move_id))
                obj.stock_move_id = stock_move_id
                obj.picking_id = picking_id
                obj.product_id = product_id
                obj.partner_id = partner_id
                #*******************************************************************

            if not partner_id:
                anomalies.append("Fournisseur à facturer non trouvé (codefour=%s)"%(codefour))



            #** Recherche TVA **************************************************
            if obj.codetvafact:
                tax_id = False
                SQL="""
                    select id
                    from account_tax
                    where description=%s
                """
                cr.execute(SQL,[obj.codetvafact])
                rows = cr.dictfetchall()
                for row in rows:
                    tax_id = row['id']
                if not tax_id:
                    anomalies.append("TVA '%s' non trouvée"%(obj.codetvafact))
                obj.tax_id = tax_id
            #******************************************************************

            # #** Comparatif prix d'origine et prix facturé *********************
            # prixorigine = round(obj.prixorigine,6)
            # prixfact    = round(obj.prixfact,6)
            # if prixorigine>0 and prixfact>0 and prixorigine!=prixfact:
            #     anomalies.append("Le prix d'origine '%s' est différent du prix facturé '%s'"%(prixorigine,prixfact))
            # #******************************************************************

            #** Vérification total ligne facturé ******************************
            prixfact      = obj.prixfact
            qtefact       = obj.qtefact
            totalfacture  = obj.totalfacture
            total_calcule = round(prixfact*qtefact,2)
            if total_calcule != totalfacture:
                anomalies.append("Le total facturé %s est différent de %s x %s (%s)"%(totalfacture,prixfact,qtefact,total_calcule))
            #******************************************************************

            #** Vérfication que total facturé correspond au total des lignes **
            total_calcule = 0
            for line in obj.import_id.line_ids:
                if line.numfac == obj.numfac:
                    if obj._origin.id == line.id:
                        total_calcule+=obj.totalfacture
                    else:
                        total_calcule+=line.totalfacture
            total_calcule = round(total_calcule,4)
            if total_calcule!=obj.montantht:
                anomalies.append("Le total des lignes %s est différent du total de la facture %s"%(total_calcule,obj.montantht))
            #******************************************************************

            #** Anomalies *****************************************************
            if len(anomalies)>0:
                anomalies = '\n'.join(anomalies)
            else:
                anomalies=False
            obj.anomalies = anomalies
            #******************************************************************





