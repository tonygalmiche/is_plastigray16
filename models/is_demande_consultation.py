# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class IsDemandeConsultation(models.Model):
    _name = 'is.demande.consultation'
    _description = "Demande de consultation"
    _inherit = ['mail.thread']
    _order = 'name desc'

    @api.depends('type_consultation')
    def _compute_prefix(self):
        """Calcule le préfixe en fonction du type de consultation"""
        for obj in self:
            prefixes = {
                'dc_mat': 'DC-MAT',
                'dc_comp': 'DC-COMP',
                'dc_emb': 'DC-EMB',
                'dc_port': 'DC-PORT',
                'dc_chine': 'DC-CHINE',
            }
            obj.prefix = prefixes.get(obj.type_consultation, '')

    @api.depends('line_ids', 'line_ids.fournisseur_ids.date_envoi_mail', 'state', 'type_consultation', 
                 'demandeur_id', 'validateur_technique_id', 'acheteur_id')
    def _compute_vsb(self):
        """Calcule la visibilité des boutons de workflow"""
        uid = self._uid
        for obj in self:
            # Bouton vers brouillon
            vsb = False
            if obj.state != 'brouillon' and (uid == obj.validateur_technique_id.id or uid == obj.acheteur_id.id):
                vsb = True
            # Pour DC-EMB, DC-COMP, DC-PORT et DC-CHINE : le demandeur peut aussi revenir en brouillon depuis transmis_achat
            if obj.state == 'transmis_achat' and obj.type_consultation in ['dc_emb', 'dc_comp', 'dc_port', 'dc_chine'] and uid == obj.demandeur_id.id:
                vsb = True
            obj.vers_brouillon_vsb = vsb
            
            # Bouton vers validation technique (pas pour DC-EMB, DC-COMP, DC-PORT et DC-CHINE)
            vsb = False
            if obj.state == 'brouillon' and uid == obj.demandeur_id.id and obj.type_consultation not in ['dc_emb', 'dc_comp', 'dc_port', 'dc_chine']:
                vsb = True
            obj.vers_validation_technique_vsb = vsb
            
            # Bouton vers transmis achat
            vsb = False
            if obj.state == 'validation_technique' and uid == obj.validateur_technique_id.id:
                vsb = True
            # Pour DC-EMB, DC-COMP, DC-PORT et DC-CHINE : passage direct de brouillon à transmis_achat par le demandeur
            if obj.state == 'brouillon' and obj.type_consultation in ['dc_emb', 'dc_comp', 'dc_port', 'dc_chine'] and uid == obj.demandeur_id.id:
                vsb = True
            obj.vers_transmis_achat_vsb = vsb
            
            # Bouton vers soldé
            vsb = False
            if obj.state == 'consultation_en_cours' and uid == obj.acheteur_id.id:
                vsb = True
            obj.vers_solde_vsb = vsb
            
            # Bouton vers annulé
            vsb = False
            if obj.state == 'brouillon' and uid == obj.demandeur_id.id:
                vsb = True
            if obj.state == 'validation_technique' and uid == obj.validateur_technique_id.id:
                vsb = True
            if obj.state in ['transmis_achat', 'consultation_en_cours'] and uid == obj.acheteur_id.id:
                vsb = True
            # Pour DC-EMB, DC-COMP, DC-PORT et DC-CHINE : le demandeur peut aussi annuler depuis transmis_achat
            if obj.state == 'transmis_achat' and obj.type_consultation in ['dc_emb', 'dc_comp', 'dc_port', 'dc_chine'] and uid == obj.demandeur_id.id:
                vsb = True
            obj.vers_annule_vsb = vsb
            
            # Bouton envoi consultation (visible si transmis_achat/consultation_en_cours et au moins un fournisseur sans mail envoyé)
            vsb = False
            if obj.state in ['transmis_achat', 'consultation_en_cours']:
                # Vérifier s'il reste des fournisseurs sans date_envoi_mail
                for line in obj.line_ids:
                    for fournisseur in line.fournisseur_ids:
                        if not fournisseur.date_envoi_mail:
                            vsb = True
                            break
                    if vsb:
                        break
            obj.envoi_consultation_vsb = vsb

    # Champs principaux
    name = fields.Char("N° de consultation", readonly=True, tracking=True, copy=False)
    active = fields.Boolean("Actif", default=True, tracking=True)
    type_consultation = fields.Selection([
        ('dc_mat', 'Matières et colorants (DC-MAT)'),
        ('dc_comp', 'Composant (DC-COMP)'),
        ('dc_emb', 'Emballages (DC-EMB)'),
        ('dc_port', 'Transport (DC-PORT)'),
        ('dc_chine', 'Import Chine (DC-CHINE)'),
    ], string="Type de consultation", required=True, default='dc_mat', tracking=True)
    prefix = fields.Char("Préfixe", compute='_compute_prefix', store=False)
    
    # Utilisateurs
    demandeur_id = fields.Many2one('res.users', 'Demandeur', required=True, tracking=True, 
                                   default=lambda self: self.env.uid, copy=False)
    date_creation = fields.Date("Date de création", required=True, tracking=True, copy=False,
                                default=lambda *a: fields.datetime.now())
    validateur_technique_id = fields.Many2one('res.users', 'Validation technique', tracking=True,
                                              default=lambda self: self._default_validateur_technique())
    acheteur_id = fields.Many2one('res.users', 'Acheteur', tracking=True, required=True)
    
    # Références
    num_ao = fields.Char("N° AO", tracking=True, help="Numéro d'affaire/ordre")
    mold_id = fields.Many2one('is.mold', 'N° moule', tracking=True)
    dossierf_id = fields.Many2one('is.dossierf', 'N° de dossier F', tracking=True)
    
    # Client / Prospect
    client_id = fields.Many2one('res.partner', 'Client', tracking=True, domain=[("is_company","=",True), ("customer","=",True)])
    prospect = fields.Char("Prospect", tracking=True)
    confidentialite = fields.Selection([
        ('oui', 'Oui'),
        ('non', 'Non'),
    ], string="Confidentialité sur client", tracking=True, default='non')
    
    # Secteur
    secteur_application = fields.Char("Secteur / Application", tracking=True)
    
    # Dates
    date_retour_consultation = fields.Date("Date souhaitée pour le retour de consultation", tracking=True,
                                           help="Complétée par le demandeur")
    date_reponse_souhaitee = fields.Date("Date de réponse souhaitée", tracking=True,
                                         help="Complétée par l'acheteur")
    date_sop = fields.Date("SOP", tracking=True, help="Start of Production")
    
    # Autres champs
    duree_vie = fields.Integer("Durée de vie (en années)", tracking=True)
    commentaire = fields.Text("Commentaire", tracking=True)
    
    # Champs spécifiques DC-PORT (Transport)
    adresse_enlevement_id = fields.Many2one('res.partner', "Adresse d'enlèvement", tracking=True,
                                            domain=[('is_company', '=', True)],
                                            help="Adresse d'enlèvement si existante")
    adresse_livraison_id = fields.Many2one('res.partner', "Adresse de livraison", tracking=True,
                                           domain=[('is_company', '=', True)],
                                           help="Adresse de livraison si existante")
    date_dms = fields.Date("Date DMS", tracking=True, help="Date de mise à disposition")
    incoterm_id = fields.Many2one('account.incoterms', "Incoterm", tracking=True,
                                  help="DAP à privilégier")
    lieu = fields.Char("Lieu", tracking=True)
    
    # État
    state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('validation_technique', 'Validation technique'),
        ('transmis_achat', 'Transmis achat'),
        ('consultation_en_cours', 'Consultation en cours'),
        ('solde', 'Soldé'),
        ('annule', 'Annulé'),
    ], string="État", default='brouillon', tracking=True)
    
    # Lignes
    line_ids = fields.One2many('is.demande.consultation.line', 'demande_id', string="Lignes", copy=True)
    
    # Champs techniques pour visibilité des boutons
    vers_brouillon_vsb = fields.Boolean('Champ technique vers_brouillon_vsb', compute='_compute_vsb', store=False)
    vers_validation_technique_vsb = fields.Boolean('Champ technique vers_validation_technique_vsb', compute='_compute_vsb', store=False)
    vers_transmis_achat_vsb = fields.Boolean('Champ technique vers_transmis_achat_vsb', compute='_compute_vsb', store=False)
    vers_solde_vsb = fields.Boolean('Champ technique vers_solde_vsb', compute='_compute_vsb', store=False)
    vers_annule_vsb = fields.Boolean('Champ technique vers_annule_vsb', compute='_compute_vsb', store=False)
    envoi_consultation_vsb = fields.Boolean('Champ technique envoi_consultation_vsb', compute='_compute_vsb', store=False)

    def _default_validateur_technique(self):
        """Récupère le validateur technique par défaut depuis la société"""
        company = self.env.company
        if company.is_validateur_technique_dc_id:
            return company.is_validateur_technique_dc_id.id
        return False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Génère le numéro de séquence en fonction du type de consultation
            type_consultation = vals.get('type_consultation', 'dc_mat')
            sequence_code = f'is.demande.consultation.{type_consultation}'
            vals['name'] = self.env['ir.sequence'].next_by_code(sequence_code)
        return super().create(vals_list)

    @api.onchange('type_consultation')
    def _onchange_type_consultation(self):
        """Définit les valeurs par défaut selon le type de consultation"""
        for obj in self:
            if obj.type_consultation == 'dc_chine':
                # Valeurs par défaut pour DC-CHINE : Incoterm FOB et Lieu SHENZHEN
                if not obj.lieu:
                    obj.lieu = 'SHENZHEN'
                if not obj.incoterm_id:
                    # Chercher l'incoterm FOB
                    fob = self.env['account.incoterms'].search([('code', '=', 'FOB')], limit=1)
                    if fob:
                        obj.incoterm_id = fob.id

    def vers_brouillon_action(self):
        """Retour à l'état brouillon"""
        for obj in self:
            obj.sudo().state = 'brouillon'

    def vers_validation_technique_action(self):
        """Passage à l'état validation technique"""
        for obj in self:
            subject = f'[{obj.name}] Validation technique'
            email_to = obj.validateur_technique_id.email
            user = self.env['res.users'].browse(self._uid)
            email_from = user.email
            nom = user.name
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = f'{base_url}/web#id={obj.id}&view_type=form&model=is.demande.consultation'
            body_html = f"""
                <p>Bonjour,</p>
                <p>{nom} vient de passer la demande de consultation <a href='{url}'>{obj.name}</a> à l'état 'Validation technique'.</p>
                <p>Merci d'en prendre connaissance.</p>
            """
            self.envoi_mail(email_from, email_to, subject, body_html)
            obj.state = 'validation_technique'

    def vers_transmis_achat_action(self):
        """Passage à l'état transmis achat"""
        for obj in self:
            subject = f'[{obj.name}] Transmis achat'
            email_to = obj.acheteur_id.email
            user = self.env['res.users'].browse(self._uid)
            email_from = user.email
            nom = user.name
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = f'{base_url}/web#id={obj.id}&view_type=form&model=is.demande.consultation'
            body_html = f"""
                <p>Bonjour,</p>
                <p>{nom} vient de passer la demande de consultation <a href='{url}'>{obj.name}</a> à l'état 'Transmis achat'.</p>
                <p>Merci d'en prendre connaissance.</p>
            """
            self.envoi_mail(email_from, email_to, subject, body_html)
            obj.state = 'transmis_achat'

    def vers_solde_action(self):
        """Passage à l'état soldé avec envoi mail au demandeur"""
        for obj in self:
            # Vérifications avant de solder
            if not obj.line_ids:
                raise ValidationError("Impossible de solder : aucune ligne dans la consultation.")
            
            erreurs = []
            for line in obj.line_ids:
                # Identifiant de ligne selon le type de consultation
                if obj.type_consultation == 'dc_emb':
                    ligne_nom = line.type_produit or f"Ligne {line.sequence or ''}"
                if obj.type_consultation == 'dc_comp':
                    ligne_nom = line.type_produit or f"Ligne {line.sequence or ''}"
                if obj.type_consultation == 'dc_port':
                    ligne_nom = line.colisage or f"Ligne {line.sequence or ''}"
                if obj.type_consultation == 'dc_chine':
                    ligne_nom = (line.mold_id.name if line.mold_id else '') or f"Ligne {line.sequence or ''}"
                if obj.type_consultation == 'dc_mat':
                    ligne_nom = line.designation or f"Ligne {line.sequence or ''}"
                
                # Vérifier qu'il y a un fournisseur retenu
                fournisseur_retenu = None
                for f in line.fournisseur_ids:
                    if f.fournisseur_retenu:
                        fournisseur_retenu = f
                        break
                
                if not fournisseur_retenu:
                    erreurs.append(f"Ligne '{ligne_nom}' : aucun fournisseur retenu")
                else:
                    if not fournisseur_retenu.reponse_prix:
                        erreurs.append(f"Ligne '{ligne_nom}' : prix manquant pour le fournisseur retenu")
                    if not fournisseur_retenu.delai:
                        erreurs.append(f"Ligne '{ligne_nom}' : délai manquant pour le fournisseur retenu")
            
            if erreurs:
                raise ValidationError("Impossible de solder :\n- " + "\n- ".join(erreurs))
            
            # Construire le tableau HTML des fournisseurs retenus (utilisé pour mail et chatter)
            if obj.type_consultation == 'dc_emb':
                # Tableau pour DC-EMB (Emballages)
                tableau_html = """
                    <table style="border-collapse: collapse; width: 100%; margin: 10px 0;">
                        <tr style="background-color: #f0f0f0;">
                            <th style="border: 1px solid #ccc; padding: 5px;">Type de produit</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Matière</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Dim. int.</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Dim. ext.</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Qté annuelle</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Lot</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Fournisseur retenu</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Prix</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Délai (jours)</th>
                        </tr>
                """
                for line in obj.line_ids:
                    fournisseur_retenu = None
                    for f in line.fournisseur_ids:
                        if f.fournisseur_retenu:
                            fournisseur_retenu = f
                            break
                    
                    if fournisseur_retenu:
                        nom_fournisseur = ""
                        if fournisseur_retenu.fournisseur_id:
                            nom_fournisseur = fournisseur_retenu.fournisseur_id.name
                        elif fournisseur_retenu.fournisseur_hors_panel:
                            nom_fournisseur = fournisseur_retenu.fournisseur_hors_panel
                        
                        tableau_html += f"""
                            <tr>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.type_produit or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.matiere or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.dimensions_int or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.dimensions_ext or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.quantite_annuelle}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.lot or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{nom_fournisseur}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{fournisseur_retenu.reponse_prix}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{fournisseur_retenu.delai}</td>
                            </tr>
                        """
                tableau_html += "</table>"
            if obj.type_consultation == 'dc_comp':
                # Tableau pour DC-COMP (Composants)
                tableau_html = """
                    <table style="border-collapse: collapse; width: 100%; margin: 10px 0;">
                        <tr style="background-color: #f0f0f0;">
                            <th style="border: 1px solid #ccc; padding: 5px;">Type de produit</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Matière</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Dimension</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Environnement</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Qté annuelle</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Standard</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Lot</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Fournisseur retenu</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Prix</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Délai (jours)</th>
                        </tr>
                """
                for line in obj.line_ids:
                    fournisseur_retenu = None
                    for f in line.fournisseur_ids:
                        if f.fournisseur_retenu:
                            fournisseur_retenu = f
                            break
                    
                    if fournisseur_retenu:
                        nom_fournisseur = ""
                        if fournisseur_retenu.fournisseur_id:
                            nom_fournisseur = fournisseur_retenu.fournisseur_id.name
                        elif fournisseur_retenu.fournisseur_hors_panel:
                            nom_fournisseur = fournisseur_retenu.fournisseur_hors_panel
                        
                        standard_txt = dict(line._fields['standard'].selection).get(line.standard, '') if line.standard else ''
                        tableau_html += f"""
                            <tr>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.type_produit or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.matiere or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.dimension or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.environnement or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.quantite_annuelle}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{standard_txt}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.lot or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{nom_fournisseur}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{fournisseur_retenu.reponse_prix}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{fournisseur_retenu.delai}</td>
                            </tr>
                        """
                tableau_html += "</table>"
            if obj.type_consultation == 'dc_port':
                # Tableau pour DC-PORT (Transport)
                tableau_html = """
                    <table style="border-collapse: collapse; width: 100%; margin: 10px 0;">
                        <tr style="background-color: #f0f0f0;">
                            <th style="border: 1px solid #ccc; padding: 5px;">Colisage</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Poids</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Fréquence</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Fournisseur retenu</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Prix</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Délai (jours)</th>
                        </tr>
                """
                for line in obj.line_ids:
                    fournisseur_retenu = None
                    for f in line.fournisseur_ids:
                        if f.fournisseur_retenu:
                            fournisseur_retenu = f
                            break
                    
                    if fournisseur_retenu:
                        nom_fournisseur = ""
                        if fournisseur_retenu.fournisseur_id:
                            nom_fournisseur = fournisseur_retenu.fournisseur_id.name
                        elif fournisseur_retenu.fournisseur_hors_panel:
                            nom_fournisseur = fournisseur_retenu.fournisseur_hors_panel
                        
                        tableau_html += f"""
                            <tr>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.colisage or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.poids or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.frequence or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{nom_fournisseur}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{fournisseur_retenu.reponse_prix}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{fournisseur_retenu.delai}</td>
                            </tr>
                        """
                tableau_html += "</table>"
            if obj.type_consultation == 'dc_chine':
                # Tableau pour DC-CHINE (Import Chine)
                tableau_html = """
                    <table style="border-collapse: collapse; width: 100%; margin: 10px 0;">
                        <tr style="background-color: #f0f0f0;">
                            <th style="border: 1px solid #ccc; padding: 5px;">N° moule</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Poids</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Dimensions du moule</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Date dispo. outillage</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Date livraison souhaitée</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Mode de transport</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Fournisseur retenu</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Prix</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Délai (jours)</th>
                        </tr>
                """
                for line in obj.line_ids:
                    fournisseur_retenu = None
                    for f in line.fournisseur_ids:
                        if f.fournisseur_retenu:
                            fournisseur_retenu = f
                            break
                    
                    if fournisseur_retenu:
                        nom_fournisseur = ""
                        if fournisseur_retenu.fournisseur_id:
                            nom_fournisseur = fournisseur_retenu.fournisseur_id.name
                        elif fournisseur_retenu.fournisseur_hors_panel:
                            nom_fournisseur = fournisseur_retenu.fournisseur_hors_panel
                        
                        mode_transport_txt = dict(line._fields['mode_transport'].selection).get(line.mode_transport, '') if line.mode_transport else ''
                        tableau_html += f"""
                            <tr>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.mold_id.name if line.mold_id else ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.poids or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.dimensions_moule or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.date_disponibilite_outillage.strftime('%d/%m/%Y') if line.date_disponibilite_outillage else ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.date_livraison_souhaitee.strftime('%d/%m/%Y') if line.date_livraison_souhaitee else ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{mode_transport_txt}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{nom_fournisseur}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{fournisseur_retenu.reponse_prix}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{fournisseur_retenu.delai}</td>
                            </tr>
                        """
                tableau_html += "</table>"
            if obj.type_consultation == 'dc_mat':
                # Tableau pour DC-MAT (Matières et colorants)
                tableau_html = """
                    <table style="border-collapse: collapse; width: 100%; margin: 10px 0;">
                        <tr style="background-color: #f0f0f0;">
                            <th style="border: 1px solid #ccc; padding: 5px;">Désignation</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Coloris</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Quantité annuelle</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Lot</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Fournisseur retenu</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Prix</th>
                            <th style="border: 1px solid #ccc; padding: 5px;">Délai (jours)</th>
                        </tr>
                """
                for line in obj.line_ids:
                    fournisseur_retenu = None
                    for f in line.fournisseur_ids:
                        if f.fournisseur_retenu:
                            fournisseur_retenu = f
                            break
                    
                    if fournisseur_retenu:
                        nom_fournisseur = ""
                        if fournisseur_retenu.fournisseur_id:
                            nom_fournisseur = fournisseur_retenu.fournisseur_id.name
                        elif fournisseur_retenu.fournisseur_hors_panel:
                            nom_fournisseur = fournisseur_retenu.fournisseur_hors_panel
                        
                        tableau_html += f"""
                            <tr>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.designation or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.coloris or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.quantite_annuelle}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.lot or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{nom_fournisseur}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{fournisseur_retenu.reponse_prix}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{fournisseur_retenu.delai}</td>
                            </tr>
                        """
                tableau_html += "</table>"
            
            # Envoi du mail au demandeur
            user = self.env['res.users'].browse(self._uid)
            email_from = user.email
            email_to = obj.demandeur_id.email
            nom = user.name
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = f'{base_url}/web#id={obj.id}&view_type=form&model=is.demande.consultation'
            
            subject = f'[{obj.name}] Consultation soldée'
            body_html = f"""
                <p>Bonjour,</p>
                <p>{nom} vient de solder la demande de consultation <a href='{url}'>{obj.name}</a>.</p>
                <p><strong>Récapitulatif des fournisseurs retenus :</strong></p>
                {tableau_html}
                <p>Cordialement,</p>
                <p>{nom}</p>
            """
            self.envoi_mail(email_from, email_to, subject, body_html)
            
            # Logger dans le chatter (même tableau)
            chatter_message = f"""
                <p><strong>Consultation soldée - Mail envoyé à {obj.demandeur_id.name} ({email_to})</strong></p>
                <p><strong>Récapitulatif des fournisseurs retenus :</strong></p>
                {tableau_html}
            """
            obj.message_post(body=chatter_message, subject="Consultation soldée")
            
            obj.sudo().state = 'solde'

    def vers_annule_action(self):
        """Passage à l'état annulé"""
        for obj in self:
            if obj.demandeur_id.id == self._uid or obj.acheteur_id.id == self._uid or obj.validateur_technique_id.id == self._uid:
                obj.sudo().state = 'annule'

    def envoi_mail(self, email_from, email_to, subject, body_html):
        """Envoi d'un email de notification"""
        for obj in self:
            vals = {
                'email_from': email_from,
                'email_to': email_to,
                'email_cc': email_from,
                'subject': subject,
                'body_html': body_html,
            }
            email = self.env['mail.mail'].sudo().create(vals)
            if email:
                self.env['mail.mail'].sudo().send(email)

    def envoi_consultation_fournisseurs_action(self):
        """Envoie les mails de consultation aux fournisseurs sélectionnés"""
        for obj in self:
            if obj.state not in ['transmis_achat', 'consultation_en_cours']:
                raise ValidationError("L'envoi des consultations n'est possible qu'aux états 'Transmis achat' ou 'Consultation en cours'.")
            
            # Récupérer l'utilisateur courant (acheteur)
            user = self.env['res.users'].browse(self._uid)
            email_from = user.email
            
            # Collecter les fournisseurs avec email (par email pour regrouper les lignes)
            fournisseurs_lignes = {}
            fournisseurs_sans_email = []
            fournisseurs_deja_envoyes = []
            
            for line in obj.line_ids:
                for fournisseur in line.fournisseur_ids:
                    # Nom à afficher
                    nom_fournisseur = ""
                    if fournisseur.fournisseur_id:
                        nom_fournisseur = fournisseur.fournisseur_id.name
                    elif fournisseur.fournisseur_hors_panel:
                        nom_fournisseur = fournisseur.fournisseur_hors_panel
                    
                    # Vérifier si mail déjà envoyé
                    if fournisseur.date_envoi_mail:
                        fournisseurs_deja_envoyes.append(nom_fournisseur or "Fournisseur inconnu")
                        continue
                    
                    # Obtenir l'email (priorité email_commercial, sinon email du fournisseur)
                    email_to_use = fournisseur.email_commercial
                    if not email_to_use and fournisseur.fournisseur_id:
                        email_to_use = fournisseur.fournisseur_id.email
                    
                    if email_to_use:
                        # Clé par email pour regrouper
                        key = email_to_use
                        if key not in fournisseurs_lignes:
                            fournisseurs_lignes[key] = {
                                'nom': nom_fournisseur,
                                'email': email_to_use,
                                'lignes': [],
                                'fournisseur_records': [],
                            }
                        fournisseurs_lignes[key]['lignes'].append(line)
                        fournisseurs_lignes[key]['fournisseur_records'].append(fournisseur)
                    else:
                        # Pas d'email - ne pas envoyer
                        fournisseurs_sans_email.append(nom_fournisseur or "Fournisseur inconnu")
            
            if not fournisseurs_lignes:
                if fournisseurs_deja_envoyes:
                    raise ValidationError("Tous les fournisseurs ont déjà reçu le mail. Pour renvoyer, effacez la date d'envoi.")
                raise ValidationError("Aucun fournisseur avec email trouvé dans les lignes.")
            
            # Envoyer un mail par fournisseur (regroupé par email)
            mails_envoyes = []
            for email_key, data in fournisseurs_lignes.items():
                nom_fournisseur = data['nom']
                email_to = data['email']
                lignes = data['lignes']
                fournisseur_records = data['fournisseur_records']
                
                # Construire le tableau des produits selon le type de consultation
                lignes_html = ""
                subject = f"Demande de consultation {obj.name}"
                if obj.type_consultation == 'dc_mat':
                    for line in lignes:
                        lignes_html += f"""
                            <tr>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.designation or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.coloris or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.quantite_annuelle}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.lot or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;"></td>
                                <td style="border: 1px solid #ccc; padding: 5px;"></td>
                            </tr>
                        """
                    body_html = f"""
                        <p>Madame, Monsieur,</p>
                        <p>Dans le cadre d'une consultation prix, nous vous serions reconnaissant de nous 
                        transmettre votre meilleure offre de prix pour la fourniture éventuelle de :</p>
                        <table style="border-collapse: collapse; width: 100%; margin: 10px 0;">
                            <tr style="background-color: #f0f0f0;">
                                <th style="border: 1px solid #ccc; padding: 5px;">Désignation</th>
                                <th style="border: 1px solid #ccc; padding: 5px;">Coloris</th>
                                <th style="border: 1px solid #ccc; padding: 5px;">Quantité annuelle</th>
                                <th style="border: 1px solid #ccc; padding: 5px;">Lot</th>
                                <th style="border: 1px solid #ccc; padding: 5px;">Prix</th>
                                <th style="border: 1px solid #ccc; padding: 5px;">Délai</th>
                            </tr>
                            {lignes_html}
                        </table>
                        <p><strong>En conformité avec REACH/ROHS</strong></p>
                        <p><strong>Secteur / Application :</strong> {obj.secteur_application or ''}</p>
                        <p><strong>Date de réponse souhaitée :</strong> {obj.date_reponse_souhaitee.strftime('%d/%m/%Y') if obj.date_reponse_souhaitee else ''}</p>
                        <p><strong>SOP :</strong> {obj.date_sop.strftime('%d/%m/%Y') if obj.date_sop else ''}</p>
                        <p><strong>Durée de vie :</strong> {obj.duree_vie or ''} {' années' if obj.duree_vie else ''}</p>
                        <p><strong>Documents à nous transmettre :</strong></p>
                        <ul>
                            <li>Fiche de Données Technique</li>
                            <li>Fiche de Données de Sécurité</li>
                        </ul>
                        <p>Cordialement,</p>
                        <p>{user.name}</p>
                    """

                if obj.type_consultation == 'dc_comp':
                    for line in lignes:
                        standard_txt = dict(line._fields['standard'].selection).get(line.standard, '') if line.standard else ''
                        lignes_html += f"""
                            <tr>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.type_produit or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.matiere or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.dimension or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.environnement or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.quantite_annuelle}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{standard_txt}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.lot or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;"></td>
                                <td style="border: 1px solid #ccc; padding: 5px;"></td>
                            </tr>
                        """
                    body_html = f"""
                        <p>Madame, Monsieur,</p>
                        <p>Dans le cadre d'une consultation prix, nous vous serions reconnaissant de nous 
                        transmettre votre meilleure offre de prix pour la fourniture éventuelle de :</p>
                        <table style="border-collapse: collapse; width: 100%; margin: 10px 0;">
                            <tr style="background-color: #f0f0f0;">
                                <th style="border: 1px solid #ccc; padding: 5px;">Type de produit</th>
                                <th style="border: 1px solid #ccc; padding: 5px;">Matière</th>
                                <th style="border: 1px solid #ccc; padding: 5px;">Dimension</th>
                                <th style="border: 1px solid #ccc; padding: 5px;">Environnement</th>
                                <th style="border: 1px solid #ccc; padding: 5px;">Quantité annuelle</th>
                                <th style="border: 1px solid #ccc; padding: 5px;">Standard</th>
                                <th style="border: 1px solid #ccc; padding: 5px;">Lot</th>
                                <th style="border: 1px solid #ccc; padding: 5px;">Prix</th>
                                <th style="border: 1px solid #ccc; padding: 5px;">Délai</th>
                            </tr>
                            {lignes_html}
                        </table>
                        <p><strong>Secteur / Application :</strong> {obj.secteur_application or ''}</p>
                        <p><strong>Date de réponse souhaitée :</strong> {obj.date_reponse_souhaitee.strftime('%d/%m/%Y') if obj.date_reponse_souhaitee else ''}</p>
                        <p><strong>SOP :</strong> {obj.date_sop.strftime('%d/%m/%Y') if obj.date_sop else ''}</p>
                        <p><strong>Durée de vie :</strong> {obj.duree_vie or ''} {' années' if obj.duree_vie else ''}</p>
                        <p><strong>Documents à nous transmettre :</strong></p>
                        <ul>
                            <li>Plan</li>
                        </ul>
                        <p>Cordialement,</p>
                        <p>{user.name}</p>
                    """

                if obj.type_consultation == 'dc_emb':
                    for line in lignes:
                        lignes_html += f"""
                            <tr>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.type_produit or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.matiere or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.dimensions_int or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.dimensions_ext or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.quantite_annuelle}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.lot or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;"></td>
                                <td style="border: 1px solid #ccc; padding: 5px;"></td>
                            </tr>
                        """
                    body_html = f"""
                        <p>Madame, Monsieur,</p>
                        <p>Dans le cadre d'une consultation prix, nous vous serions reconnaissant de nous 
                        transmettre votre meilleure offre de prix pour la fourniture éventuelle de :</p>
                        <table style="border-collapse: collapse; width: 100%; margin: 10px 0;">
                            <tr style="background-color: #f0f0f0;">
                                <th style="border: 1px solid #ccc; padding: 5px;">Type de produit</th>
                                <th style="border: 1px solid #ccc; padding: 5px;">Matière</th>
                                <th style="border: 1px solid #ccc; padding: 5px;">Dim. intérieures</th>
                                <th style="border: 1px solid #ccc; padding: 5px;">Dim. extérieures</th>
                                <th style="border: 1px solid #ccc; padding: 5px;">Quantité annuelle</th>
                                <th style="border: 1px solid #ccc; padding: 5px;">Lot</th>
                                <th style="border: 1px solid #ccc; padding: 5px;">Prix</th>
                                <th style="border: 1px solid #ccc; padding: 5px;">Délai</th>
                            </tr>
                            {lignes_html}
                        </table>
                        <p><strong>Secteur / Application :</strong> {obj.secteur_application or ''}</p>
                        <p><strong>Date de réponse souhaitée :</strong> {obj.date_reponse_souhaitee.strftime('%d/%m/%Y') if obj.date_reponse_souhaitee else ''}</p>
                        <p><strong>SOP :</strong> {obj.date_sop.strftime('%d/%m/%Y') if obj.date_sop else ''}</p>
                        <p><strong>Durée de vie :</strong> {obj.duree_vie or ''} {' années' if obj.duree_vie else ''}</p>
                        <p><strong>Documents à nous transmettre :</strong></p>
                        <ul>
                            <li>Plan</li>
                        </ul>
                        <p>Cordialement,</p>
                        <p>{user.name}</p>
                    """

                if obj.type_consultation == 'dc_port':
                    for line in lignes:
                        lignes_html += f"""
                            <tr>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.colisage or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.poids or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.frequence or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;"></td>
                                <td style="border: 1px solid #ccc; padding: 5px;"></td>
                            </tr>
                        """
                    # Informations transport
                    adresse_enlevement = obj.adresse_enlevement_id.name if obj.adresse_enlevement_id else ''
                    adresse_livraison = obj.adresse_livraison_id.name if obj.adresse_livraison_id else ''
                    incoterm = obj.incoterm_id.code if obj.incoterm_id else ''
                    body_html = f"""
                        <p>Madame, Monsieur,</p>
                        <p>Dans le cadre d'une consultation prix, nous vous serions reconnaissant de nous 
                        transmettre votre meilleure offre de prix pour le transport suivant :</p>
                        <p><strong>Adresse d'enlèvement :</strong> {adresse_enlevement}</p>
                        <p><strong>Adresse de livraison :</strong> {adresse_livraison}</p>
                        <p><strong>Date DMS :</strong> {obj.date_dms.strftime('%d/%m/%Y') if obj.date_dms else ''}</p>
                        <p><strong>Incoterm :</strong> {incoterm}</p>
                        <p><strong>Lieu :</strong> {obj.lieu or ''}</p>
                        <table style="border-collapse: collapse; width: 100%; margin: 10px 0;">
                            <tr style="background-color: #f0f0f0;">
                                <th style="border: 1px solid #ccc; padding: 5px;">Colisage</th>
                                <th style="border: 1px solid #ccc; padding: 5px;">Poids</th>
                                <th style="border: 1px solid #ccc; padding: 5px;">Fréquence</th>
                                <th style="border: 1px solid #ccc; padding: 5px;">Prix</th>
                                <th style="border: 1px solid #ccc; padding: 5px;">Délai</th>
                            </tr>
                            {lignes_html}
                        </table>
                        <p><strong>Date de réponse souhaitée :</strong> {obj.date_reponse_souhaitee.strftime('%d/%m/%Y') if obj.date_reponse_souhaitee else ''}</p>
                        <p>Cordialement,</p>
                        <p>{user.name}</p>
                    """

                if obj.type_consultation == 'dc_chine':
                    for line in lignes:
                        mode_transport_txt = dict(line._fields['mode_transport'].selection).get(line.mode_transport, '') if line.mode_transport else ''
                        lignes_html += f"""
                            <tr>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.mold_id.name if line.mold_id else ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.poids or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.dimensions_moule or ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.date_disponibilite_outillage.strftime('%d/%m/%Y') if line.date_disponibilite_outillage else ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{line.date_livraison_souhaitee.strftime('%d/%m/%Y') if line.date_livraison_souhaitee else ''}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;">{mode_transport_txt}</td>
                                <td style="border: 1px solid #ccc; padding: 5px;"></td>
                            </tr>
                        """
                    # Informations import Chine
                    adresse_enlevement = obj.adresse_enlevement_id.name if obj.adresse_enlevement_id else ''
                    adresse_livraison = obj.adresse_livraison_id.name if obj.adresse_livraison_id else ''
                    incoterm = obj.incoterm_id.code if obj.incoterm_id else ''
                    body_html = f"""
                        <p>Madame, Monsieur,</p>
                        <p>Dans le cadre d'une consultation prix, nous vous serions reconnaissant de nous 
                        transmettre votre meilleure offre de prix pour l'import suivant :</p>
                        <p><strong>Adresse d'enlèvement :</strong> {adresse_enlevement}</p>
                        <p><strong>Adresse de livraison :</strong> {adresse_livraison}</p>
                        <p><strong>Incoterm :</strong> {incoterm}</p>
                        <p><strong>Lieu :</strong> {obj.lieu or ''}</p>
                        <table style="border-collapse: collapse; width: 100%; margin: 10px 0;">
                            <tr style="background-color: #f0f0f0;">
                                <th style="border: 1px solid #ccc; padding: 5px;">N° moule</th>
                                <th style="border: 1px solid #ccc; padding: 5px;">Poids</th>
                                <th style="border: 1px solid #ccc; padding: 5px;">Dimensions du moule</th>
                                <th style="border: 1px solid #ccc; padding: 5px;">Date dispo. outillage</th>
                                <th style="border: 1px solid #ccc; padding: 5px;">Date livraison souhaitée</th>
                                <th style="border: 1px solid #ccc; padding: 5px;">Mode de transport</th>
                                <th style="border: 1px solid #ccc; padding: 5px;">Prix</th>
                            </tr>
                            {lignes_html}
                        </table>
                        <p><strong>Date de réponse souhaitée :</strong> {obj.date_reponse_souhaitee.strftime('%d/%m/%Y') if obj.date_reponse_souhaitee else ''}</p>
                        <p>Cordialement,</p>
                        <p>{user.name}</p>
                    """
                
                # Envoyer le mail
                vals = {
                    'email_from': email_from,
                    'email_to': email_to,
                    'email_cc': email_from,
                    'subject': subject,
                    'body_html': body_html,
                }
                email = self.env['mail.mail'].sudo().create(vals)
                if email:
                    self.env['mail.mail'].sudo().send(email)
                
                # Mettre à jour la date d'envoi sur les enregistrements fournisseur
                now = fields.Datetime.now()
                for fournisseur_record in fournisseur_records:
                    fournisseur_record.sudo().date_envoi_mail = now
                
                mails_envoyes.append({'nom': nom_fournisseur, 'email': email_to, 'body_html': body_html})
            
            # Logger dans le chatter
            message = "<p><strong>Consultations envoyées aux fournisseurs :</strong></p><ul>"
            for mail_info in mails_envoyes:
                message += f"<li>{mail_info['nom']} ({mail_info['email']})</li>"
            message += "</ul>"
            
            # Ajouter le contenu du mail envoyé (identique pour tous les fournisseurs)
            if mails_envoyes:
                message += "<hr/><p><strong>Contenu du mail envoyé :</strong></p>"
                message += mails_envoyes[0]['body_html']
            
            # Ajouter les fournisseurs sans email
            if fournisseurs_sans_email:
                message += "<p><strong style='color: red;'>Fournisseurs sans email (non envoyés) :</strong></p><ul>"
                for nom in fournisseurs_sans_email:
                    message += f"<li>{nom}</li>"
                message += "</ul>"
            
            # Ajouter les fournisseurs déjà contactés
            if fournisseurs_deja_envoyes:
                message += "<p><strong style='color: orange;'>Fournisseurs déjà contactés (non renvoyés) :</strong></p><ul>"
                for nom in fournisseurs_deja_envoyes:
                    message += f"<li>{nom}</li>"
                message += "</ul>"
            
            obj.message_post(body=message, subject="Envoi des consultations")
            
            # Vérifier si tous les fournisseurs ont reçu le mail => passer en 'Consultation en cours'
            tous_envoyes = True
            for line in obj.line_ids:
                for fournisseur in line.fournisseur_ids:
                    if not fournisseur.date_envoi_mail:
                        tous_envoyes = False
                        break
                if not tous_envoyes:
                    break
            
            if tous_envoyes and obj.state == 'transmis_achat':
                obj.sudo().state = 'consultation_en_cours'
        
        return True


