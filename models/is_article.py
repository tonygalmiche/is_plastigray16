# -*- coding: utf-8 -*-
from odoo import models,fields,api           # type: ignore
import datetime
import pytz
import psycopg2                              # type: ignore
import psycopg2.extras                       # type: ignore
from odoo.exceptions import ValidationError  # type: ignore
import logging
_logger = logging.getLogger(__name__)


class is_article_actualiser(models.TransientModel):
    _name = "is.article.actualiser"
    _description = u"Actualiser la liste des articles"


    def run_actualiser_liste_articles(self):
        self.actualiser_liste_articles()


    def actualiser_liste_articles(self):
        annee = datetime.date.today().year
        user    = self.env['res.users'].browse(self._uid)
        company = user.company_id
        try:
            cnx0 = psycopg2.connect("dbname='"+self._cr.dbname+"' user='"+company.is_postgres_user+"' host='"+company.is_postgres_host+"' password='"+company.is_postgres_pwd+"'")
        except Exception:
            raise ValidationError('Postgresql 0 non disponible !')
        cur0 = cnx0.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        bases = self.env['is.database'].search([])
        for base in bases:
            cnx=False
            if base.database:
                x="dbname='"+base.database  +"' user='"+company.is_postgres_user+"' host='"+company.is_postgres_host+"' password='"+company.is_postgres_pwd+"'"
                try:
                    cnx  = psycopg2.connect(x)
                except Exception:
                    raise ValidationError('Postgresql non disponible !')
            if cnx:
                cur = cnx.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                SQL= """
                    SELECT 
                        pt.id                 as id_origine,
                        pt.is_code            as name,
                        pt.name->>'fr_FR'     as designation,
                        pt.is_mold_dossierf   as moule,
                        ipf.name              as famille,
                        ipsf.name             as sous_famille,
                        ic.name               as categorie,
                        ig.name               as gestionnaire,
                        pt.is_ref_fournisseur as ref_fournisseur,
                        pt.is_ref_client      as ref_client,
                        pt.is_ref_plan        as ref_plan,
                        pt.is_couleur         as couleur,
                        rp1.name              as fournisseur,
                        rp1.is_database_origine_id as fournisseur_id,
                        rp2.is_database_origine_id as client_id,
                        uom.name->>'fr_FR'    as unite,
                        (select cout_std_total from is_cout cout where cout.name=pp.id limit 1) as cout_standard,
                        (select cout_act_total from is_cout cout where cout.name=pp.id limit 1) as cout_actualise,
                        (select sum(quantite) from is_pic_3ans pic where pic.product_id=pp.id and annee='"""+str(annee)+"""') as prevision_annee_n,
                        (   select prix_vente
                            from is_tarif_cial itc
                            where itc.id>0 and itc.indice_prix=999 and itc.product_id=pt.id
                            limit 1
                        ) as prix_vente
                    FROM product_template pt left outer join is_product_famille       ipf on pt.family_id=ipf.id
                                             left outer join is_product_sous_famille ipsf on pt.sub_family_id=ipsf.id
                                             left outer join is_category               ic on pt.is_category_id=ic.id
                                             left outer join is_gestionnaire           ig on pt.is_gestionnaire_id=ig.id
                                             left outer join res_partner               rp1 on pt.is_fournisseur_id=rp1.id
                                             left outer join res_partner               rp2 on pt.is_client_id=rp2.id
                                             left outer join uom_uom                  uom on pt.uom_id=uom.id
                                             left outer join product_product           pp on pp.product_tmpl_id=pt.id
                    WHERE 
                        pt.id>0
                        -- and ic.name='0'
                    ORDER BY pt.is_code
                    -- limit 100
                """
                cur.execute(SQL)
                rows = cur.fetchall()
                for row in rows:
                    client_id = fournisseur_id = False
                    if row['client_id']:
                        client = self.env['res.partner'].browse(row['client_id'])
                        if client.exists():
                            client_id = client.id
                    if row['fournisseur_id']:
                        fournisseur = self.env['res.partner'].browse(row['fournisseur_id'])
                        if fournisseur.exists():
                            fournisseur_id = fournisseur.id
                    vals={
                        'name'             : row['name'],
                        'designation'      : row['designation'],
                        'moule'            : row['moule'],
                        'famille'          : row['famille'],
                        'sous_famille'     : row['sous_famille'],
                        'categorie'        : row['categorie'],
                        'gestionnaire'     : row['gestionnaire'],
                        'ref_fournisseur'  : row['ref_fournisseur'],
                        'ref_client'       : row['ref_client'],
                        'ref_plan'         : row['ref_plan'],
                        'couleur'          : row['couleur'],
                        'client_id'        : client_id,
                        'fournisseur_id'   : fournisseur_id,
                        'fournisseur'      : row['fournisseur'],
                        'unite'            : row['unite'],
                        'database_id'      : base.id,
                        'societe'          : base.database,
                        'cout_standard'    : row['cout_standard'],
                        'cout_actualise'   : row['cout_actualise'],
                        'prix_vente'       : row['prix_vente'],
                        'prevision_annee_n': row['prevision_annee_n'],
                        'id_origine'       : row['id_origine'],
                    }

                    #** Recherche si l'article existe déja ********************
                    articles = self.env['is.article'].search([('societe','=',base.database),('name','=',row['name'])])
                    if len(articles)>0:
                        articles[0].write(vals)
                        action='write'
                    else:
                        self.env['is.article'].create(vals)
                        action='create'
                    _logger.info("actualiser_liste_articles : %s : %s : %s "%(base.database,action,row['name']))
                    #**********************************************************


        return {
            'name': u'Articles de tous les sites',
            'view_mode': 'tree,form',
            'res_model': 'is.article',
            'type': 'ir.actions.act_window',
            'limit': 100,
        }




