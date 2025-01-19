# -*- coding: utf-8 -*-

from odoo import models,fields,api
from odoo.exceptions import ValidationError
import datetime
import time
import psycopg2
import sys
from math import *
import logging
_logger = logging.getLogger(__name__)


class is_liste_servir_client(models.Model):
    _name='is.liste.servir.client'
    _description="Client Liste à servir"
    _order='name'

    name            = fields.Many2one('res.partner', 'Client')
    liste_servir_id = fields.Many2one('is.liste.servir', 'Liste à servir')
    listes_servir   = fields.Text("Listes à servir", compute='_compute_aff_listes_servir', readonly=True, store=False)
    nb_liste_servir = fields.Integer("Nombre de listes à servir", compute='_compute_nb_liste_servir', readonly=True, store=False)
    zip             = fields.Char('Code postal')
    city            = fields.Char('Ville')
    delai_transport = fields.Integer('Délai de transport')
    date_debut      = fields.Date("Date de début d'expédition")
    date_fin        = fields.Date("Date de fin d'expédition")
    livrable        = fields.Boolean("Livrable")

    def _compute_aff_listes_servir(self):
        for obj in self:
            liste_servir_obj = self.env['is.liste.servir']
            liste_servir_ids = liste_servir_obj.search([('partner_id','=',obj.name.id),('state','!=','traite')])
            obj.listes_servir = '\n'.join([liste.name for liste in liste_servir_ids])

    def _compute_nb_liste_servir(self):
        for obj in self:
            liste_servir_obj = self.env['is.liste.servir']
            liste_servir_ids = liste_servir_obj.search([('partner_id','=',obj.name.id),('state','!=','traite')])
            obj.nb_liste_servir = len(liste_servir_ids)

    def _get_sql(self, obj, aqp):
        SQL="""
            SELECT  sol.product_id,
            """
        if aqp:
            SQL += """
                    pt.is_livree_aqp,
               """
        SQL += """                    so.is_point_dechargement
            FROM sale_order so INNER JOIN sale_order_line sol ON so.id=sol.order_id
            """
        if aqp:
            SQL += """
            INNER JOIN product_product pp ON pp.id=sol.product_id INNER JOIN product_template pt ON pp.product_tmpl_id=pt.id
            """
        SQL += """
            WHERE so.partner_id=""" + str(obj.name.id) + """
                  AND so.state='draft'
                  AND sol.is_date_expedition<='"""+str(obj.date_fin)+"""'
                  AND sol.product_id>0
                  AND sol.is_type_commande='ferme'
                  AND so.is_type_commande!='ls'
        """
        if obj.date_debut:
            SQL=SQL+" and sol.is_date_expedition>='"+str(obj.date_debut)+"' "
        return SQL

    def points_dechargement_and_aqp(self, obj, aqp=False):
        points_dechargement = []
        SQL = self._get_sql(obj, aqp)
        self._cr.execute(SQL)
        result = self._cr.dictfetchall()
        if aqp:
            lst_aqp = []
        for row in result:
            point_dechargement = row['is_point_dechargement']
            if point_dechargement not in points_dechargement:
                points_dechargement.append(point_dechargement)
            if aqp and row['is_livree_aqp'] not in lst_aqp:
                lst_aqp.append(row['is_livree_aqp'])

        if not points_dechargement:
            points_dechargement.append(None)
        if aqp:
            return points_dechargement, lst_aqp
        return points_dechargement

    def creer_liste_servir_action(self):
        for obj in self:
            liste_servir_obj = self.env['is.liste.servir']

            if obj.name.is_source_location_id:
                is_source_location_id=obj.name.is_source_location_id.id
            else:
                is_source_location=liste_servir_obj._get_default_location()
                is_source_location_id=is_source_location.id
            vals={
                'partner_id'           : obj.name.id,
                'transporteur_id'      : obj.name.is_transporteur_id.id,
                'is_source_location_id': is_source_location_id,
                'date_debut'           : obj.date_debut,
                'date_fin'             : obj.date_fin,
                'livrable'             : obj.livrable,
            }
            listes_servir = []
            if not obj.name.is_caracteristique_liste_a_servir:
                points_dechargement = [None]
                lst_aqp = [None]
            elif obj.name.is_caracteristique_liste_a_servir == 'status_aqp':
                points_dechargement = [None]
                lst_aqp = [True, False]
            elif obj.name.is_caracteristique_liste_a_servir == 'point_de_chargement':
                points_dechargement = self.points_dechargement_and_aqp(obj, False)
                lst_aqp = [None]
            elif obj.name.is_caracteristique_liste_a_servir == 'point_de_chargement_et_status_aqp':
                points_dechargement, lst_aqp = self.points_dechargement_and_aqp(obj, True)
            for aqp in lst_aqp:
                for point_dechargement in points_dechargement:
                    liste_servir = liste_servir_obj.create(vals)
                    liste_servir.action_importer_commandes(aqp, point_dechargement)
                    if not liste_servir.line_ids:
                        liste_servir.unlink()
                    else:
                        if point_dechargement:
                            liste_servir.is_point_dechargement = point_dechargement
                        if aqp is not None:
                            liste_servir.is_livree_aqp = aqp
                        listes_servir.append(liste_servir)

            if len(listes_servir) > 1:
                return {
                    'name': 'ls',
                    'view_mode': 'tree,form',
                    'view_type': 'form',
                    'res_model': 'is.liste.servir',
                    'domain': [
                        ('partner_id' ,'=',obj.name.id),
                        ('state','!=','traite'),
                    ],
                    'type': 'ir.actions.act_window',
                    'limit': 1000,
                }
            return {
                'name': "Liste à servir",
                'view_mode': 'form',
                'res_model': 'is.liste.servir',
                'type': 'ir.actions.act_window',
                'res_id': listes_servir[0].id,
            }

    def liste_servir_action(self):
        for obj in self:
            if obj.nb_liste_servir == 1:
                liste_servir_obj = self.env['is.liste.servir']
                liste_servir_ids = liste_servir_obj.search([('partner_id','=',obj.name.id),('state','!=','traite')])
                return {
                    'name': 'ls',
                    'view_mode': 'form',
                    'res_model': 'is.liste.servir',
                    'res_id': liste_servir_ids[0].id,
                    'type': 'ir.actions.act_window',
                }
            return {
                'name': 'ls',
                'view_mode': 'tree,form',
                'view_type': 'form',
                'res_model': 'is.liste.servir',
                'domain': [
                    ('partner_id' ,'=',obj.name.id),
                    ('state','!=','traite'),
                ],
                'type': 'ir.actions.act_window',
                'limit': 1000,
            }