class IsDemandeConsultationLine(models.Model):
    _name = 'is.demande.consultation.line'
    _description = "Lignes demande de consultation"
    _order = 'demande_id, sequence'

    @api.depends('fournisseur_ids.fournisseur_retenu', 'fournisseur_ids.fournisseur_id', 'fournisseur_ids.fournisseur_hors_panel')
    def _compute_fournisseur_retenu(self):
        """Récupère le fournisseur retenu et son prix depuis les lignes fournisseurs"""
        for obj in self:
            fournisseur_retenu = False
            fournisseur_retenu_name = ""
            prix_retenu = 0.0
            for fournisseur in obj.fournisseur_ids:
                if fournisseur.fournisseur_retenu:
                    if fournisseur.fournisseur_id:
                        fournisseur_retenu = fournisseur.fournisseur_id.id
                        fournisseur_retenu_name = fournisseur.fournisseur_id.name
                    elif fournisseur.fournisseur_hors_panel:
                        fournisseur_retenu_name = fournisseur.fournisseur_hors_panel
                    prix_retenu = fournisseur.reponse_prix or 0.0
                    break
            obj.fournisseur_retenu_id = fournisseur_retenu
            obj.fournisseur_retenu_name = fournisseur_retenu_name
            obj.prix_retenu = prix_retenu

    demande_id = fields.Many2one('is.demande.consultation', "Demande de consultation", 
                                 required=True, ondelete='cascade', readonly=True)
    state = fields.Selection(related='demande_id.state', string="État", store=False)
    type_consultation = fields.Selection(related='demande_id.type_consultation', string="Type de consultation", store=False)
    sequence = fields.Integer('Ordre')
    
    # Champs communs (sauf DC-EMB)
    designation = fields.Char("Désignation")
    coloris = fields.Char("Coloris")
    
    # Champs spécifiques DC-EMB (Emballages)
    type_produit = fields.Char("Type de produit", help="carton, séparation, sachet...")
    matiere = fields.Char("Matière", help="carton, PE...")
    dimensions_int = fields.Char("Dimensions intérieures")
    dimensions_ext = fields.Char("Dimensions extérieures")
    type_cannelure = fields.Char("Type de cannelure")
    poids_emballage = fields.Float("Poids dans l'emballage", digits=(14, 2))
    standard = fields.Selection([('oui', 'Oui'), ('non', 'Non')], string="Standard")
    
    # Champs spécifiques DC-COMP (Composants)
    dimension = fields.Char("Dimension", help="ex: M4*8")
    environnement = fields.Char("Environnement", help="Insertion froid/chaud, Manuel/Auto...")
    
    # Champs spécifiques DC-PORT (Transport)
    colisage = fields.Char("Colisage")
    poids = fields.Float("Poids", digits=(14, 2))
    frequence = fields.Char("Fréquence")
    
    # Champs spécifiques DC-CHINE (Import Chine)
    mold_id = fields.Many2one('is.mold', "N° moule")
    dimensions_moule = fields.Char("Dimensions du moule")
    date_disponibilite_outillage = fields.Date("Date de disponibilité de l'outillage")
    date_livraison_souhaitee = fields.Date("Date de livraison maxi souhaitée")
    mode_transport = fields.Selection([
        ('train', 'Train'),
        ('avion', 'Avion'),
        ('bateau', 'Bateau'),
        ('sea_air', 'Sea/Air'),
    ], string="Mode de transport")
    
    # Champs communs
    quantite_annuelle = fields.Float("Quantité annuelle", digits=(14, 2))
    lot = fields.Integer("Lot", help="Lots à consulter (un par ligne)")
    
    # Fournisseurs
    fournisseur_ids = fields.One2many('is.demande.consultation.line.fournisseur', 'line_id', 
                                      string="Fournisseurs consultés", copy=True)
    
    # Champs calculés
    fournisseur_retenu_id = fields.Many2one('res.partner', "Fournisseur retenu (ID)", 
                                            compute='_compute_fournisseur_retenu', store=True)
    fournisseur_retenu_name = fields.Char("Fournisseur retenu", compute='_compute_fournisseur_retenu', store=True)
    prix_retenu = fields.Float("Prix retenu", digits=(14, 4), compute='_compute_fournisseur_retenu', store=True)

    def copy_line_action(self):
        """Copie la ligne avec ses fournisseurs (copy=True par défaut sur One2many)"""
        for obj in self:
            obj.copy({
                'demande_id': obj.demande_id.id,
                'sequence': obj.sequence + 1,
            })
        return True


