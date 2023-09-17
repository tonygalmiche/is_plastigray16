# -*- coding: utf-8 -*-
from odoo import models,fields,api
import datetime
import pytz
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


class is_dossier_article(models.Model):
    _name = 'is.dossier.article'
    _description = u"Dossier article"
    _rec_name = 'code_pg'
    _order = 'code_pg'

    code_pg       = fields.Char(u'Code PG', index=True, required=True)
    designation       = fields.Char(u"Désignation")
    moule             = fields.Char(u"Moule")
    famille           = fields.Char(u"Famille", index=True)
    sous_famille      = fields.Char(u"Sous-Famille", index=True)
    categorie         = fields.Char(u"Catégorie", index=True)
    gestionnaire      = fields.Char(u"Gestionnaire", index=True)
    ref_fournisseur   = fields.Char(u"Référence fournisseur")
    ref_plan          = fields.Char(u"Réf Plan")
    couleur           = fields.Char(u"Couleur/ Type matière")
    fournisseur       = fields.Char(u"Fournisseur par défaut")
    unite             = fields.Char(u"Unité")

    # Informations matières :
    gamme_commerciale_id = fields.Many2one('is.dossier.article.gamme.commerciale', u"Gamme commerciale") # : liste de choix ( LEXAN, ELASTOLLAN, DELRIN,…). voir annexe
    producteur_id        = fields.Many2one('is.dossier.article.producteur', u"Producteur") #: menu déroulant (SABIC, BASF, DUPONT, CHIMEI…) voir annexe
    taux_de_recycle      = fields.Integer(u"Taux de recyclé (%)") #: champ nombre
    traitement1_id       = fields.Many2one('is.dossier.article.traitement', u"Traitement 1") #: menu déroulant ( anti-UV,etc…)
    traitement2_id       = fields.Many2one('is.dossier.article.traitement', u"Traitement 2") #: menu déroulant : le même que précédemment
    utilisation_id       = fields.Many2one('is.dossier.article.utilisation', u"Utilisations") #: liste de choix : possibilité de sélectionner plusieurs choix ( capotage domotique, …)
    carte_jaune          = fields.Selection([('Oui', u'Oui'),('Non'  , u"Non")], u"Carte jaune") #: oui/non
    couleur_ral          = fields.Char(u"Couleur/Ral") #: champ libre
    documents_techniques = fields.Char(u"Documents techniques", compute="_compute_documents_techniques", readonly=True, store=False) #: lien pour accéder directement aux documents de la GED

    # Propriétés Matières :
    densite              = fields.Float(u"Densité", digits=(14,2)) #: nombre avec 2 chiffres après la virgule
    durete_id            = fields.Many2one('is.dossier.article.durete', u"Dureté") #: menu déroulant : 95 SHORE A … 
    taux_de_charge1      = fields.Integer(u"Taux de charge 1 (%)") #: champ nombre
    type_article1_id     = fields.Many2one('is.dossier.article.type.article', u"Type 1") #: menu déroulant (fibres de verre, talc, textile, bois…)
    taux_de_charge2      = fields.Integer(u"Taux de charge 2 (%) ") # champ nombre
    type_article2_id     = fields.Many2one('is.dossier.article.type.article', u"Type 2") #: menu déroulant (fibres de verre, talc, textile, bois…) Idem champ précédent
    combustion_id        = fields.Many2one('is.dossier.article.combustion', u"Combustion") #: menu déroulant ( V0, V2…)
    epaisseur_combustion = fields.Float(u"Epaisseur combustion (mm)", digits=(14,2)) #: nombre avec 2 chiffres après la virgule
    gwfi                 = fields.Integer(u"GWFI (°C)") #: champ nombre
    lab_l                = fields.Float(u" L (L*A*B)", digits=(14,2)) #: 3 cases avec nombre 2 chiffres après la virgule :
    lab_a                = fields.Float(u" A (L*A*B)", digits=(14,2)) #: 3 cases avec nombre 2 chiffres après la virgule :
    lab_b                = fields.Float(u" B (L*A*B)", digits=(14,2)) #: 3 cases avec nombre 2 chiffres après la virgule :

    # Informations production :
    mfr                 = fields.Integer(u"MFR (g/10min)") #: champ libre
    mvr                 = fields.Integer(u"MVR (cm3/10min)") #: champ libre
    norme               = fields.Char(u"Norme (n° - T°C/masse kg)") #: champ libre
    temp_transformation = fields.Char(u"T°C transformation (°C)") #: champ nombre
    temp_moule          = fields.Char(u"T°C moule (°C)") #: champ nombre
    retrait             = fields.Char(u"Retrait (// - L )") #: champ libre
    temps_etuvage       = fields.Integer(u"Temps étuvage minimum (H)") #: champ nombre
    temperature_etuvage = fields.Integer(u"Température étuvage (°C +/-10°)") #: champ nombre
    dessiccateur        = fields.Selection([('Oui', u'Oui'),('Non'  , u"Non")], u"Dessiccateur") #:  oui/non
    temp_rose           = fields.Integer(u"T°C Rosée") #: champ nombre
    taux_humidite       = fields.Float(u"Taux d'humidité maximum (%)", digits=(14,2)) #: champ nombre : 2 chiffres après la virgule
    commentaire         = fields.Char(u"Commentaires") #: champ libre
    code_recyclage_id   = fields.Many2one('is.dossier.article.code.recyclage', u"Code recyclage") #: menu déroulant : A,B…
    controle_qualite    = fields.Char(u"Contrôle qualité") #: champ libre : attention : champ présent dans onglet information à transférer dans ce nouvel onglet : attention lien avec les réceptions.
    conditions_stockage = fields.Char(u"Conditions de stockage")


    @api.depends('code_pg')
    def _compute_documents_techniques(self):
        #for obj in self:
        #    obj.documents_techniques=False

        #** Connexion à Dynacase **********************************************
        uid = self._uid
        cr  = self._cr
        company = self.env.user.company_id
        password=company.is_dynacase_pwd
        cr_dynacase=False
        if password:
            try:
                cnx_dynacase = psycopg2.connect("host='dynacase' port=5432 dbname='freedom' user='freedomowner' password='"+password+"'")
                cr_dynacase = cnx_dynacase.cursor(cursor_factory=RealDictCursor)
            except:
                #cr_dynacase=False
                raise ValidationError("Connexion à Dynacase impossible")
        #**********************************************************************
        for obj in self:
            url=False
            if cr_dynacase:
                if obj.sous_famille=="COLORANTS":
                    SQL="select id from doc48615 where dosart_codepg=%s"
                else:
                    SQL="select id from doc48613 where dosart_codepg=%s"
                cr_dynacase.execute(SQL, [obj.code_pg])
                result = cr_dynacase.fetchall()
                for row in result:
                    url="https://dynacase-rp/?sole=Y&app=FDL&action=FDL_CARD&latest=Y&id="+str(row["id"])
            obj.documents_techniques=url


    def is_dossier_article_actualiser_action(self):
        cdes = self.env['is.commande.externe'].search([('name','=',"actualiser-dossier-article")])
        for cde in cdes:
            lines=os.popen(cde.commande).readlines()
            for line in lines:
                _logger.info(line.strip())
        now = datetime.datetime.now(pytz.timezone('Europe/Paris')).strftime('%H:%M:%S')
        return {
            'name': u'Dossiers articles actualisés à '+str(now),
            'view_mode': 'tree,form',
            'res_model': 'is.dossier.article',
            'type': 'ir.actions.act_window',
        }


