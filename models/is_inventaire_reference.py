# -*- coding: utf-8 -*-
from odoo import models,fields,api
from odoo.exceptions import ValidationError, UserError
from markupsafe import escape
import logging
_logger = logging.getLogger(__name__)


_STATE = [
    ('scan'     , 'En cours'),
    ('a_valider', 'À valider'),
    ('valide'   , 'Validé'),
    ('annule'   , 'Abandonné'),
]

# Un seul inventaire dans ces états par article
_STATE_EN_COURS = ('scan', 'a_valider')

_SITUATION_SCAN = [
    ('ok'               , "Bon emplacement"),
    ('autre_emplacement', "Autre emplacement"),
    ('hors_stock'       , "Hors stock"),
]

_SITUATION_UM = _SITUATION_SCAN + [
    ('non_trouvee', "Non trouvée"),
]

_ETAT_CARTE = [
    ('a_faire' , "À faire"),
    ('en_cours', "En cours"),
    ('complet' , "Complet"),
    ('excedent', "Excédent"),
]

# Badge et barre des cartes : gris, bleu, vert, orange
_COULEUR_CARTE = {
    'a_faire' : '#8a8f94',
    'en_cours': '#0d6efd',
    'complet' : '#28a745',
    'excedent': '#fd7e14',
}

# Champs recopiés de l'enregistrement en base vers le formulaire après un scan (on_barcode_scanned est un onchange)
_CHAMPS_FORMULAIRE = [
    'state', 'product_id', 'location_id', 'location_ids', 'scan_ids', 'carte_ids', 'dernier_scan_id',
    'nb_um', 'nb_um_attendues', 'nb_uc', 'nb_uc_attendues', 'qt_odoo', 'qt_scannee', 'progression',
    'nb_emplacements', 'nb_lots', 'message', 'alerte', 'avertissement', 'date_debut',
    'date_derniere_activite', 'user_derniere_activite_id',
]


def _fmt(nombre):
    "Nombre entier avec séparateur des milliers (espace insécable)"
    return '{:,}'.format(int(round(nombre or 0))).replace(',', ' ')


def _fmt_signe(nombre):
    return ('+' if nombre>0 else '') + _fmt(nombre)