class is_liste_servir(models.Model):
    _name='is.liste.servir'
    _description="Liste à servir"
    _order='id desc'

    def _get_default_location(self):
        company_id = self.env.user.company_id.id
        warehouse_obj = self.env['stock.warehouse']
        warehouse_id = warehouse_obj.search([('company_id','=',company_id)])
        location = warehouse_id.out_type_id and  warehouse_id.out_type_id.default_location_src_id
        return location and location or False


    def _compute_is_certificat_conformite_msg(self):
        for obj in self:
            msg = False
            if obj.partner_id.is_certificat_matiere:
                nb=0
                for line in obj.line_ids:
                    certificat = self.env['is.certificat.conformite'].GetCertificat(obj.partner_id, line.product_id.id)
                    if not certificat:
                        nb+=1
                msg=u"Ne pas oublier de fournir les certificats matières."
                if nb:
                    msg+=u"\nATTENTION : Il manque "+str(nb)+u" certificats !"
            obj.is_certificat_conformite_msg = msg


    def _date_fin(self):
        now = datetime.date.today()                 # Date du jour
        date_fin = now + datetime.timedelta(days=1) # J+1
        return date_fin.strftime('%Y-%m-%d')        # Formatage


    name                   = fields.Char("N°", readonly=True)
    partner_id             = fields.Many2one('res.partner', 'Client', required=True)
    date_debut             = fields.Date("Date de début d'expédition")
    date_fin               = fields.Date("Date de fin d'expédition", required=True, default=lambda self: self._date_fin())
    livrable               = fields.Boolean("Livrable", default=False)
    transporteur_id        = fields.Many2one('res.partner', 'Transporteur')
    message                = fields.Text("Message")
    commentaire            = fields.Text("Commentaire")
    state                  = fields.Selection([
            ('creation', u'Création'),
            ('analyse', u'Analyse'),
            ('traite', u'Traité')
        ], u"État", readonly=True, index=True, default="creation")
    order_ids              = fields.One2many('sale.order', 'is_liste_servir_id', 'Commandes générées', readonly=False)
    line_ids               = fields.One2many('is.liste.servir.line', 'liste_servir_id', u"Lignes")
    uc_ids                 = fields.One2many('is.liste.servir.uc', 'liste_servir_id', u"UCs")
    um_ids                 = fields.One2many('is.liste.servir.um', 'liste_servir_id', u"UMs")
    is_source_location_id  = fields.Many2one('stock.location', 'Emplacement Source', default=_get_default_location) 
    poids_brut             = fields.Float('Poids brut', compute='_compute', readonly=True, store=False)
    poids_net              = fields.Float('Poids net' , compute='_compute', readonly=True, store=False)
    info_client            = fields.Text("Information client complèmentaire")
    galia_um_ids           = fields.One2many('is.galia.base.um', 'liste_servir_id', u"UMs scannées", readonly=True)
    uc_non_affectes        = fields.Integer(u"UCs non affectés")
    is_certificat_conformite_msg = fields.Text('Certificat de conformité', compute='_compute_is_certificat_conformite_msg', store=False, readonly=True)
    mixer                  = fields.Boolean('Mixer', default=False)
    saut_page_aqp          = fields.Boolean('Saut de page AQP', default=False)
    is_point_dechargement  = fields.Char('Point de déchargement')
    is_livree_aqp          = fields.Boolean('Pièce livrée en AQP')


    @api.onchange('mixer')
    def onchange_mixer(self):
        for obj in self:
            for line in obj.line_ids:
                line.mixer = self.mixer


    def tableaux(self):
        t=[True,False]
        return t


    @api.depends('line_ids')
    def _compute(self):
        for obj in self:
            poids_brut = 0
            poids_net  = 0
            for line in obj.line_ids:
                poids_brut = poids_brut + line.quantite * line.product_id.weight
                poids_net  = poids_net  + line.quantite * line.product_id.weight_net
            obj.poids_brut = poids_brut
            obj.poids_net  = poids_net



    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            partner = self.partner_id
            if partner.is_source_location_id:
                self.is_source_location_id = partner.is_source_location_id.id
            if partner.is_transporteur_id:
                self.transporteur_id = partner.is_transporteur_id.id


    def _message(self,partner_id,vals):
        if partner_id:
            message=""
            r=self.env['is.liste.servir.message'].search([['name', '=', partner_id]])
            for l in r:
                if l.message:
                    message=message+l.message+'\n'
            partner=self.env['res.partner'].browse(partner_id)
            if partner.is_certificat_matiere:
                message=message+'JOINDRE CERTIFICAT CONFORMITE \n'
            vals["message"]=message
        return vals


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "partner_id" in vals:
                vals=self._message(vals["partner_id"], vals)
            vals['name'] = self.env['ir.sequence'].next_by_code('is.liste.servir')
        res=super().create(vals_list)
        return res


    @api.onchange('line_ids','partner_id')
    def onchange_line_ids(self):
        self.uc_ids = False
        uc_ids=[]
        for line in self.line_ids:
            if line.mixer==False:
                vals={
                    "uc_id": line.uc_id.id,
                    "nb_uc": line.nb_uc,
                    "um_id": line.um_id.id,
                    "nb_um": line.nb_um,
                }
                uc_ids.append([0,0,vals])
        dict={}
        for line in self.line_ids:
            if line.mixer==True:
                key="%s-%s"%(line.um_id.id,line.uc_id.id)
                if key not in dict:
                    dict[key]={
                        "uc_id": line.uc_id.id,
                        "nb_uc": 0,
                        "um_id": line.um_id.id,
                        "nb_um": 0,
                    }
                dict[key]["nb_uc"]+=line.nb_uc
                dict[key]["nb_um"]+=line.nb_um
        for key in dict:
            vals={
                "uc_id": dict[key]["uc_id"],
                "nb_uc": dict[key]["nb_uc"],
                "um_id": dict[key]["um_id"],
                "nb_um": dict[key]["nb_um"],
            }
            uc_ids.append([0,0,vals])
        self.uc_ids=uc_ids


    @api.onchange('uc_ids','line_ids')
    def onchange_uc_ids(self):
        self.um_ids = False
        um_ids=[]
        for line in self.uc_ids:
            if line.mixer==False:
                vals={
                    "um_id": line.um_id.id,
                    "nb_um": ceil(line.nb_um),
                }
                um_ids.append([0,0,vals])
        dict={}
        for line in self.uc_ids:
            if line.mixer==True:
                key="%s"%(line.uc_id.id)
                if key not in dict:
                    dict[key]={
                        "um_id": line.um_id.id,
                        "nb_um": 0,
                    }
                dict[key]["nb_um"]+=line.nb_um
        for key in dict:
            vals={
                "um_id": dict[key]["um_id"],
                "nb_um": ceil(dict[key]["nb_um"]),
            }
            um_ids.append([0,0,vals])
        self.um_ids=um_ids


    def _get_sql(self,obj, aqp=None, point_dechargement=None):
        SQL="""
            SELECT  sol.order_id,
                    sol.product_id,
                    sol.is_client_order_ref,
                    sol.is_date_livraison,
                    sol.is_date_expedition,
                    sol.product_uom_qty,
                    sol.price_unit,
                    sol.is_justification,
                    sol.is_date_heure_livraison_au_plus_tot,
                    sol.is_numero_document,
                    sol.is_caldel_number,
                    sol.is_tg_number,
                    sol.is_num_ran,
                    sol.is_identifiant_transport,
                    sol.is_code_routage,
                    sol.is_point_destination
            FROM sale_order so INNER JOIN sale_order_line sol ON so.id=sol.order_id
            """
        if aqp is not None:
            SQL+="INNER JOIN product_product pp ON pp.id=sol.product_id INNER JOIN product_template pt ON pp.product_tmpl_id=pt.id "
        SQL+="""
            WHERE so.partner_id="""+str(obj.partner_id.id)+"""
                  AND so.state='draft'
                  AND sol.is_date_expedition<='"""+str(obj.date_fin)+"""'
                  AND sol.product_id>0
                  AND sol.is_type_commande='ferme'
                  AND so.is_type_commande!='ls'
        """
        if aqp is not None:
            SQL+="and pt.is_livree_aqp=" + str(aqp).upper() + " "
        if point_dechargement is not None:
            SQL+="and so.is_point_dechargement='" + point_dechargement + "' "
        if obj.date_debut:
            SQL=SQL+" and sol.is_date_expedition>='"+str(obj.date_debut)+"' "
        if obj.partner_id.is_caracteristique_bl=='cde_client':
            OrderBy="sol.is_client_order_ref"
        else:
            OrderBy="sol.product_id"
        SQL=SQL+"order by "+OrderBy
        return SQL


    def action_importer_commandes(self, aqp=None, point_dechargement=None):
        cr = self._cr
        for obj in self:
            #** Connexion à Dynacase *******************************************
            if obj.partner_id.is_certificat_matiere:
                uid=self._uid
                user=self.env['res.users'].browse(uid)
                password=user.company_id.is_dynacase_pwd
                cnx=False
                try:
                    cnx = psycopg2.connect("host='dynacase' port=5432 dbname='freedom' user='dynacaseowner' password='"+password+"'")
                    cursor = cnx.cursor()
                except:
                    msg="Impossible de se connecter à Dynacase"
                    _logger.info(msg)
                    cursor=False
            #*******************************************************************

            for row in obj.line_ids:
                row.unlink()
            SQL=self._get_sql(obj, aqp, point_dechargement)
            cr.execute(SQL)
            result = cr.dictfetchall()
            line_obj = self.env['is.liste.servir.line']
            sequence=0
            for row in result:
                sequence=sequence+1
                product_id=row['product_id']
                product=self.env['product.product'].browse(product_id)

                #** Recherche du certificat matière ****************************
                certificat_matiere=False
                if obj.partner_id.is_certificat_matiere and cursor:
                    SQL="""
                        select id
                        from doc69106
                        where doctype='F' and locked='0' and cmc_codepg='"""+product.is_code+"""' limit 1
                    """
                    _logger.info(SQL)
                    cursor.execute(SQL)
                    result2 = cursor.fetchall()
                    for row2 in result2:
                        certificat_matiere=row2[0]
                        msg="certificat_matiere=%s"%row2[0]
                        _logger.info(msg)
                #***************************************************************

                stock01 = product.get_stock('f', '01')
                lots01 = product.get_stock_lot('01')
                stocka  = product.get_stock('f')
                stockq  = product.get_stock('t')
                qt=row['product_uom_qty']






                livrable=False
                if qt<=stocka:
                    livrable=True


                test=True
                if obj.livrable==True and livrable==False:
                    test=False
