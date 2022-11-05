# -*- coding: utf-8 -*-
from odoo import models,fields,api


_DAO_RSPLAST=([
    ('A', u'A=Acceptée'),
    ('D', u'D=Déclinée'),
])


_DAO_MOTIF=([
    ('P01', 'Perdu - Prix moule & pièce'),
    ('P02', 'Perdu - Prix moule'),
    ('P03', 'Perdu - Prix pièce'),
    ('P04', 'Perdu - Délai trop long'),
    ('P05', 'Perdu - Projet client annulé'),
    ('P06', 'Perdu - Pas de retour client'),
    ('P07', 'Perdu - Choix stratégique client'),
    ('D01', 'Décliné - Motif technique (process ou techno)'),
    ('D02', 'Décliné - Capacitaire PG'),
    ('D03', 'Décliné - Volume faible'),
    ('D04', 'Décliné - Stratégique'),
])


_DAO_AVANCEMENT=([
    (u'Développement', u'Développement'),
    (u'Série'        , u'Série'),
])


_STATE=([
    (u'plascreate'     , u'créé'),
    (u'plasanalysed'   , u'analysé'),
    (u'plastransbe'    , u'transmis BE'),
    (u'plasvalidbe'    , u'validé BE'),
    (u'plasvalidcom'   , u'validé commercial'),
    (u'plasdiffusedcli', u'diffusé client'),
    (u'plasrelancecli' , u'relance client'),
    (u'plaswinned'     , u'gagné'),
    (u'plasloosed'     , u'perdu'),
    (u'plascancelled'  , u'annulé'),
])


class is_dossier_appel_offre(models.Model):
    _name = "is.dossier.appel.offre"
    _description="is_dossier_appel_offre"
    _order = "dao_num"
    _rec_name = 'dao_num'

    dao_num          = fields.Char("Numéro")
    dao_date         = fields.Date("Date consultation")
    dao_annee        = fields.Char("Année consultation")
    dao_client       = fields.Char("Client")
    dao_typeclient   = fields.Char("Type client")
    dao_sectclient   = fields.Char("Section client")
    dao_commercial   = fields.Char("Commercial")
    dao_desig        = fields.Char("Désignation")
    dao_ref          = fields.Char("Référence")
    dao_datedms      = fields.Date("Date DMS")
    dao_ca           = fields.Float("Chiffre d'affaire")
    dao_vacom        = fields.Float("VA commerciale")
    dao_pourcentva   = fields.Float("% VA")
    dao_camoule      = fields.Float("CA Moule")
    dao_be           = fields.Char("Chef de projet")
    dao_dirbe        = fields.Char("Directeur technique")
    dao_daterepbe    = fields.Date("Date réponse BE")
    dao_daterepplast = fields.Date("Date réponse Plastigray")
    dao_rsplast      = fields.Selection(_DAO_RSPLAST, "Rsp Plastigray")
    dao_daterepcli   = fields.Date("Date réponse client")
    dao_comment      = fields.Char("Commentaire")
    dao_motif        = fields.Selection(_DAO_MOTIF, "Motif")
    dao_avancement   = fields.Selection(_DAO_AVANCEMENT, "Avancement")
    state            = fields.Selection(_STATE, "Etat")
    dynacase_id      = fields.Integer("id Dynacase")
