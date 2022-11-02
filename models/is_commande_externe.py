# -*- coding: utf-8 -*-

from odoo import models,fields,api

class is_commande_externe(models.Model):
    _name='is.commande.externe'
    _description="Commande externe"
    _order='name'

    name        = fields.Char("Code"    , required=True)
    commande    = fields.Char("Commande", required=True)
    commentaire = fields.Text("Commentaire")
 