#
#                point_dechargement = False
#                if obj.partner_id.is_traitement_edi:
#                    filtre = [
#                        ('partner_id'            , '=', obj.partner_id.id),
#                        ('is_article_commande_id', '=', product_id),
#                        ('is_type_commande'      , '=', 'ouverte'),
#                        ('state'                 , '=', 'draft'),
#                    ]
#                    orders = self.env['sale.order'].search(filtre)
#                    for order in orders:
#                        point_dechargement = order.is_point_dechargement
                if test:
                    vals={
                        'liste_servir_id'   : obj.id,
                        'sequence'          : sequence,
                        'order_id'          : row['order_id'],
                        'product_id'        : row['product_id'],
                        'client_order_ref'  : row['is_client_order_ref'],
                        'date_livraison'    : row['is_date_livraison'],
                        'date_expedition'   : row['is_date_expedition'],
                        'prix'              : row['price_unit'],
                        'justification'     : row['is_justification'],
                        'quantite'          : qt,
                        'livrable'          : livrable,
                        'stock01'           : stock01,
                        'lots01'            : lots01,
                        'stocka'            : stocka,
                        'stockq'            : stockq,
                        'certificat_matiere': certificat_matiere,
                        'point_dechargement': point_dechargement,

                        'is_date_heure_livraison_au_plus_tot': row['is_date_heure_livraison_au_plus_tot'],
                        'is_numero_document'                 : row['is_numero_document'],
                        'is_caldel_number'                   : row['is_caldel_number'],
                        'is_tg_number'                       : row['is_tg_number'],
                        'is_num_ran'                         : row['is_num_ran'],
                        'is_identifiant_transport'           : row['is_identifiant_transport'],
                        'is_code_routage'                    : row['is_code_routage'],
                        'is_point_destination'               : row['is_point_destination'],
                    }
                    line_obj.create(vals)
            obj.onchange_line_ids()
            obj.onchange_uc_ids()
            obj.state="analyse"


    def action_generer_bl(self):
        cr = self._cr
        for obj in self:
            obj.order_ids.unlink()
            SQL=self._get_sql(obj)
            cr.execute(SQL)
            result = cr.fetchall()
            Test=True
            for line in obj.line_ids:
                key1=str(line.order_id.id)+"-"+str(line.product_id.id)
                anomalie="Commande non trouvée"
                for order in result:
                    key2=str(order[0])+"-"+str(order[1])
                    if key1==key2:
                        anomalie=""
                line.anomalie=anomalie
                if anomalie!="":
                    Test=False
            #** Accèder à la liste des commandes générées **********************
            if Test:
                self.generer_bl(obj)
                obj.state="traite"
                ids=[]
                for order in obj.order_ids:
                    ids.append(order.id)
                res= {
                    'domain': "[('id','in',[" + ','.join(map(str, list(ids))) + "])]",
                    'name': 'Commandes',
                    'view_mode': 'tree,form',
                    'res_model': 'sale.order',
                    'type': 'ir.actions.act_window',
                }
                return res
            #*******************************************************************


    def generer_bl(self,obj):
        cr = self._cr
        uid = self._uid
        ids = self._ids
        context = self._context
        order_obj = self.env['sale.order']
        vals={}
        lines = []
        mem=''
        point_dechargement = False
        for line in obj.line_ids:
            key=''
            if obj.partner_id.is_caracteristique_bl=='cde_odoo':
                key=''
            if obj.partner_id.is_caracteristique_bl=='cde_client':
                key=str(line.client_order_ref)
            if obj.partner_id.is_caracteristique_bl=='ref_article':
                key=str(line.product_id.id)

            key=key+(line.point_dechargement or '')

            if mem!=key:
                if vals:
                    new_id = order_obj.create(vals)
                    new_id.pg_onchange_partner_id()
                    vals={}
                    lines = []
                mem=key
            quotation_line={
                "product_id"         : line.product_id.id,
                "sequence"           : 1,
                "product_uom_qty"    : line.quantite,
                "price_unit"         : line.prix,
                "is_justification"   : line.justification,
                "product_uom"        : line.product_id.uom_id.id,
                "is_client_order_ref": line.client_order_ref,
                "is_date_livraison"  : line.date_livraison,
                "is_date_expedition" : line.date_expedition,
                "is_type_commande"   : 'ferme',
                "is_date_heure_livraison_au_plus_tot": line.is_date_heure_livraison_au_plus_tot,
                "is_numero_document"                 : line.is_numero_document,
                "is_caldel_number"                   : line.is_caldel_number,
                "is_tg_number"                       : line.is_tg_number,
                "is_num_ran"                         : line.is_num_ran,
                "is_identifiant_transport"           : line.is_identifiant_transport,
                "is_code_routage"                    : line.is_code_routage,
                "is_point_destination"               : line.is_point_destination,
            }
            point_dechargement = line.is_point_destination
            lines.append([0,False,quotation_line]) 
            values = {
                'partner_id': obj.partner_id.id,
                'is_source_location_id': obj.is_source_location_id.id,
                'client_order_ref'     : obj.name,
                'is_liste_servir_id'   : obj.id,
                'origin'               : obj.name,
                'order_line'           : lines,
                'picking_policy'       : 'direct',
                #'is_transporteur_id'   : obj.transporteur_id.id,
                'is_type_commande'     : 'ls',
                'is_info_client'       : obj.info_client,
            }
            vals.update(values)
        if vals:
            new_id = order_obj.create(vals)
            new_id.pg_onchange_partner_id()
            new_id.is_transporteur_id=obj.transporteur_id.id
            if point_dechargement:
                new_id.is_point_dechargement = line.point_dechargement



        #** Supprimer les lignes des commandes d'origine ***********************
        SQL="""
            select sol.order_id, sol.product_id, sol.product_uom_qty, sol.id
            from sale_order so inner join sale_order_line sol on so.id=sol.order_id
            where so.partner_id="""+str(obj.partner_id.id)+""" and so.state='draft' 
                  and sol.is_date_expedition<='"""+str(obj.date_fin)+"""' and sol.product_id>0
        """
        if obj.date_debut:
            SQL=SQL+" and sol.is_date_expedition>='"+str(obj.date_debut)+"' "

        SQL=SQL+" order by sol.is_date_expedition, sol.is_date_livraison"


        cr.execute(SQL)
        result = cr.fetchall()
        for line in obj.line_ids:
            key1=str(line.order_id.id)+"-"+str(line.product_id.id)
            quantite=line.quantite
            for order in result:
                key2=str(order[0])+"-"+str(order[1])
                if key1==key2 and quantite>=0:
                    order_line=self.env['sale.order.line'].search([('id', '=', order[3])])
                    qty=order_line.product_uom_qty
                    if quantite>=qty:
                        order=order_line.order_id
                        order_line.unlink()
                        #** Supprimer la commande si celle-ci est vide *********
                        if len(order.order_line)==0 and order.is_type_commande=='standard':
                            order.unlink()
                        #*******************************************************
                    else:
                        reste=qty-quantite
                        order_line.product_uom_qty = reste
                    quantite=quantite-qty
        #***********************************************************************


    def get_is_code_rowspan(self,product_id):
        cr = self._cr
        for obj in self:
            SQL="""
                select count(*)
                from is_galia_base_uc uc inner join is_galia_base_um um on uc.um_id=um.id
                                         inner join is_liste_servir ls on um.liste_servir_id=ls.id
                                         inner join product_product pp on uc.product_id=pp.id 
                where 
                    ls.id="""+str(obj.id)+""" and 
                    uc.product_id="""+str(product_id)+""" 
            """
            cr.execute(SQL)
            result = cr.fetchall()
            nb=0
            for row in result:
                nb=row[0]
            return nb


    def get_um_rowspan(self,product_id,um_id):
        cr = self._cr
        for obj in self:
            SQL="""
                select count(*)
                from is_galia_base_uc uc inner join is_galia_base_um um on uc.um_id=um.id
                                         inner join is_liste_servir ls on um.liste_servir_id=ls.id
                                         inner join product_product pp on uc.product_id=pp.id 
                where 
                    ls.id="""+str(obj.id)+""" and 
                    uc.product_id="""+str(product_id)+""" and
                    um.id="""+str(um_id)+""" 
            """
            cr.execute(SQL)
            result = cr.fetchall()
            nb=0
            for row in result:
                nb=row[0]
            return nb


    def get_etiquettes(self):
        cr = self._cr
        res=[]
        for obj in self:
            SQL="""
                select 

                    pt.is_code,
                    um.name,
                    uc.num_eti,
                    uc.qt_pieces,
                    pp.id,
                    um.id
                from is_galia_base_uc uc inner join is_galia_base_um um on uc.um_id=um.id
                                         inner join is_liste_servir ls on um.liste_servir_id=ls.id
                                         inner join product_product pp on uc.product_id=pp.id 
                                         inner join product_template pt on pp.product_tmpl_id=pt.id
                where ls.id="""+str(obj.id)+"""
                order by pt.is_code, um.name, uc.num_eti
            """
            cr.execute(SQL)
            result = cr.fetchall()
            ct_code = 0
            ct_um   = 0
            is_code_rowspan = 0
            um_rowspan = 0
            mem_code = ''
            mem_um   = ''
            for row in result:
                is_code_rowspan=0
                um_rowspan=0
                if row[0]!=mem_code:
                    mem_code=row[0]
                    is_code_rowspan=self.get_is_code_rowspan(row[4])
                    ct_code=0

                is_code_um = (row[0]+row[1])
                if is_code_um!=mem_um:
                    mem_um=is_code_um
                    um_rowspan=self.get_um_rowspan(row[4],row[5])
                    ct_um=0

                ct_code+=1
                ct_um+=1

                vals={
                    'is_code'  : row[0],
                    'um'       : row[1],
                    'uc'       : row[2],
                    'qt_pieces': row[3],
                    'is_code_rowspan': is_code_rowspan,
                    'um_rowspan': um_rowspan,
                }
                res.append(vals)
        return res


    def affecter_uc_aux_lignes_ls_action(self):
        for obj in self:
            ucs = self.env['is.galia.base.uc'].search([('liste_servir_id','=',obj.id)], order='qt_pieces desc')
            for uc in ucs:
                uc.ls_line_id=False
            for line in obj.line_ids:
                for um in obj.galia_um_ids:
                    if line.product_id==um.product_id:
                        ucs = self.env['is.galia.base.uc'].search([('um_id','=',um.id)], order='qt_pieces desc')
                        for uc in ucs:
                            if not uc.ls_line_id:
                                lines2 = self.env['is.galia.base.uc'].search([('ls_line_id','=',line.id)], order='qt_pieces desc')
                                qt = uc.qt_pieces
                                for l in lines2:
                                    qt+=l.qt_pieces
                                if qt<=line.quantite:
                                    uc.ls_line_id=line.id
            lines = self.env['is.galia.base.uc'].search([('liste_servir_id','=',obj.id),('ls_line_id','=',False)])
            nb=len(lines)
            obj.uc_non_affectes = nb


