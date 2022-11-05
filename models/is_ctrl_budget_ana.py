# -*- coding: utf-8 -*-
from odoo import models,fields,api


class is_ctrl_budget_ana_annee(models.Model):
    _name = 'is.ctrl.budget.ana.annee'
    _description = u"Contrôle bugétaire analytique - Année"
    _order='annee desc'
    _rec_name = 'annee'

    annee        = fields.Char(u'Année', index=True, required=True)
    product_ids  = fields.One2many('is.ctrl.budget.ana.product','annee_id', string="Articles", copy=True)


    def initialiser_articles(self):
        for obj in self:
            #** Recherche des articles actifs **********************************
            products = self.env['product.product'].search([('segment_id','=',16),('is_code','>=','6')])
            products_ids=[]
            for product in products:
                products_ids.append(product.id)
            #*******************************************************************
            
            #** Suppression des lignes inactives *******************************
            filtre=[
                ('annee_id','=',obj.id),
                ('product_id','not in',products_ids),
            ]
            lignes = self.env['is.ctrl.budget.ana.product'].search(filtre)
            lignes.unlink()
            #*******************************************************************

            #** Recherche des lignes actuelles *********************************
            filtre=[
                ('annee_id','=',obj.id),
            ]
            lignes = self.env['is.ctrl.budget.ana.product'].search(filtre)
            ligne_ids=[]
            for ligne in lignes:
                ligne_ids.append(ligne.product_id.id)
            #*******************************************************************

            #** Création des lignes si elles n'existent pas ********************
            for product in products:
                if product.id not in ligne_ids:
                    vals={
                        'annee_id'  : obj.id,
                        'product_id': product.id,
                    }
                    self.env['is.ctrl.budget.ana.product'].create(vals)
            #*******************************************************************


    def liste_articles_action(self):
        for obj in self:
            return {
                'name': obj.annee,
                'view_mode': 'tree,form',
                'view_type': 'form',
                'res_model': 'is.ctrl.budget.ana.product',
                'domain': [
                    ('annee_id' ,'=',obj.id),
                ],
                'context':{
                    'default_annee_id' : obj.id,
                },
                'type': 'ir.actions.act_window',
                'limit': 1000,
            }



class is_ctrl_budget_ana_product(models.Model):
    _name = 'is.ctrl.budget.ana.product'
    _description = u"Contrôle bugétaire analytique - Articles"
    _order='product_id'
    _rec_name = 'product_id'

    annee_id                 = fields.Many2one("is.ctrl.budget.ana.annee", "Année")
    product_id               = fields.Many2one('product.product', u"Article", required=True)
    is_budget_responsable_id = fields.Many2one('is.budget.responsable', "Rsp budget", related='product_id.is_budget_responsable_id', readonly=True)
    budget_annee = fields.Float(u'Budget année'    , digits=(12,0))
    budget_m01   = fields.Float(u'Budget Janvier'  , digits=(12,0))
    budget_m02   = fields.Float(u'Budget Février'  , digits=(12,0))
    budget_m03   = fields.Float(u'Budget Mars'     , digits=(12,0))
    budget_m04   = fields.Float(u'Budget Avril'    , digits=(12,0))
    budget_m05   = fields.Float(u'Budget Mai'      , digits=(12,0))
    budget_m06   = fields.Float(u'Budget Juin'     , digits=(12,0))
    budget_m07   = fields.Float(u'Budget Juillet'  , digits=(12,0))
    budget_m08   = fields.Float(u'Budget Août'     , digits=(12,0))
    budget_m09   = fields.Float(u'Budget Septembre', digits=(12,0))
    budget_m10   = fields.Float(u'Budget Octobre'  , digits=(12,0))
    budget_m11   = fields.Float(u'Budget Novembre' , digits=(12,0))
    budget_m12   = fields.Float(u'Budget Décembre' , digits=(12,0))

    @api.onchange('budget_annee')
    def _onchange_budget_annee(self):
        budget = self.budget_annee / 12.0
        self.budget_m01 = budget
        self.budget_m02 = budget
        self.budget_m03 = budget
        self.budget_m04 = budget
        self.budget_m05 = budget
        self.budget_m06 = budget
        self.budget_m07 = budget
        self.budget_m08 = budget
        self.budget_m09 = budget
        self.budget_m10 = budget
        self.budget_m11 = budget
        self.budget_m12 = budget