class is_inventaire_reference(models.Model):
    _name        = 'is.inventaire.reference'
    _inherit     = ['mail.thread', 'barcodes.barcode_events_mixin']
    _description = "Inventaire d'une référence par scan des UM / UC"
    _order       = 'date_derniere_activite desc, id desc'


    @api.depends('state', 'location_id')
    def _compute_action_attendue(self):
        for obj in self:
            action_attendue = False
            if obj.state=='scan':
                if obj.location_id:
                    action_attendue = "Scannez les UM / UC de l'emplacement %s"%obj.location_id.name
                else:
                    action_attendue = "Scannez l'emplacement"
            if obj.state=='a_valider':
                action_attendue = "Vérifiez les écarts puis validez"
            obj.action_attendue = action_attendue


    @api.depends('name', 'state', 'product_id', 'location_id', 'nb_um', 'nb_um_attendues', 'nb_uc', 'nb_uc_attendues', 'qt_odoo', 'qt_scannee', 'progression', 'ecart', 'ecart_ids')
    def _compute_info_html(self):
        couleurs = {'scan': '#17a2b8', 'a_valider': '#fd7e14', 'valide': '#28a745', 'annule': '#8a8f94'}
        for obj in self:
            titre = "<div class='d-flex justify-content-between align-items-center'><b>%s</b><span class='badge' style='background-color:%s;color:#fff'>%s</span></div>"%(
                escape(obj.name or ''), couleurs.get(obj.state, '#8a8f94'), escape(dict(_STATE).get(obj.state, '')),
            )
            lignes = []
            if obj.product_id:
                lignes.append("<b>%s</b> <span class='text-muted'>%s</span>"%(escape(obj.product_id.is_code or ''), escape(obj.product_id.name or '')))
            if obj.state=='scan':
                lignes.append("Emplacement courant : <b>%s</b>"%escape(obj.location_id.name or '—'))
            if obj.product_id and obj.state in ('a_valider', 'valide'):
                ecart = "Écart total : <b>%s</b> pièces"%_fmt_signe(obj.ecart)
                # Fond rouge dès qu'une ligne est en écart (un total à 0 peut cacher des écarts qui s'annulent)
                if obj.ecart_ids.filtered(lambda e: e.ecart):
                    ecart = "<span class='d-inline-block rounded px-2 mt-1' style='background-color:#dc3545;color:#fff'>%s</span>"%ecart
                lignes.append(ecart)
            # Titre en bloc (div) : pas de <br/> après, sinon ligne vide
            info = "<div class='lh-sm'>%s%s</div>"%(titre, "<br/>".join(lignes))
            if obj.product_id and obj.state=='scan':
                progression = int(round(obj.progression))
                info += (
                    "<div class='lh-sm'>UM <b>%s</b> / %s · UC <b>%s</b> / %s</div>"
                    "<div class='d-flex align-items-center mt-1'>"
                    "<div class='progress flex-grow-1 me-2' style='height:8px'><div class='progress-bar' style='width:%s%%;background-color:%s'></div></div>"
                    "<span class='small text-nowrap'>%s / %s · %s %%</span>"
                    "</div>"
                )%(
                    obj.nb_um, obj.nb_um_attendues, obj.nb_uc, obj.nb_uc_attendues,
                    min(progression, 100), obj._couleur_ecart(), _fmt(obj.qt_scannee), _fmt(obj.qt_odoo), progression,
                )
            obj.info_html = info


    def _couleur_ecart(self):
        "Barre de la zone grise (comme le kanban de la liste) : rouge s'il en manque, orange s'il y en a trop, vert sans écart"
        if self.qt_scannee<self.qt_odoo:
            return '#dc3545'
        if self.qt_scannee>self.qt_odoo:
            return '#fd7e14'
        return '#28a745'


    def _html_carte(self, carte):
        "Carte emplacement × lot pendant les scans (bordure épaisse : carte du dernier scan)"
        couleur = _COULEUR_CARTE.get(carte.etat, '#8a8f94')
        if carte.qt_odoo>0:
            pourcentage = 100.0*carte.qt_scannee/carte.qt_odoo
        else:
            pourcentage = carte.qt_scannee and 100 or 0
        if carte.etat=='excedent':
            texte_barre = _fmt_signe(carte.qt_scannee-carte.qt_odoo)
        else:
            texte_barre = "%s %%"%int(round(pourcentage))
        detail = "UM %s / %s · UC %s / %s"%(carte.nb_um, carte.nb_um_attendues, carte.nb_uc, carte.nb_uc_attendues)
        if carte.qt_odoo<=0 and carte.qt_scannee>0:
            detail += " · trouvée hors stock Odoo"
        bordure = carte.dernier_scan and "border:3px solid #0d6efd" or "border:1px solid #dee2e6"
        return (
            "<div class='rounded px-2 py-1 bg-white' style='%s'>"
            "<div class='d-flex justify-content-between align-items-center'>"
            "<b>%s · %s</b>"
            "<span class='text-nowrap'><span class='badge me-1' style='background-color:%s;color:#fff'>%s</span>%s / %s</span>"
            "</div>"
            "<div class='d-flex align-items-center'>"
            "<div class='progress flex-grow-1 me-2' style='height:8px'><div class='progress-bar' style='width:%s%%;background-color:%s'></div></div>"
            "<span class='small text-nowrap'>%s</span>"
            "</div>"
            "<div class='small text-muted'>%s</div>"
            "</div>"
        )%(
            bordure,
            escape(carte.location_id.name or ''), escape(carte.lot_name or 'sans lot'),
            couleur, escape(dict(_ETAT_CARTE).get(carte.etat, '')), _fmt(carte.qt_scannee), _fmt(carte.qt_odoo),
            int(min(pourcentage, 100)), couleur, texte_barre,
            detail,
        )


    @api.depends('location_id', 'carte_ids', 'dernier_scan_id', 'nb_um', 'nb_uc', 'qt_scannee', 'qt_odoo')
    def _compute_cartes_html(self):
        for obj in self:
            # Dans l'onchange du scan, les cartes recopiées gardent leurs anciennes valeurs (une carte existante dont
            # seules les quantités changent) : cartes lues sur l'enregistrement en base (_origin), mises à jour par le scan.
            # Recalcul déclenché par les totaux, qui changent à chaque scan
            cartes  = (obj._origin or obj).carte_ids
            courant = cartes.filtered(lambda c: obj.location_id and c.location_id==obj.location_id)
            autres  = cartes - courant
            courant_html = False
            if obj.location_id and obj.product_id:
                cartes = "".join(obj._html_carte(c) for c in courant)
                if not cartes:
                    cartes = "<div class='text-muted small'>Aucun stock ni UM de la référence dans cet emplacement</div>"
                courant_html = "<div class='o_is_titre'>Emplacement %s</div><div class='o_is_cartes'>%s</div>"%(escape(obj.location_id.name), cartes)
            autres_html = False
            if autres:
                autres_html = "<div class='o_is_titre'>Autres emplacements</div><div class='o_is_cartes'>%s</div>"%"".join(obj._html_carte(c) for c in autres)
            obj.cartes_courant_html = courant_html
            obj.cartes_autres_html  = autres_html


    @api.depends('ecart_ids', 'um_ids')
    def _compute_ecarts_html(self):
        "Cartes de l'écran de validation sur smartphone"
        for obj in self:
            #** Écarts (lignes sans écart seulement comptées) ******************
            cartes = []
            for ecart in obj.ecart_ids.filtered(lambda e: e.ecart):
                # Orange en plus (excédent, comme les cartes des scans), rouge en moins : un écart n'est jamais vert
                couleur = ecart.ecart>0 and '#fd7e14' or '#dc3545'
                cartes.append(
                    "<div class='border rounded px-2 py-1 bg-white'>"
                    "<div class='d-flex justify-content-between align-items-center'><b>%s · %s</b>"
                    "<span class='badge' style='background-color:%s;color:#fff'>%s</span></div>"
                    "<div class='small text-muted'>Qt Odoo %s → scannée %s</div>"
                    "</div>"%(
                        escape(ecart.location_id.name or ''), escape(ecart.lot_name or 'sans lot'),
                        couleur, _fmt_signe(ecart.ecart),
                        _fmt(ecart.qt_odoo), _fmt(ecart.qt_scannee),
                    )
                )
            nb_sans_ecart = len(obj.ecart_ids.filtered(lambda e: not e.ecart))
            ecarts_html = False
            if obj.ecart_ids:
                pied = ""
                if not cartes:
                    cartes = ["<div class='text-muted small'>Aucun écart</div>"]
                elif nb_sans_ecart:
                    # Nombre des lignes sans écart utile seulement à côté des lignes en écart
                    pied = "<div class='small text-muted mb-1'>%s ligne%s sans écart</div>"%(nb_sans_ecart, nb_sans_ecart>1 and 's' or '')
                ecarts_html = "<div class='o_is_titre'>Écarts</div><div class='o_is_cartes'>%s</div>%s"%("".join(cartes), pied)

            #** UM non trouvées ***********************************************
            cartes = []
            for ligne in obj.um_ids.filtered(lambda l: l.situation=='non_trouvee'):
                cartes.append(
                    "<div class='border rounded px-2 py-1 bg-white'>"
                    "<div class='d-flex justify-content-between'><b>UM %s</b><span>%s pcs</span></div>"
                    "<div class='small text-muted'>en %s · lot %s · %s UC</div>"
                    "</div>"%(
                        escape(ligne.um_id.name or ''), _fmt(ligne.qt_odoo),
                        escape(ligne.location_odoo_id.name or ''), escape(ligne.lots or ''), ligne.nb_uc_odoo,
                    )
                )
            um_non_trouvees_html = cartes and "<div class='o_is_titre'>UM non trouvées</div><div class='o_is_cartes'>%s</div>"%"".join(cartes) or False

            #** UM à déplacer ou à réactiver **********************************
            cartes = []
            for ligne in obj.um_ids.filtered(lambda l: l.situation in ('autre_emplacement', 'hors_stock')):
                avant = escape(ligne.location_odoo_id.name or '')
                if ligne.situation=='hors_stock' and not ligne.um_active_odoo:
                    avant = "archivée en %s"%avant
                cartes.append(
                    "<div class='border rounded px-2 py-1 bg-white'>"
                    "<div class='d-flex justify-content-between align-items-center'><b>UM %s</b>"
                    "<span class='badge' style='background-color:#fd7e14;color:#fff'>→ %s</span></div>"
                    "<div class='small text-muted'>%s → %s · %s pcs</div>"
                    "</div>"%(
                        escape(ligne.um_id.name or ''), escape(ligne.location_scan_id.name or ''),
                        avant, escape(ligne.location_scan_id.name or ''), _fmt(ligne.qt_scannee),
                    )
                )
            um_a_corriger_html = cartes and "<div class='o_is_titre'>UM à déplacer / réactiver</div><div class='o_is_cartes'>%s</div>"%"".join(cartes) or False

            obj.ecarts_html           = ecarts_html
            obj.um_non_trouvees_html  = um_non_trouvees_html
            obj.um_a_corriger_html    = um_a_corriger_html


    @api.depends('scan_ids', 'scan_ids.retire')
    def _compute_derniers_scan_ids(self):
        for obj in self:
            # Dans l'onchange du scan, les lignes sont des NewId : ordre selon l'id en base (_origin)
            scans = obj.scan_ids.filtered(lambda s: not s.retire)
            obj.derniers_scan_ids = scans.sorted(key=lambda s: -(s._origin.id or 0))[:10]


    name                      = fields.Char("N° inventaire", readonly=True, copy=False, index=True)
    product_id                = fields.Many2one('product.product', "Article", readonly=True, tracking=True, index=True, help="Article inventorié, donné par le premier scan")
    location_ids              = fields.Many2many('stock.location', 'is_inventaire_reference_location_rel', 'inventaire_id', 'location_id', "Emplacements inventoriés", readonly=True, help="Emplacements internes (hors stock client) avec du stock, des UM ou un scan de l'article, recalculés à chaque scan")
    location_id               = fields.Many2one('stock.location', "Emplacement courant", readonly=True, help="Dernier emplacement scanné")
    state                     = fields.Selection(_STATE, "État", default='scan', required=True, readonly=True, tracking=True, index=True)
    date_debut                = fields.Datetime("Premier scan", readonly=True)
    date_fin_scan             = fields.Datetime("Fin des scans", readonly=True)
    date_validation           = fields.Datetime("Date de validation", readonly=True, tracking=True)
    valideur_id               = fields.Many2one('res.users', "Validé par", readonly=True, tracking=True)
    scan_ids                  = fields.One2many('is.inventaire.reference.scan', 'inventaire_id', "Journal des scans", readonly=True)
    derniers_scan_ids         = fields.One2many('is.inventaire.reference.scan', compute='_compute_derniers_scan_ids', string="Derniers scans")
    dernier_scan_id           = fields.Many2one('is.inventaire.reference.scan', "Dernier scan", readonly=True)
    carte_ids                 = fields.One2many('is.inventaire.reference.carte', 'inventaire_id', "Cartes", readonly=True)
    ecart_ids                 = fields.One2many('is.inventaire.reference.ecart', 'inventaire_id', "Écarts", readonly=True)
    um_ids                    = fields.One2many('is.inventaire.reference.um', 'inventaire_id', "UM", readonly=True)
    message                   = fields.Char("Message"     , readonly=True, copy=False)
    alerte                    = fields.Char("Alerte"      , readonly=True, copy=False)
    avertissement             = fields.Char("Avertissement", readonly=True, copy=False)
    anomalies                 = fields.Text("Anomalies"   , readonly=True, copy=False, help="UC sans lot, UC en doublon, UM mixtes : calculées avec les écarts")
    anomalie_bloquante        = fields.Boolean("Anomalie bloquante", readonly=True, copy=False, help="UC sans lot ni Fabrication : validation impossible")
    action_attendue           = fields.Char("Action attendue", compute='_compute_action_attendue')
    info_html                 = fields.Html("Informations"       , compute='_compute_info_html'  , sanitize=False)
    cartes_courant_html       = fields.Html("Cartes de l'emplacement courant", compute='_compute_cartes_html', sanitize=False)
    cartes_autres_html        = fields.Html("Autres emplacements", compute='_compute_cartes_html', sanitize=False)
    ecarts_html               = fields.Html("Écarts (cartes)"    , compute='_compute_ecarts_html', sanitize=False)
    um_non_trouvees_html      = fields.Html("UM non trouvées"    , compute='_compute_ecarts_html', sanitize=False)
    um_a_corriger_html        = fields.Html("UM à corriger"      , compute='_compute_ecarts_html', sanitize=False)
    code                      = fields.Char("Saisie manuelle", copy=False, help="Saisie manuelle (étiquette abîmée, tests sur PC) : même traitement que le scan. N° d'UM (8 chiffres, M ou G + n°), d'UC (S + n°, ou autre n°) ou emplacement (EMP + nom)")
    nb_um                     = fields.Integer("UM scannées"   , readonly=True)
    nb_um_attendues           = fields.Integer("UM attendues"  , readonly=True)
    nb_uc                     = fields.Integer("UC scannées"   , readonly=True)
    nb_uc_attendues           = fields.Integer("UC attendues"  , readonly=True)
    qt_odoo                   = fields.Integer("Qt Odoo"       , readonly=True)
    qt_scannee                = fields.Integer("Qt scannée"    , readonly=True)
    progression               = fields.Float("Progression (%)" , readonly=True, digits=(16,0))
    nb_emplacements           = fields.Integer("Nb emplacements", readonly=True)
    nb_lots                   = fields.Integer("Nb lots"       , readonly=True)
    ecart                     = fields.Integer("Écart"         , readonly=True, help="Qt scannée - Qt Odoo")
    date_derniere_activite    = fields.Datetime("Dernière activité", default=fields.Datetime.now, readonly=True, index=True)
    user_derniere_activite_id = fields.Many2one('res.users', "Dernier utilisateur", default=lambda self: self.env.uid, readonly=True)
    commentaire               = fields.Text("Commentaire")


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('is.inventaire.reference')
        return super().create(vals_list)


    def nouvel_inventaire_action(self):
        "Ouvre l'inventaire vide de l'utilisateur s'il en a un, sinon en crée un, pour qu'il existe en base au premier scan"
        obj = self.search([
            ('create_uid', '=', self.env.uid),
            ('state'     , '=', 'scan'),
            ('scan_ids'  , '=', False),
        ], order='id desc', limit=1)
        if not obj:
            obj = self.create({})
        return obj.voir_inventaire_action()


    def voir_inventaire_action(self):
        for obj in self:
            return {
                'type'     : 'ir.actions.act_window',
                'name'     : obj.name,
                'res_model': self._name,
                'res_id'   : obj.id,
                'view_mode': 'form',
                'target'   : 'current',
            }


    def _verifier_droits(self):
        if not self.env.user.has_group('is_plastigray16.is_magasiniers_group'):
            raise ValidationError("Inventaire d'une référence réservé au groupe Magasiners")


    def _verifier_etat(self, states):
        for obj in self:
            if obj.state not in states:
                raise ValidationError("Action impossible dans l'état « %s »"%dict(_STATE)[obj.state])


    def _noter_activite(self, message=False, alerte=False, avertissement=False):
        self.write({
            'date_derniere_activite'   : fields.Datetime.now(),
            'user_derniere_activite_id': self.env.uid,
            'message'                  : message,
            'alerte'                   : alerte,
            'avertissement'            : avertissement,
        })


    #** Scan et saisie manuelle ***********************************************
    def on_barcode_scanned(self, barcode):
        # Onchange : le traitement se fait sur l'enregistrement en base, puis le formulaire est mis à jour
        origin = self._origin
        _logger.info("Inventaire référence : scan %r sur %s (id=%s)", barcode, origin.name, origin.id)
        origin.traiter_code(barcode)
        for champ in _CHAMPS_FORMULAIRE:
            self[champ] = origin[champ]


    def valider_code_action(self):
        for obj in self:
            code = obj.code
            _logger.info("Inventaire référence : saisie manuelle %r sur %s", code, obj.name)
            obj.code = False
            obj.traiter_code(code, saisie_manuelle=True)


    def _executer(self, libelle, fonction, *args):
        """Exécute une opération de l'inventaire (scan ou bouton). La fonction retourne le message, ou (message, avertissement)
        pour un résultat à vérifier (bandeau orange). Les refus et les erreurs sont affichés dans l'alerte et le chatter,
        et l'opération est annulée (savepoint) sans perdre le message"""
        self.ensure_one()
        try:
            with self.env.cr.savepoint():
                self._verifier_droits()
                res = fonction(*args)
            message, avertissement = res if isinstance(res, tuple) else (res, False)
            _logger.info("Inventaire référence : %s : %s : %s", self.name, libelle, message)
            body = "✅ %s : %s"%(libelle, message)
            if avertissement:
                body += " · ⚠ %s"%avertissement
            self.message_post(body=body)
            self._noter_activite(message=message, avertissement=avertissement)
        except UserError as e:
            _logger.info("Inventaire référence : %s : %s : refus : %s", self.name, libelle, e.args[0])
            self.message_post(body="❌ %s : refusé : %s"%(libelle, e.args[0]))
            self._noter_activite(alerte="%s : %s"%(libelle, e.args[0]))
        except Exception as e:
            _logger.exception("Inventaire référence : %s : %s : erreur", self.name, libelle)
            erreur = "Erreur : %s"%(e.args and e.args[0] or e)
            self.message_post(body="❌ %s : %s"%(libelle, erreur))
            self._noter_activite(alerte="%s : %s"%(libelle, erreur))


    def traiter_code(self, code, saisie_manuelle=False):
        "Traitement d'un code scanné ou saisi : emplacement (EMP + nom), UM (M / G + n°, ou 8 chiffres) ou UC (S + n°, ou autre n°)"
        self.ensure_one()
        code = (code or '').strip().upper()
        if code:
            libelle = "%s %s"%(saisie_manuelle and "Saisie manuelle" or "Scan", code)
            self._executer(libelle, self._traiter_code, code, saisie_manuelle)


    def _traiter_code(self, code, saisie_manuelle):
        self._verifier_etat(['scan'])
        if code.startswith('EMP'):
            return self._scan_emplacement(code[3:])
        prefixe = code[:1]
        if prefixe in ('M', 'G') and code[1:].isdigit():
            type_code, num = 'um', code[1:]
        elif prefixe=='S' and code[1:].isdigit():
            type_code, num = 'uc', code[1:]
        elif code.isdigit():
            # N° d'UM sur 8 chiffres, n° d'UC sur 9 (ou 10)
            type_code, num = (len(code)==8 and 'um' or 'uc'), code
        else:
            raise ValidationError("Code non reconnu : scannez un emplacement (EMP…), une UM ou une UC")
        if not self.location_id:
            raise ValidationError("Scannez d'abord l'emplacement")
        if type_code=='um':
            um = self.env['is.galia.base.um'].with_context(active_test=False).search([('name','=',num)], order='active desc, id desc', limit=1)
            if not um:
                raise ValidationError("UM %s inconnue d'Odoo : la créer avec « Créer et lire UC » puis la rescanner"%num)
            return self._scan_um(um, saisie_manuelle=saisie_manuelle)
        return self._scan_uc(int(num), saisie_manuelle)


    def _scan_emplacement(self, name):
        Location = self.env['stock.location']
        location = Location.search([('name','=',name), ('usage','=','internal')])
        if not location:
            if Location.search([('name','=',name)], limit=1):
                raise ValidationError("%s n'est pas un emplacement interne"%name)
            raise ValidationError("Emplacement %s non trouvé"%name)
        if len(location)>1:
            raise ValidationError("Plusieurs emplacements internes %s"%name)
        if location.is_stock_client:
            raise ValidationError("%s est un stock client (consignation) : exclu de l'inventaire"%name)
        self.location_id = location.id
        if self.product_id:
            self._actualiser()
        return "Emplacement courant : %s"%location.name


    def _get_ucs_um(self, um, product=False):
        "UC de l'UM (de l'article s'il est indiqué). UM archivée : UC archivées comprises"
        domain = [('um_id','=',um.id)]
        if product:
            domain.append(('product_id','=',product.id))
        return self.env['is.galia.base.uc'].with_context(active_test=not um.active).search(domain, order='num_eti')


    def _scan_uc(self, num_eti, saisie_manuelle):
        Uc = self.env['is.galia.base.uc'].with_context(active_test=False)
        order = 'active desc, um_active desc, id desc'
        uc = Uc.browse()
        if self.product_id:
            uc = Uc.search([('num_eti','=',num_eti), ('product_id','=',self.product_id.id)], order=order, limit=1)
        if not uc:
            uc = Uc.search([('num_eti','=',num_eti)], order=order, limit=1)
        if not uc:
            raise ValidationError("UC %s inconnue d'Odoo : la créer avec « Créer et lire UC » puis la rescanner"%num_eti)
        um = uc.um_id
        if self.product_id and uc.product_id!=self.product_id:
            raise ValidationError("UC %s : article %s, autre référence que %s"%(uc.num_eti, uc.product_id.is_code, self.product_id.is_code))
        if not uc.active and um.active:
            raise ValidationError("UC %s archivée (UM %s active)"%(uc.num_eti, um.name))
        if not uc.product_id.is_um_egale_uc and len(self._get_ucs_um(um))>1:
            raise ValidationError("Imprimez l'étiquette de l'UM %s puis scannez l'UM"%um.name)
        return self._scan_um(um, uc=uc, saisie_manuelle=saisie_manuelle)


    def _scan_um(self, um, uc=False, saisie_manuelle=False):
        "UM comptée entière (seulement ses UC de la référence pour une UM mixte) dans l'emplacement courant"
        product = self.product_id
        if not product:
            products = self._get_ucs_um(um).product_id
            if not products:
                raise ValidationError("UM %s sans UC"%um.name)
            if len(products)>1:
                raise ValidationError("UM %s mixte (%s) : scannez d'abord une UM non mixte de la référence"%(um.name, ', '.join(products.mapped('is_code'))))
            product = products
            autre = self.search([('product_id','=',product.id), ('state','in',_STATE_EN_COURS), ('id','!=',self.id)], limit=1)
            if autre:
                raise ValidationError("Inventaire %s en cours sur cet article : le reprendre depuis la liste"%autre.name)
        ucs = self._get_ucs_um(um, product)
        if not ucs:
            ucs_um = self._get_ucs_um(um)
            if not ucs_um:
                raise ValidationError("UM %s sans UC"%um.name)
            if len(ucs_um.product_id)>1:
                raise ValidationError("UM %s mixte sans UC de la référence %s"%(um.name, product.is_code))
            raise ValidationError("UM %s : article %s, autre référence que %s"%(um.name, ucs_um.product_id.is_code, product.is_code))
        deja = self.scan_ids.filtered(lambda s: s.um_id==um and not s.retire)
        if deja:
            raise ValidationError("UM %s déjà comptée en %s par %s"%(um.name, deja[0].location_id.name, deja[0].user_id.name))

        #** Situation de l'UM *************************************************
        location = self.location_id
        avertissements = []
        if not um.active or um.location_id.usage!='internal' or um.location_id.is_stock_client:
            situation = 'hors_stock'
            etat = not um.active and "archivée" or "dans %s"%(um.location_id.name or "aucun emplacement")
            avertissements.append("UM %s %s : à réactiver à la validation"%(um.name, etat))
        elif um.location_id!=location:
            situation = 'autre_emplacement'
            avertissements.append("UM %s enregistrée en %s : emplacement à corriger à la validation"%(um.name, um.location_id.name))
        else:
            situation = 'ok'
        doublons = self.env['is.galia.base.uc'].search([
            ('num_eti'  , 'in', ucs.mapped('num_eti')),
            ('um_id'    , '!=', um.id),
            ('um_active', '=' , True),
        ])
        if doublons:
            avertissements.append("UC en doublon, comptées une seule fois : %s"%", ".join("%s (UM %s)"%(d.num_eti, d.um_id.name) for d in doublons))

        if not self.product_id:
            self.write({
                'product_id': product.id,
                'date_debut': fields.Datetime.now(),
            })
        qt_pieces = sum(ucs.mapped('qt_pieces'))
        scan = self.env['is.inventaire.reference.scan'].create({
            'inventaire_id'   : self.id,
            'location_id'     : location.id,
            'location_odoo_id': um.location_id.id,
            'um_active_odoo'  : um.active,
            'um_id'           : um.id,
            'uc_id'           : uc and uc.id or False,
            'qt_pieces'       : qt_pieces,
            'nb_uc'           : len(ucs),
            'lots'            : self._get_noms_lots(ucs),
            'situation'       : situation,
            'saisie_manuelle' : saisie_manuelle,
            'message'         : " · ".join(avertissements) or False,
        })
        self.dernier_scan_id = scan.id
        retraits = self._actualiser()[0]
        message = "UM %s en %s : %s UC, %s pièces (lot %s)"%(um.name, location.name, len(ucs), qt_pieces, scan.lots)
        if uc:
            message = "UC %s · %s"%(uc.num_eti, message)
        avertissements += retraits
        return message, " · ".join(avertissements) or False


    def _get_noms_lots(self, ucs):
        noms = []
        for uc in ucs:
            for lot, qt_pieces in uc.get_lots():
                nom = lot and lot.name or uc.production or "sans lot"
                if nom not in noms:
                    noms.append(nom)
        return ", ".join(noms)


    #** Actualisation (à chaque scan, fin des scans, recalcul, validation) ****
    def _retirer_scans_modifies(self):
        """Scans retirés automatiquement : UM livrée, archivée ou déplacée par un autre programme depuis son scan, ou
        sans UC de la référence. Les autres scans sont relus (UC ajoutées ou retirées). Retourne les messages des retraits"""
        retraits = []
        for scan in self.scan_ids.filtered(lambda s: not s.retire):
            um = scan.um_id
            motif = False
            if scan.um_active_odoo and not um.active:
                motif = "archivée"
            elif um.location_id!=scan.location_odoo_id:
                if um.location_id.usage=='customer':
                    motif = "livrée"
                    if um.liste_servir_id:
                        motif += " par %s"%um.liste_servir_id.name
                else:
                    motif = "déplacée en %s"%(um.location_id.name or "aucun emplacement")
            ucs = self._get_ucs_um(um, self.product_id)
            if not motif and not ucs:
                motif = "plus aucune UC de la référence"
            if motif:
                message = "UM %s retirée : %s après son scan"%(um.name, motif)
                scan.write({
                    'retire'       : True,
                    'date_retrait' : fields.Datetime.now(),
                    'motif_retrait': message,
                })
                if self.dernier_scan_id==scan:
                    self.dernier_scan_id = False
                self.message_post(body="⚠ %s"%message)
                retraits.append(message)
                continue
            vals = {
                'qt_pieces': sum(ucs.mapped('qt_pieces')),
                'nb_uc'    : len(ucs),
                'lots'     : self._get_noms_lots(ucs),
            }
            if any(scan[k]!=v for k,v in vals.items()):
                scan.write(vals)
        return retraits


    def _calculer_locations(self):
        "Emplacements internes (hors stock client) avec du stock ou des UM actives de l'article, plus les emplacements scannés"
        domain_location = [('location_id.usage','=','internal'), ('location_id.is_stock_client','=',False)]
        quants = self.env['stock.quant'].sudo().search([('product_id','=',self.product_id.id), ('quantity','!=',0)] + domain_location)
        ucs    = self.env['is.galia.base.uc'].search([('product_id','=',self.product_id.id), ('um_active','=',True)] + domain_location)
        scans  = self.scan_ids.filtered(lambda s: not s.retire)
        return quants.location_id | ucs.location_id | scans.location_id | self.location_id


    def _actualiser(self):
        """Relit le stock, les UM et les scans (mouvements faits pendant l'inventaire pris en compte) et met à jour les cartes
        emplacement × lot et les totaux. Retourne les messages des scans retirés automatiquement et les UM attendues
        (UM : emplacement, lots, nb UC, quantité)"""
        self.ensure_one()
        Carte = self.env['is.inventaire.reference.carte']
        if not self.product_id:
            self.carte_ids.unlink()
            self.write({
                'location_ids'   : [(5, 0, 0)],
                'nb_um'          : 0, 'nb_um_attendues': 0, 'nb_uc': 0, 'nb_uc_attendues': 0,
                'qt_odoo'        : 0, 'qt_scannee'     : 0, 'progression': 0,
                'nb_emplacements': 0, 'nb_lots'        : 0,
            })
            return [], {}
        product   = self.product_id
        retraits  = self._retirer_scans_modifies()
        locations = self._calculer_locations()
        donnees   = {}

        def cle(location, lot, uc=False):
            nom = lot and lot.name or (uc and uc.production) or ''
            k = (location.id, nom)
            if k not in donnees:
                donnees[k] = {
                    'location_id'    : location.id,
                    'lot_id'         : lot and lot.id or False,
                    'lot_name'       : nom,
                    'qt_odoo'        : 0,
                    'qt_scannee'     : 0,
                    'ums'            : set(),
                    'nb_uc'          : 0,
                    'ums_attendues'  : set(),
                    'nb_uc_attendues': 0,
                }
            elif lot and not donnees[k]['lot_id']:
                donnees[k]['lot_id'] = lot.id
            return k

        #** Stock Odoo ********************************************************
        quants = self.env['stock.quant'].sudo().search([('product_id','=',product.id), ('location_id','in',locations.ids)])
        for quant in quants:
            donnees[cle(quant.location_id, quant.lot_id)]['qt_odoo'] += quant.quantity

        #** UM et UC attendues (actives dans les emplacements inventoriés) ****
        ums_attendues = {}
        ucs_attendues = self.env['is.galia.base.uc'].search([
            ('product_id' , '=' , product.id),
            ('um_active'  , '=' , True),
            ('location_id', 'in', locations.ids),
        ])
        for uc in ucs_attendues:
            for lot, qt_pieces in uc.get_lots():
                k = cle(uc.location_id, lot, uc)
                donnees[k]['ums_attendues'].add(uc.um_id.id)
                donnees[k]['nb_uc_attendues'] += 1
                if uc.um_id not in ums_attendues:
                    ums_attendues[uc.um_id] = {'location': uc.location_id, 'lots': [], 'nb_uc': 0, 'qt': 0}
                vals = ums_attendues[uc.um_id]
                vals['qt'] += qt_pieces
                if k[1] not in vals['lots']:
                    vals['lots'].append(k[1] or 'sans lot')
            ums_attendues[uc.um_id]['nb_uc'] += 1

        #** UC scannées (UC en doublon comptées une seule fois) ***************
        anomalies  = []
        bloquante  = False
        vus        = {}
        scans      = self.scan_ids.filtered(lambda s: not s.retire).sorted('id')
        nb_uc      = 0
        for scan in scans:
            for uc in self._get_ucs_um(scan.um_id, product):
                if uc.num_eti in vus:
                    anomalies.append("UC %s en doublon dans les UM %s et %s : comptée une seule fois"%(uc.num_eti, vus[uc.num_eti], scan.um_id.name))
                    continue
                vus[uc.num_eti] = scan.um_id.name
                nb_uc += 1
                for lot, qt_pieces in uc.get_lots():
                    if not lot and not uc.production:
                        anomalies.append("UC %s de l'UM %s sans lot ni Fabrication"%(uc.num_eti, scan.um_id.name))
                        bloquante = True
                    k = cle(scan.location_id, lot, uc)
                    donnees[k]['qt_scannee'] += qt_pieces
                    donnees[k]['ums'].add(scan.um_id.id)
                    donnees[k]['nb_uc'] += 1
            if scan.um_id.mixte=='oui' or len(self._get_ucs_um(scan.um_id).product_id)>1:
                anomalies.append("UM %s mixte : seules ses UC de la référence sont prises en compte"%scan.um_id.name)

        #** Cartes emplacement × lot du dernier scan (encadrées) **************
        cles_dernier_scan = set()
        dernier = self.dernier_scan_id
        if dernier and not dernier.retire:
            for uc in self._get_ucs_um(dernier.um_id, product):
                for lot, qt_pieces in uc.get_lots():
                    cles_dernier_scan.add((dernier.location_id.id, lot and lot.name or uc.production or ''))

        #** Mise à jour des cartes (sans les recréer : plusieurs opérateurs) **
        existantes = dict(((c.location_id.id, c.lot_name or ''), c) for c in self.carte_ids)
        for k, d in donnees.items():
            if not (d['qt_odoo'] or d['qt_scannee'] or d['ums_attendues'] or d['ums']):
                continue
            qt_odoo, qt_scannee = d['qt_odoo'], d['qt_scannee']
            if not qt_scannee:
                etat = 'a_faire'
            elif qt_scannee>qt_odoo:
                etat = 'excedent'
            elif qt_scannee==qt_odoo:
                etat = 'complet'
            else:
                etat = 'en_cours'
            vals = {
                'location_id'    : d['location_id'],
                'lot_id'         : d['lot_id'],
                'lot_name'       : d['lot_name'],
                'qt_odoo'        : qt_odoo,
                'qt_scannee'     : qt_scannee,
                'nb_um'          : len(d['ums']),
                'nb_um_attendues': len(d['ums_attendues']),
                'nb_uc'          : d['nb_uc'],
                'nb_uc_attendues': d['nb_uc_attendues'],
                'progression'    : qt_odoo>0 and 100.0*qt_scannee/qt_odoo or (qt_scannee and 100 or 0),
                'etat'           : etat,
                'dernier_scan'   : k in cles_dernier_scan,
            }
            carte = existantes.pop(k, None)
            if carte:
                vals = dict((champ, v) for champ, v in vals.items() if (carte[champ].id if champ in ('location_id', 'lot_id') else carte[champ])!=v)
                if vals:
                    carte.write(vals)
            else:
                vals['inventaire_id'] = self.id
                Carte.create(vals)
        for carte in existantes.values():
            carte.unlink()

        #** Totaux ************************************************************
        cartes  = self.carte_ids
        qt_odoo = sum(cartes.mapped('qt_odoo'))
        qt_scan = sum(cartes.mapped('qt_scannee'))
        self.write({
            'location_ids'      : [(6, 0, locations.ids)],
            'nb_um'             : len(scans),
            'nb_um_attendues'   : len(ums_attendues),
            'nb_uc'             : nb_uc,
            'nb_uc_attendues'   : len(ucs_attendues),
            'qt_odoo'           : qt_odoo,
            'qt_scannee'        : qt_scan,
            'progression'       : qt_odoo>0 and 100.0*qt_scan/qt_odoo or 0,
            'nb_emplacements'   : len(cartes.location_id),
            'nb_lots'           : len(set(cartes.mapped('lot_name'))),
            'anomalies'         : "\n".join(anomalies) or False,
            'anomalie_bloquante': bloquante,
        })
        return retraits, ums_attendues


    #** Écarts ****************************************************************
    def _calculer_ecarts(self):
        "Actualisation puis écarts par emplacement × lot et situation des UM. Retourne les messages des scans retirés"
        self.ensure_one()
        retraits, ums_attendues = self._actualiser()
        self.ecart_ids.unlink()
        self.um_ids.unlink()
        Ecart = self.env['is.inventaire.reference.ecart']
        for carte in self.carte_ids:
            Ecart.create({
                'inventaire_id': self.id,
                'location_id'  : carte.location_id.id,
                'lot_id'       : carte.lot_id.id,
                'lot_name'     : carte.lot_name,
                'qt_odoo'      : carte.qt_odoo,
                'qt_scannee'   : carte.qt_scannee,
                'ecart'        : carte.qt_scannee - carte.qt_odoo,
            })
        Um = self.env['is.inventaire.reference.um']
        scans = self.scan_ids.filtered(lambda s: not s.retire)
        for scan in scans:
            Um.create({
                'inventaire_id'   : self.id,
                'um_id'           : scan.um_id.id,
                'scan_id'         : scan.id,
                'location_odoo_id': scan.location_odoo_id.id,
                'um_active_odoo'  : scan.um_active_odoo,
                'location_scan_id': scan.location_id.id,
                'nb_uc_odoo'      : scan.nb_uc,
                'nb_uc_scannees'  : scan.nb_uc,
                'qt_odoo'         : scan.qt_pieces,
                'qt_scannee'      : scan.qt_pieces,
                'lots'            : scan.lots,
                'situation'       : scan.situation,
            })
        for um, vals in ums_attendues.items():
            if um in scans.um_id:
                continue
            Um.create({
                'inventaire_id'   : self.id,
                'um_id'           : um.id,
                'location_odoo_id': vals['location'].id,
                'um_active_odoo'  : True,
                'nb_uc_odoo'      : vals['nb_uc'],
                'qt_odoo'         : vals['qt'],
                'lots'            : ", ".join(vals['lots']),
                'situation'       : 'non_trouvee',
            })
        self.ecart = sum(self.ecart_ids.mapped('ecart'))
        return retraits


    def _message_ecarts(self, debut):
        ecarts = self.ecart_ids.filtered(lambda e: e.ecart)
        nb_um  = len(self.um_ids.filtered(lambda l: l.situation=='non_trouvee'))
        return "%s : %s ligne%s en écart, écart total %s pièces, %s UM non trouvée%s"%(
            debut, len(ecarts), len(ecarts)>1 and 's' or '', _fmt_signe(self.ecart), nb_um, nb_um>1 and 's' or '',
        )


    #** Boutons ***************************************************************
    def terminer_scans_action(self):
        for obj in self:
            obj._executer("Terminer les scans", obj._terminer_scans)


    def _terminer_scans(self):
        self._verifier_etat(['scan'])
        if not self.product_id:
            raise ValidationError("Aucune UM scannée")
        retraits = self._calculer_ecarts()
        self.write({
            'state'        : 'a_valider',
            'date_fin_scan': fields.Datetime.now(),
        })
        return self._message_ecarts("Scans terminés"), " · ".join(retraits) or False


    def reprendre_scans_action(self):
        for obj in self:
            obj._executer("Reprendre les scans", obj._reprendre_scans)


    def _reprendre_scans(self):
        self._verifier_etat(['a_valider'])
        self.ecart_ids.unlink()
        self.um_ids.unlink()
        self.write({'state': 'scan', 'ecart': 0})
        self._actualiser()
        return "Scans repris"


    def recalculer_ecarts_action(self):
        for obj in self:
            obj._executer("Recalculer les écarts", obj._recalculer_ecarts)


    def _recalculer_ecarts(self):
        self._verifier_etat(['a_valider'])
        retraits = self._calculer_ecarts()
        return self._message_ecarts("Écarts recalculés"), " · ".join(retraits) or False


    def abandonner_action(self):
        for obj in self:
            obj._executer("Abandonner", obj._abandonner)


    def _abandonner(self):
        self._verifier_etat(_STATE_EN_COURS)
        self.state = 'annule'
        return "Inventaire abandonné, rien n'a été modifié"


    def valider_action(self):
        for obj in self:
            obj._executer("Valider l'inventaire", obj._valider)


    def _valider(self):
        "Mise à jour du stock, des UM et des UC pour correspondre au physique (une seule transaction : savepoint de _executer)"
        self._verifier_etat(['a_valider'])
        retraits = self._calculer_ecarts()
        if retraits:
            # Une UM scannée a bougé depuis le calcul des écarts affichés : l'utilisateur doit les revoir
            raise ValidationError("Écarts modifiés depuis leur affichage (%s) : vérifiez-les puis validez à nouveau"%" · ".join(retraits))
        if self.anomalie_bloquante:
            raise ValidationError("Anomalie bloquante : %s"%self.anomalies)
        location_inv = self.env['stock.location'].search([('name','=','INV'), ('usage','=','inventory')], limit=1)
        if not location_inv:
            raise ValidationError("Emplacement 'INV' de type 'Inventaire' non trouvé")
        product = self.product_id
        nom     = "Inventaire %s (%s)"%(self.name, product.is_code)
        Uc      = self.env['is.galia.base.uc'].sudo()
        Lot     = self.env['stock.lot'].sudo()

        #** Stock : un mouvement par emplacement × lot en écart, avec INV *****
        nb_mouvements = 0
        for ecart in self.ecart_ids.filtered(lambda e: e.ecart):
            lot = ecart.lot_id
            if not lot and ecart.lot_name:
                # Lot nommé comme la Fabrication de l'UC, créé s'il n'existe pas
                lot = Lot.search([('product_id','=',product.id), ('name','=',ecart.lot_name)], limit=1)
                if not lot:
                    lot = Lot.create({'name': ecart.lot_name, 'product_id': product.id, 'company_id': self.env.company.id})
                    self.message_post(body="Lot %s créé"%lot.name)
                ecart.lot_id = lot.id
            location = ecart.location_id
            if ecart.ecart>0:
                move = Uc._creer_mouvement_lot(product, ecart.ecart, lot, location_inv, location, nom)
            else:
                move = Uc._creer_mouvement_lot(product, -ecart.ecart, lot, location, location_inv, nom)
            ecart.move_id = move.id
            nb_mouvements += 1

        #** UM et UC **********************************************************
        auteur = self.env.user.partner_id.id
        nb_um  = 0
        for ligne in self.um_ids:
            um = ligne.um_id.sudo()
            if ligne.situation=='autre_emplacement':
                message = "Inventaire %s : UM trouvée en %s au lieu de %s, emplacement corrigé"%(self.name, ligne.location_scan_id.name, um.location_id.name)
                um.location_id = ligne.location_scan_id.id
                um.message_post(body=message, author_id=auteur)
                if len(self._get_ucs_um(um).product_id)>1:
                    self.message_post(body="⚠ UM mixte %s déplacée en %s : stock des autres articles à vérifier"%(um.name, ligne.location_scan_id.name))
                nb_um += 1
            elif ligne.situation=='hors_stock':
                ucs = Uc.with_context(active_test=False).search([('um_id','=',um.id), ('product_id','=',product.id), ('active','=',False)])
                message = "Inventaire %s : UM trouvée en %s alors qu'elle était %s, réactivée"%(
                    self.name, ligne.location_scan_id.name, not um.active and "archivée" or "en %s"%(um.location_id.name or "aucun emplacement"),
                )
                um.write({'active': True, 'location_id': ligne.location_scan_id.id})
                ucs.write({'active': True})
                um.message_post(body=message, author_id=auteur)
                for uc in ucs:
                    uc.message_post(body="Inventaire %s : UC réactivée avec l'UM %s"%(self.name, um.name), author_id=auteur)
                nb_um += 1
            elif ligne.situation=='non_trouvee':
                ucs        = Uc.search([('um_id','=',um.id), ('product_id','=',product.id)])
                autres_ucs = Uc.search([('um_id','=',um.id), ('product_id','!=',product.id)])
                if autres_ucs:
                    # UM mixte : ses UC de la référence vont dans une nouvelle UM mise dans INV, l'UM mixte reste en place
                    um_inv = self.env['is.galia.base.um'].sudo().create({
                        'mixte'      : 'non',
                        'location_id': location_inv.id,
                        'date_fin'   : fields.Datetime.now(),
                    })
                    ucs.write({'um_id': um_inv.id})
                    um_inv.message_post(body="Inventaire %s : UM créée avec les UC de %s non trouvées de l'UM mixte %s"%(self.name, product.is_code, um.name), author_id=auteur)
                    um.message_post(body="Inventaire %s : UC de %s non trouvées (%s) déplacées dans l'UM %s mise dans INV"%(self.name, product.is_code, ", ".join(str(n) for n in ucs.mapped('num_eti')), um_inv.name), author_id=auteur)
                    for uc in ucs:
                        uc.message_post(body="Inventaire %s : UC non trouvée, déplacée de l'UM mixte %s vers l'UM %s mise dans INV"%(self.name, um.name, um_inv.name), author_id=auteur)
                    um = um_inv
                else:
                    um.message_post(body="Inventaire %s : UM non trouvée, mise dans INV (de %s)"%(self.name, um.location_id.name), author_id=auteur)
                # Ni l'UM ni ses UC ne sont archivées : seulement mises dans INV (hors stock). Retrouvée plus tard, elle
                # revient dans le stock par un prochain inventaire (situation « hors stock »)
                um.location_id = location_inv.id
                nb_um += 1

        self.write({
            'state'          : 'valide',
            'date_validation': fields.Datetime.now(),
            'valideur_id'    : self.env.uid,
        })
        return "Inventaire validé : %s mouvement%s de stock (écart %s pièces), %s UM modifiée%s"%(
            nb_mouvements, nb_mouvements>1 and 's' or '', _fmt_signe(self.ecart), nb_um, nb_um>1 and 's' or '',
        )


    #** Accès aux UM, UC et mouvements concernés (vue PC) ********************
    def _get_ums_concernees(self):
        "UM scannées (scans retirés compris) et UM de la situation des UM (non trouvées)"
        return self.scan_ids.um_id | self.um_ids.um_id


    def voir_ums_action(self):
        for obj in self:
            return {
                'name'     : "UM %s"%obj.name,
                'type'     : 'ir.actions.act_window',
                'res_model': 'is.galia.base.um',
                'view_mode': 'tree,form',
                'domain'   : [('id', 'in', obj._get_ums_concernees().ids)],
                # UM archivées comprises (UM archivée par un autre programme puis retrouvée)
                'context'  : {'active_test': False},
            }


    def voir_ucs_action(self):
        for obj in self:
            return {
                'name'     : "UC %s"%obj.name,
                'type'     : 'ir.actions.act_window',
                'res_model': 'is.galia.base.uc',
                'view_mode': 'tree,form',
                'domain'   : [('um_id', 'in', obj._get_ums_concernees().ids), ('product_id', '=', obj.product_id.id)],
                'context'  : {'active_test': False},
            }


    def voir_mouvements_action(self):
        for obj in self:
            return {
                'name'     : "Mouvements %s"%obj.name,
                'type'     : 'ir.actions.act_window',
                'res_model': 'stock.move',
                'view_mode': 'tree,form',
                'domain'   : [('id', 'in', obj.ecart_ids.move_id.ids)],
            }


    #** Retrait d'un scan (poubelle des derniers scans) ***********************
    def _retirer_scan(self, scan):
        self._verifier_etat(['scan'])
        if scan.retire:
            raise ValidationError("Scan déjà retiré")
        scan.write({
            'retire'       : True,
            'date_retrait' : fields.Datetime.now(),
            'motif_retrait': "Retiré par %s"%self.env.user.name,
        })
        if self.dernier_scan_id==scan:
            self.dernier_scan_id = False
        if not self.scan_ids.filtered(lambda s: not s.retire):
            # Plus aucune UM comptée : l'article sera redonné par le prochain scan
            self.write({'product_id': False, 'date_debut': False})
        self._actualiser()
        return "UM %s retirée de l'inventaire"%scan.um_id.name


