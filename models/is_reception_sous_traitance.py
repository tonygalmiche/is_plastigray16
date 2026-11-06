# -*- coding: utf-8 -*-
from odoo import models,fields,api
from odoo.exceptions import ValidationError, UserError
from markupsafe import Markup, escape
from xmlrpc import client as xmlrpclib
import logging
import math
_logger = logging.getLogger(__name__)


# Réception sous-traitance par scan (demande 2151) : choix du fournisseur (segment d'achat « Sous-traitance »),
# puis de la commande, scan des UC (étiquettes de type Commande d'odoo0), puis validation de la réception


_STATE = [
    ('scan'   , 'UC à scanner'),
    ('termine', 'Terminé'),
    ('annule' , 'Annulé'),
]

# Champs recopiés de l'enregistrement en base vers le formulaire après un scan (on_barcode_scanned est un onchange)
_CHAMPS_FORMULAIRE = ['state', 'um_id', 'ligne_ids', 'message', 'alerte']


def _receptions_ouvertes_domain():
    "Réceptions de commandes d'achat à traiter (comme le menu « Réceptions à traiter »)"
    return [
        ('picking_type_id.code', '=', 'incoming'),
        ('state'               , 'in', ('waiting', 'confirmed', 'assigned')),
        ('purchase_id'         , '!=', False),
    ]


class res_partner(models.Model):
    _inherit = 'res.partner'

    is_reception_st_nb = fields.Integer("Réceptions en cours", compute='_compute_is_reception_st_nb')

    def _compute_is_reception_st_nb(self):
        for obj in self:
            obj.is_reception_st_nb = self.env['stock.picking'].search_count(_receptions_ouvertes_domain()+[('purchase_id.partner_id', '=', obj.id)])


    def reception_st_commandes_action(self):
        "Écran 2 : commandes en cours du fournisseur"
        self.ensure_one()
        return {
            'type'     : 'ir.actions.act_window',
            'name'     : self.name,
            'res_model': 'stock.picking',
            'view_mode': 'kanban',
            'views'    : [(self.env.ref('is_plastigray16.is_reception_st_picking_kanban_view').id, 'kanban')],
            'domain'   : _receptions_ouvertes_domain()+[('purchase_id.partner_id', '=', self.id)],
            'target'   : 'current',
        }


class stock_picking(models.Model):
    _inherit = 'stock.picking'

    is_reception_st_qt    = fields.Float("Quantité à recevoir", compute='_compute_is_reception_st_qt', digits=(14, 2))
    is_reception_st_nb_uc = fields.Integer("UC théoriques"     , compute='_compute_is_reception_st_qt')

    def _compute_is_reception_st_qt(self):
        "Quantité à recevoir et nombre d'UC théorique (quantité / quantité par UC du conditionnement, arrondi au-dessus)"
        for obj in self:
            moves = obj.move_ids_without_package.filtered(lambda m: m.state not in ('done', 'cancel'))
            obj.is_reception_st_qt    = sum(moves.mapped('product_uom_qty'))
            obj.is_reception_st_nb_uc = sum(math.ceil(m.product_uom_qty/m.product_id.product_tmpl_id.get_uc()) for m in moves)


    def reception_st_scanner_action(self):
        "Commande choisie : reprend la fiche en cours de cette réception, sinon en crée une"
        self.ensure_one()
        Fiche = self.env['is.reception.sous.traitance']
        Fiche._verifier_droits()
        fiche = Fiche.search([('picking_id', '=', self.id), ('state', '=', 'scan')], order='id desc', limit=1)
        if not fiche:
            Fiche._verifier_commande(self)
            fiche = Fiche.create({'picking_id': self.id})
        return fiche.voir_action()


