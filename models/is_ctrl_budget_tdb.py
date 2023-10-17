# -*- coding: utf-8 -*-
from odoo import models,fields,api


_DESTINATION = [
    ("2", "PIC"),
    ("3", "Réa Std"),
    ("4", "Ctrl Mens"),
    ("7", "Saisie Trim"),
]


def _get_destination(dest):
    for line in _DESTINATION:
        if line[0] == dest:
            return line[1]
    return ''


class is_ctrl_budget_tdb_famille(models.Model):
    _name = 'is.ctrl.budget.tdb.famille'
    _description = u"Contrôle bugétaire - Budget Tableau de bord -Famille"
    _order='ordre,name'

    name     = fields.Char(u'Famille', index=True, required=True)
    ordre    = fields.Integer(u'Ordre', index=True, required=True)
    variable = fields.Boolean(u'Montant variable', default=True)
    fixe     = fields.Boolean(u'Montant fixe'    , default=True)
    active   = fields.Boolean(u'Active'          , default=True)


class is_ctrl_budget_tdb_famille_rel(models.Model):
    _name = 'is.ctrl.budget.tdb.famille.rel'
    _description = u"Contrôle bugétaire - Budget Tableau de bord - Famille - Relation"
    _order='id'

    saisie_id  = fields.Many2one("is.ctrl.budget.tdb.saisie", "Saisie", ondelete='cascade')
    famille_id = fields.Many2one('is.ctrl.budget.tdb.famille', u"Famille")


    def lignes_famille_action(self):
        for obj in self:
            name=str(obj.saisie_id.mois)+u'/'+str(obj.saisie_id.annee)+u':'+_get_destination(obj.saisie_id.destination)+u':'+obj.famille_id.name
            tree_view=self.env.ref('is_plastigray16.is_ctrl_budget_tdb_tree_view1')
            if obj.famille_id.fixe:
                tree_view=self.env.ref('is_plastigray16.is_ctrl_budget_tdb_tree_view2')
            # montant_fixe_filter=False
            # if obj.famille_id.fixe:
            #     montant_fixe_filter=True
            return {
                'name': name,
                'view_mode': 'tree,form',
                'views': [[tree_view.id, "list"], [False, "form"]],
                'res_model': 'is.ctrl.budget.tdb',
                'domain': [
                    ('saisie_id' ,'=',obj.saisie_id.id),
                    ('famille_id','=',obj.famille_id.id)
                ],
                'context':{
                    'default_saisie_id' : obj.saisie_id.id,
                    'default_famille_id': obj.famille_id.id,
                    #'search_default_montant_fixe_filter': montant_fixe_filter,
                },
                'type': 'ir.actions.act_window',
                'limit': 1000,
            }


class is_ctrl_budget_tdb_intitule(models.Model):
    _name = 'is.ctrl.budget.tdb.intitule'
    _description = u"Contrôle bugétaire - Budget Tableau de bord -Ligne"
    _order='ordre'
    _rec_name='intitule'

    famille_id  = fields.Many2one('is.ctrl.budget.tdb.famille', u"Famille", required=True)
    ordre       = fields.Integer(u'Ordre', index=True, required=True)
    code        = fields.Integer(u'Code', index=True, required=True)
    intitule    = fields.Char(u'Intitulé Ligne', required=True)
    active      = fields.Boolean(u'Actif', default=True)


