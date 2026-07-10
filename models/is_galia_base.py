# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools # type: ignore
from odoo.exceptions import AccessError, ValidationError, UserError  # type: ignore
from subprocess import PIPE, Popen
from xmlrpc import client as xmlrpclib
from datetime import datetime
import time
import pytz
import os
import psycopg2         # type: ignore
import psycopg2.extras  # type: ignore
import logging
_logger = logging.getLogger(__name__)

_MIXTE=[
    ('oui', 'Oui'),
    ('non', 'Non'),
]

class is_galia_base(models.Model):
    _name='is.galia.base'
    _description="Etiquettes Galia"
    _order='num_eti desc'
    _rec_name='num_eti'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _sql_constraints = [('name_uniq','UNIQUE(num_eti)', 'Cette étiquette existe déjà')] 

    num_eti       = fields.Integer("N°Étiquette", index=True, tracking=True)
    soc           = fields.Integer("Société"    , index=True, tracking=True)
    type_eti      = fields.Char("Type étiquette", index=True, tracking=True)
    num_of        = fields.Char("N°OF"          , index=True, tracking=True)
    num_carton    = fields.Integer("N°Carton"   , index=True, tracking=True)
    qt_pieces     = fields.Integer("Qt Pièces", tracking=True)
    date_creation = fields.Datetime("Date de création", index=True, tracking=True)
    login         = fields.Char("Login", tracking=True)
    active        = fields.Boolean("Actif", default=True, tracking=True)

    point_dechargement  = fields.Char('Point de déchargement', tracking=True, help="Champ 'CodeIdentificationPointDechargement' pour EDI Weidplas")
    code_routage        = fields.Char('Code routage'         , tracking=True, help="Champ 'CodeRoutage' pour EDI Weidplas")
    point_destination   = fields.Char('Point destination'    , tracking=True, help="Champ 'CodeIdentificationPointDestination' pour EDI Weidplas")


    def str2int(self,val):
        try:
            val=int(val)
        except:
            val=0
        return val


    def get_info_commande(self,cur=False,num_eti=False,code_pg=False):
        point_dechargement = code_routage = point_destination = test =  False
        if cur and num_eti:

            # TODO : Désactivé le 18/10/2025, car la commande n'est pas encore créée au moment de la ré-impression de l'UC
            # #** Recherche si l'UC du site est associée à une liste à servir ***
            # #** pour retrouver la ligne de commande et ses informations      **
            # SQL="""
            #     SELECT so.name,so.is_point_dechargement, sol.is_code_routage, sol.is_point_destination
            #     FROM is_galia_base_uc uc join stock_move move     on uc.stock_move_id=move.id
            #                              join sale_order_line sol on move.sale_line_id=sol.id
            #                              join sale_order so       on sol.order_id=so.id
            #     WHERE uc.num_eti=%s and sol.is_type_commande='ferme'
            #     order by uc.id desc, sol.id desc limit 1
            # """%num_eti
            # cur.execute(SQL)
            # rows = cur.fetchall()
            # for row in rows:
            #     test = True
            #     point_dechargement = row['is_point_dechargement']
            #     code_routage       = row['is_code_routage']
            #     point_destination  = row['is_point_destination']
            # #******************************************************************


            #** Recherche si l'UC du site est associée à une liste à servir ***
            #** pour retrouver la ligne de la liste et ses informations      **
            SQL="""
                SELECT ils.name, ils.is_point_dechargement, ilsl.is_code_routage, ilsl.is_point_destination
                FROM is_galia_base_uc uc join is_galia_base_um um on uc.um_id=um.id
                                        join is_liste_servir ils on um.liste_servir_id=ils.id
                                        join is_liste_servir_line ilsl on ilsl.liste_servir_id=ils.id
                WHERE uc.num_eti=%s 
                    and uc.active=true and um.active=true
                    and ilsl.product_id=uc.product_id
                limit 1
            """%num_eti
            cur.execute(SQL)
            rows = cur.fetchall()
            for row in rows:
                test = True
                name_ls            = row['name']
                point_dechargement = row['is_point_dechargement']
                code_routage       = row['is_code_routage']
                point_destination  = row['is_point_destination']
                _logger.info("get_info_commande : LS=%s :  point_dechargement=%s : code_routage=%s : point_destination=%s"%(name_ls, point_dechargement, code_routage, point_destination))
            #******************************************************************

            #** Recherche la dernière ligne de commande pour cet article ******
            #** si l'UC n'est pas encore associée à une commande             **
            if test==False and code_pg:
                SQL="""
                    SELECT so.name,so.is_point_dechargement, sol.is_code_routage, sol.is_point_destination
                    FROM sale_order_line sol inner join sale_order       so on sol.order_id=so.id
                                                   join product_product  pp on sol.product_id=pp.id
                                                   join product_template pt on pp.product_tmpl_id=pt.id
                    WHERE so.is_point_dechargement is not null 
                        and so.is_type_commande in ('ouverte', 'ls', 'standard') 
                        and pt.is_code='%s'
                        and sol.is_type_commande='ferme'
                    order by sol.id desc
                    limit 1
                """%code_pg
                cur.execute(SQL)
                rows=cur.fetchall()
                name_cde =""
                for row in rows:
                    name_cde           = row['name']
                    point_dechargement = row['is_point_dechargement']
                    code_routage       = row['is_code_routage']
                    point_destination  = row['is_point_destination']
                _logger.info("get_info_commande : Commande=%s :  point_dechargement=%s : code_routage=%s : point_destination=%s"%(name_cde, point_dechargement, code_routage, point_destination))
            #******************************************************************

        res={
            'point_dechargement': point_dechargement,
            'code_routage'      : code_routage,
            'point_destination' : point_destination,

        }
        return res
        

    def creer_etiquette(self, vals={}): #, vals={}):
        cr=self._cr
        if vals==[]:
            vals={}
        Action       = vals.get('ACTION')
        Soc          = vals.get('Soc')
        Etiquette    = vals.get('Etiquette')
        Imprimante   = vals.get('Imprimante')
        zzCode       = vals.get('zzCode')
        zzDebut      = self.str2int(vals.get('zzDebut'))
        zzFin        = self.str2int(vals.get('zzFin'))
        zzNbPieces   = self.str2int(vals.get('zzNbPieces'))
        zzMDP1       = vals.get('zzMDP1')
        zzMDP2       = vals.get('zzMDP2')
        zzValidation = vals.get('zzValidation')
        zzAction     = vals.get('zzAction')
        user_name    = vals.get('user_name')
        Msg=""
        MsgOK=""
        CodePG=""
        Etiq=""
        if (zzValidation=="OK"):
            SQL=""
            # ** Requetes en fonction du type d'étiquette demandé *************
            if (Etiquette=="OF" or Etiquette=="CONTROLEES"):
                SQL="""SELECT 
                        pt.id                   as product_id,
                        pt.is_code              as code_pg, 
                        pt.name->>'fr_FR'       as designation, 
                        pt.is_ref_client        as ref_client,
                        pt.is_ref_plan          as ref_plan,
                        pt.is_ind_plan          as ind_plan,
                        pt.weight               as poids_brut,
                        pt.weight_net           as poids_net,
                        coalesce(im.name, id.name) moule,
                        ic.name                 as categorie,
                        ig.name                 as gestionnaire,
                        pt.is_livree_aqp        as aqp,
                        pt.is_droite_grauche    as droite_gauche,
                        pt.is_soumise_regl      as logo_secu,
                        ite.name                  as type_etiquette,
                        ite.format_etiquette      as format_etiquette,
                        ite.adresse               as adresse,
                        ite.code_fournisseur      as code_fournisseur,
                        ite.is_cde_rtge_fond_noir as is_cde_rtge_fond_noir,
                        mp.name                   as num_of,
                        pp.id                     as product_product_id,
                        pt.is_code_fabrication    as is_code_fabrication
                    FROM mrp_production mp inner join product_product                  pp on mp.product_id=pp.id
                                            inner join product_template                 pt on pp.product_tmpl_id=pt.id
                                            inner join mrp_workorder                  mpwl on mpwl.production_id=mp.id
                                            inner join mrp_workcenter                   mw on mpwl.workcenter_id=mw.id
                                            inner join resource_resource                rr on mw.resource_id = rr.id
                                            inner join is_category                      ic on pt.is_category_id = ic.id
                                            inner join is_gestionnaire                  ig on pt.is_gestionnaire_id = ig.id
                                            left outer join is_type_etiquette          ite on pt.is_type_etiquette_id=ite.id
                                            left outer join is_mold                     im on pt.is_mold_id=im.id
                                            left outer join is_dossierf                 id on pt.is_dossierf_id=id.id

                    WHERE rr.resource_type='material' and mp.state not in ('cancel') 
                            and mp.name='%s'
                """%zzCode
            if (Etiquette=="CodePG"):
                SQL="""SELECT 
                        pt.id                   as product_id,
                        pt.is_code              as code_pg, 
                        pt.name->>'fr_FR'       as designation, 
                        pt.is_ref_client        as ref_client,
                        pt.is_ref_plan          as ref_plan,
                        pt.is_ind_plan          as ind_plan,
                        pt.weight               as poids_brut,
                        pt.weight_net           as poids_net,
                        pt.is_mold_dossierf     as moule, 
                        ic.name                 as categorie,
                        ig.name                 as gestionnaire,
                        pt.is_livree_aqp        as aqp,
                        pt.is_droite_grauche    as droite_gauche,
                        pt.is_soumise_regl      as logo_secu,
                        ite.name                  as type_etiquette,
                        ite.format_etiquette      as format_etiquette,
                        ite.adresse               as adresse,
                        ite.code_fournisseur      as code_fournisseur,
                        ite.is_cde_rtge_fond_noir as is_cde_rtge_fond_noir,
                        ''                      as num_of,
                        pp.id                   as product_product_id,
                        pt.is_code_fabrication  as is_code_fabrication
                    FROM product_product pp inner join product_template                 pt on pp.product_tmpl_id=pt.id
                                            inner join is_category                      ic on pt.is_category_id = ic.id
                                            inner join is_gestionnaire                  ig on pt.is_gestionnaire_id = ig.id
                                            left outer join is_type_etiquette          ite on pt.is_type_etiquette_id=ite.id
                    WHERE pt.is_code='%s'
                """%zzCode
            if (Etiquette=="Commande"):
                r = zzCode.split('/')
                NumCde = r[0]
                offset=0
                if len(r)>1:
                    offset = self.str2int(r[1])-1
                if (offset<0):
                    offset=0
                SQL="""SELECT 
                        pt.id                     as product_id,
                        pt.is_code                as code_pg, 
                        pt.name->>'fr_FR'         as designation, 
                        pt.is_ref_client          as ref_client,
                        pt.is_ref_plan            as ref_plan,
                        pt.is_ind_plan            as ind_plan,
                        pt.weight                 as poids_brut,
                        pt.weight_net             as poids_net,
                        im.name                   as moule, 
                        ic.name                   as categorie,
                        ig.name                   as gestionnaire,
                        pt.is_livree_aqp          as aqp,
                        pt.is_droite_grauche      as droite_gauche,
                        pt.is_soumise_regl        as logo_secu,
                        ite.name                  as type_etiquette,
                        ite.format_etiquette      as format_etiquette,
                        ite.adresse               as adresse,
                        ite.code_fournisseur      as code_fournisseur,
                        ite.is_cde_rtge_fond_noir as is_cde_rtge_fond_noir,
                        po.name                   as num_of,
                        pp.id                     as product_product_id,
                        pt.is_code_fabrication    as is_code_fabrication
                    FROM purchase_order po inner join purchase_order_line             pol on po.id=pol.order_id
                                            inner join product_product                  pp on pol.product_id=pp.id 
                                            inner join product_template                 pt on pp.product_tmpl_id=pt.id
                                            left outer join is_mold                     im on pt.is_mold_id=im.id
                                            inner join is_category                      ic on pt.is_category_id = ic.id
                                            inner join is_gestionnaire                  ig on pt.is_gestionnaire_id = ig.id
                                            left outer join is_type_etiquette          ite on pt.is_type_etiquette_id=ite.id
                    WHERE po.name='%s' 
                    ORDER BY pol.id limit 1 offset %s
                """%(NumCde,offset)
            company = self.env.user.company_id
            dbname='odoo16-%s'%Soc
            if company.is_postgres_host=='localhost':
                dbname='pg-odoo16-%s'%Soc
            try:
                cnx = psycopg2.connect("dbname='"+dbname+"' user='"+company.is_postgres_user+"' host='"+company.is_postgres_host+"' password='"+company.is_postgres_pwd+"'")
            except:
                cnx=False
                Msg+="La connexion à la base %s a échouée !\n"%dbname
            if Msg=="":
                cur = cnx.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute(SQL)
                rows = cur.fetchall()
                NbLig = len(rows)
                if NbLig==0:
                    Msg+="%s non trouvée!\n"%Etiquette
                else:
                    row=rows[0]



                



                    if (row['aqp']==True):
                        AQP='AQP'
                    else:
                        AQP=''
                    CodePG          = row['code_pg'] or ''
                    Designation     = row['designation'] or ''
                    RefClient       = row['ref_client'] or ''
                    RefPlan         = row['ref_plan'] or ''
                    IndPlan         = row['ind_plan'] or ''
                    Moule           = row['moule'] or ''
                    Cat             = self.str2int(row['categorie'])
                    Gest            = row['gestionnaire'] or ''
                    GaucheDroite    = row['droite_gauche'] or ''
                    LogoSecu        = row['logo_secu'] or ''
                    NumLot          = row['num_of'] or ''
                    PoidsBrut       = row['poids_brut'] or 0
                    PoidsNet        = row['poids_net'] or 0
                    CodeFabrication = row['is_code_fabrication'] or ''

                    if CodeFabrication!='':
                        Designation="%s-%s"%(CodeFabrication, Designation)                    

                    #** Recherche de la quantité par UC ***********************
                    product_id=row['product_id']
                    SQL="select qty from product_packaging where product_id=%s limit 1"%row['product_product_id']
                    cur.execute(SQL)
                    rows2 = cur.fetchall()
                    Quantite=1
                    for row2 in rows2:
                        Quantite=row2['qty']
                    #**********************************************************

                    #Recherche Informations sur le type de l'étiquette ********
                    TypeEti= row['type_etiquette']
                    if TypeEti=='':
                        Msg+="Type etiquette non trouvee!\n"
                    TypeEti               = row['type_etiquette'] or ''
                    FormatEti             = row['format_etiquette'] or ''
                    Adresse               = row['adresse'] or ''
                    CodeFournisseur       = row['code_fournisseur'] or ''
                    is_cde_rtge_fond_noir = row['is_cde_rtge_fond_noir'] or False
                    #**********************************************************

                    # Recherche Informations sur le client ********************
                    SQL="""
                        select rp.is_cofor, rp.name as nom_client, rp.is_code as code_client
                        from is_product_client ipc inner join res_partner rp on ipc.client_id=rp.id  
                        where ipc.product_id=%s and ipc.client_defaut='t' limit 1
                    """%product_id
                    cur.execute(SQL)
                    rows2 = cur.fetchall()
                    Fournisseur=''
                    CodeClient=''
                    NomClient=''
                    for row2 in rows2:
                        Fournisseur = row2['is_cofor'] or ''
                        CodeClient  = row2['code_client'] or ''
                        NomClient   = row2['nom_client'] or ''
                    #**********************************************************
                    if zzDebut<=0:
                        Msg+="Le numéro de la première étiquette doit-être supèrieur à 0 !\n"
                    if zzFin<zzDebut:
                        Msg+="Le numéro de la dernière étiquette doit-être supèrieur au numéro de la première !\n"
            if Msg=="":
                #** Test si la quantité modifiée ******************************
                if (zzNbPieces>0 and zzNbPieces!=Quantite):
                    if zzMDP1!=company.is_mdp_quantite:
                        Msg+="La quantité a été changée (%s => %s), la saisie du mot de passe est obligatoire !\n"%(Quantite,zzNbPieces)
                    Quantite=zzNbPieces
                #**************************************************************

                #** Test si les étiquettes existent déja dans odoo0 ***********
                if zzMDP2!=company.is_mdp_reimprimer:
                    for Nb in range(zzDebut, zzFin+1):
                        SQL = """
                            SELECT * FROM is_galia_base
                            WHERE soc='%s' AND type_eti='%s' AND num_of='%s' AND num_carton='%s'
                        """%(Soc,Etiquette,zzCode,Nb)
                        cr.execute(SQL)
                        rows2=cr.dictfetchall()
                        for row2 in rows2:
                            Msg+="Etiquette %s - %s  déjà imprimée dans odoo0, la saisie du mot de passe est obligatoire !\n"%(zzCode,Nb)
                            zzAction=""
                #**************************************************************

            if Msg!="":
                zzAction=""
            else:
                Action="Imprimer"
                if zzAction=="":
                    MsgOK="<div class=NomalNL>Cliquez sur OK pour lancer l'impression <div>"

            #** Test si impression en cours ***********************************
            if zzAction=="Imprimer" and Msg=="":
                path_lock='/tmp/imprime-etiquette-galia.lock'
                if os.path.exists(path_lock):
                    f = open(path_lock, "r")
                    Msg = f.read() 
            #******************************************************************

            if zzAction=="Imprimer" and Msg=="":
                #** Lock pour ne pas avoir 2 étiquettes avec le même numéro ***
                f = open(path_lock,'w')
                f.write("Etiquettes %s en cours d'impression par %s (site=%s)"%(zzCode,user_name,Soc))
                f.close()
                #**************************************************************

                Action=""
                for Nb in range(zzDebut, zzFin+1):
                    #time.sleep(1)


                    #** Intitialisation des variables pour l'étiquette ********
                    FN10="" # REF FRNS (30S)
                    if FormatEti=="PG":
                        FN10=CodePG      
                    if FormatEti=="MGI":
                        FN10=RefClient
                    if FormatEti=="VS":
                        FN10=RefClient  
                    if FormatEti=="DD":
                        FN10=RefClient 
                    if FormatEti=="EMS":
                        FN10=RefClient 
                    if FormatEti=="RE":
                        FN10=RefPlan   
                    if FormatEti=="EC":
                        FN10=RefPlan   
                    if TypeEti=="DEVIALET":
                         FN10=RefPlan   

                    if TypeEti=="DEVIALET":
                         FN10=RefPlan   






                    FN1="" # NProduit (P)
                    FN2=""
                    if (Cat<10 or Cat==46 or Cat==48):
                        if FormatEti=="PG":
                            FN1=RefClient
                        if FormatEti=="MGI":
                            FN1=RefPlan   
                        if FormatEti=="VS":
                            FN1=RefPlan
                        if FormatEti=="DD":
                            FN1=RefPlan  
                        if FormatEti=="EMS":
                            FN1=RefPlan 
                        if FormatEti=="RE":
                            FN1=RefClient
                        if FormatEti=="EC":
                            FN1=RefClient
                        if TypeEti=="DD" or TypeEti=="SIMU":
                            FN2=FN1       # Code Barre NProduit (sans le P devant)
                        else:
                            FN2="P"+FN1   # Code Barre NProduit (P)

                    #** Le 01/02/2022 => Code barre sur toutes les étiquettes
                    FN4  = "Q%s"%Quantite       # Code Barre Quantité (Q)
                    FN6  = "V"+Fournisseur      # Code Barre COFOR (V)
                    FN11 = ("30S"+FN10)[0:13]   # Code Barre Ref Fournisseur (30S)
                    FN3  = Quantite             # Quantité dans le carton
                    FN5  = Fournisseur          # Fournisseur (V)

                    # ** Recherche si étiquette existe dans odoo0 *************
                    SQL = """
                        SELECT num_eti, id, date_creation
                        FROM is_galia_base 
                        WHERE soc='%s' AND type_eti='%s' AND num_of='%s' AND num_carton='%s' 
                    """%(Soc,Etiquette,zzCode,Nb)
                    cr.execute(SQL)
                    rows2=cr.dictfetchall()
                    num_eti       = False
                    etiquette_id  = False
                    date_creation = datetime.now()
                    for row2 in rows2:
                        num_eti       = row2['num_eti']
                        etiquette_id  = row2['id']
                        date_creation = row2['date_creation']
                    #**********************************************************

                    #** Recherche dernier N Etiquette dans odoo0 **************
                    if num_eti==False:
                        SQL = "SELECT max(num_eti) AS numeti FROM is_galia_base WHERE num_eti<800000000 "
                        cr.execute(SQL)
                        rows2=cr.dictfetchall()
                        FN7=100000000
                        for row2 in rows2:
                            FN7=row2['numeti']+1; # N° Etiquette
                    else:
                        FN7=num_eti
                    #**********************************************************

                    if (Cat<10 or Cat==46 or Cat==48):
                        FN8="S%s"%FN7   # N° Etiquette (Code Barre)
                    FN8="S%s"%FN7       # Le 01/02/2022 => Code barre sur toutes les étiquettes
                    FN9=Designation     # Produit = Désignation du Produit
                    FN12=''
                    if Etiquette!="CodePG":
                        FN12='D'+date_creation.strftime('%d%m%y') # Date du jour
                    FN13=NumLot
                    if TypeEti=="SLEEPBOX":
                        FN13="664"+date_creation.strftime('%Y%V') # Semaine
                    if TypeEti=="NEA":
                        FN13="670"+date_creation.strftime('%Y%V') # Semaine
                    FN14=""
                    if AQP=="AQP":
                        FN14="AQP";                     # AQP
                    if CodePG!=zzCode:
                        FN15="%s / %s / %s / %s"%(CodePG,Moule,zzCode,Nb) # Ligne informations générales pour PG
                    else:
                        FN15 = "%s / %s / %s"%(CodePG,Moule,Nb) 

                    FN92='C:'
                    if TypeEti=='STELLANTIS':
                        FN92=''

                    info_commande = self.get_info_commande(cur=cur, num_eti=FN7, code_pg=CodePG)
                    point_dechargement = info_commande.get('point_dechargement')
                    code_routage       = info_commande.get('code_routage')
                    point_destination  = info_commande.get('point_destination')
     
                    #** CodeRoutage et PointDestination sur ligne commande **** 
                    FN99 = "" # PT DEST - POINT DE DESTINATION 
                    if TypeEti=='STELLANTIS':
                        FN15 = code_routage or ''
                        FN99 = point_destination or ''
                        # SQL="""
                        #         select sol.is_code_routage, sol.is_point_destination
                        #         from is_galia_base_uc uc join stock_move move on uc.stock_move_id=move.id
                        #                                  join sale_order_line sol on move.sale_line_id=sol.id
                        #         where uc.num_eti=%s 
                        #         order by uc.id desc limit 1
                        # """%FN7
                        # cur.execute(SQL)
                        # rows2 = cur.fetchall()
                        # CodeRoutage=False
                        # for row2 in rows2:
                        #     FN15 = row2['is_code_routage'] or ''
                        #     FN99 = row2['is_point_destination'] or ''
                    #**********************************************************

                    FN16=Adresse                  # Adresse PG, MGI ou VS suivant le cas
                    FN17=IndPlan                  # Indice Ref Plan
                    FN18=FN19=""
                    if GaucheDroite=="G":
                        FN18="G"                  # Piéce Gauche ou Droite
                        FN19="auche"              # Piéce Gauche ou Droite
                    if GaucheDroite=="D":
                        FN18="D"                  # Pièce Gauche ou Droite
                        FN19="roite"              # Pièce Gauche ou Droite
                    FN20=NomClient                # Raison sociale Client
                    if FormatEti=="DD":
                        FN20=" "
                    if FormatEti=="EMS":
                        FN20=" "
                    if TypeEti=="TRETY":
                        FN20="TRETY"
                    FN21 = '{:,.2f}'.format(Quantite*PoidsBrut).replace(',', ' ')+" Kg" # Poids brut du colis
                    FN24 = '{:,.2f}'.format(Quantite*PoidsNet).replace(',', ' ')+" Kg"  # Poids net du colis

                    FN30=FN90=FN91=FN98=""
                    if Etiquette=="CONTROLEES":
                        FN30="** CONTROLEES **"; # Entete5 = Poids
                    if LogoSecu=="R" or LogoSecu=="RS" or LogoSecu=="SR":
                        FN90 = "R"               # Signe Réglementation
                    if LogoSecu=="S" or LogoSecu=="RS" or LogoSecu=="SR":
                        FN91 = "S"               # Signe Sécu
                    if LogoSecu=="UR":
                        FN98 = "QMMY2" 
                    FN97=""
                    if CodeClient == "903000":
                        FN97="MADE IN FRANCE"

                    FN23 = FN130 = ''
                    if TypeEti=="LOT" or TypeEti=="DEVIALET":
                        FN23  = "H"+FN13[2:100] #,2,100);
                        FN130 = FN13
                        FN13  = ''


                    #** Point de déchargement (PTDECH) dans odoo site *********
                    FNPTDECH = point_dechargement or ''
                    # SQL="""
                    #     SELECT so.is_point_dechargement
                    #     FROM sale_order_line sol inner join sale_order       so on sol.order_id=so.id
                    #                              inner join product_product  pp on sol.product_id=pp.id
                    #                              inner join product_template pt on pp.product_tmpl_id=pt.id
                    #     WHERE 
                    #         so.is_point_dechargement is not null and
                    #         so.is_type_commande in ('ouverte', 'ls') and 
                    #         pt.is_code='%s'
                    #     order by so.id desc
                    #     limit 1
                    # """%CodePG
                    # cur.execute(SQL)
                    # rows2=cur.fetchall()
                    # FNPTDECH = ""
                    # for row2 in rows2:
                    #     FNPTDECH = row2['is_point_dechargement']
                    #**********************************************************

                    FN40="PLASTIGRAY"
                    if TypeEti=="TRETY":
                        FN40=CodeFournisseur
                    if FormatEti=="DD":
                        FN40=CodeFournisseur
                    if FormatEti=="EMS":
                        FN40=CodeFournisseur
                    if TypeEti=="EC":
                        FN40=" "
                    if TypeEti=="BUBENDORFF":
                        FN40=" "

                    FN22="1"

                    if TypeEti=="MASQUE":
                        FN20     = 'FN20'     # DEST
                        FNPTDECH = 'FNPTDECH' # FNPTDECH
                        FN97     = 'FN97'     # Made in France
                        FN40     = 'FN40'     # EXP
                        FN15     = 'FN15'     # CDE RTGE
                        FN18     = 'FN18'     # Gauche / Droite 
                        FN99     = 'FN99'     # PT DEST - POINT DE DESTINATION
                        FN92     = 'FN92'     # C: 
                        FN1      = 'FN1'      # N PROD
                        FN14     = 'FN14'     # AQP
                        FN98     = 'FN98'     # UR
                        FN24     = 'FN24'     # NET
                        FN21     = 'FN21'     # BRUT
                        FN12     = 'FN12'     # Date
                        FN3      = 'FN3'      # Quantité
                        FN7      = 'FN7'      # N Etiq
                        FN16     = 'FN16'     # xx
                        FN22     = 'FN22'     # NB colis par palette
                        FN9      = 'FN9'      # Désignation
                        FN10     = 'FN10'     # Fournisseur
                        FN13     = 'FN13'     # N Lot
                        FN13B    = 'FN13B'    # N Lot plus petit
                        FN17     = 'FN17'     # IND MODIF 
                        FN5      = 'FN5'      # COFOR
                        FN80     = 'FN80'     # 3 derniers chiffres de l'UM
                        FN4      = 'FN4'      # CBar QTE 
                        FN11     = 'FN11'     # CBar REF FRNS
                        FN6      = 'FN6'      # CBar COFOR
                        FN2      = 'FN2'      # CBar Produit
                        FN8      = 'FN8'      # CBar N° Etiq
                        FN23     = 'FN23'     # CBar N° lot
                        FN91     = 'FN91'     # S=Sécurité  
                        FN90     = 'FN90'     # R=Règlementation 


                    # Création début étiquette ********************************
                    Etiq+="\n \n##### Etiquette N%s #####\n"%Nb
                    if LogoSecu=="R" or LogoSecu=="S" or LogoSecu=="RS" or LogoSecu=="SR":
                        Etiq+="^XA^XFR:UC^FS \n"
                    if LogoSecu=="" or LogoSecu=="N" or LogoSecu=="UR":
                        Etiq+="^XA^IDR:SECU2.grf^FS \n"   # Efface le Logo Sécu de la mémoire
                        Etiq+="^XFR:UC^FS \n"

                    if is_cde_rtge_fond_noir:
                        Etiq+="""
                            ^FX ** Mettre le CDE RTGE en blanc sur fond noir ****************************** ^FS

                            ^FO645,140^GB160,1145,160,B,0^FS ^FX Bloc noir : X,Y | Larg,Haut,Epaiss,Coul,Arrondi ^FS

                            ^A0R,185,75^FO610,140^FR^FN15^FS ^FX CDE RTGE ^FS
                            ^FX ^A0R,185,75 : Police standard (0), Rotation 90° (R), Taille (185x75) ^FS
                            ^FX ^FO610,140  : Position sur l'étiquette (X=610, Y=140) ^FS
                            ^FX ^FR         : FIELD REVERSE -> Inverse la couleur (écrit en blanc sur fond noir) ^FS
                            ^FX ^FN15       : Appel de la variable numéro 15 ^FS
                            ^FX ^FS         : Fin de champ ^FS
                            ^FX *************************************************************************** ^FS
                        \n"""

                    Etiq+="^FN1 ^FD"+FN1+"^FS \n"        # N Produit (P)
                    Etiq+="^FN2 ^FD"+FN2+"^FS \n"        # N Produit (Code à Barre)
                    Etiq+="^FN3 ^FD"+str(FN3)+"^FS \n"   # Quantité(Q)
                    Etiq+="^FN4 ^FD"+FN4+"^FS \n"        # Quantité(Code à Barre)
                    Etiq+="^FN5 ^FD"+FN5+"^FS \n"        # Ref Fournisseur (30S)
                    Etiq+="^FN6 ^FD"+FN6+"^FS \n"        # Ref Fournisseur (Code à Barre)
                    Etiq+="^FN7 ^FD"+str(FN7)+"^FS \n"   # N Etiquette (S)
                    Etiq+="^FN8 ^FD"+FN8+"^FS \n"        # N Etiquette (Code à Barre)
                    Etiq+="^FN9 ^FD"+FN9+"^FS \n"        # Produit (Désignation Article)
                    Etiq+="^FN10^FD"+FN10+"^FS \n"       # Fournisseur (V)
                    Etiq+="^FN11^FD"+FN11+"^FS \n"       # Fournisseur (Code à Barre)
                    Etiq+="^FN12^FD"+FN12+"^FS \n"       # Date

                    if FN13!='':
                        Etiq+="^FN13^FD"+FN13+"^FS \n"       # N Lot (H)
                    else:
                        Etiq+="^FN130^FD"+FN130+"^FS \n"     # N Lot plus petit (H)

                    Etiq+="^FN14^FD"+FN14+"^FS \n"  
                    Etiq+="^FN15^FD"+FN15+"^FS \n"          # Entete1 = Code PG + Moule + OF + N Carton + Controle Operateur/Regleur
                    Etiq+="^FN16^FD"+FN16+"^FS \n"          # Adresse Complete Plastigray
                    Etiq+="^FN17^FD"+FN17+"^FS \n"          # Indice modification
                    Etiq+="^FN18^FD"+FN18+"^FS \n"          # Entete2
                    Etiq+="^FN20^FD"+FN20[0:23]+"^FS \n"    # Entete4=Raisons Sociale Client
                    Etiq+="^FNPTDECH^FD"+FNPTDECH+"^FS \n"  # PTDECH : Point de déchargement
                    Etiq+="^FN97^FD"+FN97+"^FS \n"  # Made in France
                    Etiq+="^FN21^FD"+FN21+"^FS \n"  # Poids Brut = Entete5
                    Etiq+="^FN24^FD"+FN24+"^FS \n"  # Poids Net
                    Etiq+="^FN23^FD"+FN23+"^FS \n"  # Code barre n° lot
                    Etiq+="^FN22^FD"+FN22+"^FS \n"  # Nb de carton
                    Etiq+="^FN30^FD"+FN30+"^FS \n"  # Entete5=Poids
                    Etiq+="^FN40^FD"+FN40+"^FS \n"  # Exp
                    Etiq+="^FN90^FD"+FN90+"^FS \n"  # Signe R = Réglement?
                    Etiq+="^FN91^FD"+FN91+"^FS \n"  # Signe S = Sécurité
                    Etiq+="^FN92^FD"+FN92+"^FS \n"  # C: pour contrôle
                    Etiq+="^FN99^FD"+FN99+"^FS \n"  # PT DEST - POINT DE DESTINATION 
                    Etiq+="^FN98^FD"+FN98+"^FS \n"  # Code UR

                    #** Data Matrix (QR Code) pour Delta Dore *****************
                    if TypeEti=="DD" or TypeEti=="EMS" or TypeEti=="NEA":
                        Etiq+="""^FO400,900^BXN,6,200^FD(P)"""+RefClient+"(2P)"+IndPlan+"(Q)"+str(Quantite)+"(9D)"+date_creation.strftime('%y%m%d')+"(1T)"+NumLot+"(K)(1P)"+RefClient+"-PLASTIGRAY(A1)PLASTIGRAY(A2)(A3)^FS"
                    #**********************************************************

                    #** Data Matrix (QR Code) pour DEVIALET *******************
                    if TypeEti=="DEVIALET":
                        CodeDevialet=RefPlan
                        QRCode=CodeDevialet+NumLot
                        Etiq+="^FO425,800^BXN,12,200^FD"+QRCode+"^FS"
                    #**********************************************************






                    if Nb==zzFin:
                        Etiq+="^MMT \n"  # Avance de l'éiquette
                    else:
                        Etiq+="^MMR \n"  # Ne pas couper les Etiquettes
                    Etiq+="^XZ \n"

                    #** Enregistrement Etiquette dans Odoo ********************
                    msg=""
                    Info = "%s - %s - %s"%(zzCode,Nb,FN7)
                    Log  = "%s - %s - %s par %s"%(zzCode,Nb,FN7,user_name)
                    if num_eti==False:
                        vals={
                            'num_eti'      : FN7,
                            'soc'          : Soc,
                            'type_eti'     : Etiquette,
                            'num_of'       : zzCode,
                            'num_carton'   : Nb,
                            'qt_pieces'    : self.str2int(FN3), # Quantite
                            'date_creation': date_creation,
                            'login'        : user_name,
                            'point_dechargement': point_dechargement,
                            'code_routage'      : code_routage,
                            'point_destination' : point_destination,
                        }
                        eti=self.env['is.galia.base'].create(vals)
                        _logger.info("Création éiquette Galia %s"%Log)
                    else:
                        eti = self.env['is.galia.base'].browse(etiquette_id)
                        eti.login              = user_name
                        eti.qt_pieces          = self.str2int(FN3)
                        eti.point_dechargement = point_dechargement
                        eti.code_routage       = code_routage
                        eti.point_destination  = point_destination
                        _logger.info("Réimpression étiquette Galia %s"%Log)
                    MsgOK+="<div class=NormalLB>Impression et enregistrement étiquette %s dans odoo0 éffectué avec succés.</div>"%Info
                    #**********************************************************

                os.unlink(path_lock)


        #** Code ZPL final ****************************************************
        ZPL=''
        if Etiq!='':
            addons_path = tools.config['addons_path'].split(',')[1]
            path = "%s/is_plastigray16/static/src/galia/"%addons_path
            Uc2   = open(path+'Uc2.zpl','rb').read().decode("utf-8")
            Uc40  = open(path+'UC-C40.zpl','rb').read().decode("utf-8")
            Secu  = open(path+'Secu.grf','rb').read().decode("utf-8")
            if TypeEti=="C40":
                ZPL=Uc40
            else:
                ZPL=Uc2
            ZPL+=Secu
            ZPL+=Etiq
        #**********************************************************************

        res={
            'Msg'     : Msg,
            'MsgOK'   : MsgOK,
            'Action'  : Action or '',
            'ZPL'     : ZPL,
        }
        return res


    def imprimer_etiquette_uc_action(self):
        company = self.env.company
        user = self.env['res.users'].browse(self._uid)
        for obj in self:
            vals={
                'ACTION'      : 'OK', 
                'Soc'         : obj.soc, 
                'Etiquette'   : obj.type_eti, 
                'Imprimante'  : 'ZPL', 
                'zzCode'      : obj.num_of, 
                'zzDebut'     : obj.num_carton, 
                'zzFin'       : obj.num_carton, 
                'zzNbPieces'  : obj.qt_pieces, 
                'zzMDP1'      : company.is_mdp_quantite,
                'zzMDP2'      : company.is_mdp_reimprimer, 
                'zzValidation': 'OK', 
                'zzAction'    : 'Imprimer', 
                'user_name'   : user.name,
            }
            
            # Écrire dans le chatter le contenu de vals
            message = "Impression étiquette UC avec les paramètres suivants :<br/>"
            for key, value in vals.items():
                # Ne pas afficher les mots de passe
                if 'MDP' not in key:
                    message += f"<b>{key}</b> : {value}<br/>"
            obj.message_post(body=message)
            
            res = obj.sudo().creer_etiquette(vals)
            Msg = res.get('Msg')
            if Msg!='':
                raise ValidationError(Msg)
            ZPL = res.get('ZPL')
            obj.imprimer_zpl(ZPL)


    def imprimer_zpl(self,ZPL, imprimante=None):


        if not imprimante:
            user=self.env['res.users'].browse(self._uid)
            imprimante=user.is_zebra_id.name or user.company_id.is_zebra_id.name
        if not imprimante:
            raise ValidationError('Imprimante Zebra non définie !')

        _logger.info('imprimante=%s : ZPL:\n%s'%(imprimante,ZPL))


        if imprimante and ZPL!='':
            cmd = 'echo "'+ZPL+'" | lpr -P'+imprimante
            p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
            stdout, stderr = p.communicate()
            if stderr:
                msg="Impossible d'imprimer sur %s !\n%s"%(imprimante,stderr.decode("utf-8"))
                _logger.error(msg)
                raise ValidationError(msg)
            msg='Envoi code ZPL sur imprimante %s'%imprimante
            _logger.info(msg)

        return imprimante


