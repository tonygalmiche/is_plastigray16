# -*- coding: utf-8 -*-
from odoo import models,fields,api
import logging
_logger = logging.getLogger(__name__)


_STATE = [
    ('scan_um', 'Scan des UM'),
    ('tri'    , 'Tri'),
    ('fin'    , 'Fin du contrôle'),
    ('termine', 'Terminé'),
    ('annule' , 'Annulé'),
]

_TYPE_LIGNE = [
    ('um_origine' , "UM d'origine"),
    ('uc_bonne'   , "UC bonne"),
    ('uc_ci'      , "UC en CI"),
    ('fin_um'     , "Fin UM en cours"),
    ('nouvelle_uc', "UC à recontrôler"),
    ('rebut'      , "Rebut"),
]


class is_controle_qualite_um(models.Model):
    _name        = 'is.controle.qualite.um'
    _inherit     = ['mail.thread']
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


    name                      = fields.Char("N° contrôle", readonly=True, copy=False, index=True)
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