class is_reception_sous_traitance(models.Model):
    _name        = 'is.reception.sous.traitance'
    _inherit     = ['mail.thread', 'barcodes.barcode_events_mixin']
    _description = "Réception sous-traitance (scan)"
    _order       = 'id desc'


    def _get_imprimante_id(self):
        user = self.env.user
        return user.is_zebra_id or user.company_id.is_zebra_id


    @api.depends('picking_id')
    def _compute_commande(self):
        for obj in self:
            picking = obj.picking_id
            move    = picking.move_ids_without_package.filtered(lambda m: m.state not in ('done', 'cancel'))[:1]
            obj.partner_id  = picking.purchase_id.partner_id
            obj.purchase_id = picking.purchase_id
            obj.move_id     = move
            obj.product_id  = move.product_id


    @api.depends('move_id', 'ligne_ids.quantite')
    def _compute_quantites(self):
        for obj in self:
            obj.qt_attendue = obj.move_id.product_uom_qty
            obj.qt_scannee  = sum(obj.ligne_ids.mapped('quantite'))


    @api.depends('state', 'um_id', 'ligne_ids')
    def _compute_action_attendue(self):
        for obj in self:
            action_attendue = False
            if obj.state=='scan':
                action_attendue = "Scannez les UC, « Fin UM » à la fin de chaque palette, puis « Fin de contrôle »"
            obj.action_attendue = action_attendue


    @api.depends('name', 'state', 'picking_id', 'um_id', 'ligne_ids', 'ligne_ids.quantite')
    def _compute_html(self):
        couleurs = {'scan': '#17a2b8', 'termine': '#28a745', 'annule': '#8a8f94'}
        for obj in self:
            # N° et état masqués sur smartphone (d-none d-md-flex) : le bandeau « action attendue » suffit
            titre = "<div class='d-none d-md-flex justify-content-between align-items-center'><b>%s</b><span class='badge' style='background-color:%s;color:#fff'>%s</span></div>"%(
                escape(obj.name or ''), couleurs.get(obj.state, '#8a8f94'), escape(dict(_STATE).get(obj.state, '')),
            )
            info = "<div class='lh-sm'>%s"%titre
            info += "<b>%s</b> · Commande <b>%s</b> · %s<br/><b>%s</b> <span class='text-muted'>%s</span>"%(
                escape(obj.partner_id.name or ''), escape(obj.purchase_id.name or ''), escape(obj.picking_id.name or ''),
                escape(obj.product_id.is_code or ''), escape(obj.product_id.name or ''),
            )
            if obj.um_id:
                info += "<br/>UM en cours : <b>%s</b> (%s UC)"%(escape(obj.um_id.name), len(obj.ligne_ids.filtered(lambda l: l.um_id==obj.um_id)))
            info += "</div>"
            obj.info_html = info

            # Barre de progression : rouge au-delà de l'attendu (accepté, mais à signaler)
            attendu = obj.qt_attendue or 0
            scanne  = obj.qt_scannee or 0
            pourcentage = attendu and min(100, round(100*scanne/attendu)) or (scanne and 100 or 0)
            couleur = scanne>attendu and '#dc3545' or (scanne==attendu and '#28a745' or '#17a2b8')
            texte = "%s / %s pièces"%(scanne, int(attendu))
            if scanne>attendu:
                texte += " · ⚠ %s de plus que l'attendu"%int(scanne-attendu)
            obj.progression_html = (
                "<div class='progress' style='height:1.6rem'>"
                "<div class='progress-bar' role='progressbar' style='width:%s%%;background-color:%s'></div></div>"
                "<div class='text-center fw-bold' style='color:%s'>%s</div>"
            )%(pourcentage, couleur, couleur, escape(texte))


    name             = fields.Char("N°", readonly=True, copy=False, index=True)
    state            = fields.Selection(_STATE, "État", default='scan', required=True, readonly=True, tracking=True, index=True)
    picking_id       = fields.Many2one('stock.picking', "Réception", required=True, readonly=True, tracking=True, index=True)
    partner_id       = fields.Many2one('res.partner', "Fournisseur", compute='_compute_commande', store=True, index=True)
    purchase_id      = fields.Many2one('purchase.order', "Commande", compute='_compute_commande', store=True, index=True)
    move_id          = fields.Many2one('stock.move', "Ligne de réception", compute='_compute_commande', store=True)
    product_id       = fields.Many2one('product.product', "Article", compute='_compute_commande', store=True, index=True)
    num_bl           = fields.Char("N° BL fournisseur", tracking=True)
    date_reception   = fields.Date("Date de réception", default=fields.Date.context_today, tracking=True)
    imprimante_id    = fields.Many2one('is.raspberry.zebra', "Imprimante", default=lambda self: self._get_imprimante_id(), tracking=True)
    um_id            = fields.Many2one('is.galia.base.um', "UM en cours", readonly=True)
    ligne_ids        = fields.One2many('is.reception.sous.traitance.ligne', 'reception_id', "UC scannées")
    qt_attendue      = fields.Float("Quantité attendue", compute='_compute_quantites', digits=(14, 2))
    qt_scannee       = fields.Integer("Quantité scannée", compute='_compute_quantites')
    code             = fields.Char("Code", copy=False, help="Saisie manuelle d'un code-barres (tests sur PC, étiquette illisible) : même traitement que le scan")
    action_attendue  = fields.Char("Action attendue", compute='_compute_action_attendue')
    message          = fields.Char("Message", readonly=True, copy=False)
    alerte           = fields.Char("Alerte" , readonly=True, copy=False)
    info_html        = fields.Html("Réception"  , compute='_compute_html', sanitize=False)
    progression_html = fields.Html("Progression", compute='_compute_html', sanitize=False)


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('is.reception.sous.traitance')
        return super().create(vals_list)


    @api.model
    def fournisseurs_action(self):
        "Écran 1 : kanban des fournisseurs de sous-traitance qui ont des commandes en cours"
        self._verifier_droits()
        pickings = self.env['stock.picking'].search(_receptions_ouvertes_domain()+[('purchase_id.partner_id.is_segment_achat.sous_traitance', '=', True)])
        return {
            'type'     : 'ir.actions.act_window',
            'name'     : "Réception sous-traitance",
            'res_model': 'res.partner',
            'view_mode': 'kanban',
            'views'    : [(self.env.ref('is_plastigray16.is_reception_st_partner_kanban_view').id, 'kanban')],
            'domain'   : [('id', 'in', pickings.purchase_id.partner_id.ids)],
            'target'   : 'current',
            'help'     : """<p class="o_view_nocontent_smiling_face">Aucun fournisseur de sous-traitance avec des réceptions en cours</p>
                <p>Seuls les fournisseurs dont la case « Sous-traitance » est cochée sur le segment d'achat sont affichés</p>""",
        }


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
        if not self.env.user.has_group('is_plastigray16.is_magasiniers_group'):
            raise ValidationError("Réception sous-traitance réservée au groupe Magasiniers")


    def _verifier_etat(self, states):
        for obj in self:
            if obj.state not in states:
                raise ValidationError("Action impossible dans l'état « %s »"%dict(_STATE)[obj.state])


    @api.model
    def _verifier_commande(self, picking):
        "Réception ouverte d'une commande d'un seul article (l'étiquette odoo0 ne contient que le n° de commande)"
        if picking.state not in ('waiting', 'confirmed', 'assigned'):
            raise ValidationError("La réception %s n'est plus à traiter"%picking.name)
        if not picking.purchase_id:
            raise ValidationError("La réception %s n'est pas liée à une commande d'achat"%picking.name)
        products = picking.purchase_id.order_line.product_id
        if len(products)!=1:
            raise ValidationError("La commande %s contient %s articles : réception par scan impossible (une étiquette ne contient que le n° de commande)"%(picking.purchase_id.name, len(products)))


    #** Scan et saisie manuelle ***********************************************
    def on_barcode_scanned(self, barcode):
        # Onchange : le traitement se fait sur l'enregistrement en base, puis le formulaire est mis à jour
        origin = self._origin
        _logger.info("Réception sous-traitance : scan %r sur %s (id=%s)", barcode, origin.name, origin.id)
        origin.traiter_code(barcode)
        for champ in _CHAMPS_FORMULAIRE:
            self[champ] = origin[champ]


    def valider_code_action(self):
        for obj in self:
            code = obj.code
            _logger.info("Réception sous-traitance : saisie manuelle %r sur %s", code, obj.name)
            obj.code = False
            obj.traiter_code(code)


    def _executer(self, libelle, fonction, *args):
        """Exécute une opération (scan ou bouton). Les refus et les erreurs sont affichés dans l'alerte
        et le chatter, et l'opération est annulée (savepoint) sans perdre le message.
        La fonction retourne le message, ou (message, alerte) si l'opération est faite avec un problème (étiquette non imprimée)"""
        self.ensure_one()
        try:
            with self.env.cr.savepoint():
                self._verifier_droits()
                res = fonction(*args)
            message, alerte = isinstance(res, tuple) and res or (res, False)
            _logger.info("Réception sous-traitance : %s : %s : %s%s", self.name, libelle, message, alerte and " · %s"%alerte or "")
            self.message_post(body="✅ %s : %s"%(libelle, message))
            if alerte:
                self.message_post(body="⚠ %s"%alerte)
            self.write({'message': message, 'alerte': alerte})
        except UserError as e:
            _logger.info("Réception sous-traitance : %s : %s : refus : %s", self.name, libelle, e.args[0])
            self.message_post(body="❌ %s : refusé : %s"%(libelle, e.args[0]))
            self.write({'message': False, 'alerte': "%s : %s"%(libelle, e.args[0])})
        except Exception as e:
            _logger.exception("Réception sous-traitance : %s : %s : erreur", self.name, libelle)
            erreur = "Erreur : %s"%(e.args and e.args[0] or e)
            self.message_post(body="❌ %s : %s"%(libelle, erreur))
            self.write({'message': False, 'alerte': "%s : %s"%(libelle, erreur)})


    def traiter_code(self, code):
        self.ensure_one()
        code = (code or '').strip().upper()
        if code:
            self._executer("Scan %s"%code, self._traiter_code, code)


    def _lire_etiquette_odoo0(self, num_eti):
        "Étiquette UC dans odoo0 (is.galia.base)"
        company = self.env.company
        DB       = company.is_nom_base_odoo0
        USERPASS = company.is_mdp_admin
        URL      = company.is_url_odoo0
        sock = xmlrpclib.ServerProxy('%s/xmlrpc/2/object'%URL)
        try:
            lignes = sock.execute_kw(DB, 2, USERPASS, 'is.galia.base', 'search_read', [[('num_eti','=',num_eti)]], {
                'fields': ['num_eti', 'soc', 'type_eti', 'num_of', 'num_carton', 'qt_pieces', 'date_creation'],
                'limit' : 1,
                'order' : 'id desc',
            })
        except Exception as e:
            raise ValidationError("Problème de connexion sur %s ou sur la base %s : %s"%(URL, DB, e))
        return lignes and lignes[0] or False


    def _traiter_code(self, code):
        "Scan d'une UC : contrôles, puis création de l'UC dans l'UM en cours (créée si besoin)"
        self._verifier_etat(['scan'])
        prefixe = code[:1]
        num     = code[1:]
        if prefixe!='S' or not num.isdigit():
            raise ValidationError("Code non reconnu : scannez une étiquette UC")
        num_eti = int(num)
        self._verifier_commande(self.picking_id)
        if self.ligne_ids.filtered(lambda l: l.num_eti==num_eti):
            raise ValidationError("UC %s déjà scannée"%num_eti)
        UC = self.env['is.galia.base.uc']
        if UC.with_context(active_test=False).search_count([('num_eti','=',num_eti)]):
            raise ValidationError("UC %s déjà reçue (elle existe déjà dans Odoo)"%num_eti)
        etiquette = self._lire_etiquette_odoo0(num_eti)
        if not etiquette:
            raise ValidationError("Étiquette %s non trouvée dans odoo0"%num_eti)
        if etiquette['type_eti']!='Commande':
            raise ValidationError("L'étiquette %s est de type « %s » : seules les étiquettes de type Commande sont acceptées"%(num_eti, etiquette['type_eti']))
        soc = self.env.company.is_code_societe
        if soc and str(etiquette['soc'])!=str(soc):
            raise ValidationError("L'étiquette %s est d'un autre site (société %s)"%(num_eti, etiquette['soc']))
        if (etiquette['num_of'] or '')!=self.purchase_id.name:
            raise ValidationError("L'étiquette %s est de la commande %s, pas de la commande %s"%(num_eti, etiquette['num_of'], self.purchase_id.name))

        #** UM en cours (créée au premier scan, ou après « Fin UM ») ************
        um = self.um_id
        if not um:
            um = self.env['is.galia.base.um'].create({
                'mixte'      : 'non',
                'location_id': self.move_id.location_dest_id.id,
            })
            um.message_post(body=Markup("UM créée par la réception sous-traitance %s (commande %s)")%(self.name, self.purchase_id.name))
            self.um_id = um.id

        #** Création de l'UC dans la base du site ******************************
        uc_id = UC.creer_uc({
            'um_id'        : um.id,
            'num_eti'      : num_eti,
            'type_eti'     : etiquette['type_eti'],
            'num_carton'   : etiquette['num_carton'],
            'qt_pieces'    : etiquette['qt_pieces'],
            'date_creation': etiquette['date_creation'] or fields.Datetime.now(),
            'production'   : self.purchase_id.name,
            'product_id'   : self.product_id.id,
            'origine'      : "la réception sous-traitance %s"%self.name,
        })
        self.write({'ligne_ids': [(0, 0, {
            'uc_id'           : uc_id,
            'um_id'           : um.id,
            'num_eti'         : num_eti,
            'quantite'        : etiquette['qt_pieces'],
            'quantite_origine': etiquette['qt_pieces'],
        })]})
        return "UC %s : %s pièces dans l'UM %s"%(num_eti, etiquette['qt_pieces'], um.name)


    #** Boutons ***************************************************************
    def fin_um_action(self):
        for obj in self:
            obj._executer("Fin UM", obj._fin_um)


    def _fin_um(self):
        self._verifier_etat(['scan'])
        um = self.um_id
        if not um:
            raise ValidationError("Aucune UM en cours")
        nb_uc = len(self.ligne_ids.filtered(lambda l: l.um_id==um))
        self.um_id = False
        message = "UM %s terminée (%s UC)"%(um.name, nb_uc)
        # Pas d'étiquette pour une UM d'une seule UC : l'étiquette UC suffit
        if nb_uc<=1:
            return message+" · pas d'étiquette UM (1 seule UC)"
        impression = self._imprimer_um(um)
        if '⚠' in impression:
            return message, "Étiquette UM %s non imprimée : à réimprimer depuis la fiche UM"%um.name
        return message+impression


    def fin_controle_action(self):
        for obj in self:
            obj._executer("Fin de contrôle", obj._fin_controle)


    def _fin_controle(self):
        "Validation de la réception avec la quantité scannée (comme « Transfert »), puis lot de la réception sur les UC"
        self._verifier_etat(['scan'])
        if not self.num_bl:
            raise ValidationError("Saisissez le n° de BL fournisseur")
        if not self.ligne_ids:
            raise ValidationError("Aucune UC scannée")
        picking = self.picking_id
        move    = self.move_id
        self._verifier_commande(picking)
        if not move or move.state in ('done', 'cancel'):
            raise ValidationError("Ligne de réception non trouvée")

        #** UM en cours terminée ***********************************************
        alertes = []
        if self.um_id:
            res = self._fin_um()
            if isinstance(res, tuple):
                alertes.append(res[1])

        #** Validation de la réception (reliquat automatique) ******************
        qt = self.qt_scannee
        transfert = self.env['stock.transfer_details'].with_context(active_id=picking.id).create({
            'is_num_bl'        : self.num_bl,
            'is_date_reception': self.date_reception,
        })
        for line in transfert.line_ids:
            line.quantity = qt if line.move_id==move else 0
        transfert.valider_action()
        if move.state!='done':
            raise ValidationError("La réception %s n'a pas été validée"%picking.name)

        #** UC : ligne de réception, lot ; UM : emplacement réel du stock ******
        location = move.move_line_ids.location_dest_id[:1] or move.location_dest_id
        ucs = self.ligne_ids.uc_id
        ucs.write({'stock_move_rcp_id': move.id})
        ucs.retrouver_lot_action()
        self.ligne_ids.um_id.write({'location_id': location.id})
        self.state = 'termine'
        message = "Réception %s validée : %s pièces, %s UC, %s UM dans %s"%(picking.name, qt, len(ucs), len(self.ligne_ids.um_id), location.name)
        if qt>self.qt_attendue:
            message += " (%s de plus que l'attendu)"%int(qt-self.qt_attendue)
        return (message, " · ".join(alertes)) if alertes else message


    def abandonner_action(self):
        "Supprime les UC et UM créées par le scan : la réception n'est pas modifiée"
        for obj in self:
            obj._verifier_droits()
            obj._verifier_etat(['scan'])
            ucs = obj.ligne_ids.uc_id
            ums = obj.ligne_ids.um_id | obj.um_id
            obj.ligne_ids.unlink()
            ucs.sudo().unlink()
            ums.filtered(lambda um: not um.uc_ids).sudo().unlink()
            obj.write({'state': 'annule', 'um_id': False, 'message': "Abandonné : UC et UM créées supprimées", 'alerte': False})


    def retour_commandes_action(self):
        "Retour à la liste des commandes en cours du fournisseur"
        self.ensure_one()
        return self.partner_id.reception_st_commandes_action()


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
            _logger.exception("Réception sous-traitance : %s : impression %s", self.name, libelle)
            erreur = e.args and e.args[0] or e
            self.message_post(body="❌ Impression %s : %s"%(libelle, erreur))
            return " · ⚠ non imprimée : %s"%erreur


    def _imprimer_uc(self, uc):
        def imprimer():
            uc.sudo().imprimer_etiquette_uc_action(imprimante=self._imprimante())
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


