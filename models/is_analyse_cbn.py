# -*- coding: utf-8 -*-
from odoo import models,fields,api
#import time
from datetime import datetime, timedelta
import json 
#from collections import OrderedDict
#import tempfile


class product_product(models.Model):
    _inherit = "product.product"

    def get_analyse_cbn(self, 
            ok=False,
            code_pg=False, 
            gest=False, 
            cat=False, 
            moule=False, 
            projet=False, 
            client=False, 
            fournisseur=False, 
            semaines=False, 
            type_cde=False, 
            type_rapport=False, 
            calage=False, 
            valorisation=False,
            product_id=False,
    ):
        cr = self._cr
        if ok:
            self.env['is.mem.var'].set(self._uid, 'analyse_cbn_code_pg'     , code_pg)
            self.env['is.mem.var'].set(self._uid, 'analyse_cbn_gest'        , gest)
            self.env['is.mem.var'].set(self._uid, 'analyse_cbn_cat'         , cat)
            self.env['is.mem.var'].set(self._uid, 'analyse_cbn_moule'       , moule)
            self.env['is.mem.var'].set(self._uid, 'analyse_cbn_projet'      , projet)
            self.env['is.mem.var'].set(self._uid, 'analyse_cbn_client'      , client)
            self.env['is.mem.var'].set(self._uid, 'analyse_cbn_fournisseur' , fournisseur)
            self.env['is.mem.var'].set(self._uid, 'analyse_cbn_semaines'    , semaines)
            self.env['is.mem.var'].set(self._uid, 'analyse_cbn_type_cde'    , type_cde)
            self.env['is.mem.var'].set(self._uid, 'analyse_cbn_type_rapport', type_rapport)
            self.env['is.mem.var'].set(self._uid, 'analyse_cbn_calage'      , calage)
            self.env['is.mem.var'].set(self._uid, 'analyse_cbn_valorisation', valorisation)
        else:
            code_pg      = self.env['is.mem.var'].get(self._uid, 'analyse_cbn_code_pg')
            gest         = self.env['is.mem.var'].get(self._uid, 'analyse_cbn_gest')
            cat          = self.env['is.mem.var'].get(self._uid, 'analyse_cbn_cat')
            moule        = self.env['is.mem.var'].get(self._uid, 'analyse_cbn_moule')
            projet       = self.env['is.mem.var'].get(self._uid, 'analyse_cbn_projet')
            client       = self.env['is.mem.var'].get(self._uid, 'analyse_cbn_client')
            fournisseur  = self.env['is.mem.var'].get(self._uid, 'analyse_cbn_fournisseur')
            semaines     = self.env['is.mem.var'].get(self._uid, 'analyse_cbn_semaines')
            type_cde     = self.env['is.mem.var'].get(self._uid, 'analyse_cbn_type_cde')
            type_rapport = self.env['is.mem.var'].get(self._uid, 'analyse_cbn_type_rapport')
            calage       = self.env['is.mem.var'].get(self._uid, 'analyse_cbn_calage')
            valorisation = self.env['is.mem.var'].get(self._uid, 'analyse_cbn_valorisation')


        semaines = int(semaines)


        # #** Requête ***********************************************************
        # SQL="""
        #     select 
        #         pp.id,
        #         pp.product_tmpl_id,
        #         pt.is_code,
        #         pt.name->>'fr_FR' designation
        #     from product_product pp join product_template pt on pp.product_tmpl_id=pt.id 
        #     where pt.is_code like '%s%%' limit 50
        # """%(code_pg)
        # cr.execute(SQL)
        # result = cr.dictfetchall()
        # lig=0
        # key=""
        # lines={}
        # trcolor=""
        # for row in result:
        #     if key!=row['is_code']:
        #         key=row['is_code']

        #         if trcolor=="#ffffff":
        #             trcolor="#f2f3f4"
        #         else:
        #             trcolor="#ffffff"
        #         trstyle="background-color:%s"%(trcolor)

        #         vals={
        #             "key"        : key,
        #             "product_tmpl_id": row["product_tmpl_id"],
        #             "trstyle"    : trstyle,
        #             "trstyle"    : trstyle,
        #             "is_code"    : row["is_code"],
        #             "designation": row["designation"],
        #         }
        #         lines[key]=vals
        #         lig+=1
        # #**********************************************************************




        # ** Filtre pour les requêtes ******************************************
        filtre=""
        if product_id:
            filtre=filtre+" and pp.id="+str(product_id)+" "

        if code_pg:
            filtre=filtre+" and pt.is_code ilike '"+code_pg+"%' "
        if type_rapport=="Achat":
            filtre=filtre+" and pt.purchase_ok=true "
        else:
            filtre=filtre+" and pt.purchase_ok<>true "
        if cat:
            filtre=filtre+" and ic.name='"+cat+"' "
        if moule:
            moules = moule.split(',')
            res=[]
            for m in moules:
                res.append("'"+str(m)+"'")
            moules=",".join(res)
            moules='('+moules+')'
            filtre=filtre+" and (im.name in "+moules+" or id.name in "+moules+" )"
        if projet:
            filtre=filtre+" and (imp1.name ilike '%"+projet+"%' or imp2.name ilike '%"+projet+"%') "
        if client:
            filtre=filtre+" and rp.is_code='"+client+"' "
        # **********************************************************************

        titre              = self._get_titre(type_rapport,valorisation)
        cat2id             = self._get_cat2id()                          # Catégories
        Couts              = self._get_Couts()                           # Coûts
        TypeCde            = self._get_TypeCde(type_rapport)             # Type de commande d'achat
        select_gest        = self._get_select_gest(filtre,fournisseur)   # Liste des gestionnaires
        select_fournisseur = self._get_select_fournisseur(filtre,gest)   # Liste des fournisseurs

        #Liste de choix *******************************************************
        options = select_gest
        gest_options=[]
        for o in options:
            selected=False
            if o==gest:
                selected=True
            gest_options.append({
                "id": o,
                "name": o,
                "selected": selected,
            })
        options = select_fournisseur
        fournisseur_options=[]
        for o in options:
            selected=False
            if o==fournisseur:
                selected=True
            fournisseur_options.append({
                "id": o,
                "name": o,
                "selected": selected,
            })
        options = [4,8,12,16,18,20,25,30,40,60]
        semaines_options=[]
        for o in options:
            selected=False
            if o==int(semaines):
                selected=True
            semaines_options.append({
                "id": o,
                "name": o,
                "selected": selected,
            })
        options = ['','ferme_uniquement','ferme','ouverte','cadencée']
        type_cde_options=[]
        for o in options:
            selected=False
            if o==type_cde:
                selected=True
            type_cde_options.append({
                "id": o,
                "name": o,
                "selected": selected,
            })
        options = ["Achat", "Fabrication"]
        type_rapport_options=[]
        for o in options:
            selected=False
            if o==type_rapport:
                selected=True
            type_rapport_options.append({
                "id": o,
                "name": o,
                "selected": selected,
            })
        options = ["Date de fin", "Date de début"]
        calage_options=[]
        for o in options:
            selected=False
            if o==calage:
                selected=True
            calage_options.append({
                "id": o,
                "name": o,
                "selected": selected,
            })
        options = ["Non", "Oui"]
        valorisation_options=[]
        for o in options:
            selected=False
            if o==valorisation:
                selected=True
            valorisation_options.append({
                "id": o,
                "name": o,
                "selected": selected,
            })
        # **********************************************************************



        # ** Filtre sur le fournisseur (partner_id) ****************************
        partner_id=False
        if fournisseur:
            tab=fournisseur.split('-')
            SQL="select id from res_partner where is_code='"+tab[0]+"' and is_adr_code='"+tab[1]+"' "
            cr.execute(SQL)
            result = cr.fetchall()
            for row in result:
                partner_id=row[0]
        if gest:
            filtre=filtre+" and ig.name='"+gest+"' "
        if partner_id:
            filtre=filtre+""" 
                and (
                        (   select rp2.id from product_supplierinfo ps inner join res_partner rp2 on ps.partner_id=rp2.id   
                            where ps.product_tmpl_id=pt.id order by ps.sequence limit 1
                        )="""+str(partner_id)+"""
                    )
            """
        filtre=filtre+" AND ic.name!='80' "
        # **********************************************************************

        TabSemaines = self._get_TabSemaines(semaines)    # Tableau des semaines
        StocksA     = self._get_Stocks('f')              # StocksA (control_quality=f)
        StocksQ     = self._get_Stocks('t')              # StocksQ (control_quality=t)
        StocksSecu  = self._get_StocksSecu()             # StocksSecu
        Fournisseurs, Delai_Fournisseurs = self._get_Fournisseurs_Delai_Fournisseurs() # Fournisseurs + Delai_Fournisseurs



        # ** Recherche des Prévisions du CBN  ******************************
        TabIni={}
        result1 = self._get_FS_SA(filtre)
        TabIni=self.RemplitTab2(TabIni, result1, TabSemaines, type_rapport, 
            StocksA, StocksQ, StocksSecu, Fournisseurs, Delai_Fournisseurs, 
            calage, valorisation, Couts, fournisseur, TypeCde, type_cde)
        # ******************************************************************

        # ** Recherche des commandes client ********************************
        result2 = self._get_CF_CP(filtre)
        TabIni=self.RemplitTab2(TabIni, result2, TabSemaines, type_rapport, 
            StocksA, StocksQ, StocksSecu, Fournisseurs, Delai_Fournisseurs, 
            calage, valorisation, Couts, fournisseur, TypeCde, type_cde)
        # ******************************************************************

        # ** Recherche des OF **********************************************
        result3 = self._get_FL(filtre)
        TabIni=self.RemplitTab2(TabIni, result3, TabSemaines, type_rapport, 
            StocksA, StocksQ, StocksSecu, Fournisseurs, Delai_Fournisseurs, 
            calage, valorisation, Couts, fournisseur, TypeCde, type_cde)
        # ******************************************************************

        # ** Recherche des composants des OF *******************************
        result4 = self._get_FM(filtre)
        TabIni=self.RemplitTab2(TabIni, result4, TabSemaines, type_rapport, 
            StocksA, StocksQ, StocksSecu, Fournisseurs, Delai_Fournisseurs, 
            calage, valorisation, Couts, fournisseur, TypeCde, type_cde)
        # ******************************************************************

        # ** Recherche des commandes fournisseurs  *************************
        result5 = self._get_SF(filtre)
        TabIni=self.RemplitTab2(TabIni, result5, TabSemaines, type_rapport, 
            StocksA, StocksQ, StocksSecu, Fournisseurs, Delai_Fournisseurs, 
            calage, valorisation, Couts, fournisseur, TypeCde, type_cde)
        # ******************************************************************

        # ** Recherche pour avoir tous les articles dans le résultat  ******
        if valorisation:
            result6 = self._get_stock(filtre)
            TabIni=self.RemplitTab2(TabIni, result6, TabSemaines, type_rapport, 
                StocksA, StocksQ, StocksSecu, Fournisseurs, Delai_Fournisseurs, 
                calage, valorisation, Couts, fournisseur, TypeCde, type_cde)
        # ******************************************************************


        result = result1+result2+result3+result4+result5
        res={}
        for row in result:
            key = row["code_pg"]
            if key not in res:
                res[key] = {
                    "key": key,
                    "product_id" : row["product_id"],
                    "code_pg"    : row["code_pg"],
                    "designation": row["designation"],
                    "typeod"     : {},
                }

            key2=row["typeod"]
            if key2 not in res[key]["typeod"]:
                res[key]["typeod"][key2] = {
                    "key"   : key2,
                    "typeod": row["typeod"],
                    "cols"  : {}
                }
                for d in TabSemaines:
                    res[key]["typeod"][key2]["cols"][d]={
                        "key"   : d,
                        "qt"    : 0,
                        "qttxt" : "",
                    }

            res[key]["typeodlist"] = list(res[key]["typeod"].values())
            res[key]["rowspan"] = len(res[key]["typeodlist"])






            if calage=='' or calage=='Date de fin':
                DateLundi=self.datelundi(row["date_fin"], TabSemaines)
            else:
                DateLundi=self.datelundi(row["date_fin"], TabSemaines)
            
            if DateLundi:
                print(DateLundi)
                if DateLundi in TabSemaines:
                    qt = res[key]["typeod"][key2]["cols"][DateLundi]["qt"]+row["qt"]
                    res[key]["typeod"][key2]["cols"][DateLundi]["qt"]= qt
                    if qt>0:
                        qttxt = int(qt)
                        res[key]["typeod"][key2]["cols"][DateLundi]["qttxt"] = qttxt
                    print(DateLundi, row["qt"])



            res[key]["typeod"][key2]["colslist"] = list(res[key]["typeod"][key2]["cols"].values())


            # if row["qt"]>0:
            #    print(DateLundi, row["qt"])



                # if typeod=='FL' and qt<0:
                #     qt=-0.01

                # qt = qt or 0 #NoneType

                # # if DateLundi not in Tab[Cle]:
                # #    Tab[Cle][DateLundi]=0
                # # Tab[Cle][DateLundi]=Tab[Cle][DateLundi]+round(Sens*qt,2);





        #print(json.dumps(res, indent = 4))

                # mp.id as numod, 
                # mp.start_date as date_debut, 
                # mp.start_date_cq as date_fin, 
                # mp.quantity as qt, 
                # mp.type as typeod, 
                # mp.product_id,
                # pt.is_code as code_pg, 
                # pt.name->>'fr_FR' designation,
                # pt.is_stock_secu, 
                # pt.produce_delay, 
                # pt.lot_mini, 
                # pt.multiple,
                # pt.is_mold_dossierf as moule,
                # mp.name as name,
                # ig.name as gest





        # print(TabIni)
        # lig=1
        # nb=len(TabIni)
        # for line in TabIni:
        #     print(lig,'/',nb,line, TabIni[line])
        #     lig+=1


        # #** RemplitTab2Sho *************************************************
        # TabSho={}
        # lig=0
        # Tab=TabIni
        # #for key, val in Tab.iteritems():
        # for key, val in Tab.items():
        #     Type=Tab[key]['TypeOD']
        #     if Type!='99-Stock':
        #         color=self.color_cel(Type)
        #         if 0 not in TabSho:
        #             TabSho[0]={}
        #         if 1 not in TabSho:
        #             TabSho[1]={}
        #         TabSho[0][lig]=Tab[key]["Code"]
        #         TabSho[1][lig]=Type
        #         Type=Type[3:]
        #         for i in range(0, semaines):
        #             k=TabSemaines[i]
        #             if k in Tab[key]:
        #                 Qt=round(Tab[key][k],2)
        #             else:
        #                 Qt=0
        #             Lien="#"
        #             k=TabSemaines[i]+'OT'
        #             if k in Tab[key]:
        #                 OT=Tab[key][k]
        #                 OT=OT[0:len(OT)-1]
        #             else:
        #                 OT=''
        #             k=TabSemaines[i]+'INFO'
        #             if k in Tab[key]:
        #                 INFO=Tab[key][k]
        #             else:
        #                 INFO=''
        #             docid=''
        #             if Type=='FS' or Type=='SA' or Type=='CF' or Type=='CP' or Type=='FL' or Type=='SF':
        #                 Lien="Modif_FS_Liste.php?zzTypeOD="+Type.lower()+"&zzNumOD="+str(OT)
        #                 docid=str(OT)
        #             k=i+2
        #             if k not in TabSho:
        #                 TabSho[k]={}

        #             if Qt==0 and color!='Black':
        #                 val=''
        #             else:
        #                 val="{0:10.0f}".format(Qt)
        #             TabSho[k][lig]="<a style=\"color:"+color+";\" class=\"info\" type='"+Type+"' docid='"+str(docid)+"'>"+val+"<span>"+INFO+"</span></a>"

        #             #** Calcul du stock theorique **************************
        #             if Tab[key]['TypeOD']=='90-Stock':
        #                 if i==0:
        #                     Stock=Tab[key][0]+Qt
        #                 else:
        #                     q=TabSho[1+i][lig]
        #                     Stock=TabSho[1+i][lig]+Qt
        #                 TabSho[2+i][lig]=Stock

        #             #*******************************************************

        #             #** Calcul du stock valorisé ***************************
        #             if Tab[key]['TypeOD']=='92-Stock Valorisé':
        #                 if i==0:
        #                     Stock=Tab[key][0]+Qt;
        #                 else:
        #                     Stock=TabSho[1+i][lig]+Qt;
        #                 TabSho[2+i][lig]=round(Stock,2)
        #             #*******************************************************
        #         lig+=1
        # Tab=TabSho
        # # ******************************************************************


        # lig=1
        # nb=len(Tab)
        # for line in Tab:
        #     print(lig,'/',nb,line, Tab[line])
        #     lig+=1












        #** Titres des colonnes ***********************************************
        now = datetime.now()
        DateCol = now - timedelta(days=now.weekday())
        date_cols=[]
        for o in range(0,int(semaines)):
            date_cols.append({
                "key": o,
                "semaine": DateCol.strftime("S%W"),
                "date": DateCol.strftime("%d.%m"),
            })
            DateCol = DateCol + timedelta(days=7)
        #**********************************************************************



        #** Ajout de la couleur des lignes ************************************
        sorted_dict = dict(sorted(TabIni.items())) 
        trcolor=""
        for k in sorted_dict:
            if trcolor=="#ffffff":
                trcolor="#f2f3f4"
            else:
                trcolor="#ffffff"
            trstyle="background-color:%s"%(trcolor)
            sorted_dict[k]["trstyle"] = trstyle
        lines = list(sorted_dict.values())
        #**********************************************************************


        #** Ajout de la couleur des lignes (newlines) *************************
        sorted_dict = dict(sorted(res.items())) 
        trcolor=""
        for k in sorted_dict:
            if trcolor=="#ffffff":
                trcolor="#f2f3f4"
            else:
                trcolor="#ffffff"
            trstyle="background-color:%s"%(trcolor)
            sorted_dict[k]["trstyle"] = trstyle
        newlines = list(sorted_dict.values())
        #**********************************************************************


        print(date_cols)

        res={
            "titre"       : titre,
            "newlines"    : newlines,
            "lines"       : lines,
            "date_cols"   : date_cols,
            "code_pg"     : code_pg,
            "gest"        : gest,
            "cat"         : cat,
            "moule"       : moule,
            "projet"      : projet,
            "client"      : client,
            "fournisseur" : fournisseur,
            "semaines"    : semaines,
            "type_cde"    : type_cde,
            "type_rapport": type_rapport,
            "calage"      : calage,
            "valorisation": valorisation,
            "gest_options"        : gest_options,
            "fournisseur_options" : fournisseur_options,
            "semaines_options"    : semaines_options,
            "type_cde_options"    : type_cde_options,
            "type_rapport_options": type_rapport_options,
            "calage_options"      : calage_options,
            "valorisation_options": valorisation_options,
        }
        return res


    def _get_titre(self,type_rapport,valorisation):
        titre="Suggestions de fabrication"
        if type_rapport=="Achat":
            titre="Suggestions d'achat"
        if valorisation=="Oui":
            titre="Valorisation stock fabrication"
            if type_rapport=="Achat":
                titre="Valorisation stock achat"
        return titre


    def _get_cat2id(self):
        cr = self._cr
        SQL="""
            select id, name
            from is_category 
            where id>0
        """
        cr.execute(SQL)
        result = cr.fetchall()
        cat2id={}
        for row in result:
            cat2id[row[1]]=row[0]
        return cat2id


    def _get_Couts(self):
        cr = self._cr
        SQL="""
            select name, cout_act_total
            from is_cout 
        """
        cr.execute(SQL)
        result = cr.fetchall()
        Couts={}
        for row in result:
            Couts[row[0]]=row[1]
        return Couts


    def _get_TypeCde(self,type_rapport):
        cr = self._cr
        TypeCde={}
        if type_rapport=="Achat":
            SQL="""
                SELECT 
                    cof.type_commande, 
                    cof.partner_id, 
                    rp.is_code, 
                    rp.is_adr_code, 
                    cofp.product_id
                FROM is_cde_ouverte_fournisseur cof inner join is_cde_ouverte_fournisseur_product cofp on cofp.order_id=cof.id
                                                    inner join res_partner rp on cof.partner_id=rp.id
            """
            cr.execute(SQL)
            result = cr.fetchall()
            for row in result:
                cle=('0000'+row[2])[-4:]+'-'+row[3]+'/'+str(row[4])
                TypeCde[cle]=row[0]
            SQL="""
                SELECT 
                    rp.is_code, 
                    rp.is_adr_code, 
                    product_id
                FROM is_cde_ferme_cadencee cfc inner join res_partner rp on cfc.partner_id=rp.id
            """
            cr.execute(SQL)
            result = cr.fetchall()
            for row in result:
                cle=('0000'+row[0])[-4:]+'-'+row[1]+'/'+str(row[2])
                TypeCde[cle]=u'cadencée'
        return TypeCde


    def _get_select_gest(self,filtre,fournisseur):
        cr = self._cr
        SQL="""
            SELECT distinct ig.name gest
            FROM product_product pp inner join product_template      pt   on pp.product_tmpl_id=pt.id

                                    left outer join is_mold          im   on pt.is_mold_id=im.id
                                    left outer join is_dossierf      id   on pt.is_dossierf_id=id.id
                                    inner join      is_gestionnaire  ig   on pt.is_gestionnaire_id=ig.id
                                    left outer join is_category      ic   on pt.is_category_id=ic.id
                                    left outer join is_mold_project  imp1 on im.project=imp1.id
                                    left outer join is_mold_project  imp2 on id.project=imp2.id
                                    left outer join res_partner      rp   on pt.is_client_id=rp.id
            WHERE pp.id>0 """+filtre+"""
        """
        if fournisseur:
            code=fournisseur.split('-')[0]
            SQL=SQL+""" 
                and (
                    (
                        select rp2.is_code 
                        from product_supplierinfo ps inner join res_partner rp2 on ps.partner_id=rp2.id   
                        where ps.product_tmpl_id=pt.id order by ps.sequence,ps.id limit 1
                    )='"""+code+"""'
                )

            """
        SQL=SQL+""" ORDER BY ig.name """
        cr.execute(SQL)
        result = cr.fetchall()
        SelectGestionnaires={}
        for row in result:
            SelectGestionnaires[row[0]]=1
        #SelectGestionnaires=OrderedDict(sorted(SelectGestionnaires.items(), key=lambda t: t[0]))

        select_gest=[]
        select_gest.append('')
        for x in SelectGestionnaires:
            select_gest.append(x)
        return select_gest


    def _get_select_fournisseur(self,filtre,gest=False):
        cr = self._cr
        if gest:
            filtre=filtre+" and ig.name='"+gest+"' "

        #** Recherche des articles ayant des données ***************************
        #debut=datetime.datetime.now()
        #_logger.info('Début')
        #_logger.info('Fin '+_now(debut))
        r1=self._get_FS_SA(filtre)
        r2=self._get_CF_CP(filtre)
        r3=self._get_FL(filtre)
        r4=self._get_FM(filtre)
        r5=self._get_SF(filtre)
        product_ids=[]
        for row in (r1+r2+r3+r4+r5):
            product_id=str(row["product_id"])
            if product_id not in product_ids:
                product_ids.append(product_id)
        #_logger.info('Fin '+_now(debut))
        #***********************************************************************

        SQL="""
            SELECT 
                (   select concat(rp2.is_code,'-',rp2.is_adr_code)
                    from product_supplierinfo ps inner join res_partner rp2 on ps.partner_id=rp2.id   
                    where ps.product_tmpl_id=pt.id order by ps.sequence,ps.id limit 1
                ) code_fournisseur

            FROM product_product pp inner join product_template      pt   on pp.product_tmpl_id=pt.id
                                    left outer join is_mold          im   on pt.is_mold_id=im.id
                                    left outer join is_dossierf      id   on pt.is_dossierf_id=id.id
                                    inner join      is_gestionnaire  ig   on pt.is_gestionnaire_id=ig.id
                                    left outer join is_category      ic   on pt.is_category_id=ic.id
                                    left outer join is_mold_project  imp1 on im.project=imp1.id
                                    left outer join is_mold_project  imp2 on id.project=imp2.id
                                    left outer join res_partner      rp   on pt.is_client_id=rp.id
          WHERE pp.id>0 """+filtre+"""
        """
        if len(product_ids):
            SQL=SQL+" AND pp.id in ("+','.join(product_ids)+") "
        cr.execute(SQL)
        result = cr.fetchall()
        select_fournisseur=[]
        select_fournisseur.append('')
        for row in result:
            cle=row[0]
            if cle and cle not in select_fournisseur:
                select_fournisseur.append(cle)
        select_fournisseur.sort()
        return select_fournisseur








    def _get_FS_SA(self,filtre):
        cr = self._cr
        SQL="""
            SELECT 
                mp.id as numod, 
                mp.start_date as date_debut, 
                mp.start_date_cq as date_fin, 
                mp.quantity as qt, 
                mp.type as typeod, 
                mp.product_id,
                pt.is_code as code_pg, 
                pt.name->>'fr_FR' designation,
                pt.is_stock_secu, 
                pt.produce_delay, 
                pt.lot_mini, 
                pt.multiple,
                pt.is_mold_dossierf as moule,
                mp.name as name,
                ig.name as gest
            FROM mrp_prevision mp inner join product_product      pp   on mp.product_id=pp.id 
                                  inner join product_template     pt   on pp.product_tmpl_id=pt.id
                                  left outer join is_mold         im   on pt.is_mold_id=im.id
                                  left outer join is_dossierf     id   on pt.is_dossierf_id=id.id
                                  left outer join is_gestionnaire ig   on pt.is_gestionnaire_id=ig.id
                                  left outer join is_category     ic   on pt.is_category_id=ic.id
                                  left outer join is_mold_project imp1 on im.project=imp1.id
                                  left outer join is_mold_project imp2 on id.project=imp2.id
                                  left outer join res_partner     rp   on pt.is_client_id=rp.id
            WHERE mp.id>0 """+filtre+""" 
            ORDER BY mp.name
        """
        cr.execute(SQL)
        #result = cr.fetchall()
        result = cr.dictfetchall()
        return result


    def _get_CF_CP(self,filtre):
        cr = self._cr
        SQL="""
            SELECT 
                so.id as numod, 
                sol.is_date_expedition as date_debut, 
                sol.is_date_expedition as date_fin, 
                sol.product_uom_qty as qt, 
                sol.is_type_commande as typeod, 
                sol.product_id, 
                pt.is_code as code_pg, 
                pt.name->>'fr_FR' designation,
                pt.is_stock_secu, 
                pt.produce_delay, 
                pt.lot_mini, 
                pt.multiple,
                pt.is_mold_dossierf as moule,
                so.name as name
            FROM sale_order_line sol inner join sale_order           so   on sol.order_id=so.id 
                               inner join product_product      pp   on sol.product_id=pp.id
                               inner join product_template     pt   on pp.product_tmpl_id=pt.id
                               left outer join is_mold         im   on pt.is_mold_id=im.id
                               left outer join is_dossierf     id   on pt.is_dossierf_id=id.id
                               left outer join is_gestionnaire ig   on pt.is_gestionnaire_id=ig.id
                               left outer join is_category     ic   on pt.is_category_id=ic.id
                               left outer join is_mold_project imp1 on im.project=imp1.id
                               left outer join is_mold_project imp2 on id.project=imp2.id
                               left outer join res_partner     rp   on pt.is_client_id=rp.id
            WHERE sol.id>0 """+filtre+""" and sol.state<>'done' and sol.state<>'cancel'
            ORDER BY sol.name
        """
        cr.execute(SQL)
        #result = cr.fetchall()
        result = cr.dictfetchall()
        return result


    def _get_FL(self,filtre):
        cr = self._cr
        SQL="""
            SELECT 
                mp.id as numod, 
                mp.date_planned_start as date_debut, 
                mp.date_planned_start as date_fin, 
                sm.product_qty as qt, 
                'FL' as typeod, 
                sm.product_id, 
                pt.is_code as code_pg, 
                pt.name->>'fr_FR' designation,
                pt.is_stock_secu, 
                pt.produce_delay, 
                pt.lot_mini, 
                pt.multiple,
                pt.is_mold_dossierf as moule,
                mp.name as name
            FROM stock_move sm    inner join product_product       pp   on sm.product_id=pp.id
                                  inner join product_template      pt   on pp.product_tmpl_id=pt.id
                                   inner join mrp_production       mp   on mp.id=sm.production_id
                                    left outer join is_mold        im   on pt.is_mold_id=im.id
                                   left outer join is_dossierf     id   on pt.is_dossierf_id=id.id
                                   left outer join is_gestionnaire ig   on pt.is_gestionnaire_id=ig.id
                                   left outer join is_category     ic   on pt.is_category_id=ic.id and ic.name!='74'
                                   left outer join is_mold_project imp1 on im.project=imp1.id
                                   left outer join is_mold_project imp2 on id.project=imp2.id
                                   left outer join res_partner     rp   on pt.is_client_id=rp.id
            WHERE sm.id>0 """+filtre+""" and production_id>0 and sm.state<>'done' and sm.state<>'cancel'
            ORDER BY sm.name 
        """
        cr.execute(SQL)
        #result = cr.fetchall()
        result = cr.dictfetchall()
        return result


    def _get_FM(self,filtre):
        cr = self._cr
        SQL="""
            SELECT 
                sm.id as numod, 
                sm.date_deadline as date_debut, 
                sm.date_deadline as date_fin, 
                sm.product_qty as qt, 
                'FM' as typeod, 
                sm.product_id, 
                pt.is_code as code_pg, 
                pt.name->>'fr_FR' designation,
                pt.is_stock_secu, 
                pt.produce_delay, 
                pt.lot_mini, 
                pt.multiple,
                pt.is_mold_dossierf as moule,
                sm.name as name
            FROM stock_move sm    inner join product_product      pp   on sm.product_id=pp.id
                            inner join product_template     pt   on pp.product_tmpl_id=pt.id
                            left outer join is_mold         im   on pt.is_mold_id=im.id
                            left outer join is_dossierf     id   on pt.is_dossierf_id=id.id
                            left outer join is_gestionnaire ig   on pt.is_gestionnaire_id=ig.id
                            left outer join is_category     ic   on pt.is_category_id=ic.id
                            left outer join is_mold_project imp1 on im.project=imp1.id
                            left outer join is_mold_project imp2 on id.project=imp2.id
                            left outer join res_partner     rp   on pt.is_client_id=rp.id

            WHERE sm.id>0 """+filtre+""" and raw_material_production_id>0 and sm.state<>'done' and sm.state<>'cancel' 
            ORDER BY sm.name
        """
        cr.execute(SQL)
        #result = cr.fetchall()
        result = cr.dictfetchall()
        return result


    def _get_SF(self,filtre):
        cr = self._cr
        SQL="""
            SELECT 
                po.id as numod, 
                pol.date_planned as date_debut, 
                pol.date_planned as date_fin, 
                sm.product_qty as qt, 
                'SF' as typeod, 
                pol.product_id, 
                pt.is_code as code_pg, 
                pt.name->>'fr_FR' designation,
                pt.is_stock_secu, 
                pt.produce_delay, 
                pt.lot_mini, 
                pt.multiple,
                pt.is_mold_dossierf as moule,
                po.name as name
            FROM purchase_order_line pol left outer join purchase_order po    on pol.order_id=po.id 
                                     inner join product_product           pp    on pol.product_id=pp.id
                                     inner join product_template          pt    on pp.product_tmpl_id=pt.id
                                     inner join stock_move                sm    on pol.id=sm.purchase_line_id
                                     left outer join is_mold              im    on pt.is_mold_id=im.id
                                     left outer join is_dossierf          id    on pt.is_dossierf_id=id.id
                                     left outer join is_gestionnaire      ig    on pt.is_gestionnaire_id=ig.id
                                     left outer join is_category          ic    on pt.is_category_id=ic.id and ic.name not in ('70','72','73','74')
                                     left outer join is_mold_project      imp1  on im.project=imp1.id
                                     left outer join is_mold_project      imp2  on id.project=imp2.id
                                     left outer join res_partner          rp    on pt.is_client_id=rp.id
              WHERE pol.id>0 """+filtre+""" and pol.state<>'draft' and pol.state<>'done' and pol.state<>'cancel'
                    and sm.state in ('draft','waiting','confirmed','assigned')
              ORDER BY pol.name
        """
        cr.execute(SQL)
        #result = cr.fetchall()
        result = cr.dictfetchall()
        return result






    def _get_TabSemaines(self,nb_semaines):
        date=datetime.now()
        jour=date.weekday()
        date = date - timedelta(days=jour)
        TabSemaines=[]
        for i in range(0,int(nb_semaines)):
            d=date.strftime('%Y%m%d')
            TabSemaines.append(d)
            date = date + timedelta(days=7)
        return TabSemaines


    def _get_Stocks(self,control_quality='f'):
        cr = self._cr
        SQL="""
            select sq.product_id, sum(sq.quantity) as qt
            from stock_quant sq inner join stock_location sl on sq.location_id=sl.id 
            where 
                sl.usage='internal' and 
                sl.active='t' and 
                sl.control_quality='"""+control_quality+"""' 
            group by sq.product_id 
            order by sq.product_id
        """
        cr.execute(SQL)
        result = cr.fetchall()
        Stocks={}
        for row in result:
            Stocks[row[0]]=row[1]
        return Stocks


    def _get_StocksSecu(self):
        cr = self._cr
        SQL="""
            select pp.id, pt.is_stock_secu as qt
            from product_product pp inner join product_template pt on pp.product_tmpl_id=pt.id 
        """
        cr.execute(SQL)
        result = cr.fetchall()
        StocksSecu={}
        for row in result:
            StocksSecu[row[0]]=row[1]
        return StocksSecu


    def _get_Fournisseurs_Delai_Fournisseurs(self):
        cr = self._cr
        SQL="""
            select 
                pp.id      as product_id, 
                rp.is_code as is_code, 
                rp.name    as name, 
                ps.delay   as delay, 
                rp.is_adr_code
            from product_product pp, product_supplierinfo ps, res_partner rp 
            where pp.product_tmpl_id=ps.product_tmpl_id and ps.partner_id=rp.id 
            order by ps.sequence, ps.id
        """


        cr.execute(SQL)
        result = cr.fetchall()
        Fournisseurs={}
        Delai_Fournisseurs={}
        for row in result:
            name=('0000'+row[1])[-4:]+'-'+row[4]
            if name=='':
                name=row[2]
            Fournisseurs[row[0]]=name
            Delai_Fournisseurs[row[0]]=row[3]
        return [Fournisseurs,Delai_Fournisseurs]


    def _get_stock(self,filtre):
        cr = self._cr
        SQL="""
            SELECT 
                pt.id as numod, 
                '' as date_debut, 
                '' as date_fin, 
                0 as qt, 
                'stock' as typeod, 
                pp.id as product_id, 
                pt.is_code as code_pg, 
                pt.name->>'fr_FR' designation,
                pt.is_stock_secu, 
                pt.produce_delay, 
                pt.lot_mini, 
                pt.multiple,
                pt.is_mold_dossierf as moule,
                '' as name
            FROM product_product pp inner join product_template         pt    on pp.product_tmpl_id=pt.id
                                   left outer join is_mold              im    on pt.is_mold_id=im.id
                                   left outer join is_dossierf          id    on pt.is_dossierf_id=id.id
                                   left outer join is_gestionnaire      ig    on pt.is_gestionnaire_id=ig.id
                                   left outer join is_category          ic    on pt.is_category_id=ic.id and ic.name not in ('70','72','73','74')
                                   left outer join is_mold_project      imp1  on im.project=imp1.id
                                   left outer join is_mold_project      imp2  on id.project=imp2.id
                                   left outer join res_partner          rp    on pt.is_client_id=rp.id
            WHERE pt.id>0 """+filtre+"""
            ORDER BY pt.is_code
        """
        cr.execute(SQL)
        #result = cr.fetchall()
        result = cr.dictfetchall()
        return result








    def RemplitTab2(self,Tab, result, TabSemaines, type_rapport, StocksA, 
            StocksQ, StocksSecu, Fournisseurs, Delai_Fournisseurs, calage, 
            valorisation, Couts, fournisseur, TypeCde, type_commande):

        for row in result:
            numod         = row["numod"]
            date_debut    = row["date_debut"]
            date_fin      = row["date_fin"]
            qt            = row["qt"]
            typeod        = (row["typeod"] or '').strip()
            product_id    = row["product_id"]
            code_pg       = row["code_pg"]
            designation   = row["designation"]
            is_stock_secu = row["is_stock_secu"]
            produce_delay = row["produce_delay"]
            lot_mini      = row["lot_mini"]
            multiple      = row["multiple"]
            moule         = row["moule"] or ''
            name          = row["name"]

            test=True
            if type_rapport=='Achat':
                is_code=''
                if product_id in Fournisseurs:
                    is_code    = Fournisseurs[product_id]
                cle        = is_code+'/'+str(product_id);
                t=''
                if cle in TypeCde:
                    t=TypeCde[cle]
                    Code=code_pg+' ('+t+')'
                if type_commande!='' and type_commande!=t:
                    test=False
            StockA=0
            StockQ=0
            if product_id in StocksA:
                StockA=StocksA[product_id]
            if product_id in StocksQ:
                StockQ=StocksQ[product_id]
            if typeod=='stock' and StockA==0 and StockQ==0:
                test=False

            if test:
                Tri=moule
                if type_rapport=='Achat':
                    if product_id in Fournisseurs:
                        Fournisseur=Fournisseurs[product_id]
                    else:
                        Fournisseur='0000'
                    Tri=Fournisseur
                if typeod=='':
                    typeod='ferme'
                Cle=code_pg+typeod

                Code=Tri+' / <b>'+code_pg+'</b> '
                if type_rapport=='Achat' and moule!='':
                    Code=Code+' / '+moule
                if type_rapport=='Achat':
                    k       = is_code+'/'+str(product_id)
                    if k in TypeCde:
                        t=TypeCde[k]
                        Code=Code+' ('+t+')'
                if type_rapport=='Achat':
                    Delai=0
                    if product_id in Delai_Fournisseurs:
                        Delai=Delai_Fournisseurs[product_id]
                else:
                    Delai=produce_delay

                Code=Code+'<a href="#" title="Rafraichir cette ligne"><img productid="'+str(product_id)+'" src="/is_plastigray/static/src/img/refresh-icon.png" style="max-height: 16px;"/></a>'
                Code=Code+\
                    '<br />'+\
                    designation+'<br />'+\
                    "{0:10.0f}".format(is_stock_secu)+' / '+\
                    "{0:10.0f}".format(Delai)+' / '+\
                    "{0:10.0f}".format(lot_mini)+' / '+\
                    "{0:10.0f}".format(multiple)+' / '+\
                    "{0:10.0f}".format(StockA)+' / '+\
                    "{0:10.0f}".format(StockQ)
                
                Code = designation


                if Cle not in Tab:
                    Tab[Cle]={}

                Tab[Cle]["key"] = Cle


                Tab[Cle]["product_id"]  = product_id
                Tab[Cle]["code_pg"]     = code_pg
                Tab[Cle]["designation"] = designation




                #** Les chiffres permettent de trier les lignes ****************
                t={
                    "ferme"        : "10-CF",
                    "previsionnel" : "20-CP",
                    "FL"           : "30-FL",
                    "FM"           : "40-FM",
                    "SF"           : "50-SF",
                    "ft"           : "60-FT",
                    "fs"           : "70-FS",
                    "sa"           : "80-SA",
                    "stock"        : "99-Stock",
                }
                Tab[Cle]["TypeOD"] = typeod
                if typeod in t:
                    Tab[Cle]["TypeOD"] = t[typeod]
                #***************************************************************


                #** Permet de déterminer le sens dans le calcul du stock *******
                t={
                    "ferme"        : -1,
                    "previsionnel" : -1,
                    "FL"           : 1,
                    "FM"           : -1,
                    "SF"           : 1,
                    "fs"           : 1,
                    "ft"           : -1,
                    "sa"           : 1,
                    "stock"        : 1,
                }
                Sens=1
                if typeod in t:
                    Sens = t[typeod]
                #***************************************************************

                if calage=='' or calage=='Date de fin':
                    DateLundi=self.datelundi(date_fin, TabSemaines)
                else:
                    DateLundi=self.datelundi(date_debut, TabSemaines)
            
                if typeod=='FL' and qt<0:
                    qt=-0.01

                qt = qt or 0 #NoneType

                # if DateLundi not in Tab[Cle]:
                #    Tab[Cle][DateLundi]=0
                # Tab[Cle][DateLundi]=Tab[Cle][DateLundi]+round(Sens*qt,2);

                # if DateLundi+'OT' not in Tab[Cle]:
                #    Tab[Cle][DateLundi+'OT']=''
                # Tab[Cle][DateLundi+'OT']=Tab[Cle][DateLundi+'OT']+str(numod)+","

                # if DateLundi+'INFO' not in Tab[Cle]:
                #    Tab[Cle][DateLundi+'INFO']=''

                # Tab[Cle][DateLundi+'INFO']=Tab[Cle][DateLundi+'INFO']+name+" : "+str(round(qt,2))+'<br />'

                # #** Calcul du stock theorique **********************************
                # Cle=code_pg+'90-Stock'
                # if Cle not in Tab:
                #     Tab[Cle]={}
                # Tab[Cle]['Code'] = Code
                # Tab[Cle]['TypeOD'] = '90-Stock'
                # StockSecu=0
                # if product_id in StocksSecu:
                #     StockSecu=StocksSecu[product_id]

                # if valorisation:
                #     Tab[Cle][0]=StockA+StockQ
                # else:
                #     Tab[Cle][0]=StockA-StockSecu

                # if DateLundi not in Tab[Cle]:
                #     Tab[Cle][DateLundi]=0
                # Tab[Cle][DateLundi]=Tab[Cle][DateLundi]+round(Sens*qt,2);
                # #***************************************************************

                # #** Valorisation stock *****************************************
                # if valorisation:
                #     Cout=0
                #     if product_id in Couts:
                #         Cout=Couts[product_id]
                #     Cle1=code_pg+u'90-Stock'
                #     Cle2=code_pg+u'92-Stock Valorisé'
                #     if Cle2 not in Tab:
                #         Tab[Cle2]={}
                #     Tab[Cle2]['Code'] = Code
                #     Tab[Cle2]['TypeOD']=u'92-Stock Valorisé'
                #     Tab[Cle2][0]=Tab[Cle1][0]*Cout
                #     Tab[Cle2][DateLundi]=Tab[Cle1][DateLundi]*Cout
                # #***************************************************************

        return Tab


    def datelundi(self,date,TabSemaines): 
        if date=='':
            return TabSemaines[0]
        #date=date[:10]
        #date=datetime.strptime(date, '%Y-%m-%d')
        if date:
            jour=date.weekday()
            date = date - timedelta(days=jour)
            date = date.strftime('%Y%m%d')
            if date<TabSemaines[0]:
                date=TabSemaines[0]
        return date or ''


    def color_cel(self,TypeOD,cel=0): 
        TypeOD=TypeOD[3:]
        t={
            "CF"    : "DarkRed",
            "CP"    : "DarkGreen",
            "FL"    : "DarkMagenta",
            "FM"    : "#000000",
            "SF"    : "DarkMagenta",
            "FS"    : "DarkBlue",
            "FT"    : "#000000",
            "SA"    : "DarkBlue",
            "Stock" : "Black",
        }
        color="Gray"
        if TypeOD in t:
            color=t[TypeOD]
        if TypeOD=='Stock' and cel<0:
            color='Red'
        return color















