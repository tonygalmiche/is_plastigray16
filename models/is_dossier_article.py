# -*- coding: utf-8 -*-
from odoo import models,fields,api           # type: ignore
from odoo.exceptions import ValidationError  # type: ignore
import datetime
import pytz
from subprocess import PIPE, Popen
import psycopg2                             # type: ignore
from psycopg2.extras import RealDictCursor  # type: ignore
import logging
_logger = logging.getLogger(__name__)


class is_dossier_article(models.Model):
    _name = 'is.dossier.article'
    _inherit=['mail.thread']
    _description = "Dossier article"
    _rec_name = 'code_pg'
    _order = 'code_pg'


    type_dossier = fields.Selection([
        ("matiere",   "Matière"),
        ("colorant",  "Colorant"),
        ("composant", "Composant"),
    ], string="Type dossier", required=True, default='matiere', tracking=True)
    code_pg           = fields.Char('Code PG', index=True, required=True, tracking=True)
    designation       = fields.Char("Désignation", tracking=True)
    moule             = fields.Char("Moule", tracking=True)
    famille           = fields.Char("Famille", index=True, tracking=True)
    sous_famille      = fields.Char("Sous-Famille", index=True, tracking=True)
    categorie         = fields.Char("Catégorie", index=True, tracking=True)
    gestionnaire      = fields.Char("Gestionnaire", index=True, tracking=True)
    ref_fournisseur   = fields.Char("Référence fournisseur", tracking=True)
    ref_plan          = fields.Char("Réf Plan", tracking=True)
    couleur           = fields.Char("Couleur/ Type matière", tracking=True)
    fournisseur       = fields.Char("Fournisseur par défaut", tracking=True)
    unite             = fields.Char("Unité")
    automobile        = fields.Boolean("Automobile", help="Destiné aux produits automobile", default=False)

    # Informations matières :
    gamme_commerciale_id = fields.Many2one('is.dossier.article.gamme.commerciale', "Gamme commerciale", tracking=True) # : liste de choix ( LEXAN, ELASTOLLAN, DELRIN,…). voir annexe
    producteur_id        = fields.Many2one('is.dossier.article.producteur', "Producteur", tracking=True) #: menu déroulant (SABIC, BASF, DUPONT, CHIMEI…) voir annexe
    taux_de_recycle      = fields.Integer("Taux de recyclé (%)", tracking=True) #: champ nombre
    traitement1_id       = fields.Many2one('is.dossier.article.traitement', "Traitement 1", tracking=True) #: menu déroulant ( anti-UV,etc…)
    traitement2_id       = fields.Many2one('is.dossier.article.traitement', "Traitement 2", tracking=True) #: menu déroulant : le même que précédemment
    utilisation_id       = fields.Many2one('is.dossier.article.utilisation', "Utilisations", tracking=True) #: liste de choix : possibilité de sélectionner plusieurs choix ( capotage domotique, …)
    carte_jaune          = fields.Selection([('Oui', u'Oui'),('Non'  , "Non")], "Carte jaune", tracking=True) #: oui/non
    couleur_ral          = fields.Char("Couleur/Ral", tracking=True) #: champ libre
    documents_techniques = fields.Char("Documents techniques", compute="_compute_documents_techniques", readonly=True, store=False) #: lien pour accéder directement aux documents de la GED

    # Propriétés Matières :
    densite              = fields.Float("Densité", digits=(14,2), tracking=True) #: nombre avec 2 chiffres après la virgule
    durete_id            = fields.Many2one('is.dossier.article.durete', "Dureté", tracking=True) #: menu déroulant : 95 SHORE A … 
    taux_de_charge1      = fields.Integer("Taux de charge 1 (%)", tracking=True) #: champ nombre
    type_article1_id     = fields.Many2one('is.dossier.article.type.article', "Type 1", tracking=True) #: menu déroulant (fibres de verre, talc, textile, bois…)
    taux_de_charge2      = fields.Integer("Taux de charge 2 (%) ", tracking=True) # champ nombre
    type_article2_id     = fields.Many2one('is.dossier.article.type.article', "Type 2", tracking=True) #: menu déroulant (fibres de verre, talc, textile, bois…) Idem champ précédent
    combustion_id        = fields.Many2one('is.dossier.article.combustion', "Combustion", tracking=True) #: menu déroulant ( V0, V2…)
    epaisseur_combustion = fields.Float("Epaisseur combustion (mm)", digits=(14,2), tracking=True) #: nombre avec 2 chiffres après la virgule
    gwfi                 = fields.Integer("GWFI (°C)", tracking=True) #: champ nombre
    lab_l                = fields.Float(" L (L*A*B)", digits=(14,2), tracking=True) #: 3 cases avec nombre 2 chiffres après la virgule :
    lab_a                = fields.Float(" A (L*A*B)", digits=(14,2), tracking=True) #: 3 cases avec nombre 2 chiffres après la virgule :
    lab_b                = fields.Float(" B (L*A*B)", digits=(14,2), tracking=True) #: 3 cases avec nombre 2 chiffres après la virgule :

    # Informations production :
    mfr                 = fields.Char("MFR (g/10min)", tracking=True) #: champ libre
    mvr                 = fields.Char("MVR (cm3/10min)", tracking=True) #: champ libre
    norme               = fields.Char("Norme (n° - T°C/masse kg)", tracking=True) #: champ libre
    temp_transformation = fields.Char("T°C transformation (°C)", tracking=True) #: champ nombre
    temp_moule          = fields.Char("T°C moule (°C)", tracking=True) #: champ nombre
    retrait             = fields.Char("Retrait (// - L )", tracking=True) #: champ libre
    temps_etuvage       = fields.Integer("Temps étuvage minimum (H)", tracking=True) #: champ nombre
    temperature_etuvage = fields.Integer("Température étuvage (°C +/-10°)", tracking=True) #: champ nombre
    dessiccateur        = fields.Selection([('Oui', u'Oui'),('Non'  , "Non")], "Dessiccateur", tracking=True) #:  oui/non
    temp_rose           = fields.Integer("T°C Rosée", tracking=True) #: champ nombre
    taux_humidite       = fields.Float("Taux d'humidité maximum (%)", digits=(14,2), tracking=True) #: champ nombre : 2 chiffres après la virgule
    commentaire         = fields.Char("Commentaires", tracking=True) #: champ libre
    code_recyclage_id   = fields.Many2one('is.dossier.article.code.recyclage', "Code recyclage", tracking=True) #: menu déroulant : A,B…
    caracteristique_specifique = fields.Text("Caractéristiques spécifiques", tracking=True)
    controle_qualite    = fields.Char("Contrôle qualité", tracking=True) #: champ libre : attention : champ présent dans onglet information à transférer dans ce nouvel onglet : attention lien avec les réceptions.
    conditions_stockage = fields.Char("Conditions de stockage", tracking=True)
    empreinte_carbonne  = fields.Float('Empreinte Carbone (kg CO2 - Eq)', digits=(14,2))
    active              = fields.Boolean('Actif', default=True, tracking=True)


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
                _logger.info("Connexion Dynacase OK")
            except:
                cr_dynacase=False
                _logger.info("Connexion à Dynacase impossible")
                #raise ValidationError("Connexion à Dynacase impossible")
        #**********************************************************************
        for obj in self:
            url=False
            if cr_dynacase:
                if obj.sous_famille=="COLORANTS":
                    SQL="select id from doc48615 where dosart_codepg=%s"
                else:
                    SQL="select id from doc48613 where dosart_codepg=%s"
                cr_dynacase.execute(SQL, [obj.code_pg])
                _logger.info("SQL=%s (%s)"%(SQL,obj.code_pg))
                result = cr_dynacase.fetchall()
                for row in result:
                    url="https://dynacase-rp/?sole=Y&app=FDL&action=FDL_CARD&latest=Y&id="+str(row["id"])
            _logger.info("url=%s"%url)
            obj.documents_techniques=url


    def is_dossier_article_actualiser_action(self):
        cdes = self.env['is.commande.externe'].search([('name','=',"actualiser-dossier-article")])
        for cde in cdes:
            p = Popen(cde.commande, shell=True, stdout=PIPE, stderr=PIPE)
            stdout, stderr = p.communicate()
            _logger.info("%s => %s"%(cde.commande,stdout))
            if stderr:
                raise ValidationError("Erreur dans commande externe '%s' => %s"%(cde.commande,stderr))
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