class is_liste_servir_line(models.Model):
    _name='is.liste.servir.line'
    _description="Lignes liste à servir"
    _order='sequence,id'

    def name_get(self):
        res=[]
        for obj in self:
            t=[]
            t.append(obj.product_id.is_code)
            if obj.client_order_ref:
                t.append(obj.client_order_ref)
            if obj.point_dechargement:
                t.append(obj.point_dechargement)
            name=u", ".join(t)
            res.append((obj.id, name))
        return res


    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if name:
            ids = self.search(cr, user, ['|','|',('product_id.is_code','ilike', name),('client_order_ref','ilike', name),('point_dechargement','ilike', name)], limit=limit, context=context)
        else:
            ids = self.search(cr, user, args, limit=limit, context=context)
        result = self.name_get(cr, user, ids, context=context)
        return result


    @api.depends('product_id','quantite')
    def _compute(self):
        cr = self._cr
        for obj in self:
            if obj.product_id:
                mold_dossierf=False
                if obj.product_id.is_dossierf_id:
                    mold_dossierf=obj.product_id.is_dossierf_id.name
                if obj.product_id.is_mold_id:
                    mold_dossierf=obj.product_id.is_mold_id.name
                obj.mold_dossierf=mold_dossierf

                SQL="""
                    select pa.ul,pa.qty,pa.ul_container,pa.rows*pa.ul_qty
                    from product_product pp left outer join product_packaging pa on pp.id=pa.product_id 
                    where pp.id="""+str(obj.product_id.id)+"""
                    limit 1
                """
                cr.execute(SQL)
                result = cr.fetchall()
                for row in result:
                    if row[0]:
                        qt=obj.quantite
                        stock01_uc = obj.stock01
                        stocka_uc  = obj.stocka
                        stockq_uc  = obj.stockq
                        uc=row[1]
                        if uc!=0:
                            nb_uc=qt/uc
                            stock01_uc = stock01_uc/uc
                            stocka_uc  = stocka_uc/uc
                            stockq_uc  = stockq_uc/uc
                        nb_um=row[3]
                        if row[1]!=0 and row[3]!=0:
                            nb_um=qt/(row[1]*row[3])
                        obj.uc_id     = row[0]
                        obj.nb_uc     = nb_uc
                        obj.um_id     = row[2]
                        obj.nb_um     = nb_um
                        obj.stock01_uc = stock01_uc
                        obj.stocka_uc  = stocka_uc
                        obj.stockq_uc  = stockq_uc

    def _compute_is_certificat_conformite_vsb(self):
        for obj in self:
            vsb = False
            if obj.liste_servir_id.partner_id.is_certificat_matiere:
                certificat = self.env['is.certificat.conformite'].GetCertificat(obj.liste_servir_id.partner_id, obj.product_id.id)
                if certificat:
                    vsb = 1
                else:
                    vsb = 2
            obj.is_certificat_conformite_vsb = vsb


    liste_servir_id    = fields.Many2one('is.liste.servir', 'Liste à servir', required=True, ondelete='cascade')
    sequence           = fields.Integer('Sequence')
    product_id         = fields.Many2one('product.product', 'Article', required=True, readonly=True)

    mold_id            = fields.Many2one('is.mold', 'Moule'          , related='product_id.is_mold_id', readonly=True)
    dossierf_id        = fields.Many2one('is.dossierf', 'Dossier F'  , related='product_id.is_dossierf_id', readonly=True)
    mold_dossierf      = fields.Char('Moule / Dossier F', compute='_compute', readonly=True, store=True)

    stock01            = fields.Float('Stock 01 US' , help="Stock 01 en US")
    lots01             = fields.Text('Lots 01 US')
    stocka             = fields.Float('Stock A US'  , help="Stock A en US")
    stockq             = fields.Float('Stock Q US'  , help="Stock Q en US")

    stock01_uc         = fields.Float('Stock 01 UC' , help="Stock 01 en UC", compute='_compute', readonly=True, store=True)
    stocka_uc          = fields.Float('Stock A UC'  , help="Stock A en UC" , compute='_compute', readonly=True, store=True)
    stockq_uc          = fields.Float('Stock Q UC'  , help="Stock Q en UC" , compute='_compute', readonly=True, store=True)

    date_livraison     = fields.Date('Date de livraison', readonly=True)
    quantite           = fields.Float('Qt Cde US')
    livrable           = fields.Boolean("Livrable")
    date_expedition    = fields.Date("Date d'expédition"   , readonly=True)
    prix               = fields.Float("Prix", digits=(14,4), readonly=True)
    justification      = fields.Char('Justification')
    uc_id              = fields.Many2one('is.product.ul', 'UC'      , compute='_compute', readonly=True, store=True)
    nb_uc              = fields.Float('Qt Cde UC'                    , compute='_compute', readonly=True, store=True)
    um_id              = fields.Many2one('is.product.ul', 'UM'      , compute='_compute', readonly=True, store=True)
    nb_um              = fields.Float('Qt Cde UM'                    , compute='_compute', readonly=True, store=True)
    mixer              = fields.Boolean('Mixer', help="L'UM de cet article peut-être mixée avec un autre", default=False)
    order_id           = fields.Many2one('sale.order', 'Commande', required=False, readonly=True)
    client_order_ref   = fields.Char('Cde Client', readonly=True)
    point_dechargement = fields.Char('Point de déchargement', readonly=True)
    certificat_matiere = fields.Char('Certificat matiere', readonly=True)
    anomalie           = fields.Char('Commentaire')
    is_certificat_conformite_vsb = fields.Integer('Certificat de conformité', compute='_compute_is_certificat_conformite_vsb', store=False, readonly=True)

    is_date_heure_livraison_au_plus_tot = fields.Char('Liv au plus tôt'  , help="Champ 'DateHeurelivraisonAuPlusTot' pour EDI Weidplas")
    is_numero_document                  = fields.Char('N°Document'       , help="Champ 'NumeroDocument' pour EDI Weidplas => N°UM de PSA")
    is_caldel_number                    = fields.Char('Caldel Number'    , help="Champ 'CaldelNumber' pour EDI Weidplas")
    is_tg_number                        = fields.Char('TG Number'        , help="Champ 'TGNumber' pour EDI Weidplas => N°UM de Weidplas")
    is_num_ran                          = fields.Char('NumRAN'           , help="Champ 'NumRAN' pour EDI PO => N°UM de PO")
    is_code_routage                     = fields.Char('Code routage'     , help="Champ 'CodeRoutage' pour EDI Weidplas")
    is_point_destination                = fields.Char('Point destination', help="Champ 'CodeIdentificationPointDestination' pour EDI Weidplas")
    is_identifiant_transport            = fields.Char("N° identifiant transport", help="Champ 'IdTransport' pour EDI Weidplas/PO à remettre sur le BL")


    def pas_de_certifcat_action(self):
        for obj in self:
            print(obj)


    def imprimer_certificat_action(self):
        view_id = self.env.ref('is_plastigray16.is_certificat_conformite_form_view').id
        for obj in self:
            certificat = self.env['is.certificat.conformite'].GetCertificat(obj.liste_servir_id.partner_id, obj.product_id.id)
            if certificat:
                return {
                    'name': "Certificat de conformité",
                    'view_mode': 'form',
                    'view_id': view_id,
                    'res_model': 'is.certificat.conformite',
                    'type': 'ir.actions.act_window',
                    'res_id': certificat.id,
                    'domain': '[]',
                }


    def action_acceder_certificat(self):
        context=self._context
        if 'certificat_matiere' in context:
            docid=context['certificat_matiere']
            return {
                'name': "Certificat",
                'url': "https://dynacase-rp/?sole=Y&app=FDL&action=FDL_CARD&id="+docid,
                'type': 'ir.actions.act_url',
            }


    def action_acceder_article(self):
        view_id = self.env.ref('is_plastigray16.is_product_template_only_form_view').id
        for obj in self:
            return {
                'name': "Article",
                'view_mode': 'form',
                'view_id': view_id,
                'res_model': 'product.template',
                'type': 'ir.actions.act_window',
                'res_id': obj.product_id.product_tmpl_id.id,
                'domain': '[]',
            }



