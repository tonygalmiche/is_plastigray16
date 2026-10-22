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
    'message', 'alerte', 'date_derniere_activite', 'user_derniere_activite_id',
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


    @api.depends('state', 'ligne_ids.type')
    def _compute_action_attendue(self):
        for obj in self:
            action_attendue = False
            if obj.state=='scan_um':
                action_attendue = "Scannez les UM"
            if obj.state=='tri':
                action_attendue = "Scannez une UC"
            obj.action_attendue   = action_attendue
            # Abandon possible tant qu'aucune UC n'a été traitée
            obj.abandon_possible  = obj.state in ('scan_um', 'tri') and not obj.ligne_ids.filtered(lambda l: l.type!='um_origine')


    @api.depends('product_id', 'lot_id', 'location_id', 'qt_initiale', 'qt_restante', 'nb_um_origine')
    def _compute_info_html(self):
        for obj in self:
            info = False
            if obj.product_id:
                info = (
                    "<div class='lh-sm'>"
                    "<b>%s</b> <span class='text-muted'>%s</span><br/>"
                    "Lot <b>%s</b> en <b>%s</b> · %s UM · reste <b>%s</b> / %s"
                    "</div>"
                )%(
                    escape(obj.product_id.is_code or ''), escape(obj.product_id.name or ''),
                    escape(obj.lot_id.name or ''), escape(obj.location_id.name or ''),
                    obj.nb_um_origine, obj.qt_restante, obj.qt_initiale,
                )
            obj.info_html = info


    name                      = fields.Char("N° contrôle", readonly=True, copy=False, index=True)
    info_html                 = fields.Html("Article et lot", compute='_compute_info_html', sanitize=False)
    state                     = fields.Selection(_STATE, "État", default='scan_um', required=True, readonly=True, tracking=True, index=True)
    imprimante_id             = fields.Many2one('is.raspberry.zebra', "Imprimante", default=lambda self: self._get_imprimante_id(), tracking=True)
    location_id               = fields.Many2one('stock.location', "Emplacement", readonly=True, tracking=True, help="Emplacement Qxx de la 1re UM scannée")
    product_id                = fields.Many2one('product.product', "Article", readonly=True, tracking=True, index=True)
    lot_id                    = fields.Many2one('stock.lot', "Lot", readonly=True, tracking=True, index=True)
    um_origine_ids            = fields.Many2many('is.galia.base.um', 'is_controle_qualite_um_origine_rel', 'controle_id', 'um_id', "UM d'origine", readonly=True)
    um_en_cours_id            = fields.Many2one('is.galia.base.um', "UM en cours", readonly=True, help="UM en cours de remplissage avec les UC bonnes")
    uc_a_valider_id           = fields.Many2one('is.galia.base.uc', "UC à valider", readonly=True, help="UC scannée en attente de validation de sa quantité")
    qt_saisie                 = fields.Integer("Quantité")
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


    def traiter_code(self, code):
        "Traitement d'un code scanné ou saisi selon l'état du contrôle. Les refus et les erreurs sont affichés dans l'alerte et le chatter"
        self.ensure_one()
        self._verifier_droits()
        code = (code or '').strip().upper()
        if not code:
            return
        try:
            # Savepoint : en cas de refus ou d'erreur, le traitement est annulé mais le message reste enregistré
            with self.env.cr.savepoint():
                if self.state=='scan_um':
                    um = self._get_um_scan_um(code)
                    message = self._ajouter_um(um)
                elif self.state=='tri':
                    raise ValidationError("Scan des UC : pas encore développé (étape 4)")
                else:
                    raise ValidationError("Aucun scan attendu dans l'état « %s »"%dict(_STATE)[self.state])
            _logger.info("Contrôle qualité UM : %s : %s : %s", self.name, code, message)
            self.message_post(body="✅ Scan %s : %s"%(code, message))
            self._noter_activite(message=message)
        except UserError as e:
            _logger.info("Contrôle qualité UM : %s : %s : refus : %s", self.name, code, e.args[0])
            self.message_post(body="❌ Scan %s : refusé : %s"%(code, e.args[0]))
            self._noter_activite(alerte="%s : %s"%(code, e.args[0]))
        except Exception as e:
            _logger.exception("Contrôle qualité UM : %s : %s : erreur", self.name, code)
            erreur = "Erreur : %s"%(e.args and e.args[0] or e)
            self.message_post(body="❌ Scan %s : %s"%(code, erreur))
            self._noter_activite(alerte="%s : %s"%(code, erreur))


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
        self._verifier_etat(['scan_um'])
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
            obj.state = 'scan_um'
            obj._noter_activite()


    def abandonner_action(self):
        for obj in self:
            obj._verifier_droits()
            if not obj.abandon_possible:
                raise ValidationError("Abandon impossible : des UC ont déjà été traitées, il faut aller jusqu'à « Fin du contrôle »")
            obj.state = 'annule'
            obj._noter_activite(message="Contrôle abandonné, UM libérées")


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