class is_inventaire_reference_scan(models.Model):
    _name        = 'is.inventaire.reference.scan'
    _description = "Journal des scans de l'inventaire d'une référence"
    _order       = 'id desc'

    inventaire_id    = fields.Many2one('is.inventaire.reference', "Inventaire", required=True, ondelete='cascade', index=True)
    inventaire_state = fields.Selection(related='inventaire_id.state')
    location_id      = fields.Many2one('stock.location', "Emplacement scanné", required=True)
    location_odoo_id = fields.Many2one('stock.location', "Emplacement Odoo", help="Emplacement de l'UM dans Odoo au moment du scan : un changement retire le scan")
    um_active_odoo   = fields.Boolean("UM active au scan")
    um_id            = fields.Many2one('is.galia.base.um', "UM", required=True, index=True)
    uc_id            = fields.Many2one('is.galia.base.uc', "UC scannée", help="UC scannée (article UC=UM ou UC seule dans son UM)")
    qt_pieces        = fields.Integer("Qt pièces", help="Pièces des UC de la référence dans l'UM, relues à chaque actualisation")
    nb_uc            = fields.Integer("Nb UC")
    lots             = fields.Char("Lots")
    user_id          = fields.Many2one('res.users', "Opérateur", default=lambda self: self.env.uid, required=True)
    date_scan        = fields.Datetime("Date", default=fields.Datetime.now, required=True)
    situation        = fields.Selection(_SITUATION_SCAN, "Situation", required=True)
    saisie_manuelle  = fields.Boolean("Saisie manuelle")
    message          = fields.Char("Message")
    retire           = fields.Boolean("Retiré", index=True)
    date_retrait     = fields.Datetime("Date de retrait")
    motif_retrait    = fields.Char("Motif du retrait")


    def retirer_scan_action(self):
        for obj in self:
            inventaire = obj.inventaire_id
            inventaire._executer("Retrait de l'UM %s"%obj.um_id.name, inventaire._retirer_scan, obj)


    def voir_um_action(self):
        for obj in self:
            return obj.um_id.acceder_um_action()


    def voir_uc_action(self):
        for obj in self:
            return obj.uc_id.acceder_uc_action()