class is_galia_base_um(models.Model):
    _name='is.galia.base.um'
    _description="Etiquettes Galia UM"
    _order='name desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _sql_constraints = [('name_uniq','UNIQUE(name)', u'Cette étiquette UM existe déjà')]

    @api.depends('uc_ids')
    def _compute(self):
        for obj in self:
            qt_pieces  = 0
            product_id = False
            if obj.mixte=='non':
                for line in obj.uc_ids:
                    qt_pieces += line.qt_pieces
                    product_id = line.product_id
            obj.product_id = product_id
            obj.qt_pieces  = qt_pieces
            premiere_uc = obj.uc_ids[:1]
            obj.etiquette_um_a5 = bool(premiere_uc.product_id.product_tmpl_id.is_type_etiquette_um_id)

    name             = fields.Char("N°Étiquette UM", readonly=True             , index=True, tracking=True)
    mixte            = fields.Selection(_MIXTE, "UM mixte", default='non', required=True, tracking=True)
    liste_servir_id  = fields.Many2one('is.liste.servir', 'Liste à servir'     , index=True, tracking=True)
    bon_transfert_id = fields.Many2one('is.bon.transfert', 'Bon de transfert'  , index=True, tracking=True)
    production_id    = fields.Many2one('mrp.production', 'Ordre de fabrication', index=True, tracking=True)
    location_id      = fields.Many2one('stock.location', 'Emplacement actuel'  , index=True, domain=[("usage","=","internal")], default=lambda self: self._get_location_id(), tracking=True)
    location_dest_id = fields.Many2one('stock.location', 'Emplacement de destination'      , domain=[("usage","=","internal")], tracking=True)
    uc_ids           = fields.One2many('is.galia.base.uc'  , 'um_id', "UCs")
    product_id       = fields.Many2one('product.product', 'Article', readonly=True, compute='_compute', store=False)
    qt_pieces        = fields.Integer("Qt Pièces"                  , readonly=True, compute='_compute', store=False)
    etiquette_um_a5  = fields.Boolean("Étiquette UM A5", readonly=True, compute='_compute', store=False)
    employee_id      = fields.Many2one("hr.employee", "Employé", tracking=True)
    date_fin         = fields.Datetime("Date fin UM", tracking=True)
    active           = fields.Boolean("Active", default=True, copy=False, index=True, tracking=True)
    date_ctrl_rcp    = fields.Datetime("Date contrôle réception", tracking=True)
    information      = fields.Text("Information", readonly=True, compute='_compute_information_anomalie', store=False)
    anomalie         = fields.Text("Anomalie"   , readonly=True, compute='_compute_information_anomalie', store=False)


    def get_qt_par_lot(self):
        for obj in self:
            #** Recherche des quantités par article et par lot ****************
            mydict={}
            for uc in obj.uc_ids:
                key="%s-%s"%(uc.product_id.is_code,uc.production)
                if key not in mydict:
                    mydict[key]={
                        'product'   : uc.product_id,
                        'production': uc.production,
                        'qt_pieces' : 0
                    }
                mydict[key]['qt_pieces']+=uc.qt_pieces
            sorted_dict = dict(sorted(mydict.items())) 
            #******************************************************************

            for key in sorted_dict:
                #** Recherche du lot ******************************************
                vals=sorted_dict[key]
                domain=[
                    ('product_id','=',vals['product'].id),
                    ('name'      ,'=',vals['production']),
                ]
                lots=self.env['stock.lot'].search(domain)
                lot_id=(len(lots) and lots[0].id) or False
                vals['lot_id'] = lot_id
                #**************************************************************

                #** Recherche du stock ****************************************
                domain=[
                    ('product_id' ,'=',vals['product'].id),
                    ('location_id','=',obj.location_id.id),
                    ('lot_id'     ,'=',lot_id),
                ]
                quants=self.env['stock.quant'].search(domain)
                stock=0
                for quant in quants:
                    stock+=quant.quantity
                vals['stock'] = stock
                #**************************************************************
            return sorted_dict


    @api.depends('location_id','uc_ids')
    def _compute_information_anomalie(self):
        for obj in self:
            information=[]
            anomalie = []
            sorted_dict = obj.get_qt_par_lot()
            for key in sorted_dict:
                vals=sorted_dict[key]
                msg="%s : %s : lot_id=%s : Qt UM=%s : Stock=%s"%(
                    vals['product'].is_code.ljust(8),
                    vals['production'].ljust(8),
                    str(vals['lot_id']).ljust(8),
                    str(int(vals['qt_pieces'])).ljust(4),
                    int(vals['stock'])
                )
                if vals['qt_pieces']<=vals['stock']:
                    information.append(msg)
                else:
                    anomalie.append(msg)
            obj.information = (len(information) and '\n'.join(information)) or False
            obj.anomalie    = (len(anomalie)    and '\n'.join(anomalie)) or False


    def deplacer_um_action(self):
        for obj in self:
            if obj.anomalie:
                raise ValidationError("Déplacement impossible car stock non disponible dans emplacement '%s':\n%s"%(obj.location_id.name,obj.anomalie))
            sorted_dict = obj.get_qt_par_lot()
            for key in sorted_dict:
                product = sorted_dict[key]['product']
                qty     = sorted_dict[key]['qt_pieces']
                lot_id  = sorted_dict[key]['lot_id']
                name="UM %s"%obj.name
                vals={
                    "product_id": product.id,
                    "product_uom": product.uom_id.id,
                    "location_id": obj.location_id.id,
                    "location_dest_id": obj.location_dest_id.id,
                    "origin": name,
                    "name": name,
                    "reference": name,
                    "procure_method": "make_to_stock",
                    "product_uom_qty": qty,
                    "scrapped": False,
                    "propagate_cancel": True,
                    "is_inventory": True,
                    "additional": False,
                }
                move=self.env['stock.move'].create(vals)
                vals={
                    "move_id": move.id,
                    "product_id": product.id,
                    "product_uom_id": product.uom_id.id,
                    "location_id": obj.location_id.id,
                    "location_dest_id": obj.location_dest_id.id,
                    "lot_id": lot_id,
                    "qty_done": qty,
                    "reference": name,
                }
                move_line=self.env['stock.move.line'].create(vals)
                move._action_done()
            obj.location_id = obj.location_dest_id.id
            obj.location_dest_id = False
            return True















    def _get_location_id(self):
        filtre = [
            ('name' , '=', 'ATELIER'),
            ('usage', '=', 'internal'),
        ]
        lines = self.env["stock.location"].search(filtre)
        location_id = lines and lines[0].id or False
        return location_id
       

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Utiliser la séquence uniquement si le name n'est pas déjà fourni
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('is.galia.base.um')
        return super().create(vals_list)


    @api.onchange('liste_servir_id')
    def onchange_liste_servir_id(self):
        location_id = self.liste_servir_id.is_source_location_id.id
        if location_id:
            self.location_id = location_id


    @api.onchange('bon_transfert_id')
    def onchange_bon_transfert_id(self):
        location_id = self.bon_transfert_id.location_id.id
        if location_id:
            self.location_id = location_id


    @api.onchange('production_id')
    def onchange_production_id(self):
        location_id = self.production_id.location_dest_id.id
        if location_id:
            self.location_id = location_id


    def acceder_um_action(self):
        view_id = self.env.ref('is_plastigray16.is_galia_base_um_form_view').id
        for obj in self:
            return {
                'name': "Etiquettes UM",
                'view_mode': 'form',
                'view_id': view_id,
                'res_model': 'is.galia.base.um',
                'type': 'ir.actions.act_window',
                'res_id': obj.id,
                'domain': '[]',
            }


    def voir_uc_action(self):
        for obj in self:
            res= {
                'name': obj.name,
                'view_mode': 'tree,form',
                'res_model': 'is.galia.base.uc',
                'type': 'ir.actions.act_window',
                'domain': [('um_id','=',obj.id)],
            }
            return res


    def imprimer_etiquette_um_action(self):
        for obj in self : 
            cdes = self.env['is.commande.externe'].search([('name','=',"imprimer-etiquette-um")])
            for cde in cdes:
                model=self._name
                uid=self._uid
                user=self.env['res.users'].browse(uid)
                soc=user.company_id.partner_id.is_code
                x = cde.commande
                x = x.replace("#soc"  , soc)
                x = x.replace("#um_id", str(obj.id))
                x = x.replace("#uid"  , str(uid))
                
                # Écrire dans le chatter le contenu de la commande
                message = "Impression étiquette UM avec les paramètres suivants :<br/>"
                message += f"<b>Société</b> : {soc}<br/>"
                message += f"<b>UM ID</b> : {obj.id}<br/>"
                message += f"<b>Utilisateur ID</b> : {uid}<br/>"
                message += f"<b>Utilisateur</b> : {user.name}<br/>"
                message += f"<b>Commande</b> : {x}<br/>"
                obj.message_post(body=message)
                
                _logger.info(x)
                lines=os.popen(x).readlines()
                for line in lines:
                    _logger.info(line.strip())


    def imprimer_etiquette_um_a5(self, imprimante=False):
        # Balises ZPL utilisées :
        # ^XA : début du format d'étiquette
        # ^CI28 : encodage UTF-8, pour les caractères accentués
        # ^PW : largeur de l'étiquette (en dots)
        # ^LL : longueur/hauteur de l'étiquette (en dots)
        # ^FO : position (x,y) de l'élément qui suit, depuis le coin haut-gauche
        # ^GB : dessine un cadre/une ligne (largeur, hauteur, épaisseur du trait)
        # ^A0R : police utilisée pour le texte qui suit (hauteur, largeur des caractères), tournée à 90°
        # ^FD : donnée (texte) à afficher
        # ^FS : fin de l'élément
        # ~DG : télécharge un graphique (logo Sécu) en mémoire imprimante
        # ^XG : rappelle un graphique déjà téléchargé en mémoire (position, facteurs d'agrandissement x/y)
        # ^BY : épaisseur/ratio des modules du code-barre qui suit
        # ^B3 : dessine un code-barre Code 39 (orientation, checksum, hauteur, ligne de lecture...)
        # ^XZ : fin du format d'étiquette
        #
        # Comme pour l'étiquette UC (Uc2.zpl) et l'étiquette UM actuelle (qui recharge le même format 'UC'),
        # toute l'étiquette est dessinée tournée à 90° (^A0R) : le logo Secu.grf, qui n'est jamais tourné
        # lui-même, s'affiche alors dans le bon sens une fois l'étiquette physiquement tournée à la lecture.

        # Imprimante Zebra 300dpi => 300/25.4 dots par mm
        #DOTS_PAR_MM = 300/25.4
        DOTS_PAR_MM = 300/25 # Pour grossir un peu

        def mm(valeur_mm):
            return round(valeur_mm*DOTS_PAR_MM)

        # Toutes les dimensions ci-dessous sont exprimées en mm, dans le repère logique
        # non tourné (0,0)=haut-gauche, x vers la droite, y vers le bas, comme un plan classique.
        LARGEUR  = 210  # Largeur étiquette (A5 paysage)
        HAUTEUR  = 148  # Hauteur étiquette (A5 paysage)
        EPAISSEUR = 3   # Epaisseur des traits, en dots
        TAILLE_POLICE       = 3 # Hauteur/largeur des caractères des labels
        TAILLE_POLICE_5MM   = 5 # Hauteur/largeur des caractères des valeurs, en 5mm
        TAILLE_POLICE_7MM   = 7 # Hauteur/largeur des caractères des valeurs, en 7mm
        TAILLE_POLICE_13MM  = 13 # Hauteur/largeur des caractères des valeurs, en 13mm
        MARGE_TEXTE_GAUCHE  = 2 # Marge ajoutée devant les labels de la colonne de gauche
        DECALAGE_TEXTE      = 8 # Décalage des labels, en dots (1pt vers le bas et vers la droite)
        ESPACE_LABEL_VALEUR = 1 # Espace minimum entre le label et sa valeur, en mm

        # Rotation 90° de tout le plan logique (x,y) vers le repère physique de l'étiquette,
        # pour que le texte ^A0R se lise de haut en bas comme sur l'étiquette UC.
        # taille_police : pour le texte (^A0R), l'ancre déborde vers la cellule au-dessus si on
        # ne décale pas d'une hauteur de caractère ; laisser à 0 pour les lignes (^GB).
        def FO(x, y, taille_police=0):
            decalage = DECALAGE_TEXTE if taille_police else 0 # Uniquement pour le texte, pas pour les lignes (^GB)
            px = mm(HAUTEUR-y-taille_police)-decalage # -decalage : vers la gauche, pour ne pas coller à la ligne
            py = mm(x)+decalage                       # +decalage : vers le bas, pour ne pas coller à la ligne
            return "^FO%s,%s"%(px, py)

        # Logo Sécu (case vide entre les poids et le Produit, colonne de droite)
        # NB : avec FO(x,y), c'est y qui pilote la position horizontale à l'écran et x la position
        # verticale (le texte tourné ^A0R inverse les deux par rapport à une lecture non tournée).
        LOGO_SECU_MAGNIFICATION = 1 # ^XG n'accepte que des facteurs entiers (1,2,3...)
        LOGO_SECU_TAILLE = 22*LOGO_SECU_MAGNIFICATION # Taille du logo (256 dots ≈ 22mm à l'échelle 1), pour ne pas déborder dans la cellule au-dessus, comme le texte
        LOGO_SECU_Y = 46+((76-46)-LOGO_SECU_TAILLE)/2 # Centré horizontalement (à l'écran) dans la ligne 46-76
        LOGO_SECU_X = 210-LOGO_SECU_TAILLE-TAILLE_POLICE_7MM-2 # Proche du bas (à l'écran), en laissant la place aux lettres R/S juste après
        LOGO_SECU_LETTRE_X = LOGO_SECU_X+LOGO_SECU_TAILLE # Lettres R/S affichées juste après le logo (à l'écran)

        # Contenu du graphique Secu.grf (logo sécurité), envoyé une fois en mémoire imprimante
        addons_path = tools.config['addons_path'].split(',')[1]
        path = "%s/is_plastigray16/static/src/galia/"%addons_path
        SECU_GRF = open(path+'Secu.grf','rb').read().decode("utf-8")
        SECU_GRF = SECU_GRF.split('^XA')[0] # Le fichier contient un fragment parasite '^XA^LL0750' en fin de fichier, qui casse le format

        # Lignes horizontales (dans le repère logique) : (y, x_debut, x_fin)
        LIGNES_H = [
            (0    , 0  , 210),
            (20   , 0  , 210),
            (46   , 0  , 210),
            (76   , 0  , 210),
            (104  , 0  , 100),
            (125  , 0  , 210),
            (148  , 0  , 210),
            (33   , 100, 210),
            (86.5 , 100, 210),
            (114.5, 100, 210),
        ]

        # Lignes verticales (dans le repère logique) : (x, y_debut, y_fin)
        LIGNES_V = [
            (0  , 0    , 148),
            (210, 0    , 148),
            (100, 0    , 148),
            (136, 33   , 46),
            (173, 33   , 46),
            (140, 114.5, 125),
        ]

        # Labels (dans le repère logique) : (x, y, texte, colonne)
        LABELS = [
            (0  , 0    , "Destinataire"       , 'gauche'),
            (0  , 20   , "N°document"         , 'gauche'),
            (0  , 46   , "N°produit (P)"      , 'gauche'),
            (0  , 76   , "Quantité (Q)"       , 'gauche'),
            (0  , 104  , "Fournisseur (V)"    , 'gauche'),
            (0  , 125  , "N°étiquette"        , 'gauche'),

            (100, 0    , "Lieu de livraison"  , 'droite'),
            (100, 20   , "Adresse expéditeur" , 'droite'),
            (100, 33   , "Poids net (kg)"     , 'droite'),
            (136, 33   , "Poids brut (kg)"    , 'droite'),
            (173, 33   , "Nb boites"          , 'droite'),
            (100, 76   , "Produit"            , 'droite'),
            (100, 86.5 , "Ref Logistique"     , 'droite'),
            (100, 114.5, "Date"               , 'droite'),
            (140, 114.5, "Indice Modification", 'droite'),
            (100, 125  , "N°lot (H)"          , 'droite'),
        ]

        # Codes-barres : (x, y, hauteur, clé de la valeur, préfixe)
        # y = bas de la ligne du tableau - hauteur - ESPACE_CODE_BARRE (espace avant le trait du dessous)
        # x des codes-barres à droite = base de la colonne (100) + 2mm (décalage vers la droite)
        ESPACE_CODE_BARRE = 3 # mm - marge de sécurité (le rendu ne semble pas respecter exactement 1mm)
        CODES_BARRES = [
            (MARGE_TEXTE_GAUCHE, 76   -13-ESPACE_CODE_BARRE, 13, 'numero_produit', 'P'),
            (MARGE_TEXTE_GAUCHE, 104  -13-ESPACE_CODE_BARRE, 13, 'quantite_um'   , 'Q'),
            (MARGE_TEXTE_GAUCHE, 125  -13-ESPACE_CODE_BARRE, 13, 'fournisseur'   , 'V'),
            (MARGE_TEXTE_GAUCHE, 148  -13-ESPACE_CODE_BARRE, 13, 'num_etiquette' , ''),
            (100+2             , 114.5-13-ESPACE_CODE_BARRE, 13, 'ref_logistique', ''),
            (100+2             , 148  -13-ESPACE_CODE_BARRE, 13, 'num_lot'       , 'H'),
        ]

        for obj in self:
            # Destinataire : adresse du client par défaut de l'article de la première UC de cette UM, sur 3 lignes
            premiere_uc = obj.uc_ids[:1]
            client = premiere_uc.product_id.product_tmpl_id.is_client_ids.filtered(lambda c: c.client_defaut)[:1].client_id
            lignes_destinataire = [
                client.name or '',
                client.street or '',
                ' '.join(filter(None, [client.zip, client.city])),
            ] if client else []

            # Point de déchargement de la commande de la ligne de livraison de la première UC, juste après le label Destinataire
            point_dechargement = premiere_uc.stock_move_id.sale_line_id.order_id.is_point_dechargement or ''

            # Adresse expéditeur : champ 'Adresse expéditeur' du type étiquette UM de l'article, sur une ligne
            expediteur = premiere_uc.product_id.product_tmpl_id.is_type_etiquette_um_id.adresse_expediteur or ''

            # Fournisseur (V) : champ is_cofor du client de l'article
            fournisseur = client.is_cofor or ''

            # Poids net/brut : somme, pour chaque UC, du poids net/brut de l'article multiplié par sa quantité
            poids_net  = sum(uc.qt_pieces*uc.product_id.product_tmpl_id.weight_net for uc in obj.uc_ids)
            poids_brut = sum(uc.qt_pieces*uc.product_id.product_tmpl_id.weight     for uc in obj.uc_ids)

            # Nb boites : nombre d'UC de cette UM
            nb_boites = len(obj.uc_ids)

            # Lieu de livraison : point de destination de la ligne de commande de la ligne de livraison de la première UC
            lieu_livraison = premiere_uc.stock_move_id.sale_line_id.is_point_destination or ''

            # N°produit (P) : référence de l'article selon le type étiquette UM (ref PG/plan/client)
            article        = premiere_uc.product_id.product_tmpl_id
            type_eti_um    = article.is_type_etiquette_um_id
            REF_LOGISTIQUE = {
                'ref_pg'    : article.is_code,
                'ref_plan'  : article.is_ref_plan,
                'ref_client': article.is_ref_client,
            }
            numero_produit = REF_LOGISTIQUE.get(type_eti_um.ref_logistique) or ''

            # Logo Sécu : affiché si is_soumise_regl est renseigné, avec les lettres R et/ou S
            is_soumise_regl = article.is_soumise_regl or ''

            # Produit : désignation de l'article, précédée du code fabrication selon is_type_etiquette_um
            produit = article.name or ''
            if type_eti_um.produit=='avec_code_fabrication' and article.is_code_fabrication:
                produit = "%s-%s"%(article.is_code_fabrication, produit)

            # Quantité (Q) : quantité de l'UM
            quantite_um = obj.qt_pieces

            # Ref Logistique : référence plan de l'article
            ref_logistique = article.is_ref_plan or ''

            # Date : date de création de la première UC, au format Ymd
            date = premiere_uc.date_creation.strftime('%Y%m%d') if premiere_uc.date_creation else ''

            # N°lot (H) : champ 'Production' de la première UC
            num_lot = premiere_uc.production or ''

            # Indice Modification : indice plan de l'article
            indice_modification = article.is_ind_plan or ''

            # N°étiquette : nom de l'UM
            num_etiquette = obj.name or ''

            # Pour les UM mixtes, ces valeurs n'ont pas de sens (pas un seul article) et sont effacées, sans code-barre
            CODES_BARRES_SUPPRIMES = []
            if obj.mixte=='oui':
                is_soumise_regl   = ''
                numero_produit    = ''
                quantite_um       = ''
                produit           = ''
                ref_logistique    = ''
                indice_modification = ''
                date              = ''
                num_lot           = ''
                CODES_BARRES_SUPPRIMES = ['numero_produit', 'quantite_um', 'ref_logistique', 'num_lot']

            ZPL  = "^XA\n"
            ZPL += "^CI28\n" # Encodage UTF-8, pour les caractères accentués
            ZPL += "^PW%s\n"%(mm(HAUTEUR)+EPAISSEUR) # Largeur physique = hauteur logique (étiquette tournée à 90°)
            ZPL += "^LL%s\n"%(mm(LARGEUR)+EPAISSEUR) # Hauteur physique = largeur logique (étiquette tournée à 90°)
            if is_soumise_regl:
                ZPL += SECU_GRF # Envoi du graphique une seule fois, avant tout le reste (sinon l'étiquette est corrompue)
            for y, x_debut, x_fin in LIGNES_H:
                # Ligne horizontale logique => ligne verticale physique
                ZPL += "%s^GB%s,%s,%s^FS\n"%(FO(x_debut, y), EPAISSEUR, mm(x_fin-x_debut), EPAISSEUR)
            for x, y_debut, y_fin in LIGNES_V:
                # Ligne verticale logique => ligne horizontale physique
                ZPL += "%s^GB%s,%s,%s^FS\n"%(FO(x, y_fin), mm(y_fin-y_debut), EPAISSEUR, EPAISSEUR)
            for x, y, texte, colonne in LABELS:
                marge = MARGE_TEXTE_GAUCHE if colonne=='gauche' else 0
                if texte=="N°étiquette":
                    # Suffixe (G) UM mixte ou (M) UM homogène
                    texte = "%s (%s)"%(texte, 'G' if obj.mixte=='oui' else 'M')
                ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(x+marge, y, TAILLE_POLICE), mm(TAILLE_POLICE), mm(TAILLE_POLICE), texte)

            # Valeur du Point de déchargement, juste après le label Destinataire (sur la même ligne)
            x_point_dechargement = 25 # Largeur approximative du label 'Destinataire'
            ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(x_point_dechargement, 0, TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), point_dechargement)

            # Valeur du Destinataire, affichée ligne par ligne sous le label
            y_valeur = TAILLE_POLICE+ESPACE_LABEL_VALEUR # Juste sous le label, avec un minimum d'espace
            for num_ligne, ligne in enumerate(lignes_destinataire):
                y_ligne = y_valeur+num_ligne*TAILLE_POLICE_5MM
                ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(MARGE_TEXTE_GAUCHE, y_ligne, TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), ligne)

            # Valeur de l'Adresse expéditeur, sur une seule ligne sous le label
            y_expediteur = 20+TAILLE_POLICE+ESPACE_LABEL_VALEUR # Label 'Adresse expéditeur' positionné à y=20
            ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(100, y_expediteur, TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), expediteur)

            # Valeurs des poids net/brut et du nb boites, sous les labels positionnés à y=33
            y_poids = 33+TAILLE_POLICE+ESPACE_LABEL_VALEUR
            ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(100, y_poids, TAILLE_POLICE_7MM), mm(TAILLE_POLICE_7MM), mm(TAILLE_POLICE_7MM), '%.2f'%poids_net)
            ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(136, y_poids, TAILLE_POLICE_7MM), mm(TAILLE_POLICE_7MM), mm(TAILLE_POLICE_7MM), '%.2f'%poids_brut)
            ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(173, y_poids, TAILLE_POLICE_7MM), mm(TAILLE_POLICE_7MM), mm(TAILLE_POLICE_7MM), nb_boites)

            # Valeur du Lieu de livraison, sous le label positionné à y=0
            y_livraison = TAILLE_POLICE+ESPACE_LABEL_VALEUR
            ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(100, y_livraison, TAILLE_POLICE_13MM), mm(TAILLE_POLICE_13MM), mm(TAILLE_POLICE_13MM), lieu_livraison)

            # Valeur du N°produit (P), juste après le label (sur la même ligne) pour économiser de la hauteur
            x_produit = 20 # Largeur approximative du label 'N°produit (P)'
            ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(x_produit, 46, TAILLE_POLICE_13MM), mm(TAILLE_POLICE_13MM), mm(TAILLE_POLICE_13MM), numero_produit)

            # Valeur du Produit, sous le label positionné à y=76
            y_produit_designation = 76+TAILLE_POLICE+ESPACE_LABEL_VALEUR
            ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(100, y_produit_designation, TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), produit)

            # Valeur de la Quantité (Q), juste après le label (sur la même ligne)
            x_quantite = 20 # Largeur approximative du label 'Quantité (Q)'
            ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(x_quantite, 76, TAILLE_POLICE_13MM), mm(TAILLE_POLICE_13MM), mm(TAILLE_POLICE_13MM), quantite_um)

            # Valeur de Ref Logistique, juste après le label (sur la même ligne) pour gagner de la hauteur
            x_ref_logistique = 100+28 # Colonne de droite (base 100) + largeur approximative du label 'Ref Logistique'
            ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(x_ref_logistique, 86.5, TAILLE_POLICE_13MM), mm(TAILLE_POLICE_13MM), mm(TAILLE_POLICE_13MM), ref_logistique)

            # Valeurs de Date et Indice Modification, sous les labels positionnés à y=114.5
            y_date = 114.5+TAILLE_POLICE+ESPACE_LABEL_VALEUR
            ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(100, y_date, TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), date)
            ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(140, y_date, TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), indice_modification)

            # Valeur du N°lot (H), juste après le label (sur la même ligne) pour gagner de la hauteur
            x_num_lot = 100+14 # Colonne de droite (base 100) + largeur approximative du label 'N°lot (H)'
            ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(x_num_lot, 125, TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), num_lot)

            # Valeur du N°étiquette, juste après le label (sur la même ligne) pour gagner de la hauteur
            x_etiquette = 25 # Largeur approximative du label 'N°étiquette'
            ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(x_etiquette, 125, TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), num_etiquette)

            # Valeur du Fournisseur (V), juste après le label (sur la même ligne) pour gagner de la hauteur
            x_fournisseur = 25 # Largeur approximative du label 'Fournisseur (V)'
            ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(x_fournisseur, 104, TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), fournisseur)

            # Codes-barres : N°produit (P), Quantité (Q), Fournisseur (V), N°étiquette, Ref Logistique
            VALEURS_CODE_BARRE = {
                'numero_produit' : numero_produit,
                'quantite_um'    : quantite_um,
                'fournisseur'    : fournisseur,
                # Préfixe G (UM mixte) ou M (UM homogène), uniquement pour le code-barre
                'num_etiquette'  : ('G' if obj.mixte=='oui' else 'M')+num_etiquette,
                'ref_logistique' : ref_logistique,
                'num_lot'        : num_lot,
            }
            for x, y, hauteur, cle, prefixe in CODES_BARRES:
                if cle in CODES_BARRES_SUPPRIMES:
                    continue
                valeur = "%s%s"%(prefixe, VALEURS_CODE_BARRE[cle])
                ZPL += "^BY4,2.0\n" # Module doublé (2 -> 4 dots) pour des codes-barres 2x plus larges
                ZPL += "%s^B3R,N,%s,N,N^FD%s^FS\n"%(FO(x, y, hauteur), mm(hauteur), valeur)

            # Logo Sécu : identique au code de creer_etiquette (^XGR:SECU2.grf,1,1^FS, sans ^FW),
            # correctement orienté car toute l'étiquette est tournée à 90° comme l'étiquette UC.
            if is_soumise_regl:
                ZPL += "%s^XGR:SECU2.grf,%s,%s^FS\n"%(FO(LOGO_SECU_X, LOGO_SECU_Y, LOGO_SECU_TAILLE), LOGO_SECU_MAGNIFICATION, LOGO_SECU_MAGNIFICATION)
                if 'R' in is_soumise_regl:
                    # R aligné sur le bord haut du logo (à l'écran)
                    ZPL += "%s^A0R,%s,%s^FDR^FS\n"%(FO(LOGO_SECU_LETTRE_X, LOGO_SECU_Y, TAILLE_POLICE_7MM), mm(TAILLE_POLICE_7MM), mm(TAILLE_POLICE_7MM))
                if 'S' in is_soumise_regl:
                    # S aligné sur le bord bas du logo (à l'écran)
                    ZPL += "%s^A0R,%s,%s^FDS^FS\n"%(FO(LOGO_SECU_LETTRE_X, LOGO_SECU_Y+LOGO_SECU_TAILLE-TAILLE_POLICE_7MM, TAILLE_POLICE_7MM), mm(TAILLE_POLICE_7MM), mm(TAILLE_POLICE_7MM))

            ZPL += "^MMT\n"   #Avance de l'éiquette
            ZPL += "^XZ\n"


            try:
                imprimante_utilisee = self.env['is.galia.base'].imprimer_zpl(ZPL, imprimante=imprimante)
            except Exception as e:
                # Nouveau curseur : le message doit survivre au rollback provoqué par l'exception
                with self.pool.cursor() as new_cr:
                    new_env = api.Environment(new_cr, self.env.uid, self.env.context)
                    new_env['is.galia.base.um'].browse(obj.id).message_post(
                        body="Échec de l'impression étiquette UM A5 (%s) : %s"%(obj.name, e)
                    )
                raise

            # Écrire dans le chatter à chaque impression
            message = "Impression étiquette UM A5 (%s) sur l'imprimante <b>%s</b>"%(obj.name, imprimante_utilisee)
            obj.message_post(body=message)

        return True


    def imprimer_etiquette_uc_action(self):
        user = self.env['res.users'].browse(self._uid)
        company = self.env.company
        for obj in self:
            domain = [('um_id','=',obj.id)]
            ucs = self.env['is.galia.base.uc'].search(domain)
            for uc in ucs:
                uc.imprimer_etiquette_uc_action()