class is_reception_sous_traitance_ligne(models.Model):
    _name        = 'is.reception.sous.traitance.ligne'
    _description = "Réception sous-traitance : UC scannées"
    _order       = 'id desc'

    reception_id     = fields.Many2one('is.reception.sous.traitance', "Fiche", required=True, ondelete='cascade', index=True)
    num_eti          = fields.Integer("N° UC", readonly=True)
    uc_id            = fields.Many2one('is.galia.base.uc', "UC", readonly=True)
    um_id            = fields.Many2one('is.galia.base.um', "UM", readonly=True)
    quantite         = fields.Integer("Quantité")
    quantite_origine = fields.Integer("Quantité de l'étiquette", readonly=True)
    impression       = fields.Char("Impression", readonly=True)


    def write(self, vals):
        "Quantité modifiée : mise à jour de l'UC et réimpression de son étiquette"
        if 'quantite' not in vals:
            return super().write(vals)
        anciennes = {obj.id: obj.quantite for obj in self}
        res = super().write(vals)
        for obj in self:
            if obj.quantite==anciennes[obj.id]:
                continue
            fiche = obj.reception_id
            fiche._verifier_etat(['scan'])
            if obj.quantite<=0:
                raise ValidationError("La quantité de l'UC %s doit être supérieure à 0"%obj.num_eti)
            obj.uc_id.sudo().qt_pieces = obj.quantite
            impression = fiche._imprimer_uc(obj.uc_id)
            super(is_reception_sous_traitance_ligne, obj).write({'impression': "Quantité %s → %s%s"%(anciennes[obj.id], obj.quantite, impression)})
            fiche.message_post(body="UC %s : quantité %s → %s%s"%(obj.num_eti, anciennes[obj.id], obj.quantite, impression))
        return res


    def voir_uc_action(self):
        for obj in self:
            return obj.uc_id.acceder_uc_action()