class IsDemandeConsultationLineFournisseur(models.Model):
    _name = 'is.demande.consultation.line.fournisseur'
    _description = "Fournisseurs par ligne de demande de consultation"
    _order = 'line_id, sequence'

    @api.onchange('fournisseur_id')
    def _onchange_fournisseur_id(self):
        """Remplit automatiquement l'email du contact commercial du fournisseur"""
        for obj in self:
            if obj.fournisseur_id:
                # Chercher le contact de type Commercial
                email = False
                for contact in obj.fournisseur_id.child_ids:
                    if contact.is_type_contact and contact.is_type_contact.name and \
                       'commercial' in contact.is_type_contact.name.lower():
                        if contact.email:
                            email = contact.email
                            break
                obj.email_commercial = email

    line_id = fields.Many2one('is.demande.consultation.line', "Ligne de demande", 
                              required=True, ondelete='cascade', readonly=True)
    state = fields.Selection(related='line_id.demande_id.state', string="État", store=False)
    sequence = fields.Integer('Ordre')
        
    # Fournisseur
    fournisseur_id = fields.Many2one('res.partner', "Fournisseur", 
                                     domain=[('is_company', '=', True), ('supplier_rank', '>', 0)])
    email_commercial = fields.Char("Email commercial")
    fournisseur_hors_panel = fields.Char("Fournisseur hors panel")
    
    # Réponses
    reponse_prix = fields.Float("Réponse prix", digits=(14, 4), help="Prix pour chaque lot", copy=False)
    delai = fields.Integer("Délai (jours)", copy=False)
    
    # Sélection par l'acheteur
    fournisseur_retenu = fields.Boolean("Fournisseur retenu", default=False, copy=False)
    
    # Suivi envoi mail
    date_envoi_mail = fields.Datetime("Date d'envoi du mail", copy=False,
                                      help="Effacer ce champ pour renvoyer le mail")

