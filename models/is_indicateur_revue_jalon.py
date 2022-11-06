# -*- coding: utf-8 -*-
from odoo import models,fields,api


class is_indicateur_revue_jalon(models.Model):
    _name = "is.indicateur.revue.jalon"
    _description="is_indicateur_revue_jalon"
    _rec_name = 'moule'
    _order = "moule"
    _sql_constraints = [
        ('moule_uniq', 'unique(moule)', u"Le moule doit-être unique !")
    ]


    annee_investissement        = fields.Char('Année investissement')
    client                      = fields.Char('Client', required=True)
    moule                       = fields.Char('Moule' , required=True)
    chef_de_projet              = fields.Char('Chef de projet')
    chrono                      = fields.Char('Chrono')
    j_actuelle                  = fields.Char('J actuelle')
    revue_de_lancement          = fields.Char('Revue de lancement')
    revue_des_risques           = fields.Char('Revue des risques')
    responsable_outillage       = fields.Char('Responsable outillage')
    metrologie                  = fields.Char('Métrologie')
    qualite_developpement       = fields.Char('Qualité développement')
    j0                          = fields.Date('J0')
    date_validation_j0          = fields.Date('Date validation J0')
    avancement_j0               = fields.Integer('Avancement J0')
    j4                          = fields.Date('J4')
    date_validation_j4          = fields.Date('Date validation J4')
    avancement_j4               = fields.Integer('Avancement J4')
    etat                        = fields.Char('état')
    j5                          = fields.Date('J5')
    date_validation_j5          = fields.Date('Date validation J5')
    avancement_j5               = fields.Integer('Avancement J5')
    quantite_annuelle           = fields.Integer('Quantité annuelle')
    affectation_presse          = fields.Char('Affectation presse (Revue de lancement)')
    affectation_presse_actuelle = fields.Char('Affectation presse actuelle')
    cycle_par_piece1            = fields.Float('Cycle par pièce 1')
    cycle_par_piece2            = fields.Float('Cycle par pièce 2')
    nb_emp1                     = fields.Float('Nb empreintes 1')
    nb_emp2                     = fields.Float('Nb empreintes 2')
    mod1                        = fields.Float('MOD 1')
    mod2                        = fields.Float('MOD 2')
    tx_rebut_vendu1             = fields.Float('Tx rebut vendu 1')
    tx_rebut_vendu2             = fields.Float('Tx rebut vendu 2')
    poids_piece1                = fields.Float('Poids pièce (en g) 1')
    poids_piece2                = fields.Float('Poids pièce (en g) 2')
    poids_carotte1              = fields.Float('Poids carotte (en g) 1')
    poids_carotte2              = fields.Float('Poids carotte (en g) 2')
    ca_annuel                   = fields.Integer('CA Annuel')
    vac                         = fields.Integer('VAC')
    dynacase_id                 = fields.Integer('id Dynacase')
