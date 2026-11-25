# -*- coding: utf-8 -*-
from odoo import models,fields,api
from odoo.exceptions import ValidationError, UserError
from markupsafe import Markup, escape
import logging
_logger = logging.getLogger(__name__)


_STATE = [
    ('scan'   , 'UM à scanner'),
    ('termine', 'Terminé'),
    ('annule' , 'Annulé'),
]

# Champs recopiés de l'enregistrement en base vers le formulaire après un scan (on_barcode_scanned est un onchange)
_CHAMPS_FORMULAIRE = [
    'state', 'um_id', 'location_id', 'ligne_ids', 'message', 'alerte',
]


class is_fusionner_um(models.Model):
    _name        = 'is.fusionner.um'
    _inherit     = ['mail.thread', 'barcodes.barcode_events_mixin']
    _description = "Fusionner des UM (scan)"
    _order       = 'id desc'


    def _get_imprimante_id(self):
        user = self.env.user
        return user.is_zebra_id or user.company_id.is_zebra_id


    @api.depends('state', 'ligne_ids')
    def _compute_action_attendue(self):
        for obj in self:
            action_attendue = False
            if obj.state=='scan':
                if len(obj.ligne_ids)<2:
                    action_attendue = "Scannez les UM à fusionner (la première est gardée), ou l'UC d'une UM d'une seule UC"
                else:
                    action_attendue = "Scannez une autre UM, ou « Fusionner les UM »"
            obj.action_attendue = action_attendue


    @api.depends('name', 'state', 'location_id', 'ligne_ids')
    def _compute_info_html(self):
        couleurs = {'scan': '#17a2b8', 'termine': '#28a745', 'annule': '#8a8f94'}
        for obj in self:
            # N° et état masqués sur smartphone (d-none d-md-flex) : le bandeau « action attendue » suffit
            titre = "<div class='d-none d-md-flex justify-content-between align-items-center'><b>%s</b><span class='badge' style='background-color:%s;color:#fff'>%s</span></div>"%(
                escape(obj.name or ''), couleurs.get(obj.state, '#8a8f94'), escape(dict(_STATE).get(obj.state, '')),
            )
            info = "<div class='lh-sm'>%s"%titre
            if obj.ligne_ids:
                info += "<b>%s UM</b> · <b>%s UC</b> · <b>%s pcs</b> · emplacement <b>%s</b>"%(
                    len(obj.ligne_ids), sum(obj.ligne_ids.mapped('nb_uc')), sum(obj.ligne_ids.mapped('quantite')),
                    escape(obj.location_id.name or ''),
                )
            info += "</div>"
            obj.info_html = info


    name            = fields.Char("N°", readonly=True, copy=False, index=True)
    state           = fields.Selection(_STATE, "État", default='scan', required=True, readonly=True, tracking=True, index=True)
    imprimante_id   = fields.Many2one('is.raspberry.zebra', "Imprimante", default=lambda self: self._get_imprimante_id(), tracking=True)
    um_id           = fields.Many2one('is.galia.base.um', "UM gardée", readonly=True, tracking=True, index=True, help="Première UM scannée")
    location_id     = fields.Many2one('stock.location', "Emplacement", readonly=True, tracking=True, help="Emplacement de la première UM scannée")
    ligne_ids       = fields.One2many('is.fusionner.um.ligne', 'fusion_id', "UM", readonly=True)
    impression      = fields.Char("Impression", readonly=True, copy=False, help="Impression de l'étiquette de l'UM gardée")
    code            = fields.Char("Code", copy=False, help="Saisie manuelle d'un code-barres (tests sur PC, étiquette illisible) : même traitement que le scan")
    action_attendue = fields.Char("Action attendue", compute='_compute_action_attendue')
    message         = fields.Char("Message", readonly=True, copy=False)
    alerte          = fields.Char("Alerte" , readonly=True, copy=False)
    info_html       = fields.Html("Fusion", compute='_compute_info_html', sanitize=False)


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('is.fusionner.um')
        return super().create(vals_list)


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


    def voir_ums_action(self):
        for obj in self:
            return {
                'name'     : "UM %s"%obj.name,
                'type'     : 'ir.actions.act_window',
                'res_model': 'is.galia.base.um',
                'view_mode': 'tree,form',
                'domain'   : [('id', 'in', obj.ligne_ids.um_id.ids)],
            }


    def voir_ucs_action(self):
        "UC des UM de la fiche : avant la fusion dans leurs UM, après dans l'UM gardée"
        for obj in self:
            return {
                'name'     : "UC %s"%obj.name,
                'type'     : 'ir.actions.act_window',
                'res_model': 'is.galia.base.uc',
                'view_mode': 'tree,form',
                'domain'   : [('um_id', 'in', obj.ligne_ids.um_id.ids)],
            }


    def _verifier_droits(self):
        if not self.env.user.has_group('is_plastigray16.is_fusionner_um_group'):
            raise ValidationError("Fusionner des UM réservé au groupe « Fusionner des UM »")


    def _verifier_etat(self, states):
        for obj in self:
            if obj.state not in states:
                raise ValidationError("Action impossible dans l'état « %s »"%dict(_STATE)[obj.state])


    #** Scan et saisie manuelle ***********************************************
    def on_barcode_scanned(self, barcode):
        # Onchange : le traitement se fait sur l'enregistrement en base, puis le formulaire est mis à jour
        origin = self._origin
        _logger.info("Fusionner des UM : scan %r sur %s (id=%s)", barcode, origin.name, origin.id)
        origin.traiter_code(barcode)
        for champ in _CHAMPS_FORMULAIRE:
            self[champ] = origin[champ]


    def valider_code_action(self):
        for obj in self:
            code = obj.code
            _logger.info("Fusionner des UM : saisie manuelle %r sur %s", code, obj.name)
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
            _logger.info("Fusionner des UM : %s : %s : %s%s", self.name, libelle, message, alerte and " · %s"%alerte or "")
            self.message_post(body="✅ %s : %s"%(libelle, message))
            if alerte:
                self.message_post(body="⚠ %s"%alerte)
            self.write({'message': message, 'alerte': alerte})
        except UserError as e:
            _logger.info("Fusionner des UM : %s : %s : refus : %s", self.name, libelle, e.args[0])
            self.message_post(body="❌ %s : refusé : %s"%(libelle, e.args[0]))
            self.write({'message': False, 'alerte': "%s : %s"%(libelle, e.args[0])})
        except Exception as e:
            _logger.exception("Fusionner des UM : %s : %s : erreur", self.name, libelle)
            erreur = "Erreur : %s"%(e.args and e.args[0] or e)
            self.message_post(body="❌ %s : %s"%(libelle, erreur))
            self.write({'message': False, 'alerte': "%s : %s"%(libelle, erreur)})


    def traiter_code(self, code):
        self.ensure_one()
        code = (code or '').strip().upper()
        if code:
            self._executer("Scan %s"%code, self._traiter_code, code)


    def _traiter_code(self, code):
        """Scan d'une UM (M/G + n°), ou d'une UC (S + n°) seule dans son UM (pas d'étiquette UM imprimée pour une UM
        d'une seule UC) : UM ajoutée à la fiche, rien n'est modifié avant « Fusionner les UM »"""
        self._verifier_etat(['scan'])
        prefixe = code[:1]
        num     = code[1:]
        if prefixe not in ('M', 'G', 'S') or not num.isdigit():
            raise ValidationError("Code non reconnu : scannez une étiquette UM, ou UC si elle est seule dans son UM")
        if prefixe=='S':
            uc = self.env['is.galia.base.uc'].with_context(active_test=False).search([('num_eti','=',int(num))], order='active desc, id desc', limit=1)
            if not uc:
                raise ValidationError("UC non trouvée")
            if not uc.active:
                raise ValidationError("UC archivée")
            if uc.product_id.is_um_egale_uc:
                raise ValidationError("UC %s : article %s UC=UM, pas de fusion possible"%(uc.num_eti, uc.product_id.is_code))
            um = uc.um_id
            if len(um.uc_ids)>1:
                raise ValidationError("UC %s dans l'UM %s de %s UC : scannez l'étiquette UM"%(uc.num_eti, um.name, len(um.uc_ids)))
        else:
            um = self.env['is.galia.base.um'].with_context(active_test=False).search([('name','=',num)], order='active desc, id desc', limit=1)
            if not um:
                raise ValidationError("UM non trouvée")
        self._ajouter_um(um)
        if um==self.um_id:
            return "UM %s gardée, dans l'emplacement %s"%(um.name, um.location_id.name)
        return "UM %s ajoutée (%s UM à fusionner)"%(um.name, len(self.ligne_ids))


    #** Contrôles et ajout d'une UM *******************************************
    def _controler_um(self, um, location=False):
        """Contrôles d'une UM à fusionner (au scan, puis de nouveau à la fusion : l'UM a pu changer depuis le scan).
        location : emplacement de la première UM (par défaut celui de la fiche)"""
        location = location or self.location_id
        if not um.active:
            raise ValidationError("UM %s archivée"%um.name)
        if not um.uc_ids:
            raise ValidationError("UM %s sans UC"%um.name)
        if um.location_id.usage!='internal':
            raise ValidationError("UM %s en %s : pas un emplacement interne"%(um.name, um.location_id.name or 'aucun emplacement'))
        if location and um.location_id!=location:
            raise ValidationError("UM %s en %s : pas dans l'emplacement de la première UM (%s)"%(um.name, um.location_id.name, location.name))
        if um.liste_servir_id:
            raise ValidationError("UM %s dans la liste à servir %s"%(um.name, um.liste_servir_id.name))
        if um.bon_transfert_id:
            raise ValidationError("UM %s dans le bon de transfert %s"%(um.name, um.bon_transfert_id.name))
        if um.controle_qualite_id:
            raise ValidationError("UM %s dans le contrôle qualité en cours %s"%(um.name, um.controle_qualite_id.name))
        products_um_uc = um.uc_ids.product_id.filtered(lambda p: p.is_um_egale_uc)
        if products_um_uc:
            raise ValidationError("UM %s : article UC=UM (%s)"%(um.name, ', '.join(products_um_uc.mapped('is_code'))))


    def _ajouter_um(self, um):
        "Ajoute l'UM à la fiche. La première UM est l'UM gardée et fixe l'emplacement"
        if um in self.ligne_ids.um_id:
            raise ValidationError("UM %s déjà scannée"%um.name)
        self._controler_um(um)
        vals = {
            'ligne_ids': [(0, 0, {
                'sequence': len(self.ligne_ids)+1,
                'um_id'   : um.id,
                'gardee'  : not self.ligne_ids,
                'nb_uc'   : len(um.uc_ids),
                'uc_id'   : len(um.uc_ids)==1 and um.uc_ids.id or False,
                'quantite': sum(um.uc_ids.mapped('qt_pieces')),
                'articles': ', '.join(sorted(set(um.uc_ids.product_id.mapped('is_code')))),
            })],
        }
        if not self.ligne_ids:
            vals['um_id']       = um.id
            vals['location_id'] = um.location_id.id
        self.write(vals)


    def _retirer_um(self, um):
        """Retire l'UM de la fiche (poubelle). Si c'est l'UM gardée, la suivante devient l'UM gardée
        et donne l'emplacement"""
        self._verifier_etat(['scan'])
        self.ligne_ids.filtered(lambda l: l.um_id==um).unlink()
        lignes = self.ligne_ids.sorted(lambda l: (l.sequence, l.id))
        for i,ligne in enumerate(lignes, start=1):
            ligne.write({'sequence': i, 'gardee': i==1})
        premiere = lignes[:1]
        self.write({
            'um_id'      : premiere.um_id.id,
            'location_id': premiere.um_id.location_id.id,
        })
        message = "UM %s retirée"%um.name
        if premiere:
            message += " (UM %s gardée)"%premiere.um_id.name
        return message


    @api.model
    def creer_depuis_um(self, ums):
        "Fiche créée depuis la liste des UM (UM cochées, la première est gardée), comme si elles avaient été scannées"
        self._verifier_droits()
        if len(ums)<2:
            raise ValidationError("Cochez au moins 2 UM à fusionner")
        # Contrôles avant la création : une fiche annulée consommerait un n° (trou dans la séquence)
        for um in ums:
            self._controler_um(um, location=ums[0].location_id)
        obj = self.create({})
        for um in ums:
            obj._ajouter_um(um)
        obj.message_post(body="✅ Fiche créée depuis la liste des UM : %s"%', '.join(ums.mapped('name')))
        return obj.voir_action()


    #** Boutons ***************************************************************
    def fusionner_action(self):
        for obj in self:
            obj._executer("Fusionner les UM", obj._fusionner)


    def annuler_action(self):
        "Vide la fiche pour recommencer, sans rien modifier"
        for obj in self:
            obj._verifier_droits()
            obj._verifier_etat(['scan'])
            obj.write({
                'um_id'      : False,
                'location_id': False,
                'ligne_ids'  : [(5, 0, 0)],
                'message'    : False,
                'alerte'     : False,
            })


    def abandonner_action(self):
        for obj in self:
            obj._verifier_droits()
            obj._verifier_etat(['scan'])
            obj.write({'state': 'annule', 'message': "Abandonné", 'alerte': False})


    def nouvelle_fusion_action(self):
        return self.nouveau_action()


    #** Fusion ****************************************************************
    def _fusionner(self):
        """Met les UC des autres UM dans l'UM gardée (même emplacement, sans mouvement de stock) : picking des UC, qui
        archive les UM vidées et passe l'UM gardée en mixte si elle a plusieurs articles. Puis réimprime l'UM gardée"""
        self._verifier_etat(['scan'])
        if len(self.ligne_ids)<2:
            raise ValidationError("Scannez au moins 2 UM")
        um     = self.um_id.sudo()
        autres = self.ligne_ids.filtered(lambda l: not l.gardee).um_id.sudo()
        # Contrôles refaits : les UM ont pu changer depuis le scan
        for u in um | autres:
            self._controler_um(u)
        autres.uc_ids.picking_um(um_dest_id=um.id)
        lien_um = Markup('<a href="#" data-oe-model="is.galia.base.um" data-oe-id="%s">%s</a>')
        um.message_post(body=Markup("Fusion %s : UC des UM %s ajoutées")%(
            self.name, Markup(', ').join(lien_um%(u.id, u.name) for u in autres),
        ))
        for u in autres:
            u.message_post(body=Markup("Fusion %s : UC mises dans l'UM %s")%(self.name, lien_um%(um.id, um.name)))
        self.impression = self._imprimer_um(um)
        self.state = 'termine'
        message = "UM %s : %s UM fusionnées, %s UC"%(um.name, len(autres)+1, len(um.uc_ids))
        if um.mixte=='oui':
            message += ", UM mixte"
        if '⚠' in self.impression:
            return message, "⚠ Étiquette UM non imprimée : à réimprimer depuis la fiche UM"
        return message


    #** Impression sur l'imprimante de la fiche *******************************
    def _imprimante(self):
        if not self.imprimante_id:
            raise ValidationError("Choisissez l'imprimante")
        return self.imprimante_id.name


    def _imprimer_um(self, um):
        """Étiquette UM : A5 si le type d'étiquette UM de l'article le demande, sinon l'ancienne.
        Une erreur d'impression n'annule pas la fusion (étiquette à réimprimer depuis la fiche UM). Retourne le complément du message"""
        try:
            with self.env.cr.savepoint():
                imprimante = self._imprimante()
                if um.etiquette_um_a5:
                    um.sudo().imprimer_etiquette_um_a5(imprimante=imprimante)
                else:
                    um.sudo().imprimer_etiquette_um_ancienne(imprimante=imprimante)
            return " · étiquette imprimée"
        except Exception as e:
            _logger.exception("Fusionner des UM : %s : impression étiquette UM %s", self.name, um.name)
            erreur = e.args and e.args[0] or e
            self.message_post(body="❌ Impression étiquette UM %s : %s"%(um.name, erreur))
            return " · ⚠ étiquette non imprimée : %s"%erreur