class is_galia_base_uc(models.Model):
    _name='is.galia.base.uc'
    _description="Etiquettes Galia UC"
    _order='num_eti desc'
    _rec_name='num_eti'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _sql_constraints = [('num_eti_uniq','UNIQUE(num_eti,um_id)', u'Cette étiquette existe déjà dans cette UM')]

    um_id         = fields.Many2one('is.galia.base.um', 'UM', required=True, ondelete='cascade', tracking=True)
    um_mixte      = fields.Selection(related="um_id.mixte")
    um_active     = fields.Boolean(related="um_id.active")
    num_eti       = fields.Integer("N°Étiquette UC", required=True, index=True, tracking=True)
    type_eti      = fields.Char("Type étiquette", required=True   , index=True, tracking=True)
    num_carton    = fields.Integer("N°Carton", required=True      , index=True, tracking=True)
    qt_pieces     = fields.Integer("Qt Pièces", required=True, tracking=True)
    date_creation = fields.Datetime("Date de création", required=True, tracking=True)
    production_id = fields.Many2one('mrp.production', 'Ordre de fabrication', tracking=True)
    production    = fields.Char('Fabrication', tracking=True, index=True)
    product_id    = fields.Many2one('product.product', 'Article', required=True , index=True, tracking=True)
    employee_id   = fields.Many2one("hr.employee", "Employé", tracking=True)
    liste_servir_id   = fields.Many2one('is.liste.servir' , 'Liste à servir'  , related='um_id.liste_servir_id')
    bon_transfert_id  = fields.Many2one('is.bon.transfert', 'Bon de transfert', related='um_id.bon_transfert_id')
    ls_line_id        = fields.Many2one('is.liste.servir.line' , 'Ligne liste à servir', tracking=True)
    bt_line_id        = fields.Many2one('is.bon.transfert.line', 'Ligne bon de transfert', tracking=True)
    stock_move_id     = fields.Many2one('stock.move', 'Ligne livraison', tracking=True)
    stock_move_rcp_id = fields.Many2one('stock.move', 'Ligne réception', tracking=True)
    reception_inter_site_id = fields.Many2one('is.reception.inter.site', 'Réception inter-site', tracking=True)
    reimprime               = fields.Boolean("UC à ré-imprimer", default=False, tracking=True, help="Il faut ré-imprimer cette UC car le point de déchargement, le code routage ou le point de destination a changé")
    etiquette_remplacee_le  = fields.Datetime("Etiquette remplacée le", tracking=True, help="Date et heure de mise en place de l'étiquette ré-imprimée")
    active                  = fields.Boolean("Actif", default=True, tracking=True)




    def etiquette_remplacee_action(self):
        for obj in self:
            obj.etiquette_remplacee_le = datetime.now()
        return []


    def acceder_uc_action(self):
        for obj in self:
            return {
                'name': "Etiquettes UC",
                'view_mode': 'form',
                'res_model': 'is.galia.base.uc',
                'type': 'ir.actions.act_window',
                'res_id': obj.id,
                'domain': '[]',
            }


    def imprimer_etiquette_uc_action(self):
        user = self.env['res.users'].browse(self._uid)
        company = self.env.company
        DB        = company.is_nom_base_odoo0
        USERID    = 2
        DBLOGIN   = company.is_login_admin
        USERPASS  = company.is_mdp_admin
        URL       = company.is_url_odoo0 
        sock = xmlrpclib.ServerProxy('%s/xmlrpc/2/object'%URL)
        for obj in self:
            #** Retrouver la société de l'étiquette ***************************
            Soc=False
            domain=[('num_eti','=',obj.num_eti)]
            try:
                lines=sock.execute_kw(DB, USERID, USERPASS, 'is.galia.base', 'search_read', [domain], {'fields': ['num_eti', 'soc'], 'limit': 3, 'order': 'id desc'})
            except:
                msg="Problème de connexion sur %s ou sur la base %s"%(URL,DB)
                raise ValidationError(msg)
            for line in lines:
                Soc=line.get('soc')
            if not Soc:
                msg="Etiquette %s non trouvée dans Odoo 0"%obj.num_eti
                raise ValidationError(msg)
            #******************************************************************
            vals={
                'ACTION'      : 'OK', 
                'Soc'         : Soc, 
                'Etiquette'   : obj.type_eti, 
                'Imprimante'  : 'ZPL', 
                'zzCode'      : obj.production, 
                'zzDebut'     : obj.num_carton, 
                'zzFin'       : obj.num_carton, 
                'zzNbPieces'  : obj.qt_pieces, 
                'zzMDP1'      : company.is_mdp_quantite,
                'zzMDP2'      : company.is_mdp_reimprimer, 
                'zzValidation': 'OK', 
                'zzAction'    : 'Imprimer', 
                'user_name'   : user.name,
            }
            
            # Écrire dans le chatter le contenu de vals
            message = "Impression étiquette UC avec les paramètres suivants :<br/>"
            for key, value in vals.items():
                # Ne pas afficher les mots de passe
                if 'MDP' not in key:
                    message += f"<b>{key}</b> : {value}<br/>"


            #message += "uc_id=%s<br/>"%obj.id
            message += "UC=%s<br/>"%obj.num_eti
            message += "UM=%s<br/>"%obj.um_id.name
            message += "Liste à servir=%s<br/>"%obj.um_id.liste_servir_id.name

            obj.message_post(body=message)
            
            try:
                res = sock.execute_kw(DB, USERID, USERPASS, 'is.galia.base', 'creer_etiquette', [[0], vals])
            except:
                msg="Problème de connexion sur %s ou sur la base %s"%(URL,DB)
                raise ValidationError(msg)
            if 'Msg' in res:
                if res['Msg']!='':
                    raise ValidationError(res['Msg'])
            ZPL = res.get('ZPL')
            self.env['is.galia.base'].imprimer_zpl(ZPL)
            return True