class is_ctrl_budget_tdb_saisie(models.Model):
    _name = 'is.ctrl.budget.tdb.saisie'
    _description = u"Contrôle bugétaire - Budget Tableau de bord - Saisie"
    _order='annee desc, mois desc, destination'

    annee        = fields.Char(u'Année'  , index=True, required=True)
    mois         = fields.Integer(u'Mois', index=True, required=True)
    destination  = fields.Selection(_DESTINATION  , "Destination", index=True, required=True)
    ligne_ids    = fields.One2many('is.ctrl.budget.tdb', 'saisie_id', u"Lignes", copy=True)
    famille_ids  = fields.One2many('is.ctrl.budget.tdb.famille.rel','saisie_id', string="Familles", copy=True)

    def copy(self,vals):
        for obj in self:
            vals['annee']=obj.annee+u' (copie)'
            res=super(is_ctrl_budget_tdb_saisie, self).copy(vals)
            return res

    # La fonction name_get est une fonction standard d'Odoo permettant de définir le nom des fiches (dans les relations x2x)
    # La fonction name_search permet de définir les résultats des recherches dans les relations x2x. En général, elle appelle la fonction name_get
    def name_get(self):
        res=[]
        for obj in self:
            name=str(obj.mois)+u'/'+str(obj.annee)+u':'+_get_destination(obj.destination)
            res.append((obj.id, name))
        return res


    def lignes_action(self):
        for obj in self:
            name=str(obj.mois)+u'/'+str(obj.annee)+u':'+_get_destination(obj.destination)
            return {
                'name': name,
                'view_mode': 'tree,form',
                'res_model': 'is.ctrl.budget.tdb',
                'domain': [
                    ('saisie_id' ,'=',obj.id),
                ],
                'context':{
                    'default_saisie_id' : obj.id,
                    'search_default_montant_fixe_filter': True,
                },
                'type': 'ir.actions.act_window',
                'limit': 1000,
            }


    def initialiser_lignes(self):
        for obj in self:
            #** Recherche des intitules actifs *********************************
            intitules = self.env['is.ctrl.budget.tdb.intitule'].search([])
            intitules_ids=[]
            for intitule in intitules:
                intitules_ids.append(intitule.id)
            #*******************************************************************
            
            #** Suppression des lignes inactives *******************************
            filtre=[
                ('saisie_id','=',obj.id),
                ('intitule_id','not in',intitules_ids),
            ]
            lignes = self.env['is.ctrl.budget.tdb'].search(filtre)
            lignes.unlink()
            #*******************************************************************

            #** Recherche des intitules actifs *********************************
            filtre=[
                ('saisie_id','=',obj.id),
            ]
            lignes = self.env['is.ctrl.budget.tdb'].search(filtre)
            ligne_ids=[]
            for ligne in lignes:
                ligne_ids.append(ligne.intitule_id.id)
            #*******************************************************************

            #** Création des lignes si elles n'existent pas ********************
            for intitule in intitules:
                if intitule.id not in ligne_ids:
                    vals={
                        'saisie_id'  : obj.id,
                        'ordre'      : intitule.ordre,
                        'intitule_id': intitule.id,
                        'code'       : intitule.code,
                    }
                    self.env['is.ctrl.budget.tdb'].create(vals)
            #*******************************************************************

            #** Création des lignes des familles *******************************
            obj.famille_ids.unlink()
            familles = self.env['is.ctrl.budget.tdb.famille'].search([])
            for famille in familles:
                vals={
                    'saisie_id' : obj.id,
                    'famille_id': famille.id,
                }
                self.env['is.ctrl.budget.tdb.famille.rel'].create(vals)
            #*******************************************************************


class is_ctrl_budget_tdb(models.Model):
    _name = 'is.ctrl.budget.tdb'
    _description = u"Contrôle bugétaire - Budget Tableau de bord"
    _order='ordre'


    @api.depends('intitule_id')
    def _compute(self):
        for obj in self:
            obj.famille_id  = obj.intitule_id.famille_id.id


    saisie_id        = fields.Many2one("is.ctrl.budget.tdb.saisie", "Saisie", ondelete='cascade')
    ordre            = fields.Integer(u'Ordre', index=True, required=True)
    intitule_id      = fields.Many2one('is.ctrl.budget.tdb.intitule', u"Intitulé", required=True)
    code             = fields.Integer(u'Code', index=True, required=True)
    famille_id       = fields.Many2one("is.ctrl.budget.tdb.famille", "Famille", index=True, store=True, readonly=True, compute='_compute')
    montant_variable = fields.Float('Montant Variable', digits=(14,2))
    montant_fixe     = fields.Float('Montant Fixe'    , digits=(14,2))






