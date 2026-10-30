# -*- coding: utf-8 -*-
from odoo import models, fields, tools # type: ignore
from odoo.exceptions import ValidationError  # type: ignore
from subprocess import PIPE, Popen
from xmlrpc import client as xmlrpclib
from datetime import datetime
import os
import re
import psycopg2         # type: ignore
import psycopg2.extras  # type: ignore
import logging
_logger = logging.getLogger(__name__)


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


    def _creer_etiquette_uc_odoo0(self, uc_ref, production, qt):
        """Crée une nouvelle étiquette UC dans odoo0 (même société et type que l'UC uc_ref, OF production, n° de carton = plus grand + 1).
        Retourne num_eti, num_carton et le ZPL. Utilisée par le contrôle qualité et « Scinder UM par lot »"""
        company  = self.env.company
        DB       = company.is_nom_base_odoo0
        USERID   = 2
        USERPASS = company.is_mdp_admin
        URL      = company.is_url_odoo0
        sock = xmlrpclib.ServerProxy('%s/xmlrpc/2/object'%URL)
        def executer(methode, args, kwargs=None):
            try:
                return sock.execute_kw(DB, USERID, USERPASS, 'is.galia.base', methode, args, kwargs or {})
            except Exception:
                _logger.exception("Création étiquette UC : odoo0 : %s", methode)
                raise ValidationError("Problème de connexion sur %s ou sur la base %s (%s)"%(URL, DB, methode))
        lignes = executer('search_read', [[('num_eti','=',uc_ref.num_eti)]], {'fields': ['soc'], 'limit': 1, 'order': 'id desc'})
        soc = lignes and lignes[0]['soc']
        if not soc:
            raise ValidationError("Étiquette %s non trouvée dans odoo0"%uc_ref.num_eti)
        domain = [('soc','=',soc), ('type_eti','=',uc_ref.type_eti), ('num_of','=',production)]
        lignes = executer('search_read', [domain], {'fields': ['num_carton'], 'limit': 1, 'order': 'num_carton desc'})
        num_carton = (lignes and lignes[0]['num_carton'] or 0) + 1
        # Sans le mot de passe de réimpression : refus si ce n° de carton existe déjà (deux créations en même temps)
        res = executer('creer_etiquette', [[0], {
            'ACTION'      : 'OK',
            'Soc'         : soc,
            'Etiquette'   : uc_ref.type_eti,
            'Imprimante'  : 'ZPL',
            'zzCode'      : production,
            'zzDebut'     : num_carton,
            'zzFin'       : num_carton,
            'zzNbPieces'  : qt,
            'zzMDP1'      : company.is_mdp_quantite,
            'zzValidation': 'OK',
            'zzAction'    : 'Imprimer',
            'user_name'   : self.env.user.name,
        }])
        if res.get('Msg'):
            raise ValidationError("odoo0 : %s"%res['Msg'])
        lignes = executer('search_read', [domain+[('num_carton','=',num_carton)]], {'fields': ['num_eti'], 'limit': 1})
        if not lignes:
            raise ValidationError("Étiquette %s / carton %s non créée dans odoo0"%(production, num_carton))
        return {'num_eti': lignes[0]['num_eti'], 'num_carton': num_carton, 'zpl': res.get('ZPL')}


    def _message_erreur_site(self, e, database, url):
        "Message lisible pour une erreur XML-RPC vers la base d'un site"
        if isinstance(e, xmlrpclib.Fault):
            #** Le faultString contient toute la trace : on ne garde que le
            #** message de la dernière exception (ex. 'ValueError: message')
            msg = e.faultString.strip()
            for ligne in msg.split('\n'):
                res = re.match(r'^[\w.]+: (.*)', ligne)
                if res:
                    msg = res.group(1).strip()
            return "Erreur dans la base %s : %s"%(database,msg.split('\n')[0])
        return "Base %s injoignable sur %s (%s)"%(database,url,e)


    def _get_site(self, database):
        "Connexion XML-RPC à la base d'un site"
        if not (database.port_server and database.database and database.password):
            raise ValidationError("Base du site %s non paramétrée (base, port et mot de passe obligatoires)"%database.name)
        #** Sans adresse IP, la base du site est sur le même serveur Odoo
        url = 'http://%s:%s/xmlrpc/object'%(database.ip_server or 'localhost',database.port_server)
        return {
            'database': database,
            'url'     : url,
            'sock'    : xmlrpclib.ServerProxy(url),
        }


    def _execute_site(self, site, model, method, *args):
        "Appel XML-RPC à la base d'un site, avec un message lisible en cas d'erreur"
        database = site['database']
        try:
            return site['sock'].execute(database.database, 2, database.password, model, method, *args)
        except (xmlrpclib.Fault, OSError) as e:
            raise ValidationError(self._message_erreur_site(e,database.database,site['url']))


    def _get_database_origine(self):
        "Base du site des étiquettes sélectionnées (elles doivent être d'une seule société)"
        sans_soc = self.filtered(lambda r: not r.soc)
        if sans_soc:
            raise ValidationError("Société non renseignée sur les étiquettes %s"%', '.join(str(x) for x in sans_soc.mapped('num_eti')))
        socs = sorted(set(self.mapped('soc')))
        if len(socs)!=1:
            raise ValidationError("Les étiquettes sélectionnées doivent être d'une seule société (trouvé : %s)"%', '.join(str(x) for x in socs))
        database = self.env['is.database'].search([('database','=like','%%-%s'%socs[0])], limit=1)
        if not database:
            raise ValidationError("Base du site de la société %s non trouvée"%socs[0])
        return database


    def _rechercher_article_site(self, site, obj):
        "Recherche de l'article (et de l'OF) de l'étiquette dans la base d'un site"
        product_id=production_id=False
        if obj.type_eti=='OF':
            rows = self._execute_site(site, 'mrp.production', 'search_read', [('name','=',obj.num_of)], ['product_id'], 0, 1)
            product_id    = rows and rows[0]['product_id'] and rows[0]['product_id'][0]
            production_id = rows and rows[0]['id']
        if obj.type_eti=='Commande':
            rows = self._execute_site(site, 'purchase.order.line', 'search_read', [('order_id.name','=',obj.num_of)], ['product_id'], 0, 1)
            product_id = rows and rows[0]['product_id'] and rows[0]['product_id'][0]
        if obj.type_eti=='CodePG':
            ids = self._execute_site(site, 'product.product', 'search', [('is_code','=',obj.num_of)], 0, 1)
            product_id = ids and ids[0]
        return product_id, production_id


    def copier_uc_vers_site_action(self, database_dest):
        """Copie les étiquettes sélectionnées dans les UC de la base du site de destination avec une nouvelle UM par article et lot.
        Si la destination n'est pas la société des étiquettes, l'article est recherché dans la base d'origine puis par son
        code PG dans la base de destination (comme une réception inter-site) et l'UC n'est pas liée à l'OF"""
        erreurs=[]
        groupes={}
        database_orig = self._get_database_origine()
        inter_site    = database_dest!=database_orig
        site      = self._get_site(database_dest)
        site_orig = inter_site and self._get_site(database_orig)
        DB        = database_dest.database
        ids = self._execute_site(site, 'stock.location', 'search', [('usage','=','customer')], 0, 1)
        if not ids:
            raise ValidationError("Aucun emplacement de type 'Client' dans %s"%DB)
        location_id = ids[0]

        #** Contrôles et regroupement par article et lot **********************
        for obj in self:
            try:
                #** L'UC ne doit pas déjà exister, même archivée **************
                domain=[('num_eti','=',obj.num_eti),('active','in',[True,False])]
                if self._execute_site(site, 'is.galia.base.uc', 'search', domain):
                    erreurs.append("Etiquette %s : UC déjà présente dans %s"%(obj.num_eti,DB))
                    continue

                #** Recherche de l'article ************************************
                if inter_site:
                    #** Article de la base d'origine retrouvé par son code PG
                    #** dans la base de destination, sans lien avec l'OF
                    production_id = False
                    product_id    = self._rechercher_article_site(site_orig, obj)[0]
                    if not product_id:
                        erreurs.append("Etiquette %s : article non trouvé dans %s (%s %s)"%(obj.num_eti,database_orig.database,obj.type_eti,obj.num_of))
                        continue
                    code_pg = self._execute_site(site_orig, 'product.product', 'read', [product_id], ['is_code'])[0]['is_code']
                    ids = self._execute_site(site, 'product.product', 'search', [('is_code','=',code_pg)], 0, 1)
                    product_id = ids and ids[0]
                    if not product_id:
                        erreurs.append("Etiquette %s : code PG %s non trouvé dans %s"%(obj.num_eti,code_pg,DB))
                        continue
                else:
                    product_id,production_id = self._rechercher_article_site(site, obj)
                    if not product_id:
                        erreurs.append("Etiquette %s : article non trouvé dans %s (%s %s)"%(obj.num_eti,DB,obj.type_eti,obj.num_of))
                        continue

                #** Recherche du lot dans la base du site *********************
                ids = self._execute_site(site, 'stock.lot', 'search', [('name','=',obj.num_of),('product_id','=',product_id)], 0, 1)
                lot_id = ids[0] if ids else False
            except ValidationError as e:
                erreurs.append("Etiquette %s : %s"%(obj.num_eti,e.args[0]))
                continue

            key=(product_id,obj.num_of,production_id,lot_id)
            groupes.setdefault(key, self.env['is.galia.base'])
            groupes[key]|=obj
        if erreurs:
            raise ValidationError("Aucune UC n'a été copiée :\n%s"%'\n'.join(erreurs))
        #**********************************************************************

        #** Création des UM et des UC dans la base du site ********************
        #** L'UM et ses UC sont créées en un seul appel pour ne pas laisser
        #** d'UM vide dans la base du site en cas d'erreur
        ums=[]
        origine = (inter_site and " (copie inter-site depuis %s)"%database_orig.database) or ''
        for (product_id,num_of,production_id,lot_id),objs in groupes.items():
            uc_ids=[]
            for obj in objs:
                vals={
                    'num_eti'      : obj.num_eti,
                    'type_eti'     : obj.type_eti,
                    'num_carton'   : obj.num_carton,
                    'qt_pieces'    : obj.qt_pieces,
                    'production'   : obj.num_of,
                    'production_id': production_id,
                    'lot_id'       : lot_id,
                    'product_id'   : product_id,
                    'date_creation': fields.Datetime.to_string(obj.date_creation),
                }
                uc_ids.append((0,0,vals))
            um_vals={
                'mixte'      : 'non',
                'location_id': location_id,
                'uc_ids'     : uc_ids,
            }
            try:
                um_id   = self._execute_site(site, 'is.galia.base.um', 'create', um_vals)
                um_name = self._execute_site(site, 'is.galia.base.um', 'read', [um_id], ['name'])[0]['name']
            except ValidationError as e:
                msg="Création UM pour %s UC (%s) : %s"%(len(objs),num_of,e.args[0])
                _logger.error("copier_uc_vers_site_action : %s"%msg)
                erreurs.append(msg)
                continue
            msg="UM %s créée dans %s avec %s UC (%s)%s"%(um_name,DB,len(objs),num_of,origine)
            _logger.info("copier_uc_vers_site_action : %s"%msg)
            ums.append(msg)
            for obj in objs:
                obj.message_post(body="UC copiée dans l'UM %s de la base %s%s"%(um_name,DB,origine))
        #**********************************************************************

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title'  : "Copie des UC dans la base du site",
                'message': '\n'.join(ums+erreurs),
                'type'   : (erreurs and 'danger') or 'success',
                'sticky' : True,
                'next'   : {'type': 'ir.actions.act_window_close'},
            },
        }
