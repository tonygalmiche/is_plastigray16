# -*- coding: utf-8 -*-
from odoo import models,fields,api
from odoo.exceptions import ValidationError, UserError
from markupsafe import escape
import logging
_logger = logging.getLogger(__name__)


_STATE = [
    ('scan'   , 'Scan'),
    ('termine', 'Terminé'),
    ('annule' , 'Annulé'),
]

# Champs recopiés de l'enregistrement en base vers le formulaire après un scan (on_barcode_scanned est un onchange)
_CHAMPS_FORMULAIRE = [
    'state', 'location_id', 'client_id', 'ligne_ids', 'message', 'alerte',
]


class is_retour_client(models.Model):
    _name        = 'is.retour.client'
    _inherit     = ['mail.thread', 'barcodes.barcode_events_mixin']
    _description = "Retour client (scan)"
    _order       = 'id desc'


    @api.depends('state', 'location_id')
    def _compute_action_attendue(self):
        for obj in self:
            action_attendue = False
            if obj.state=='scan':
                if obj.location_id:
                    action_attendue = "Scannez les UM (UC si UC=UM)"
                else:
                    action_attendue = "Scannez l'emplacement de destination"
            obj.action_attendue = action_attendue


    @api.depends('name', 'state', 'location_id', 'client_id', 'ligne_ids')
    def _compute_html(self):
        couleurs = {'scan': '#17a2b8', 'termine': '#28a745', 'annule': '#8a8f94'}
        for obj in self:
            # N° et état masqués sur smartphone (d-none d-md-flex) : le bandeau « action attendue » suffit
            info = "<div class='lh-sm'><div class='d-none d-md-flex justify-content-between align-items-center'><b>%s</b><span class='badge' style='background-color:%s;color:#fff'>%s</span></div>"%(
                escape(obj.name or ''), couleurs.get(obj.state, '#8a8f94'), escape(dict(_STATE).get(obj.state, '')),
            )
            info += "<div>Emplacement : <b>%s</b></div>"%escape(obj.location_id.name or '-')
            info += "<div>Client : <b>%s</b></div>"%escape(obj.client_id and "%s %s"%(obj.client_id.is_code or '', obj.client_id.name) or '-')
            info += "</div>"
            obj.info_html = info

            # Récapitulatif par article : nombre d'UM, d'UC et de pièces
            recap = {}
            for ligne in obj.ligne_ids:
                ucs = ligne.um_id.with_context(active_test=False).uc_ids
                for product in ucs.product_id:
                    ucs_article = ucs.filtered(lambda uc: uc.product_id==product)
                    if product not in recap:
                        recap[product] = {'nb_um': 0, 'nb_uc': 0, 'quantite': 0}
                    recap[product]['nb_um']    += 1
                    recap[product]['nb_uc']    += len(ucs_article)
                    recap[product]['quantite'] += sum(ucs_article.mapped('qt_pieces'))
            html = False
            if recap:
                lignes = []
                total = {'nb_um': len(obj.ligne_ids), 'nb_uc': 0, 'quantite': 0}
                for product in sorted(recap, key=lambda p: p.is_code or ''):
                    vals = recap[product]
                    total['nb_uc']    += vals['nb_uc']
                    total['quantite'] += vals['quantite']
                    # Une carte par article, comme les UM scannées : désignation sur une seule ligne (coupée)
                    lignes.append(
                        "<div class='o_is_carte d-flex align-items-center px-2 py-1'>"
                        "<div class='flex-grow-1 text-truncate'><b>%s</b><span class='text-muted small ms-1'>%s</span></div>"
                        "<div class='text-nowrap ms-2'>%s UM · %s UC · <b>%s</b></div>"
                        "</div>"%(
                        escape(product.is_code or ''), escape(product.name or ''), vals['nb_um'], vals['nb_uc'], vals['quantite'],
                    ))
                html = (
                    "<div class='o_is_recap'>%s"
                    "<div class='o_is_carte d-flex align-items-center px-2 py-1 fw-bold'>"
                    "<div class='flex-grow-1'>Total</div><div class='text-nowrap ms-2'>%s UM · %s UC · %s</div>"
                    "</div></div>"
                )%("".join(lignes), total['nb_um'], total['nb_uc'], total['quantite'])
            obj.recap_html = html


    name            = fields.Char("N°", readonly=True, copy=False, index=True)
    state           = fields.Selection(_STATE, "État", default='scan', required=True, readonly=True, tracking=True, index=True)
    location_id     = fields.Many2one('stock.location', "Emplacement", readonly=True, tracking=True, help="Emplacement de destination : dernier emplacement scanné")
    client_id       = fields.Many2one('res.partner', "Client", readonly=True, tracking=True, index=True, help="Client par défaut de l'article de la première UM scannée")
    ligne_ids       = fields.One2many('is.retour.client.ligne', 'retour_id', "UM scannées", readonly=True)
    nb_um           = fields.Integer("Nb UM", compute='_compute_nb', store=True)
    date_validation = fields.Datetime("Date de validation", readonly=True, tracking=True)
    valideur_id     = fields.Many2one('res.users', "Validé par", readonly=True, tracking=True)
    code            = fields.Char("Code", copy=False, help="Saisie manuelle d'un code-barres (étiquette illisible, tests sur PC) : même traitement que le scan")
    action_attendue = fields.Char("Action attendue", compute='_compute_action_attendue')
    libelle_valider = fields.Char("Libellé du bouton Valider", compute='_compute_libelle_valider')
    message         = fields.Char("Message", readonly=True, copy=False)
    alerte          = fields.Char("Alerte" , readonly=True, copy=False)
    info_html       = fields.Html("Informations" , compute='_compute_html', sanitize=False)
    recap_html      = fields.Html("Récapitulatif", compute='_compute_html', sanitize=False)


    @api.depends('location_id')
    def _compute_libelle_valider(self):
        for obj in self:
            obj.libelle_valider = "Valider l'entrée en stock en %s"%(obj.location_id.name or '')


    @api.depends('ligne_ids')
    def _compute_nb(self):
        for obj in self:
            obj.nb_um = len(obj.ligne_ids)


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('is.retour.client')
        return super().create(vals_list)


    def unlink(self):
        # Retour validé : garder la trace (lignes et lien vers les mouvements de stock), même pour un administrateur
        for obj in self:
            if obj.state=='termine':
                raise ValidationError("Retour %s validé : suppression impossible"%obj.name)
        return super().unlink()


    def nouveau_action(self):
        "Reprend la fiche en cours de l'utilisateur s'il en a une, sinon en crée une, pour qu'elle existe en base au premier scan"
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
        if not self.env.user.has_group('is_plastigray16.is_magasiniers_group'):
            raise ValidationError("Retour client réservé au groupe Magasiniers")


    def _verifier_etat(self, states):
        for obj in self:
            if obj.state not in states:
                raise ValidationError("Action impossible dans l'état « %s »"%dict(_STATE)[obj.state])


    #** Scan et saisie manuelle ***********************************************
    def on_barcode_scanned(self, barcode):
        # Onchange : le traitement se fait sur l'enregistrement en base, puis le formulaire est mis à jour
        origin = self._origin
        _logger.info("Retour client : scan %r sur %s (id=%s)", barcode, origin.name, origin.id)
        origin.traiter_code(barcode)
        for champ in _CHAMPS_FORMULAIRE:
            self[champ] = origin[champ]


    def valider_code_action(self):
        for obj in self:
            code = obj.code
            _logger.info("Retour client : saisie manuelle %r sur %s", code, obj.name)
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
            _logger.info("Retour client : %s : %s : %s", self.name, libelle, message)
            self.message_post(body="✅ %s : %s"%(libelle, message))
            self.write({'message': message, 'alerte': False})
        except UserError as e:
            _logger.info("Retour client : %s : %s : refus : %s", self.name, libelle, e.args[0])
            self.message_post(body="❌ %s : refusé : %s"%(libelle, e.args[0]))
            self.write({'message': False, 'alerte': "%s : %s"%(libelle, e.args[0])})
        except Exception as e:
            _logger.exception("Retour client : %s : %s : erreur", self.name, libelle)
            erreur = "Erreur : %s"%(e.args and e.args[0] or e)
            self.message_post(body="❌ %s : %s"%(libelle, erreur))
            self.write({'message': False, 'alerte': "%s : %s"%(libelle, erreur)})


    def traiter_code(self, code):
        self.ensure_one()
        code = (code or '').strip().upper()
        if code:
            self._executer("Scan %s"%code, self._traiter_code, code)


    def _traiter_code(self, code):
        "Emplacement (EMP + nom), UM (M / G + n°, ou 8 chiffres) ou UC d'un article UC=UM (S + n°, ou autre n°)"
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
            raise ValidationError("Scannez d'abord l'emplacement de destination")
        if type_code=='um':
            um = self.env['is.galia.base.um'].with_context(active_test=False).search([('name','=',num)], limit=1)
            if not um:
                raise ValidationError("UM %s non trouvée"%num)
            return self._ajouter_um(um)
        return self._scan_uc(int(num))


    def _scan_emplacement(self, name):
        Location = self.env['stock.location']
        location = Location.search([('name','=',name), ('usage','=','internal')])
        if not location:
            if Location.search([('name','=',name)], limit=1):
                raise ValidationError("%s n'est pas un emplacement interne"%name)
            raise ValidationError("Emplacement %s non trouvé"%name)
        if len(location)>1:
            raise ValidationError("Plusieurs emplacements internes %s"%name)
        self.location_id = location.id
        return "Emplacement de destination : %s"%location.name


    def _scan_uc(self, num_eti):
        "Article UC=UM : pas d'étiquette UM, l'UC donne l'UM (la plus récente dans l'emplacement Client ou archivée)"
        ucs = self.env['is.galia.base.uc'].with_context(active_test=False).search([('num_eti','=',num_eti)], order='id desc')
        if not ucs:
            raise ValidationError("UC %s non trouvée"%num_eti)
        if not ucs[0].product_id.is_um_egale_uc:
            raise ValidationError("UC %s : article %s pas UC=UM, scannez l'étiquette UM"%(num_eti, ucs[0].product_id.is_code))
        ucs = ucs.filtered(lambda uc: not uc.um_id.active or uc.um_id.location_id.usage=='customer')
        if not ucs:
            raise ValidationError("UC %s : aucune UM dans l'emplacement Client ou archivée"%num_eti)
        return self._ajouter_um(ucs[0].um_id, uc=ucs[0])


    def _get_client(self, um):
        "Client par défaut des articles de l'UM (un seul client)"
        clients = um.with_context(active_test=False).uc_ids.product_id.product_tmpl_id.is_client_id
        if not clients:
            raise ValidationError("UM %s : article sans client par défaut"%um.name)
        if len(clients)>1:
            raise ValidationError("UM %s avec des articles de plusieurs clients (%s)"%(um.name, ', '.join(clients.mapped('is_code'))))
        return clients


    def _verifier_um(self, um, ligne=False):
        "Contrôles d'une UM de la fiche (au scan et à la validation)"
        client = self._get_client(um)
        um._verifier_retour_client()
        if self.client_id and client!=self.client_id:
            raise ValidationError("UM %s du client %s %s, ce retour est pour le client %s %s"%(
                um.name, client.is_code or '', client.name, self.client_id.is_code or '', self.client_id.name))
        autre = self.env['is.retour.client.ligne'].search([
            ('um_id'          , '=' , um.id),
            ('retour_id.state', '=' , 'scan'),
            ('id'             , '!=', ligne and ligne.id or 0),
        ], limit=1)
        if autre:
            if autre.retour_id==self:
                raise ValidationError("UM %s déjà scannée"%um.name)
            raise ValidationError("UM %s déjà dans le retour %s non validé"%(um.name, autre.retour_id.name))
        return client


    def _ajouter_um(self, um, uc=False):
        "Ajout de l'UM à la liste, sans entrée en stock"
        client = self._verifier_um(um)
        ucs = um.with_context(active_test=False).uc_ids
        self.write({
            'client_id': client.id,
            'ligne_ids': [(0, 0, {
                'um_id'    : um.id,
                'uc_id'    : uc and uc.id or False,
                'um_active': um.active,
                'nb_uc'    : len(ucs),
                'quantite' : sum(ucs.mapped('qt_pieces')),
            })],
        })
        # Message court : une seule ligne sur le TC22. Article UC=UM : n° de l'UC scannée (l'étiquette UM n'est jamais imprimée)
        if uc:
            return "+ UC %s%s : %s pcs"%(uc.num_eti, not um.active and " (archivée)" or "", sum(ucs.mapped('qt_pieces')))
        return "+ UM %s%s : %s UC · %s pcs"%(um.name, not um.active and " (archivée)" or "", len(ucs), sum(ucs.mapped('qt_pieces')))


    def _supprimer_ligne(self, ligne):
        "Ligne retirée de la liste (erreur de scan) : l'UM et ses UC ne sont pas modifiées"
        self._verifier_etat(['scan'])
        name = ligne.um_id.name
        ligne.unlink()
        if not self.ligne_ids:
            self.client_id = False
        return "UM %s retirée de la liste"%name


    #** Boutons ***************************************************************
    def valider_action(self):
        for obj in self:
            obj._executer("Validation", obj._valider)


    def _valider(self):
        "Entrée en stock de toutes les UM de la liste, en tout ou rien (savepoint de _executer)"
        self._verifier_etat(['scan'])
        if not self.location_id:
            raise ValidationError("Scannez l'emplacement de destination")
        if not self.ligne_ids:
            raise ValidationError("Aucune UM scannée")
        # Contrôles refaits sur toutes les UM avant de commencer : la situation a pu changer depuis le scan
        for ligne in self.ligne_ids:
            self._verifier_um(ligne.um_id, ligne=ligne)
        for ligne in self.ligne_ids:
            um = ligne.um_id.sudo()
            ligne.move_ids = [(6, 0, um.retour_client(self.location_id, self.name).ids)]
        self.write({
            'state'          : 'termine',
            'date_validation': fields.Datetime.now(),
            'valideur_id'    : self.env.uid,
        })
        nb = len(self.ligne_ids)
        return "%s UM %s en stock dans %s"%(nb, nb>1 and "remises" or "remise", self.location_id.name)


    def abandonner_action(self):
        for obj in self:
            obj._verifier_droits()
            obj._verifier_etat(['scan'])
            obj.write({'state': 'annule', 'message': "Abandonné", 'alerte': False})


    def nouveau_retour_action(self):
        return self.nouveau_action()


    #** Boutons de la vue PC **************************************************
    def voir_ums_action(self):
        for obj in self:
            return {
                'name'     : "UM %s"%obj.name,
                'type'     : 'ir.actions.act_window',
                'res_model': 'is.galia.base.um',
                'view_mode': 'tree,form',
                'domain'   : [('id', 'in', obj.ligne_ids.um_id.ids)],
                # UM archivées comprises (retour pas encore validé)
                'context'  : {'active_test': False},
            }


    def voir_ucs_action(self):
        for obj in self:
            return {
                'name'     : "UC %s"%obj.name,
                'type'     : 'ir.actions.act_window',
                'res_model': 'is.galia.base.uc',
                'view_mode': 'tree,form',
                'domain'   : [('um_id', 'in', obj.ligne_ids.um_id.ids)],
                'context'  : {'active_test': False},
            }


    def voir_mouvements_action(self):
        for obj in self:
            return {
                'name'     : "Mouvements %s"%obj.name,
                'type'     : 'ir.actions.act_window',
                'res_model': 'stock.move',
                'view_mode': 'tree,form',
                'domain'   : [('id', 'in', obj.ligne_ids.move_ids.ids)],
            }


