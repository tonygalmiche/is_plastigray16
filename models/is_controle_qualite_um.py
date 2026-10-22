# -*- coding: utf-8 -*-
from odoo import models,fields,api
from odoo.exceptions import ValidationError, UserError
from markupsafe import escape
import logging
_logger = logging.getLogger(__name__)


_STATE = [
    ('scan_um', 'Scan des UM'),
    ('tri'    , 'Tri'),
    ('fin'    , 'Fin du contrôle'),
    ('termine', 'Terminé'),
    ('annule' , 'Annulé'),
]

# Une UM n'est que dans un seul contrôle dans ces états
_STATE_EN_COURS = ('scan_um', 'tri', 'fin')

_TYPE_LIGNE = [
    ('um_origine' , "UM d'origine"),
    ('uc_bonne'   , "UC bonne"),
    ('uc_ci'      , "UC en CI"),
    ('fin_um'     , "Fin UM en cours"),
    ('nouvelle_uc', "UC à recontrôler"),
    ('rebut'      , "Rebut"),
]

# Champs recopiés de l'enregistrement en base vers le formulaire après un scan (on_barcode_scanned est un onchange)
_CHAMPS_FORMULAIRE = [
    'state', 'location_id', 'product_id', 'lot_id', 'um_origine_ids', 'ligne_ids', 'ligne_um_origine_ids',
    'um_en_cours_id', 'uc_a_valider_id', 'qt_saisie', 'attente_emplacement', 'um_a_deplacer_id',
    'message', 'alerte', 'date_derniere_activite', 'user_derniere_activite_id',
]

# Scan d'emplacement attendu en état tri
_ATTENTE_EMPLACEMENT = [
    ('fin_um', "Fin UM en cours"),
    ('uc_um' , "UC bonne d'un article UC=UM"),
]