class is_fusionner_um_ligne(models.Model):
    _name        = 'is.fusionner.um.ligne'
    _description = "Fusionner des UM : UM"
    _order       = 'sequence, id'

    fusion_id = fields.Many2one('is.fusionner.um', "Fiche", required=True, ondelete='cascade', index=True)
    sequence  = fields.Integer("Ordre", help="Ordre de scan : la première UM est gardée")
    um_id     = fields.Many2one('is.galia.base.um', "UM", required=True, index=True)
    gardee    = fields.Boolean("UM gardée")
    uc_id     = fields.Many2one('is.galia.base.uc', "UC seule", help="UC de l'UM si elle n'en a qu'une (pas d'étiquette UM imprimée)")
    nb_uc     = fields.Integer("Nb UC", help="Avant la fusion")
    quantite  = fields.Integer("Quantité", help="Avant la fusion")
    articles  = fields.Char("Articles")
    libelle   = fields.Char("UM / UC", compute='_compute_libelle', help="UC si l'UM n'a qu'une UC (pas d'étiquette UM imprimée), sinon UM")
    state     = fields.Selection(related='fusion_id.state')


    @api.depends('uc_id', 'um_id')
    def _compute_libelle(self):
        for obj in self:
            obj.libelle = obj.uc_id and "UC %s"%obj.uc_id.num_eti or "UM %s"%(obj.um_id.name or '')


    def supprimer_action(self):
        "Poubelle : fenêtre de confirmation avec le détail de la ligne (le texte de confirm d'un bouton est fixe)"
        for obj in self:
            return {
                'type'     : 'ir.actions.act_window',
                'name'     : "Retirer %s ?"%obj.libelle,
                'res_model': self._name,
                'res_id'   : obj.id,
                'view_mode': 'form',
                'views'    : [(self.env.ref('is_plastigray16.is_fusionner_um_ligne_supprimer_form_view').id, 'form')],
                'target'   : 'new',
            }


    def confirmer_suppression_action(self):
        "UM retirée de la fiche"
        for obj in self:
            fiche = obj.fusion_id
            fiche._executer("Retrait %s"%obj.libelle, fiche._retirer_um, obj.um_id)
        return {'type': 'ir.actions.act_window_close'}


    def voir_um_action(self):
        for obj in self:
            return obj.um_id.acceder_um_action()


class is_galia_base_um(models.Model):
    _inherit = 'is.galia.base.um'

    def fusionner_um_action(self):
        "Action de la liste des UM : fiche de fusion des UM cochées, à valider"
        return self.env['is.fusionner.um'].creer_depuis_um(self)
