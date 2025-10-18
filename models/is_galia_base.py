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
                for row in rows:
                    point_dechargement = row['is_point_dechargement']
                    code_routage       = row['is_code_routage']
                    point_destination  = row['is_point_destination']
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
                        ite.name                as type_etiquette,
                        ite.format_etiquette    as format_etiquette,
                        ite.adresse             as adresse,
                        ite.code_fournisseur    as code_fournisseur,
                        mp.name                 as num_of,
                        pp.id                   as product_product_id,
                        pt.is_code_fabrication  as is_code_fabrication
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
                        ite.name                as type_etiquette,
                        ite.format_etiquette    as format_etiquette,
                        ite.adresse             as adresse,
                        ite.code_fournisseur    as code_fournisseur,
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
                        pt.id                   as product_id,
                        pt.is_code              as code_pg, 
                        pt.name->>'fr_FR'       as designation, 
                        pt.is_ref_client        as ref_client,
                        pt.is_ref_plan          as ref_plan,
                        pt.is_ind_plan          as ind_plan,
                        pt.weight               as poids_brut,
                        pt.weight_net           as poids_net,
                        im.name                 as moule, 
                        ic.name                 as categorie,
                        ig.name                 as gestionnaire,
                        pt.is_livree_aqp        as aqp,
                        pt.is_droite_grauche    as droite_gauche,
                        pt.is_soumise_regl      as logo_secu,
                        ite.name                as type_etiquette,
                        ite.format_etiquette    as format_etiquette,
                        ite.adresse             as adresse,
                        ite.code_fournisseur    as code_fournisseur,
                        po.name                 as num_of,
                        pp.id                   as product_product_id,
                        pt.is_code_fabrication  as is_code_fabrication
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
                    if (row['aqp']=='t'):
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
                    TypeEti         = row['type_etiquette'] or ''
                    FormatEti       = row['format_etiquette'] or ''
                    Adresse         = row['adresse'] or ''
                    CodeFournisseur = row['code_fournisseur'] or ''
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


    def imprimer_zpl(self,ZPL):
        user=self.env['res.users'].browse(self._uid)
        imprimante=user.is_zebra_id.name or user.company_id.is_zebra_id.name
        if not imprimante:
            raise ValidationError('Imprimante Zebra non définie !')
        if imprimante and ZPL!='':
            cmd = 'echo "'+ZPL+'" | lpr -P'+imprimante
            p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
            stdout, stderr = p.communicate()
            if stderr:
                msg="Impossible d'imprimer sur %s !\n%s"%(imprimante,stderr.decode("utf-8"))
                raise ValidationError(msg)
            msg='Envoi code ZPL sur imprimante %s'%imprimante
            _logger.info(msg)


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
    production    = fields.Char('Fabrication', tracking=True)
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
    active                  = fields.Boolean("Actif", default=True, tracking=True)


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