class is_controle_qualite_um(models.Model):
    _name        = 'is.controle.qualite.um'
    _inherit     = ['mail.thread', 'barcodes.barcode_events_mixin']
    _description = "Contrôle qualité des UM par scan"
    _order       = 'date_derniere_activite desc, id desc'


    def _get_imprimante_id(self):
        user = self.env.user
        return user.is_zebra_id or user.company_id.is_zebra_id


    @api.depends('ligne_ids.type', 'ligne_ids.quantite')
    def _compute_quantites(self):
        for obj in self:
            qt = dict((t[0], 0) for t in _TYPE_LIGNE)
            nb_um_origine = 0
            for ligne in obj.ligne_ids:
                qt[ligne.type] += ligne.quantite
                if ligne.type=='um_origine':
                    nb_um_origine+=1
            # Les lignes fin_um ne comptent pas : leurs pièces sont déjà dans uc_bonne
            qt_sortie = qt['uc_bonne'] + qt['uc_ci'] + qt['nouvelle_uc'] + qt['rebut']
            obj.qt_initiale     = qt['um_origine']
            obj.qt_bonne        = qt['uc_bonne']
            obj.qt_ci           = qt['uc_ci']
            obj.qt_nouvelles_uc = qt['nouvelle_uc']
            obj.qt_rebut        = qt['rebut']
            obj.qt_restante     = qt['um_origine'] - qt_sortie
            obj.nb_um_origine   = nb_um_origine
            obj.progression     = qt['um_origine'] and 100.0*qt_sortie/qt['um_origine'] or 0


    @api.depends('state', 'ligne_ids.type', 'uc_a_valider_id', 'attente_emplacement', 'um_a_deplacer_id')
    def _compute_action_attendue(self):
        for obj in self:
            action_attendue = False
            if obj.state=='scan_um':
                action_attendue = "Scannez les UM"
            if obj.state=='tri':
                if obj.attente_emplacement:
                    action_attendue = "Scannez l'emplacement de l'UM %s"%obj.um_a_deplacer_id.name
                elif obj.uc_a_valider_id:
                    action_attendue = "Validez la quantité de l'UC %s"%obj.uc_a_valider_id.num_eti
                else:
                    action_attendue = "Scannez une UC"
            obj.action_attendue   = action_attendue
            # Abandon possible tant qu'aucune UC n'a été traitée
            obj.abandon_possible  = obj.state in ('scan_um', 'tri') and not obj.ligne_ids.filtered(lambda l: l.type!='um_origine')


    @api.depends('name', 'state', 'product_id', 'lot_id', 'location_id', 'ligne_ids', 'qt_initiale', 'qt_restante', 'qt_bonne', 'qt_ci', 'nb_um_origine', 'progression')
    def _compute_info_html(self):
        couleurs = {'scan_um': '#17a2b8', 'tri': '#fd7e14', 'fin': '#dc3545', 'termine': '#28a745', 'annule': '#8a8f94'}
        for obj in self:
            # N° du contrôle et état (pas de barre d'état en en-tête, pour gagner de la place sur smartphone)
            titre = "<div class='d-flex justify-content-between align-items-center'><b>%s</b><span class='badge' style='background-color:%s;color:#fff'>%s</span></div>"%(
                escape(obj.name or ''), couleurs.get(obj.state, '#8a8f94'), escape(dict(_STATE).get(obj.state, '')),
            )
            info = "<div class='lh-sm'>%s</div>"%titre
            if obj.product_id:
                lignes_um    = obj.ligne_ids.filtered(lambda l: l.type=='um_origine')
                qt_a_trier   = sum(lignes_um.mapped('qt_a_trier'))
                nb_uc_triees = len(obj.ligne_ids.filtered(lambda l: l.type in ('uc_bonne', 'uc_ci')))
                nb_uc        = nb_uc_triees + sum(lignes_um.mapped('nb_uc_a_trier'))
                # Pièces écartées : retirées des UC diminuées, à recontrôler ou à mettre au rebut à la fin du contrôle
                qt_ecartees  = obj.qt_restante - qt_a_trier
                progression  = int(round(obj.progression))
                info = (
                    "<div class='lh-sm'>"
                    "%s"
                    "<b>%s</b> <span class='text-muted'>%s</span><br/>"
                    "Lot <b>%s</b> en <b>%s</b> · %s UM · %s pcs<br/>"
                    "À trier <b>%s</b> · écartées <b>%s</b> · bonnes %s · CI %s"
                    "</div>"
                    "<div class='d-flex align-items-center mt-1'>"
                    "<div class='progress flex-grow-1 me-2' style='height:8px'><div class='progress-bar' style='width:%s%%'></div></div>"
                    "<span class='small'>%s / %s UC · %s %%</span>"
                    "</div>"
                )%(
                    titre,
                    escape(obj.product_id.is_code or ''), escape(obj.product_id.name or ''),
                    escape(obj.lot_id.name or ''), escape(obj.location_id.name or ''), obj.nb_um_origine, obj.qt_initiale,
                    qt_a_trier, qt_ecartees, obj.qt_bonne, obj.qt_ci,
                    progression, nb_uc_triees, nb_uc, progression,
                )
            obj.info_html = info


    @api.depends('ligne_ids')
    def _compute_ligne_um_a_trier_ids(self):
        for obj in self:
            obj.ligne_um_a_trier_ids = obj.ligne_ids.filtered(lambda l: l.type=='um_origine' and l.nb_uc_a_trier)


    @api.depends('ligne_ids', 'um_en_cours_id')
    def _compute_um_triees_html(self):
        "Cartes des UM créées ou déplacées par le tri, les plus récentes en haut"
        for obj in self:
            ums = {}
            # Dans l'onchange du scan, les lignes sont des NewId : ordre selon l'id en base (_origin)
            lignes = obj.ligne_ids.filtered(lambda l: l.type in ('uc_bonne', 'uc_ci', 'fin_um'))
            for ligne in sorted(lignes, key=lambda l: l._origin.id or 0):
                um = ligne.um_id
                if um not in ums:
                    ums[um] = {'ucs': [], 'quantite': 0, 'destination': False, 'ordre': 0}
                vals = ums[um]
                vals['ordre'] = ligne._origin.id or 0
                if ligne.type in ('uc_bonne', 'uc_ci'):
                    vals['ucs'].append(ligne)
                    vals['quantite'] += ligne.quantite
                if ligne.location_dest_id:
                    vals['destination'] = ligne.location_dest_id
            cartes   = []
            en_cours = False
            for um, vals in sorted(ums.items(), key=lambda x: -x[1]['ordre']):
                if um==obj.um_en_cours_id:
                    badge = "<span class='badge bg-warning text-dark ms-1'>en cours</span>"
                elif vals['destination']:
                    # Gris en style : la classe bg-secondary ne ressort pas dans le thème Odoo 16
                    couleur = vals['destination'].name=='CI' and '#8a8f94' or '#28a745'
                    badge = "<span class='badge ms-1' style='background-color:%s;color:#fff'>→ %s</span>"%(couleur, escape(vals['destination'].name))
                else:
                    badge = ""
                if um.product_id.is_um_egale_uc:
                    badge += "<span class='badge bg-info text-dark ms-1'>UC=UM</span>"
                ucs = ", ".join("%s%s"%(l.uc_id.num_eti, l.type=='uc_ci' and " (%s)"%l.quantite or "") for l in vals['ucs'])
                carte = (
                    "<div class='border rounded px-2 py-1 bg-white'>"
                    "<div class='d-flex justify-content-between'><span><b>UM %s</b>%s</span><span>%s UC · %s pcs</span></div>"
                    "<div class='small text-muted'>%s</div>"
                    "</div>"%(escape(um.name), badge, len(vals['ucs']), vals['quantite'], ucs)
                )
                # L'UM en cours est affichée à part, au-dessus des UM triées
                if um==obj.um_en_cours_id:
                    en_cours = carte
                else:
                    cartes.append(carte)
            # Grille o_is_cartes (controle_qualite_um.scss) : une colonne sur smartphone, plusieurs sur PC
            obj.um_en_cours_html = en_cours and "<div class='o_is_cartes'>%s</div>"%en_cours
            obj.um_triees_html   = cartes and "<div class='o_is_cartes'>%s</div>"%"".join(cartes) or False


    name                      = fields.Char("N° contrôle", readonly=True, copy=False, index=True)
    ligne_um_a_trier_ids      = fields.One2many('is.controle.qualite.um.ligne', compute='_compute_ligne_um_a_trier_ids', string="UM à trier")
    um_triees_html            = fields.Html("UM triées"  , compute='_compute_um_triees_html', sanitize=False)
    um_en_cours_html          = fields.Html("UM en cours", compute='_compute_um_triees_html', sanitize=False)
    info_html                 = fields.Html("Article et lot", compute='_compute_info_html', sanitize=False)
    state                     = fields.Selection(_STATE, "État", default='scan_um', required=True, readonly=True, tracking=True, index=True)
    imprimante_id             = fields.Many2one('is.raspberry.zebra', "Imprimante", default=lambda self: self._get_imprimante_id(), tracking=True)
    location_id               = fields.Many2one('stock.location', "Emplacement", readonly=True, tracking=True, help="Emplacement Qxx de la 1re UM scannée")
    product_id                = fields.Many2one('product.product', "Article", readonly=True, tracking=True, index=True)
    lot_id                    = fields.Many2one('stock.lot', "Lot", readonly=True, tracking=True, index=True)
    um_origine_ids            = fields.Many2many('is.galia.base.um', 'is_controle_qualite_um_origine_rel', 'controle_id', 'um_id', "UM d'origine", readonly=True)
    um_en_cours_id            = fields.Many2one('is.galia.base.um', "UM en cours", readonly=True, help="UM en cours de remplissage avec les UC bonnes")
    uc_a_valider_id           = fields.Many2one('is.galia.base.uc', "UC à valider", readonly=True, help="UC scannée en attente de validation de sa quantité")
    uc_a_valider_qt           = fields.Integer("Qt de l'UC", related='uc_a_valider_id.qt_pieces')
    uc_a_valider_um_id        = fields.Many2one('is.galia.base.um', "UM de l'UC", related='uc_a_valider_id.um_id')
    qt_saisie                 = fields.Integer("Quantité")
    attente_emplacement       = fields.Selection(_ATTENTE_EMPLACEMENT, "Emplacement attendu", readonly=True, copy=False)
    um_a_deplacer_id          = fields.Many2one('is.galia.base.um', "UM à déplacer", readonly=True, copy=False, help="UM déplacée au scan de l'emplacement")
    qt_initiale               = fields.Integer("Qt initiale"         , compute='_compute_quantites', store=True)
    qt_bonne                  = fields.Integer("Qt bonne"            , compute='_compute_quantites', store=True)
    qt_ci                     = fields.Integer("Qt en CI"            , compute='_compute_quantites', store=True)
    qt_nouvelles_uc           = fields.Integer("Qt à recontrôler"    , compute='_compute_quantites', store=True)
    qt_rebut                  = fields.Integer("Qt rebut"            , compute='_compute_quantites', store=True)
    qt_restante               = fields.Integer("Qt restante"         , compute='_compute_quantites', store=True)
    nb_um_origine             = fields.Integer("Nb UM"               , compute='_compute_quantites', store=True)
    progression               = fields.Float("Progression (%)"       , compute='_compute_quantites', store=True, digits=(16,0))
    date_derniere_activite    = fields.Datetime("Dernière activité"  , default=fields.Datetime.now, readonly=True, index=True)
    user_derniere_activite_id = fields.Many2one('res.users', "Dernier utilisateur", default=lambda self: self.env.uid, readonly=True)
    ligne_ids                 = fields.One2many('is.controle.qualite.um.ligne', 'controle_id', "Journal", readonly=True)
    ligne_um_origine_ids      = fields.One2many('is.controle.qualite.um.ligne', 'controle_id', "Lignes des UM d'origine", readonly=True, domain=[('type','=','um_origine')])
    code                      = fields.Char("Code", copy=False, help="Saisie manuelle d'un code-barres (tests sur PC, étiquette illisible) : même traitement que le scan")
    action_attendue           = fields.Char("Action attendue", compute='_compute_action_attendue')
    abandon_possible          = fields.Boolean("Abandon possible", compute='_compute_action_attendue')
    message                   = fields.Char("Message", readonly=True, copy=False)
    alerte                    = fields.Char("Alerte" , readonly=True, copy=False)


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('is.controle.qualite.um')
        return super().create(vals_list)


    def nouveau_controle_action(self):
        "Ouvre le contrôle vide de l'utilisateur s'il en a un, sinon en crée un, pour qu'il existe en base au premier scan"
        controle = self.search([
            ('create_uid', '=', self.env.uid),
            ('state'     , '=', 'scan_um'),
            ('ligne_ids' , '=', False),
        ], order='id desc', limit=1)
        if not controle:
            controle = self.create({})
        return controle.voir_controle_action()


    def voir_controle_action(self):
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
        if not self.env.user.has_group('is_plastigray16.is_qualite_group'):
            raise ValidationError("Contrôle qualité réservé au groupe Qualité")


    def _verifier_etat(self, states):
        for obj in self:
            if obj.state not in states:
                raise ValidationError("Action impossible dans l'état « %s »"%dict(_STATE)[obj.state])


    def _noter_activite(self, message=False, alerte=False):
        self.write({
            'date_derniere_activite'   : fields.Datetime.now(),
            'user_derniere_activite_id': self.env.uid,
            'message'                  : message,
            'alerte'                   : alerte,
        })


    #** Scan et saisie manuelle ***********************************************
    def on_barcode_scanned(self, barcode):
        # Onchange : le traitement se fait sur l'enregistrement en base, puis le formulaire est mis à jour
        origin = self._origin
        _logger.info("Contrôle qualité UM : scan %r sur %s (id=%s)", barcode, origin.name, origin.id)
        origin.traiter_code(barcode)
        for champ in _CHAMPS_FORMULAIRE:
            self[champ] = origin[champ]


    def valider_code_action(self):
        for obj in self:
            code = obj.code
            _logger.info("Contrôle qualité UM : saisie manuelle %r sur %s", code, obj.name)
            obj.code = False
            obj.traiter_code(code)


    def _executer(self, libelle, fonction, *args):
        """Exécute une opération du contrôle (scan ou bouton). Les refus et les erreurs sont affichés dans l'alerte
        et le chatter, et l'opération est annulée (savepoint) sans perdre le message"""
        self.ensure_one()
        try:
            with self.env.cr.savepoint():
                self._verifier_droits()
                message = fonction(*args)
            _logger.info("Contrôle qualité UM : %s : %s : %s", self.name, libelle, message)
            self.message_post(body="✅ %s : %s"%(libelle, message))
            self._noter_activite(message=message)
        except UserError as e:
            _logger.info("Contrôle qualité UM : %s : %s : refus : %s", self.name, libelle, e.args[0])
            self.message_post(body="❌ %s : refusé : %s"%(libelle, e.args[0]))
            self._noter_activite(alerte="%s : %s"%(libelle, e.args[0]))
        except Exception as e:
            _logger.exception("Contrôle qualité UM : %s : %s : erreur", self.name, libelle)
            erreur = "Erreur : %s"%(e.args and e.args[0] or e)
            self.message_post(body="❌ %s : %s"%(libelle, erreur))
            self._noter_activite(alerte="%s : %s"%(libelle, erreur))


    def traiter_code(self, code):
        "Traitement d'un code scanné ou saisi selon l'état du contrôle"
        self.ensure_one()
        code = (code or '').strip().upper()
        if code:
            self._executer("Scan %s"%code, self._traiter_code, code)


    def _traiter_code(self, code):
        if self.state=='scan_um':
            um = self._get_um_scan_um(code)
            return self._ajouter_um(um)
        if self.state=='tri':
            if self.attente_emplacement:
                return self._scan_emplacement(code)
            # Étiquette UM pendant le tri : ajout direct de l'UM (seules les UC=UM, sans étiquette UM, passent par « Retour à l'ajout des UM »)
            if code[:1] in ('M', 'G'):
                return self._ajouter_um(self._get_um_scan_um(code))
            return self._scan_uc(code)
        raise ValidationError("Aucun scan attendu dans l'état « %s »"%dict(_STATE)[self.state])


    def _get_um_scan_um(self, code):
        "UM d'une étiquette UM (M/G + n°), ou d'une étiquette UC (S + n°) d'un article UC=UM"
        prefixe = code[:1]
        num     = code[1:]
        if prefixe not in ('M', 'G', 'S') or not num.isdigit():
            raise ValidationError("Code non reconnu : scannez une étiquette UM")
        if prefixe=='S':
            uc = self.env['is.galia.base.uc'].with_context(active_test=False).search([('num_eti','=',int(num))], order='active desc, id desc', limit=1)
            if not uc:
                raise ValidationError("UC non trouvée")
            if not uc.active:
                raise ValidationError("UC archivée")
            if not uc.product_id.is_um_egale_uc:
                raise ValidationError("Article %s non UC=UM : scannez l'étiquette UM"%uc.product_id.is_code)
            return uc.um_id
        um = self.env['is.galia.base.um'].with_context(active_test=False).search([('name','=',num)], order='active desc, id desc', limit=1)
        if not um:
            raise ValidationError("UM non trouvée")
        return um


    def _verifier_um(self, um):
        "Refuse l'UM si elle ne peut pas être contrôlée avec les autres UM du contrôle. Retourne son lot"
        if not um.active:
            raise ValidationError("UM %s archivée"%um.name)
        if um.mixte!='non':
            raise ValidationError("UM %s mixte"%um.name)
        if not um.uc_ids:
            raise ValidationError("UM %s sans UC"%um.name)
        if not um.location_id.control_quality:
            raise ValidationError("UM %s en %s : pas un emplacement Contrôle qualité"%(um.name, um.location_id.name))
        if um.liste_servir_id:
            raise ValidationError("UM %s dans la liste à servir %s"%(um.name, um.liste_servir_id.name))
        if um.bon_transfert_id:
            raise ValidationError("UM %s dans le bon de transfert %s"%(um.name, um.bon_transfert_id.name))
        lots = self.env['stock.lot']
        for uc in um.uc_ids:
            for lot,qt_pieces in uc.get_lots():
                if not lot:
                    raise ValidationError("UM %s : lot de l'UC %s non trouvé"%(um.name, uc.num_eti))
                lots |= lot
        if len(lots)>1:
            raise ValidationError("UM %s avec plusieurs lots (%s)"%(um.name, ', '.join(lots.mapped('name'))))
        if self.product_id and um.product_id!=self.product_id:
            raise ValidationError("UM %s : article %s différent de %s"%(um.name, um.product_id.is_code, self.product_id.is_code))
        if self.lot_id and lots!=self.lot_id:
            raise ValidationError("UM %s : lot %s différent de %s"%(um.name, lots.name, self.lot_id.name))
        if self.location_id and um.location_id!=self.location_id:
            raise ValidationError("UM %s : emplacement %s différent de %s"%(um.name, um.location_id.name, self.location_id.name))
        if um.anomalie:
            raise ValidationError("UM %s : stock insuffisant dans %s"%(um.name, um.location_id.name))
        if um in self.um_origine_ids:
            raise ValidationError("UM %s déjà scannée"%um.name)
        autre = self.search([('um_origine_ids','in',um.ids), ('state','in',_STATE_EN_COURS), ('id','!=',self.id)], limit=1)
        if autre:
            raise ValidationError("UM %s déjà dans le contrôle %s"%(um.name, autre.name))
        return lots


    def _ajouter_um(self, um):
        self._verifier_etat(['scan_um', 'tri'])
        lot = self._verifier_um(um)
        vals = {'um_origine_ids': [(4, um.id)]}
        if not self.product_id:
            vals.update({
                'product_id' : um.product_id.id,
                'lot_id'     : lot.id,
                'location_id': um.location_id.id,
            })
        self.write(vals)
        self.env['is.controle.qualite.um.ligne'].create({
            'controle_id': self.id,
            'type'       : 'um_origine',
            'um_id'      : um.id,
            'quantite'   : um.qt_pieces,
        })
        return "UM %s ajoutée : %s UC, %s pièces"%(um.name, um.nb_uc, um.qt_pieces)


    #** Boutons ***************************************************************
    def commencer_tri_action(self):
        for obj in self:
            obj._verifier_droits()
            obj._verifier_etat(['scan_um'])
            if not obj.ligne_um_origine_ids:
                raise ValidationError("Scannez au moins une UM avant de commencer le tri")
            obj.state = 'tri'
            obj._noter_activite(message="Tri commencé")


    def ajouter_um_action(self):
        for obj in self:
            obj._verifier_droits()
            obj._verifier_etat(['tri'])
            obj._verifier_rien_en_attente()
            obj.state = 'scan_um'
            obj._noter_activite()


    def abandonner_action(self):
        for obj in self:
            obj._verifier_droits()
            if not obj.abandon_possible:
                raise ValidationError("Abandon impossible : des UC ont déjà été traitées, il faut aller jusqu'à « Fin du contrôle »")
            obj.state = 'annule'
            obj._noter_activite(message="Contrôle abandonné, UM libérées")


    def valider_uc_action(self):
        for obj in self:
            obj._executer("UC %s"%obj.uc_a_valider_id.num_eti, obj._valider_uc)


    def annuler_action(self):
        "Annule l'UC en attente de validation ou le scan d'emplacement attendu"
        for obj in self:
            obj.write({
                'uc_a_valider_id'    : False,
                'qt_saisie'          : 0,
                'attente_emplacement': False,
                'um_a_deplacer_id'   : False,
            })
            obj._noter_activite()


    def fin_um_en_cours_action(self):
        for obj in self:
            obj._executer("Fin UM en cours", obj._fin_um_en_cours)


    #** Tri des UC (état tri) *************************************************
    def _verifier_rien_en_attente(self):
        if self.uc_a_valider_id and not self.attente_emplacement:
            raise ValidationError("Validez ou annulez d'abord l'UC %s"%self.uc_a_valider_id.num_eti)
        if self.attente_emplacement:
            raise ValidationError("Scannez d'abord l'emplacement de l'UM %s, ou annulez"%self.um_a_deplacer_id.name)


    def _scan_uc(self, code):
        "Scan d'une UC à trier : elle est mise en attente de validation de sa quantité"
        self._verifier_rien_en_attente()
        prefixe = code[:1]
        num     = code[1:]
        if prefixe!='S' or not num.isdigit():
            raise ValidationError("Code non reconnu : scannez une étiquette UC")
        uc = self.env['is.galia.base.uc'].with_context(active_test=False).search([('num_eti','=',int(num))], order='active desc, id desc', limit=1)
        if not uc:
            raise ValidationError("UC non trouvée")
        if not uc.active:
            raise ValidationError("UC archivée")
        if self.ligne_ids.filtered(lambda l: l.uc_id==uc and l.type!='um_origine'):
            raise ValidationError("UC %s déjà triée"%uc.num_eti)
        if uc.um_id not in self.ligne_um_origine_ids.um_id:
            raise ValidationError("UC %s dans l'UM %s, qui n'est pas une UM de ce contrôle"%(uc.num_eti, uc.um_id.name))
        self.write({
            'uc_a_valider_id': uc.id,
            'qt_saisie'      : uc.qt_pieces,
        })
        return "UC %s : %s pièces, à valider"%(uc.num_eti, uc.qt_pieces)


    def _valider_uc(self):
        "Validation de la quantité de l'UC : UC bonne (quantité inchangée) ou UC diminuée envoyée en CI"
        self._verifier_etat(['tri'])
        uc = self.uc_a_valider_id
        if not uc:
            raise ValidationError("Aucune UC à valider")
        if self.attente_emplacement:
            raise ValidationError("Scannez d'abord l'emplacement de l'UM %s, ou annulez"%self.um_a_deplacer_id.name)
        qt = self.qt_saisie
        if qt<=0:
            raise ValidationError("La quantité doit être supérieure à 0")
        if qt>uc.qt_pieces:
            raise ValidationError("Quantité %s supérieure à celle de l'UC (%s) : augmentation interdite"%(qt, uc.qt_pieces))
        um_origine = uc.um_id
        if qt<uc.qt_pieces:
            message = self._uc_diminuee(uc, qt)
            self.write({'uc_a_valider_id': False, 'qt_saisie': 0})
            return message
        if uc.product_id.is_um_egale_uc:
            # UC=UM : l'UC reste seule dans son UM, déplacée au scan de l'emplacement
            self.write({
                'attente_emplacement': 'uc_um',
                'um_a_deplacer_id'   : um_origine.id,
                'qt_saisie'          : 0,
            })
            return "UC %s bonne (%s pièces) : scannez l'emplacement de l'UM %s"%(uc.num_eti, qt, um_origine.name)
        um_en_cours = self.um_en_cours_id
        if um_en_cours:
            uc.sudo().picking_um(um_dest_id=um_en_cours.id)
        else:
            um_en_cours = self.env['is.galia.base.um'].browse(uc.sudo().picking_um())
            # date_fin renseignée : THEIA ne doit pas prendre cette UM pour l'UM en cours de l'OF
            um_en_cours.sudo().date_fin = fields.Datetime.now()
            self.um_en_cours_id = um_en_cours.id
        self._sortir_um_vide(um_origine)
        self.env['is.controle.qualite.um.ligne'].create({
            'controle_id'  : self.id,
            'type'         : 'uc_bonne',
            'uc_id'        : uc.id,
            'um_origine_id': um_origine.id,
            'um_id'        : um_en_cours.id,
            'quantite'     : qt,
        })
        self.write({'uc_a_valider_id': False, 'qt_saisie': 0})
        return "UC %s bonne (%s pièces) mise dans l'UM en cours %s"%(uc.num_eti, qt, um_en_cours.name)


    def _uc_diminuee(self, uc, qt):
        "UC diminuée : nouvelle quantité, étiquette à réimprimer, seule dans une UM déplacée en CI"
        if len(uc.lot_ids)>1:
            raise ValidationError("UC %s avec plusieurs lignes de lots : quantité non modifiable ici"%uc.num_eti)
        location_ci = self._get_location('CI')
        um_origine  = uc.um_id
        qt_avant    = uc.qt_pieces
        vals = {'qt_pieces': qt}
        if uc.lot_ids:
            vals['lot_ids'] = [(1, uc.lot_ids.id, {'qt_pieces': qt})]
        uc.sudo().write(vals)
        uc.sudo().message_post(body="Contrôle qualité %s : quantité %s → %s"%(self.name, qt_avant, qt))
        self._imprimer_uc(uc)
        if uc.product_id.is_um_egale_uc:
            um = um_origine
        else:
            um = self.env['is.galia.base.um'].browse(uc.sudo().picking_um())
            um.sudo().date_fin = fields.Datetime.now()
            self._sortir_um_vide(um_origine)
        moves = self._deplacer_um(um, location_ci)
        self.env['is.controle.qualite.um.ligne'].create({
            'controle_id'     : self.id,
            'type'            : 'uc_ci',
            'uc_id'           : uc.id,
            'um_origine_id'   : um_origine.id,
            'um_id'           : um.id,
            'quantite'        : qt,
            'location_dest_id': location_ci.id,
            'move_ids'        : [(6, 0, moves.ids)],
        })
        return "UC %s diminuée (%s → %s pièces), UM %s déplacée en CI"%(uc.num_eti, qt_avant, qt, um.name)


    def _fin_um_en_cours(self):
        self._verifier_etat(['tri'])
        self._verifier_rien_en_attente()
        um = self.um_en_cours_id
        if not um:
            raise ValidationError("Aucune UM en cours")
        self._imprimer_um(um)
        self.write({
            'attente_emplacement': 'fin_um',
            'um_a_deplacer_id'   : um.id,
        })
        return "UM %s terminée (%s UC, %s pièces) : scannez son emplacement"%(um.name, um.nb_uc, um.qt_pieces)


    def _scan_emplacement(self, code):
        "Scan de l'emplacement de destination de l'UM en attente (fin UM en cours, ou UC bonne d'un article UC=UM)"
        if not code.startswith('EMP'):
            raise ValidationError("Scannez l'étiquette d'un emplacement (EMP…)")
        location = self._get_location(code[3:])
        um = self.um_a_deplacer_id
        moves = self._deplacer_um(um, location)
        if self.attente_emplacement=='fin_um':
            self.env['is.controle.qualite.um.ligne'].create({
                'controle_id'     : self.id,
                'type'            : 'fin_um',
                'um_id'           : um.id,
                'quantite'        : um.qt_pieces,
                'location_dest_id': location.id,
                'move_ids'        : [(6, 0, moves.ids)],
            })
            self.um_en_cours_id = False
            message = "UM %s déplacée en %s"%(um.name, location.name)
        else:
            uc = self.uc_a_valider_id
            self.env['is.controle.qualite.um.ligne'].create({
                'controle_id'     : self.id,
                'type'            : 'uc_bonne',
                'uc_id'           : uc.id,
                'um_origine_id'   : um.id,
                'um_id'           : um.id,
                'quantite'        : uc.qt_pieces,
                'location_dest_id': location.id,
                'move_ids'        : [(6, 0, moves.ids)],
            })
            message = "UC %s bonne, UM %s déplacée en %s"%(uc.num_eti, um.name, location.name)
        self.write({
            'uc_a_valider_id'    : False,
            'attente_emplacement': False,
            'um_a_deplacer_id'   : False,
        })
        return message


    def _sortir_um_vide(self, um):
        "UM d'origine vidée par picking_um (qui l'archive) : mise tout de suite dans INV, sans attendre la fin du contrôle"
        um = um.sudo()
        if not um.active:
            um.mettre_um_archivee_dans_inv_action()


    def _get_location(self, name):
        locations = self.env['stock.location'].search([('name','=',name), ('usage','=','internal')])
        if not locations:
            raise ValidationError("Emplacement interne %s non trouvé"%name)
        if len(locations)>1:
            raise ValidationError("Plusieurs emplacements internes %s"%name)
        return locations


    def _deplacer_um(self, um, location):
        "Déplace l'UM et son stock (deplacer_um_action). Retourne les mouvements créés"
        if um.location_id==location:
            return self.env['stock.move']
        um    = um.sudo()
        Move  = self.env['stock.move'].sudo()
        # stock_move.reference n'est pas indexé (8 millions de lignes) : recherche limitée aux mouvements créés ici
        self.env.cr.execute("SELECT COALESCE(MAX(id), 0) FROM stock_move")
        id_max = self.env.cr.fetchone()[0]
        um.location_dest_id = location.id
        um.deplacer_um_action()
        return Move.search([('id','>',id_max), ('reference','=',"UM %s"%um.name)])


    #** Impressions (étape 6) *************************************************
    def _imprimer_uc(self, uc):
        self.message_post(body="Étiquette UC %s à réimprimer (%s pièces) : impression à l'étape 6"%(uc.num_eti, uc.qt_pieces))


    def _imprimer_um(self, um):
        format_um = um.etiquette_um_a5 and "A5" or "ancienne"
        self.message_post(body="Étiquette UM %s (%s) à imprimer : impression à l'étape 6"%(um.name, format_um))