class is_liste_servir_message(models.Model):
    _name='is.liste.servir.message'
    _description="Message liste à servir"
    _order='name'
    _sql_constraints = [('name_uniq','UNIQUE(name)', 'Ce client existe déjà')] 

    name    = fields.Many2one('res.partner', 'Client', required=True)
    message = fields.Text('Message')


class is_liste_servir_uc(models.Model):
    _name='is.liste.servir.uc'
    _description="UC Liste à servir"
    _order='uc_id'

    liste_servir_id = fields.Many2one('is.liste.servir', 'Liste à servir', required=True, ondelete='cascade')
    uc_id           = fields.Many2one('is.product.ul', 'UC')
    nb_uc           = fields.Float('Nb UC')
    um_id           = fields.Many2one('is.product.ul', 'UM')
    nb_um           = fields.Float('Nb UM')
    mixer           = fields.Boolean('Mixer', help="L'UM peut-être mixée avec une autre", default=False)

 
class is_liste_servir_um(models.Model):
    _name='is.liste.servir.um'
    _description="UM Liste à servir"
    _order='um_id,nb_um desc'

    liste_servir_id = fields.Many2one('is.liste.servir', 'Liste à servir', required=True, ondelete='cascade')
    um_id           = fields.Many2one('is.product.ul', 'UM')
    nb_um           = fields.Float('Nb UM')