class is_inventaire_reference_carte(models.Model):
    _name        = 'is.inventaire.reference.carte'
    _description = "Carte emplacement × lot de l'inventaire d'une référence"
    _order       = 'inventaire_id, location_id, lot_name'

    inventaire_id   = fields.Many2one('is.inventaire.reference', "Inventaire", required=True, ondelete='cascade', index=True)
    location_id     = fields.Many2one('stock.location', "Emplacement", required=True)
    lot_id          = fields.Many2one('stock.lot', "Lot")
    lot_name        = fields.Char("Nom du lot", help="Nom du lot, ou Fabrication de l'UC si le lot n'existe pas (créé à la validation)")
    qt_odoo         = fields.Integer("Qt Odoo")
    qt_scannee      = fields.Integer("Qt scannée")
    nb_um           = fields.Integer("UM scannées")
    nb_um_attendues = fields.Integer("UM attendues")
    nb_uc           = fields.Integer("UC scannées")
    nb_uc_attendues = fields.Integer("UC attendues")
    progression     = fields.Float("Progression (%)", digits=(16,0))
    etat            = fields.Selection(_ETAT_CARTE, "État")
    dernier_scan    = fields.Boolean("Dernier scan")


class is_inventaire_reference_ecart(models.Model):
    _name        = 'is.inventaire.reference.ecart'
    _description = "Écart emplacement × lot de l'inventaire d'une référence"
    _order       = 'inventaire_id, location_id, lot_name'

    inventaire_id  = fields.Many2one('is.inventaire.reference', "Inventaire", required=True, ondelete='cascade', index=True)
    location_id    = fields.Many2one('stock.location', "Emplacement", required=True)
    lot_id         = fields.Many2one('stock.lot', "Lot")
    lot_name       = fields.Char("Nom du lot")
    qt_odoo        = fields.Integer("Qt Odoo")
    qt_scannee     = fields.Integer("Qt scannée")
    ecart          = fields.Integer("Écart", help="Qt scannée - Qt Odoo")
    move_id       = fields.Many2one('stock.move', "Mouvement de stock")


    def voir_mouvement_action(self):
        for obj in self:
            return {
                'type'     : 'ir.actions.act_window',
                'res_model': 'stock.move',
                'res_id'   : obj.move_id.id,
                'view_mode': 'form',
            }


class is_inventaire_reference_um(models.Model):
    _name        = 'is.inventaire.reference.um'
    _description = "Situation des UM de l'inventaire d'une référence"
    _order       = 'inventaire_id, situation, um_id'

    inventaire_id    = fields.Many2one('is.inventaire.reference', "Inventaire", required=True, ondelete='cascade', index=True)
    um_id            = fields.Many2one('is.galia.base.um', "UM", required=True)
    scan_id          = fields.Many2one('is.inventaire.reference.scan', "Scan")
    location_odoo_id = fields.Many2one('stock.location', "Emplacement Odoo", help="Emplacement avant l'inventaire")
    um_active_odoo   = fields.Boolean("UM active avant l'inventaire")
    location_scan_id = fields.Many2one('stock.location', "Emplacement scanné")
    nb_uc_odoo       = fields.Integer("Nb UC Odoo")
    nb_uc_scannees   = fields.Integer("Nb UC scannées")
    qt_odoo          = fields.Integer("Qt Odoo")
    qt_scannee       = fields.Integer("Qt scannée")
    lots             = fields.Char("Lots")
    situation        = fields.Selection(_SITUATION_UM, "Situation", required=True)


    def voir_um_action(self):
        for obj in self:
            return obj.um_id.acceder_um_action()