class is_controle_qualite_um_ligne(models.Model):
    _name        = 'is.controle.qualite.um.ligne'
    _description = "Journal du contrôle qualité des UM par scan"
    _order       = 'id'

    controle_id      = fields.Many2one('is.controle.qualite.um', "Contrôle", required=True, ondelete='cascade', index=True)
    date             = fields.Datetime("Date", default=fields.Datetime.now, required=True)
    user_id          = fields.Many2one('res.users', "Utilisateur", default=lambda self: self.env.uid, required=True)
    type             = fields.Selection(_TYPE_LIGNE, "Type", required=True)
    uc_id            = fields.Many2one('is.galia.base.uc', "UC")
    um_origine_id    = fields.Many2one('is.galia.base.um', "UM d'origine", help="UM d'où vient l'UC")
    um_id            = fields.Many2one('is.galia.base.um', "UM")
    quantite         = fields.Integer("Quantité")
    location_dest_id = fields.Many2one('stock.location', "Destination")
    move_ids         = fields.Many2many('stock.move', 'is_controle_qualite_um_ligne_move_rel', 'ligne_id', 'move_id', "Mouvements de stock")
    nb_uc            = fields.Integer("Nb UC", related='um_id.nb_uc')
    controle_state   = fields.Selection(related='controle_id.state')
    nb_uc_a_trier    = fields.Integer("UC à trier", compute='_compute_nb_uc_a_trier')
    qt_a_trier       = fields.Integer("Qt à trier", compute='_compute_nb_uc_a_trier')


    @api.depends('um_id', 'controle_id.ligne_ids')
    def _compute_nb_uc_a_trier(self):
        "UC de l'UM d'origine pas encore triées (une UC=UM triée reste dans son UM)"
        for obj in self:
            ucs_triees = obj.controle_id.ligne_ids.filtered(lambda l: l.type in ('uc_bonne', 'uc_ci')).uc_id
            ucs = obj.um_id.uc_ids - ucs_triees
            obj.nb_uc_a_trier = len(ucs)
            obj.qt_a_trier    = sum(ucs.mapped('qt_pieces'))


    def retirer_um_action(self):
        "Retire l'UM du contrôle, tant qu'aucune de ses UC n'a été traitée"
        for obj in self:
            controle = obj.controle_id
            controle._verifier_droits()
            controle._verifier_etat(['scan_um'])
            if obj.type!='um_origine':
                raise ValidationError("Seule une ligne d'UM d'origine peut être retirée")
            um = obj.um_id
            if controle.ligne_ids.filtered(lambda l: l.type in ('uc_bonne', 'uc_ci') and l.um_origine_id==um):
                raise ValidationError("Retrait impossible : des UC de l'UM %s ont déjà été traitées"%um.name)
            controle.um_origine_ids = [(3, um.id)]
            # Journal non modifiable par le groupe Qualité : suppression de la ligne en sudo
            obj.sudo().unlink()
            if not controle.um_origine_ids:
                controle.write({'product_id': False, 'lot_id': False, 'location_id': False})
            message = "UM %s retirée du contrôle %s"%(um.name, controle.name)
            controle.message_post(body="✅ %s"%message)
            um.sudo().message_post(body="✅ %s"%message, author_id=self.env.user.partner_id.id)
            controle._noter_activite(message=message)


class is_galia_base_um(models.Model):
    _inherit = 'is.galia.base.um'

    def _compute_controle_qualite_id(self):
        for obj in self:
            obj.controle_qualite_id = self.env['is.controle.qualite.um'].search([
                ('um_origine_ids', 'in', obj.ids),
                ('state'         , 'in', _STATE_EN_COURS),
            ], limit=1)

    controle_qualite_id = fields.Many2one('is.controle.qualite.um', "Contrôle qualité en cours", compute='_compute_controle_qualite_id')
