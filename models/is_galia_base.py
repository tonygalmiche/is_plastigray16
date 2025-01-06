# -*- coding: utf-8 -*-
from odoo import models,fields,api  # type: ignore
from datetime import datetime
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

    num_eti       = fields.Integer(u"N°Étiquette", index=True)
    soc           = fields.Integer(u"Société"    , index=True)
    type_eti      = fields.Char(u"Type étiquette", index=True)
    num_of        = fields.Char(u"N°OF"          , index=True)
    num_carton    = fields.Integer(u"N°Carton"   , index=True)
    qt_pieces     = fields.Integer(u"Qt Pièces")
    date_creation = fields.Datetime(u"Date de création")
    login         = fields.Char(u"Login")

    def str2int(self,val):
        try:
            val=int(val)
        except:
            val=0
        return val

    def creer_etiquette(self, vals={}): #, vals={}):
        cr=self._cr
        if vals==[]:
            vals={}


        print(vals)

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
        Msg=""
        MsgOK=""
        CodePG=""
        if (zzValidation=="OK"):
            SQL=""
            # ** Requetes en fonction du type d'étiquette demandé *************
            if (Etiquette=="OF" or Etiquette=="CONTROLEES"):
                SQL="""SELECT 
                        pt.id                   as product_id,
                        pt.is_code              as code_pg, 
                        pt.name->>'fr_FR'                 as designation, 
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
                        pp.id                   as product_product_id
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
                        pt.name->>'fr_FR'                 as designation, 
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
                        pp.id                   as product_product_id
                    FROM product_product pp inner join product_template                 pt on pp.product_tmpl_id=pt.id
                                            inner join is_category                      ic on pt.is_category_id = ic.id
                                            inner join is_gestionnaire                  ig on pt.is_gestionnaire_id = ig.id
                                            left outer join is_type_etiquette          ite on pt.is_type_etiquette_id=ite.id
                    WHERE pt.is_code='%s'
                """%zzCode
            if (Etiquette=="Commande"):
                r = zzCode.split('/')
                NumCde = r[0]
                offset = int(r[1])/1-1
                if (offset<0):
                    offset=0
                SQL="""SELECT 
                        pt.id                   as product_id,
                        pt.is_code              as code_pg, 
                        pt.name->>'fr_FR'                 as designation, 
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
                        pp.id                   as product_product_id
                    FROM purchase_order po inner join purchase_order_line             pol on po.id=pol.order_id
                                            inner join product_product                  pp on pol.product_id=pp.id 
                                            inner join product_template                 pt on pp.product_tmpl_id=pt.id
                                            left outer join is_mold                     im on pt.is_mold_id=im.id
                                            inner join is_category                      ic on pt.is_category_id = ic.id
                                            inner join is_gestionnaire                  ig on pt.is_gestionnaire_id = ig.id
                                            left outer join is_type_etiquette          ite on pt.is_type_etiquette_id=ite.id
                    WHERE po.name='$NumCde' 
                    ORDER BY pol.id limit 1 offset $offset ";
                """
            company = self.env.user.company_id
            dbname='odoo16-%s'%Soc
            if company.is_postgres_host=='localhost':
                dbname='pg-odoo16-%s'%Soc
            try:
                cnx = psycopg2.connect("dbname='"+dbname+"' user='"+company.is_postgres_user+"' host='"+company.is_postgres_host+"' password='"+company.is_postgres_pwd+"'")
            except:
                cnx=False
                Msg+="La connexion à la base %s a échouée ! <br>\n"%dbname
            if Msg=="":
                cur = cnx.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute(SQL)
                rows = cur.fetchall()
                NbLig = len(rows)
                if NbLig==0:
                    Msg+="%s non trouvée! <br />"%Etiquette
                else:
                    row=rows[0]
                    if (row['aqp']=='t'):
                        AQP='AQP'
                    else:
                        AQP=''
                    CodePG       = row['code_pg']
                    Designation  = row['designation']
                    RefClient    = row['ref_client']
                    RefPlan      = row['ref_plan']
                    IndPlan      = row['ind_plan']
                    Moule        = row['moule']
                    Cat          = self.str2int(row['categorie'])
                    Gest         = row['gestionnaire']
                    GaucheDroite = row['droite_gauche']
                    LogoSecu     = row['logo_secu']
                    NumLot       = row['num_of']
                    PoidsBrut    = row['poids_brut']
                    PoidsNet     = row['poids_net']

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
                        Msg+="Type etiquette non trouvee! <br />"
                    TypeEti         = row['type_etiquette']
                    FormatEti       = row['format_etiquette']
                    Adresse         = row['adresse']
                    CodeFournisseur = row['code_fournisseur']
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
                    for row2 in rows2:
                        Fournisseur = row2['is_cofor']
                        CodeClient  = row2['code_client']
                        NomClient   = row2['nom_client']
                    #**********************************************************
                    if zzDebut<=0:
                        Msg+="Le numéro de la première étiquette doit-être supèrieur à 0 ! <br />"
                    if zzFin<zzDebut:
                        Msg+="Le numéro de la dernière étiquette doit-être supèrieur au numéro de la première ! <br />"
            if Msg=="":
                #** Test si la quantité modifiée ******************************
                if (zzNbPieces>0 and zzNbPieces!=Quantite):
                    if (zzMDP1!="quantite"):
                        Msg+="La quantité a été changée, la saisie du mot de passe est obligatoire ! <br />"
                    Quantite=zzNbPieces
                #**************************************************************

                #** Test si les étiquettes existent déja dans odoo0 ***********
                if zzMDP2!="reimp2023":
                    for Nb in range(zzDebut, zzFin+1):
                        SQL = """
                            SELECT * FROM is_galia_base
                            WHERE soc='%s' AND type_eti='%s' AND num_of='%s' AND num_carton='%s'
                        """%(Soc,Etiquette,zzCode,Nb)
                        cr.execute(SQL)
                        rows2=cr.dictfetchall()
                        for row2 in rows2:
                            Msg+="Etiquette %s - %s  déjà imprimée dans odoo0, la saisie du mot de passe est obligatoire !<br />"%(zzCode,Nb)
                            zzAction=""
                #**************************************************************
            if Msg!="":
                zzAction=""
            else:
                Action="Imprimer"
                if zzAction=="":
                    MsgOK="<div class=NomalNL>Cliquez sur OK pour lancer l'impression <div>"
            if zzAction=="Imprimer" and Msg=="":
                ZPL=""
                for Nb in range(zzDebut, zzFin+1):
                    Etiq=""

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
                    FN4  = "Q$Quantite"    # Code Barre Quantit?(Q)
                    FN6  = "V$Fournisseur" # Code Barre COFOR (V)
                    FN11 = "30S$FN10"      # Code Barre Ref Fournisseur (30S)
                    FN3  = Quantite        # Quantité dans le carton
                    FN5  = Fournisseur     # Fournisseur (V)

                    # ** Recherche si étiquette existe dans odoo0 *************
                    SQL = """
                        SELECT num_eti 
                        FROM is_galia_base 
                        WHERE soc='%s' AND type_eti='%s' AND num_of='%s' AND num_carton='%s' 
                    """%(Soc,Etiquette,zzCode,Nb)
                    cr.execute(SQL)
                    rows2=cr.dictfetchall()
                    num_eti = False
                    for row2 in rows2:
                        num_eti = row2['num_eti']
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
                    now = datetime.now()
                    if Etiquette!="CodePG":
                        FN12='D'+now.strftime('%Y%m%d') # Date du jour
                    FN13=NumLot
                    if TypeEti=="SLEEPBOX":
                        FN13="664"+now.strftime('%Y%V') # Semaine
                    if TypeEti=="NEA":
                        FN13="670"+now.strftime('%Y%V') # Semaine
                    if AQP=="AQP":
                        FN14="AQP";                     # AQP
                    if CodePG!=zzCode:
                        FN15="%s / %s / %s / %s"%(CodePG,Moule,zzCode,Nb) # Ligne informations générales pour PG
                    else:
                        FN15 = "%s / %s / %s"%(CodePG,Moule,Nb) 
                

                    FN99 = ""
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



                    # Création de l'étiquette *********************************
                    Etiq+="\n\r \n\r ##### Etiquette N%s #####\n\r"%Nb
                    if LogoSecu=="R" or LogoSecu=="S" or LogoSecu=="RS" or LogoSecu=="SR":
                        Etiq+="^XA^XFR:UC^FS \n\r"
                    if LogoSecu=="" or LogoSecu=="N" or LogoSecu=="UR":
                        Etiq+="^XA^IDR:SECU2.grf^FS \n\r"   # Efface le Logo Sécu de la mémoire
                        Etiq+="^XFR:UC^FS \n\r"

                    print('num_eti=', num_eti, FN7, Etiq)



        #             if ($TypeEti=="LOT" or $TypeEti=="DEVIALET") {
        #                 $FN23 = "H".substr($FN13,2,100);
        #             } else {
        #                 $FN23 = '';
        #             }

        #             //** Point de déchargement (PTDECH) ********************************
        #             $SQL="
        #                 SELECT so.is_point_dechargement
        #                 FROM sale_order_line sol inner join sale_order       so on sol.order_id=so.id
        #                                          inner join product_product  pp on sol.product_id=pp.id
        #                                          inner join product_template pt on pp.product_tmpl_id=pt.id
        #                 WHERE 
        #                     -- so.state='draft' and 
        #                     -- sol.state='draft' and 
        #                     so.is_point_dechargement is not null and
        #                     so.is_type_commande in ('ouverte', 'ls') and 
        #                     pt.is_code='$CodePG'
        #                 order by so.id desc
        #                 limit 1
        #             ";
        #             $result2 = pg_query($cnx, $SQL) or die ("$SQL \n -> ".pg_last_error($cnx)." \n");
        #             $FNPTDECH = "";
        #             while ($row2 = pg_fetch_array($result2)) {
        #                 $FNPTDECH = $row2['is_point_dechargement'];
        #             }
        #             //echo "FNPTDECH = $FNPTDECH $SQL\n";
        #             //******************************************************************

        #             $Etiq.="^FN1 ^FD$FN1^FS \n\r";   //N Produit (P)
        #             $Etiq.="^FN2 ^FD$FN2^FS \n\r";   //N Produit (Code à Barre)
        #             $Etiq.="^FN3 ^FD$FN3^FS \n\r";   //Quantité(Q)
        #             $Etiq.="^FN4 ^FD$FN4^FS \n\r";   //Quantité(Code à Barre)
        #             $Etiq.="^FN5 ^FD$FN5^FS \n\r";   //Ref Fournisseur (30S)
        #             $Etiq.="^FN6 ^FD$FN6^FS \n\r";   //Ref Fournisseur (Code à Barre)
        #             $Etiq.="^FN7 ^FD$FN7^FS \n\r";   //N Etiquette (S)
        #             $Etiq.="^FN8 ^FD$FN8^FS \n\r";   //N Etiquette (Code à Barre)
        #             $Etiq.="^FN9 ^FD$FN9^FS \n\r";   //Produit (Désignation Article)
        #             $Etiq.="^FN10^FD$FN10^FS \n\r";  //Fournisseur (V)
        #             $Etiq.="^FN11^FD$FN11^FS \n\r";  //Fournisseur (Code à Barre)
        #             $Etiq.="^FN12^FD$FN12^FS \n\r";  //Date
        #             $Etiq.="^FN13^FD$FN13^FS \n\r";  //N Lot (H)
        #             $Etiq.="^FN14^FD$FN14^FS \n\r";  
        #             $Etiq.="^FN15^FD$FN15^FS \n\r";  //Entete1 = Code PG + Moule + OF + N Carton + Controle Operateur/Regleur
        #             $Etiq.="^FN16^FD$FN16^FS \n\r";  //Adresse Complete Plastigray
        #             $Etiq.="^FN17^FD$FN17^FS \n\r";  //Indice modification
        #             $Etiq.="^FN18^FD$FN18^FS \n\r";  //Entete2
        #             $Etiq.="^FN20^FD".substr($FN20,0,23)."^FS \n\r";  //Entete4=Raisons Sociale Client
                    
        #             $Etiq.="^FNPTDECH^FD$FNPTDECH^FS \n\r";  //PTDECH : Point de déchargement
                    
        #             $Etiq.="^FN97^FD$FN97^FS \n\r";  //Made in France
        #             $Etiq.="^FN21^FD$FN21^FS \n\r";  //Poids Brut = Entete5
        #             $Etiq.="^FN24^FD$FN24^FS \n\r";  //Poids Net

        #             $Etiq.="^FN23^FD$FN23^FS \n\r";  //Code barre n° lot
        #             $Etiq.="^FN22^FD 1 ^FS \n\r";    //Nb de carton
        #             $Etiq.="^FN30^FD$FN30^FS \n\r";  //Entete5=Poids

        #             $FN40="PLASTIGRAY";
        #             if ($TypeEti=="TRETY") $FN40=$CodeFournisseur;
        #             if ($FormatEti=="DD")  $FN40=$CodeFournisseur;
        #             if ($FormatEti=="EMS") $FN40=$CodeFournisseur;
        #             if ($TypeEti=="EC")          $FN40=" ";
        #             if ($TypeEti=="BUBENDORFF")  $FN40=" ";

        #             $Etiq.="^FN40^FD$FN40^FS \n\r"; //Exp
        #             $Etiq.="^FN90^FD$FN90^FS \n\r"; //Signe R = Réglement?
        #             $Etiq.="^FN91^FD$FN91^FS \n\r"; //Signe S = Sécurité
        #             $Etiq.="^FN99^FD$FN99^FS \n\r"; // controle fréquentiel
        #             $Etiq.="^FN98^FD$FN98^FS \n\r"; // Code UR

        #             //** Data Matrix (QR Code) pour Delta Dore *************************
        #             if ($TypeEti=="DD" or $TypeEti=="EMS" or $TypeEti=="NEA") {
        #                 $Etiq.="
        #                     ^FO400,900
        #                     ^BXN,6,200
        #                     ^FD(P)$RefClient(2P)$IndPlan(Q)$Quantite(9D)".date("ymd")."(1T)$NumLot(K)(1P)$RefClient-PLASTIGRAY(A1)PLASTIGRAY(A2)(A3)^FS
        #                 ";
        #             }
        #             //******************************************************************

        #             //** Data Matrix (QR Code) pour DEVIALET ***************************
        #             if ($TypeEti=="DEVIALET") {
        #                 $CodeDevialet=$RefPlan;
        #                 $QRCode=$CodeDevialet.$NumLot;
        #                 $Etiq.="
        #                     ^FO425,800
        #                     ^BXN,12,200
        #                     ^FD$QRCode^FS
        #                 ";
        #             }
        #             //******************************************************************


        #             if ($Nb==$zzFin) {
        #                 $Etiq.="^MMT \n\r";     //Avance de l'éiquette
        #             }
        #             else {
        #                 $Etiq.="^MMR \n\r";         //Ne pas couper les Etiquettes
        #             }
        #             $Etiq.="^XZ \n\r";

        #             //** Enregistrement Etiquette dans Odoo ****************************
        #             $msg="";
        #             $Info=$zzCode." - ".$Nb." - ".$FN7;
        #             if ($num_eti==False) {
        #                 $BDateCreation=date("Y-m-d H:i:s",mktime());
        #                 $SQL="INSERT INTO is_galia_base (num_eti, soc, type_eti, num_of, num_carton, qt_pieces, date_creation, login)
        #                        VALUES ('".utf8_decode($FN7)."',
        #                                '".utf8_decode($Soc)."',
        #                                '".utf8_decode($Etiquette)."',
        #                                '".utf8_decode($zzCode)."',
        #                                '".utf8_decode($Nb)."',
        #                                '".utf8_decode($FN3)."',
        #                                '".localdate2utc($BDateCreation)."',
        #                                '".utf8_decode($name)."') ";
        #                 $result2 = pg_query($cnx0, $SQL);
        #                 if ($result2==False) {
        #                     echo "<div class=MsgErr>Etiquette $Info non enregistrée => Impression abandonnée à partir de cette étiquette !</div>";
        #                     break;
        #                 }
        #             } else {
        #                 $SQL="UPDATE is_galia_base set write_date=now() at time zone 'UTC', qt_pieces=$FN3 WHERE num_eti=$num_eti";
        #                 $result2 = pg_query($cnx0, $SQL);
        #                 if ($result2==False) {
        #                     echo "<div class=MsgErr>Etiquette $Info non enregistrée => Impression abandonnée à partir de cette étiquette !</div>";
        #                     break;
        #                 }
        #             }
        #             echo "<div class=NormalLB>Impression et enregistrement étiquette $Info dans odoo0 éffectué avec succés.</div>";
        #             //******************************************************************

        #             $ZPL.=$Etiq;
        #         }


        #         //** Impression ********************************************************
        #         if ($Imprimante=="ZPL"){
        #             $filename="code-zpl-$zzCode.txt";
        #             $path="/var/www/odoo/odoo-erp/planning/PDF/$filename";
        #             if ($TypeEti=="C40"){
        #                 `cat UC-C40.zpl>$path`;
        #             }else{
        #                 `cat Uc2.zpl>$path`;
        #             }
        #             `cat Secu.grf>>$path`;
        #             `echo "$ZPL">>$path`;
        #             echo "<a class=\"NormalLN\" style=\"color:red;font-size:12pt\" href=\"./PDF/$filename\" download>Code ZPL</a><br />\n";
        #         } else {
        #             if ($TypeEti=="C40"){
        #                 `cat UC-C40.zpl   | lpr -P $Imprimante`;
        #             }else{
        #                 `cat Uc2.zpl   | lpr -P $Imprimante`;
        #             }
        #             `cat Secu.grf  | lpr -P $Imprimante`;
        #             `echo "$ZPL"  | lpr -P $Imprimante`;
        #         }
        #         //**********************************************************************


        #         $Action="";
        #         $Quantite="";
        #         $zzMDP1="";
        #         $zzMDP2="";
        #         unlink($lockpath); 
        #     }
        # }


        res={
            'Msg'   : Msg,
            'MsgOK' : MsgOK,
            'Action': Action,
        }

        print('res=',res)

        return res