class is_retour_client_ligne(models.Model):
    _name        = 'is.retour.client.ligne'
    _description = "Retour client : UM scannées"
    _order       = 'id desc'

    retour_id  = fields.Many2one('is.retour.client', "Retour client", required=True, ondelete='cascade', index=True)
    state      = fields.Selection(related='retour_id.state')
    um_id      = fields.Many2one('is.galia.base.um', "UM", required=True, index=True)
    uc_id      = fields.Many2one('is.galia.base.uc', "UC scannée", help="Article UC=UM : UC scannée à la place de l'UM")
    product_id = fields.Many2one('product.product', "Article", compute='_compute_product_id')
    libelle    = fields.Char("UM / UC", compute='_compute_libelle', help="Article UC=UM : n° de l'UC scannée (l'étiquette UM n'est jamais imprimée), sinon n° de l'UM")
    um_active  = fields.Boolean("UM active avant le retour")
    nb_uc      = fields.Integer("Nb UC")
    quantite   = fields.Integer("Quantité")
    move_ids   = fields.Many2many('stock.move', 'is_retour_client_ligne_move_rel', 'ligne_id', 'move_id', "Mouvements", readonly=True)


    def _compute_libelle(self):
        for obj in self:
            obj.libelle = obj.uc_id and "UC %s"%obj.uc_id.num_eti or "UM %s"%(obj.um_id.name or '')


    def _compute_product_id(self):
        for obj in self:
            products = obj.um_id.with_context(active_test=False).uc_ids.product_id
            obj.product_id = len(products)==1 and products.id or False


    def supprimer_action(self):
        "Poubelle : fenêtre de confirmation avec le détail de la ligne (le texte de confirm d'un bouton est fixe)"
        for obj in self:
            return {
                'type'     : 'ir.actions.act_window',
                'name'     : "Retirer %s ?"%obj.libelle,
                'res_model': self._name,
                'res_id'   : obj.id,
                'view_mode': 'form',
                'views'    : [(self.env.ref('is_plastigray16.is_retour_client_ligne_supprimer_form_view').id, 'form')],
                'target'   : 'new',
            }


    def confirmer_suppression_action(self):
        "UM retirée de la liste"
        for obj in self:
            fiche = obj.retour_id
            fiche._executer("Suppression UM %s"%obj.um_id.name, fiche._supprimer_ligne, obj)
        return {'type': 'ir.actions.act_window_close'}


    def voir_um_action(self):
        for obj in self:
            return obj.um_id.acceder_um_action()