class is_article(models.Model):
    _name='is.article'
    _description="is.article"
    _order='name,societe'


    database_id       = fields.Many2one("is.database", "Site", index=True)
    societe           = fields.Char("Base", index=True)
    name              = fields.Char("Code PG", index=True)
    designation       = fields.Char("Désignation")
    moule             = fields.Char("Moule")
    famille           = fields.Char("Famille", index=True)
    sous_famille      = fields.Char("Sous-Famille", index=True)
    categorie         = fields.Char("Catégorie", index=True)
    gestionnaire      = fields.Char("Gestionnaire", index=True)
    ref_fournisseur   = fields.Char("Référence fournisseur")
    ref_client        = fields.Char("Référence client")
    ref_plan          = fields.Char("Réf Plan")
    couleur           = fields.Char("Couleur/ Type matière")
    fournisseur       = fields.Char("Fournisseur")
    unite             = fields.Char("Unité")
    cout_standard     = fields.Float("Coût standard")
    cout_actualise    = fields.Float("Coût actualisé")
    prix_vente        = fields.Float("Prix de vente")
    prevision_annee_n = fields.Float("Prévision Année N")
    client_id         = fields.Many2one('res.partner', 'Client par défaut')
    fournisseur_id    = fields.Many2one('res.partner', 'Fournisseur par défaut')
    id_origine        = fields.Integer("Id d'origine")
    url_origine       = fields.Char("URL Origine", copy=False, compute='_compute_url_origine', help="Lien vers le Odoo du site")


    @api.depends('id_origine')
    def _compute_url_origine(self):
        for obj in self:
            url=False
            database = obj.database_id.database
            if obj.id_origine and database:
                database=database.replace('16-','')
                url = "https://%s/web#id=%s&cids=1&model=product.template&view_type=form"%(database,obj.id_origine)
            obj.url_origine = url


    def name_get(self):
        result = []
        for obj in self:          
            name="%s %s"%(obj.name or '',obj.designation or '')
            result.append((obj.id, name))
        return result