class is_galia_base_um(models.Model):
    _name='is.galia.base.um'
    _description="Etiquettes Galia UM"
    _order='name desc'
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

    name             = fields.Char("N°Étiquette UM", readonly=True             , index=True)
    mixte            = fields.Selection(_MIXTE, "UM mixte", default='non', required=True)
    liste_servir_id  = fields.Many2one('is.liste.servir', 'Liste à servir'     , index=True)
    bon_transfert_id = fields.Many2one('is.bon.transfert', 'Bon de transfert'  , index=True)
    production_id    = fields.Many2one('mrp.production', 'Ordre de fabrication', index=True)
    location_id      = fields.Many2one('stock.location', 'Emplacement'         , index=True, domain=[("usage","=","internal")], default=lambda self: self._get_location_id())
    uc_ids           = fields.One2many('is.galia.base.uc'  , 'um_id', "UCs")
    product_id       = fields.Many2one('product.product', 'Article', readonly=True, compute='_compute', store=False)
    qt_pieces        = fields.Integer("Qt Pièces"                 , readonly=True, compute='_compute', store=False)
    employee_id      = fields.Many2one("hr.employee", "Employé")
    date_fin         = fields.Datetime("Date fin UM")
    active           = fields.Boolean("Active", default=True, copy=False, index=True)
    date_ctrl_rcp    = fields.Datetime("Date contrôle réception")


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
                _logger.info(x)
                lines=os.popen(x).readlines()
                for line in lines:
                    _logger.info(line.strip())
 

