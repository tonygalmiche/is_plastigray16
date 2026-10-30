# -*- coding: utf-8 -*-
from odoo import models,fields,api
from odoo.exceptions import ValidationError, UserError
from markupsafe import Markup, escape
import logging
_logger = logging.getLogger(__name__)


_STATE = [
    ('scan'     , 'UM à scanner'),
    ('a_valider', 'À valider'),
    ('termine'  , 'Terminé'),
    ('annule'   , 'Annulé'),
]

# Champs recopiés de l'enregistrement en base vers le formulaire après un scan (on_barcode_scanned est un onchange)
_CHAMPS_FORMULAIRE = [
    'state', 'um_id', 'product_id', 'location_id', 'lot_id', 'ligne_ids', 'ligne_uc_ids', 'message', 'alerte',
]


class is_scinder_um_par_lot(models.Model):
    _name        = 'is.scinder.um.par.lot'
    _inherit     = ['mail.thread', 'barcodes.barcode_events_mixin']
    _description = "Scinder UM par lot (scan)"
    _order       = 'id desc'


    def _get_imprimante_id(self):
        user = self.env.user
        return user.is_zebra_id or user.company_id.is_zebra_id


    @api.depends('state')
    def _compute_action_attendue(self):
        for obj in self:
            action_attendue = False
            if obj.state=='scan':
                action_attendue = "Scannez l'UM"
            if obj.state=='a_valider':
                action_attendue = "Vérifiez puis « Scinder l'UM »"
            obj.action_attendue = action_attendue


    @api.depends('name', 'state', 'um_id', 'product_id', 'location_id', 'ligne_ids', 'ligne_uc_ids')
    def _compute_apercu_html(self):
        couleurs = {'scan': '#17a2b8', 'a_valider': '#fd7e14', 'termine': '#28a745', 'annule': '#8a8f94'}
        for obj in self:
            titre = "<div class='d-flex justify-content-between align-items-center'><b>%s</b><span class='badge' style='background-color:%s;color:#fff'>%s</span></div>"%(
                escape(obj.name or ''), couleurs.get(obj.state, '#8a8f94'), escape(dict(_STATE).get(obj.state, '')),
            )
            info = "<div class='lh-sm'>%s"%titre
            if obj.um_id:
                info += "<b>UM %s</b> · <b>%s</b> <span class='text-muted'>%s</span><br/>En <b>%s</b> · %s lots"%(
                    escape(obj.um_id.name), escape(obj.product_id.is_code or ''), escape(obj.product_id.name or ''),
                    escape(obj.location_id.name or ''), len(obj.ligne_ids),
                )
            info += "</div>"
            obj.info_html = info

            # UC de plusieurs lots : une carte par UC scindée
            cartes_uc = []
            for uc_origine in obj.ligne_uc_ids.uc_origine_id:
                lignes = obj.ligne_uc_ids.filtered(lambda l: l.uc_origine_id==uc_origine)
                detail = []
                for ligne in lignes:
                    if ligne.nouvelle_uc:
                        libelle = "Nouvelle UC %s"%(ligne.uc_id and "%s (carton %s)"%(ligne.uc_id.num_eti, ligne.uc_id.num_carton) or "")
                    else:
                        libelle = "UC %s gardée"%uc_origine.num_eti
                    detail.append("<div>%s : <b>%s</b> pcs du lot <b>%s</b>%s</div>"%(
                        escape(libelle), ligne.quantite, escape(ligne.lot_id.name or ''), escape(ligne.impression or ''),
                    ))
                cartes_uc.append(
                    "<div class='border rounded px-2 py-1 bg-white'>"
                    "<div><b>UC %s</b> (carton %s) · %s pcs</div>"
                    "<div class='small'>%s</div>"
                    "</div>"%(uc_origine.num_eti, uc_origine.num_carton, sum(lignes.mapped('quantite')), "".join(detail))
                )
            obj.uc_html = cartes_uc and "<div class='o_is_cartes'>%s</div>"%"".join(cartes_uc) or False

            # Une carte par lot : UM gardée ou nouvelle UM
            cartes_um = []
            for ligne in obj.ligne_ids:
                if ligne.nouvelle_um:
                    um = ligne.um_id and "Nouvelle UM %s"%ligne.um_id.name or "Nouvelle UM"
                    badge = "<span class='badge ms-1' style='background-color:#fd7e14;color:#fff'>nouvelle</span>"
                else:
                    um = "UM %s"%(ligne.um_id.name or '')
                    badge = "<span class='badge ms-1' style='background-color:#28a745;color:#fff'>gardée</span>"
                cartes_um.append(
                    "<div class='border rounded px-2 py-1 bg-white'>"
                    "<div class='d-flex justify-content-between'><span><b>%s</b>%s</span><span>%s UC · %s pcs</span></div>"
                    "<div class='small text-muted'>Lot %s%s</div>"
                    "</div>"%(escape(um), badge, ligne.nb_uc, ligne.quantite, escape(ligne.lot_id.name or ''), escape(ligne.impression or ''))
                )
            obj.um_html = cartes_um and "<div class='o_is_cartes'>%s</div>"%"".join(cartes_um) or False

            # Étiquettes imprimées automatiquement par « Scinder l'UM »
            etiquettes = False
            if obj.state=='a_valider':
                nb_uc = len(obj.ligne_uc_ids)
                nb_um = len(obj.ligne_ids)
                etiquettes = "Étiquettes imprimées automatiquement : <b>%s UC</b> et <b>%s UM</b>"%(nb_uc, nb_um)
            obj.etiquettes_html = etiquettes


    name            = fields.Char("N°", readonly=True, copy=False, index=True)
    state           = fields.Selection(_STATE, "État", default='scan', required=True, readonly=True, tracking=True, index=True)
    imprimante_id   = fields.Many2one('is.raspberry.zebra', "Imprimante", default=lambda self: self._get_imprimante_id(), tracking=True)
    um_id           = fields.Many2one('is.galia.base.um', "UM scannée", readonly=True, tracking=True, index=True)
    product_id      = fields.Many2one('product.product', "Article", readonly=True, tracking=True, index=True)
    location_id     = fields.Many2one('stock.location', "Emplacement", readonly=True, tracking=True)
    lot_id          = fields.Many2one('stock.lot', "Lot gardé par l'UM", readonly=True, tracking=True, index=True, help="Lot qui a le plus de pièces")
    ligne_ids       = fields.One2many('is.scinder.um.par.lot.ligne', 'scinder_id', "Lots", readonly=True)
    ligne_uc_ids    = fields.One2many('is.scinder.um.par.lot.uc', 'scinder_id', "UC de plusieurs lots", readonly=True)
    code            = fields.Char("Code", copy=False, help="Saisie manuelle d'un code-barres (tests sur PC, étiquette illisible) : même traitement que le scan")
    action_attendue = fields.Char("Action attendue", compute='_compute_action_attendue')
    message         = fields.Char("Message", readonly=True, copy=False)
    alerte          = fields.Char("Alerte" , readonly=True, copy=False)
    info_html       = fields.Html("UM"             , compute='_compute_apercu_html', sanitize=False)
    uc_html         = fields.Html("UC à scinder"   , compute='_compute_apercu_html', sanitize=False)
    um_html         = fields.Html("UM par lot"     , compute='_compute_apercu_html', sanitize=False)
    etiquettes_html = fields.Html("Étiquettes"     , compute='_compute_apercu_html', sanitize=False)


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('is.scinder.um.par.lot')
        return super().create(vals_list)


    def nouveau_action(self):
        "Ouvre la fiche vide de l'utilisateur s'il en a une, sinon en crée une, pour qu'elle existe en base au premier scan"
        obj = self.search([
            ('create_uid', '=', self.env.uid),
            ('state'     , '=', 'scan'),
        ], order='id desc', limit=1)
        if not obj:
            obj = self.create({})
        return obj.voir_action()


    def voir_action(self):
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
            raise ValidationError("Scinder UM par lot réservé au groupe Qualité")


    def _verifier_etat(self, states):
        for obj in self:
            if obj.state not in states:
                raise ValidationError("Action impossible dans l'état « %s »"%dict(_STATE)[obj.state])


    #** Scan et saisie manuelle ***********************************************
    def on_barcode_scanned(self, barcode):
        # Onchange : le traitement se fait sur l'enregistrement en base, puis le formulaire est mis à jour
        origin = self._origin
        _logger.info("Scinder UM par lot : scan %r sur %s (id=%s)", barcode, origin.name, origin.id)
        origin.traiter_code(barcode)
        for champ in _CHAMPS_FORMULAIRE:
            self[champ] = origin[champ]


    def valider_code_action(self):
        for obj in self:
            code = obj.code
            _logger.info("Scinder UM par lot : saisie manuelle %r sur %s", code, obj.name)
            obj.code = False
            obj.traiter_code(code)


    def _executer(self, libelle, fonction, *args):
        """Exécute une opération (scan ou bouton). Les refus et les erreurs sont affichés dans l'alerte
        et le chatter, et l'opération est annulée (savepoint) sans perdre le message"""
        self.ensure_one()
        try:
            with self.env.cr.savepoint():
                self._verifier_droits()
                message = fonction(*args)
            _logger.info("Scinder UM par lot : %s : %s : %s", self.name, libelle, message)
            self.message_post(body="✅ %s : %s"%(libelle, message))
            self.write({'message': message, 'alerte': False})
        except UserError as e:
            _logger.info("Scinder UM par lot : %s : %s : refus : %s", self.name, libelle, e.args[0])
            self.message_post(body="❌ %s : refusé : %s"%(libelle, e.args[0]))
            self.write({'message': False, 'alerte': "%s : %s"%(libelle, e.args[0])})
        except Exception as e:
            _logger.exception("Scinder UM par lot : %s : %s : erreur", self.name, libelle)
            erreur = "Erreur : %s"%(e.args and e.args[0] or e)
            self.message_post(body="❌ %s : %s"%(libelle, erreur))
            self.write({'message': False, 'alerte': "%s : %s"%(libelle, erreur)})


    def traiter_code(self, code):
        self.ensure_one()
        code = (code or '').strip().upper()
        if code:
            self._executer("Scan %s"%code, self._traiter_code, code)


    def _traiter_code(self, code):
        "Scan de l'UM : aperçu de la scission, rien n'est modifié"
        self._verifier_etat(['scan'])
        prefixe = code[:1]
        num     = code[1:]
        if prefixe not in ('M', 'G') or not num.isdigit():
            raise ValidationError("Code non reconnu : scannez une étiquette UM")
        um = self.env['is.galia.base.um'].with_context(active_test=False).search([('name','=',num)], order='active desc, id desc', limit=1)
        if not um:
            raise ValidationError("UM non trouvée")
        self._preparer(um)
        self.state = 'a_valider'
        return "UM %s : %s lots, %s UC à scinder"%(um.name, len(self.ligne_ids), len(self.ligne_uc_ids.uc_origine_id))


    #** Calcul de la scission *************************************************
    def _get_production(self, lot):
        "OF qui porte le nom du lot"
        return self.env['mrp.production'].search([('name','=',lot.name), ('product_id','=',lot.product_id.id)], limit=1)


    def _calculer(self, um):
        """Contrôle l'UM et calcule la scission. Retourne :
        - scissions : [(uc, [(lot, qt), ...])] des UC de plusieurs lots, le lot de la fabrication de l'UC en premier
        - lots      : {lot: {'nb_uc': .., 'quantite': ..}} après la scission des UC
        - lot_um    : lot gardé par l'UM (le plus de pièces, à égalité celui de l'OF de l'UM)"""
        if not um.active:
            raise ValidationError("UM %s archivée"%um.name)
        if um.mixte!='non':
            raise ValidationError("UM %s mixte : créez d'abord les UM homogènes depuis la fiche UM"%um.name)
        if not um.uc_ids:
            raise ValidationError("UM %s sans UC"%um.name)
        if um.location_id.usage!='internal':
            raise ValidationError("UM %s en %s : pas un emplacement interne"%(um.name, um.location_id.name or 'aucun emplacement'))
        if um.liste_servir_id:
            raise ValidationError("UM %s dans la liste à servir %s"%(um.name, um.liste_servir_id.name))
        if um.bon_transfert_id:
            raise ValidationError("UM %s dans le bon de transfert %s"%(um.name, um.bon_transfert_id.name))
        if um.controle_qualite_id:
            raise ValidationError("UM %s dans le contrôle qualité en cours %s"%(um.name, um.controle_qualite_id.name))
        if um.product_id.is_um_egale_uc:
            raise ValidationError("Article %s UC=UM : rien à scinder"%um.product_id.is_code)
        if um.anomalie:
            raise ValidationError("UM %s en anomalie (stock insuffisant dans %s) :\n%s"%(um.name, um.location_id.name, um.anomalie))
        scissions = []
        lots      = {}
        def ajouter(lot, qt):
            if lot not in lots:
                lots[lot] = {'nb_uc': 0, 'quantite': 0}
            lots[lot]['nb_uc']    += 1
            lots[lot]['quantite'] += qt
        for uc in um.uc_ids.sorted('num_eti'):
            # Quantités par lot de l'UC (un même lot peut être sur plusieurs lignes du tableau des lots)
            qt_lots = {}
            for lot,qt in uc.get_lots():
                if not lot:
                    raise ValidationError("UM %s : lot de l'UC %s non trouvé"%(um.name, uc.num_eti))
                qt_lots[lot] = qt_lots.get(lot, 0) + qt
            if len(qt_lots)>1:
                # L'UC garde le lot de sa fabrication
                lot_uc = [lot for lot in qt_lots if lot.name==uc.production]
                if not lot_uc:
                    raise ValidationError("UC %s : le lot de sa fabrication %s n'est pas dans son tableau des lots (%s)"%(
                        uc.num_eti, uc.production, ', '.join(lot.name for lot in qt_lots)))
                lot_uc = lot_uc[0]
                autres = sorted([lot for lot in qt_lots if lot!=lot_uc], key=lambda l: l.name)
                scissions.append((uc, [(lot, qt_lots[lot]) for lot in [lot_uc]+autres]))
            for lot,qt in qt_lots.items():
                ajouter(lot, qt)
        if len(lots)<2:
            raise ValidationError("UM %s d'un seul lot (%s) : rien à faire"%(um.name, ', '.join(lot.name for lot in lots)))
        nom_of = um.production_id.name
        lot_um = max(lots, key=lambda lot: (lots[lot]['quantite'], lot.name==nom_of))
        return scissions, lots, lot_um


    def _preparer(self, um):
        "Aperçu : une ligne par lot et une ligne par partie des UC de plusieurs lots"
        scissions, lots, lot_um = self._calculer(um)
        lignes = []
        for lot in [lot_um] + sorted([lot for lot in lots if lot!=lot_um], key=lambda l: l.name):
            lignes.append((0, 0, {
                'lot_id'     : lot.id,
                'nb_uc'      : lots[lot]['nb_uc'],
                'quantite'   : lots[lot]['quantite'],
                'nouvelle_um': lot!=lot_um,
                'um_id'      : lot==lot_um and um.id or False,
            }))
        lignes_uc = []
        for uc,qt_lots in scissions:
            for i,(lot,qt) in enumerate(qt_lots):
                lignes_uc.append((0, 0, {
                    'uc_origine_id': uc.id,
                    'lot_id'       : lot.id,
                    'quantite'     : qt,
                    'nouvelle_uc'  : i>0,
                    'uc_id'        : i==0 and uc.id or False,
                }))
        self.write({
            'um_id'       : um.id,
            'product_id'  : um.product_id.id,
            'location_id' : um.location_id.id,
            'lot_id'      : lot_um.id,
            'ligne_ids'   : [(5, 0, 0)] + lignes,
            'ligne_uc_ids': [(5, 0, 0)] + lignes_uc,
        })


    #** Boutons ***************************************************************
    def scinder_action(self):
        for obj in self:
            obj._executer("Scinder l'UM %s"%obj.um_id.name, obj._scinder)


    def annuler_action(self):
        "Retour au scan sans rien modifier"
        for obj in self:
            obj._verifier_droits()
            obj._verifier_etat(['a_valider'])
            obj.write({
                'state'       : 'scan',
                'um_id'       : False,
                'product_id'  : False,
                'location_id' : False,
                'lot_id'      : False,
                'ligne_ids'   : [(5, 0, 0)],
                'ligne_uc_ids': [(5, 0, 0)],
                'message'     : False,
                'alerte'      : False,
            })


    def abandonner_action(self):
        for obj in self:
            obj._verifier_droits()
            obj._verifier_etat(['scan', 'a_valider'])
            obj.write({'state': 'annule', 'message': "Abandonné", 'alerte': False})


    def nouvelle_um_action(self):
        return self.nouveau_action()


    #** Scission **************************************************************
    def _scinder(self):
        """Scinde les UC de plusieurs lots, puis l'UM (une nouvelle UM par lot autre que celui de l'UM), dans le même
        emplacement et sans mouvement de stock, puis imprime toutes les étiquettes"""
        self._verifier_etat(['a_valider'])
        um = self.um_id.sudo()
        # Aperçu recalculé : l'UM a pu changer depuis le scan
        self._preparer(um)
        lien_um = Markup('<a href="#" data-oe-model="is.galia.base.um" data-oe-id="%s">%s</a>')
        lien_uc = Markup('<a href="#" data-oe-model="is.galia.base.uc" data-oe-id="%s">%s</a>')
        zpls = {}

        #** UC de plusieurs lots : nouvelle UC pour chaque lot autre que celui de la fabrication de l'UC
        UC = self.env['is.galia.base.uc'].sudo()
        for uc in self.ligne_uc_ids.uc_origine_id.sudo():
            lignes     = self.ligne_uc_ids.filtered(lambda l: l.uc_origine_id==uc)
            ligne_uc   = lignes.filtered(lambda l: not l.nouvelle_uc)
            qt_avant   = uc.qt_pieces
            lots_avant = ', '.join("%s : %s"%(l.lot_id.name, l.qt_pieces) for l in uc.lot_ids)
            nouvelles  = UC
            for ligne in lignes.filtered('nouvelle_uc'):
                production = self._get_production(ligne.lot_id)
                # Étiquette créée dans odoo0 : le savepoint ne l'annule pas en cas d'erreur
                etiquette = self.env['is.galia.base']._creer_etiquette_uc_odoo0(uc, ligne.lot_id.name, ligne.quantite)
                uc_id = UC.creer_uc({
                    'um_id'        : um.id,
                    'num_eti'      : etiquette['num_eti'],
                    'type_eti'     : uc.type_eti,
                    'num_carton'   : etiquette['num_carton'],
                    'qt_pieces'    : ligne.quantite,
                    'date_creation': fields.Datetime.now(),
                    'production_id': production.id,
                    'lot_id'       : ligne.lot_id.id,
                    'production'   : ligne.lot_id.name,
                    'product_id'   : uc.product_id.id,
                    'origine'      : "la scission par lot %s de l'UC %s"%(self.name, uc.num_eti),
                })
                ligne.uc_id = uc_id
                zpls[uc_id] = etiquette['zpl']
                nouvelles |= UC.browse(uc_id)
            uc.write({
                'lot_ids'  : [(5, 0, 0)],
                'lot_id'   : ligne_uc.lot_id.id,
                'qt_pieces': ligne_uc.quantite,
            })
            uc.message_post(body=Markup("Scission par lot %s : quantité %s → %s, lots %s → %s, nouvelles UC : %s")%(
                self.name, qt_avant, ligne_uc.quantite, lots_avant, ligne_uc.lot_id.name,
                Markup(', ').join(lien_uc%(n.id, n.num_eti) for n in nouvelles),
            ))

        #** UM : une nouvelle UM par lot autre que celui de l'UM (même emplacement, sans mouvement de stock)
        nouvelles_um = self.env['is.galia.base.um'].sudo()
        ucs_um = UC.search([('um_id','=',um.id)])
        for ligne in self.ligne_ids.filtered('nouvelle_um'):
            ucs = ucs_um.filtered(lambda uc: uc.get_lots()[0][0]==ligne.lot_id)
            nouvelle_um = nouvelles_um.browse(ucs.picking_um())
            nouvelle_um.write({
                'production_id': self._get_production(ligne.lot_id).id,
                # date_fin renseignée : THEIA ne doit pas prendre cette UM pour l'UM en cours de l'OF
                'date_fin'     : fields.Datetime.now(),
            })
            nouvelle_um.message_post(body=Markup("UM du lot %s créée à partir de l'UM %s (scission par lot %s)")%(ligne.lot_id.name, lien_um%(um.id, um.name), self.name))
            ligne.um_id = nouvelle_um.id
            nouvelles_um |= nouvelle_um
        # L'UM scannée prend l'OF du lot gardé
        production = self._get_production(self.lot_id)
        if production and production!=um.production_id:
            um.production_id = production.id
        um.message_post(body=Markup("Scission par lot %s : lot %s gardé, nouvelles UM : %s")%(
            self.name, self.lot_id.name,
            Markup(', ').join(lien_um%(n.id, n.name) for n in nouvelles_um),
        ))

        #** Impression automatique de toutes les étiquettes : UC scindées, nouvelles UC, UM scannée, nouvelles UM
        nb_erreurs = 0
        for ligne in self.ligne_uc_ids:
            ligne.impression = self._imprimer_uc(ligne.uc_id, zpl=zpls.get(ligne.uc_id.id))
            nb_erreurs += '⚠' in ligne.impression
        for ligne in self.ligne_ids:
            ligne.impression = self._imprimer_um(ligne.um_id)
            nb_erreurs += '⚠' in ligne.impression
        self.state = 'termine'
        message = "UM %s scindée : %s nouvelles UM, %s nouvelles UC"%(um.name, len(nouvelles_um), len(self.ligne_uc_ids.filtered('nouvelle_uc')))
        if nb_erreurs:
            message += " · ⚠ %s étiquettes non imprimées : à réimprimer depuis la fiche UC ou UM"%nb_erreurs
        return message


    #** Impressions sur l'imprimante de la fiche ******************************
    def _imprimante(self):
        if not self.imprimante_id:
            raise ValidationError("Choisissez l'imprimante")
        return self.imprimante_id.name


    def _imprimer(self, libelle, fonction):
        """Une erreur d'impression n'annule pas l'opération (étiquette à réimprimer depuis la fiche UC ou UM).
        Retourne le complément du message"""
        try:
            with self.env.cr.savepoint():
                fonction()
            return " · imprimée"
        except Exception as e:
            _logger.exception("Scinder UM par lot : %s : impression %s", self.name, libelle)
            erreur = e.args and e.args[0] or e
            self.message_post(body="❌ Impression %s : %s"%(libelle, erreur))
            return " · ⚠ non imprimée : %s"%erreur


    def _imprimer_uc(self, uc, zpl=False):
        "Étiquette UC : ZPL déjà généré par odoo0 (nouvelle UC), sinon réimpression avec la nouvelle quantité (UC scindée)"
        def imprimer():
            imprimante = self._imprimante()
            if zpl:
                self.env['is.galia.base'].imprimer_zpl(zpl, imprimante=imprimante)
            else:
                uc.sudo().imprimer_etiquette_uc_action(imprimante=imprimante)
        return self._imprimer("étiquette UC %s"%uc.num_eti, imprimer)


    def _imprimer_um(self, um):
        "Étiquette UM : A5 si le type d'étiquette UM de l'article le demande, sinon l'ancienne"
        def imprimer():
            imprimante = self._imprimante()
            if um.etiquette_um_a5:
                um.sudo().imprimer_etiquette_um_a5(imprimante=imprimante)
            else:
                um.sudo().imprimer_etiquette_um_ancienne(imprimante=imprimante)
        return self._imprimer("étiquette UM %s"%um.name, imprimer)