class is_dossier_article_gamme_commerciale(models.Model):
    _name = 'is.dossier.article.gamme.commerciale'
    _description="is_dossier_article_gamme_commerciale"
    _order='name'
    _sql_constraints = [('name_uniq','UNIQUE(name)', 'Ce code existe déjà')] 

    name = fields.Char("Code",required=True, index=True)

class is_dossier_article_producteur(models.Model):
    _name = 'is.dossier.article.producteur'
    _description="is_dossier_article_producteur"
    _order='name'
    _sql_constraints = [('name_uniq','UNIQUE(name)', 'Ce code existe déjà')] 

    name = fields.Char("Code",required=True, index=True)

class is_dossier_article_traitement(models.Model):
    _name = 'is.dossier.article.traitement'
    _description="is_dossier_article_traitement"
    _order='name'
    _sql_constraints = [('name_uniq','UNIQUE(name)', 'Ce code existe déjà')] 

    name = fields.Char("Code",required=True, index=True)

class is_dossier_article_utilisation(models.Model):
    _name = 'is.dossier.article.utilisation'
    _description="is_dossier_article_utilisation"
    _order='name'
    _sql_constraints = [('name_uniq','UNIQUE(name)', 'Ce code existe déjà')] 

    name = fields.Char("Code",required=True, index=True)

class is_dossier_article_durete(models.Model):
    _name = 'is.dossier.article.durete'
    _description="is_dossier_article_durete"
    _order='name'
    _sql_constraints = [('name_uniq','UNIQUE(name)', 'Ce code existe déjà')] 

    name = fields.Char("Code",required=True, index=True)

class is_dossier_article_type_article(models.Model):
    _name = 'is.dossier.article.type.article'
    _description="is_dossier_article_type_article"
    _order='name'
    _sql_constraints = [('name_uniq','UNIQUE(name)', 'Ce code existe déjà')] 

    name = fields.Char("Code",required=True, index=True)

class is_dossier_article_combustion(models.Model):
    _name = 'is.dossier.article.combustion'
    _description="is_dossier_article_combustion"
    _order='name'
    _sql_constraints = [('name_uniq','UNIQUE(name)', 'Ce code existe déjà')] 

    name = fields.Char("Code",required=True, index=True)

class is_dossier_article_code_recyclage(models.Model):
    _name = 'is.dossier.article.code.recyclage'
    _description="is_dossier_article_code_recyclage"
    _order='name'
    _sql_constraints = [('name_uniq','UNIQUE(name)', 'Ce code existe déjà')] 

    name = fields.Char("Code",required=True, index=True)