class is_galia_base_uc(models.Model):
    _name='is.galia.base.uc'
    _description="Etiquettes Galia UC"
    _order='num_eti desc'
    _rec_name='num_eti'
    _sql_constraints = [('num_eti_uniq','UNIQUE(num_eti,um_id)', u'Cette étiquette existe déjà dans cette UM')]

    um_id         = fields.Many2one('is.galia.base.um', 'UM', required=True, ondelete='cascade')
    um_mixte      = fields.Selection(related="um_id.mixte")
    um_active     = fields.Boolean(related="um_id.active")
    num_eti       = fields.Integer("N°Étiquette UC", required=True, index=True)
    type_eti      = fields.Char("Type étiquette", required=True   , index=True)
    num_carton    = fields.Integer("N°Carton", required=True      , index=True)
    qt_pieces     = fields.Integer("Qt Pièces", required=True)
    date_creation = fields.Datetime("Date de création", required=True)
    production_id = fields.Many2one('mrp.production', 'Ordre de fabrication')
    production    = fields.Char('Fabrication')
    product_id    = fields.Many2one('product.product', 'Article', required=True , index=True)
    employee_id   = fields.Many2one("hr.employee", "Employé")
    liste_servir_id   = fields.Many2one('is.liste.servir' , 'Liste à servir'  , related='um_id.liste_servir_id')
    bon_transfert_id  = fields.Many2one('is.bon.transfert', 'Bon de transfert', related='um_id.bon_transfert_id')
    ls_line_id        = fields.Many2one('is.liste.servir.line' , 'Ligne liste à servir')
    bt_line_id        = fields.Many2one('is.bon.transfert.line', 'Ligne bon de transfert')
    stock_move_id     = fields.Many2one('stock.move', 'Ligne livraison')
    stock_move_rcp_id = fields.Many2one('stock.move', 'Ligne réception')
    reception_inter_site_id = fields.Many2one('is.reception.inter.site', 'Réception inter-site')


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