class is_scinder_um_par_lot_ligne(models.Model):
    _name        = 'is.scinder.um.par.lot.ligne'
    _description = "Scinder UM par lot : lots"
    _order       = 'id'

    scinder_id  = fields.Many2one('is.scinder.um.par.lot', "Fiche", required=True, ondelete='cascade', index=True)
    lot_id      = fields.Many2one('stock.lot', "Lot", required=True)
    nb_uc       = fields.Integer("Nb UC")
    quantite    = fields.Integer("Quantité")
    nouvelle_um = fields.Boolean("Nouvelle UM")
    um_id       = fields.Many2one('is.galia.base.um', "UM", help="UM gardée, ou UM créée pour ce lot")
    impression  = fields.Char("Impression")


    def voir_um_action(self):
        for obj in self:
            return obj.um_id.acceder_um_action()


class is_scinder_um_par_lot_uc(models.Model):
    _name        = 'is.scinder.um.par.lot.uc'
    _description = "Scinder UM par lot : UC de plusieurs lots"
    _order       = 'id'

    scinder_id    = fields.Many2one('is.scinder.um.par.lot', "Fiche", required=True, ondelete='cascade', index=True)
    uc_origine_id = fields.Many2one('is.galia.base.uc', "UC d'origine", required=True)
    lot_id        = fields.Many2one('stock.lot', "Lot", required=True)
    quantite      = fields.Integer("Quantité")
    nouvelle_uc   = fields.Boolean("Nouvelle UC")
    uc_id         = fields.Many2one('is.galia.base.uc', "UC", help="UC d'origine pour le lot de sa fabrication, sinon UC créée pour ce lot")
    impression    = fields.Char("Impression")


    def voir_uc_action(self):
        for obj in self:
            return obj.uc_id.acceder_uc_action()
