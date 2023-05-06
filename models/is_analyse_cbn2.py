# -*- coding: utf-8 -*-
from odoo import models,fields,api
import time
from datetime import datetime, timedelta
from collections import OrderedDict
import tempfile
import logging
_logger = logging.getLogger(__name__)


# def duree(debut):
#     dt = datetime.datetime.now() - debut
#     ms = (dt.days * 24 * 60 * 60 + dt.seconds) * 1000 + dt.microseconds / 1000.0
#     ms=int(ms)
#     return ms


# def _now(debut):
#     return str(int(duree(debut)/100.0)/10.0)+"s"


class product_product(models.Model):
    _inherit = "product.product"


    def load_tr(self,filter,trcolor,trid):
        product_id=filter.get('product_id')
        res=self.analyse_cbn2(filter,trcolor,trid)

        html=res['html']

        vals={
            'product_id': product_id,
            'html'      : html, 
        }
        return vals






    def analyse_cbn2(self,filter=False,trcolor=False,trid=False):
        cr, uid, context = self.env.args
        debut=datetime.datetime.now()
        _logger.info('Début requête')
        product_id=filter.get('product_id',False)
        validation    = filter['validation']
        # if validation=='ko':
        #     #** Lecture des critères enregistrés *******************************
        #     code_pg_debut = self.env['is.mem.var'].get(uid,'code_pg_debut')
        #     gest = self.env['is.mem.var'].get(uid,'gest')
        #     cat = self.env['is.mem.var'].get(uid,'cat')
        #     moule = self.env['is.mem.var'].get(uid,'moule')
        #     projet = self.env['is.mem.var'].get(uid,'projet')
        #     client = self.env['is.mem.var'].get(uid,'client')
        #     fournisseur = self.env['is.mem.var'].get(uid,'fournisseur')
        #     type_commande = self.env['is.mem.var'].get(uid,'type_commande')
        #     type_rapport  = self.env['is.mem.var'].get(uid,'type_rapport')
        #     calage = self.env['is.mem.var'].get(uid,'calage')
        #     nb_semaines   = self.env['is.mem.var'].get(uid,'nb_semaines')
        #     valorisation=''
        # else:
        #     #** Lecture des filtres ********************************************
        #     code_pg_debut = filter['code_pg_debut']
        #     gest          = filter['gest']
        #     cat           = filter['cat']
        #     moule         = filter['moule']
        #     projet        = filter['projet']
        #     client        = filter['client']
        #     fournisseur   = filter['fournisseur']
        #     type_commande = filter['type_commande']
        #     type_rapport  = filter['type_rapport']
        #     calage        = filter['calage']
        #     nb_semaines   = filter['nb_semaines']
        #     valorisation  = filter['valorisation']
        #     #*******************************************************************


        #     #** Enregistrement des critères enregistrés ************************
        #     self.env['is.mem.var'].set(uid, 'code_pg_debut', code_pg_debut)
        #     self.env['is.mem.var'].set(uid, 'gest', gest)
        #     self.env['is.mem.var'].set(uid, 'cat', cat)
        #     self.env['is.mem.var'].set(uid, 'moule', moule)
        #     self.env['is.mem.var'].set(uid, 'projet', projet)
        #     self.env['is.mem.var'].set(uid, 'client', client)
        #     self.env['is.mem.var'].set(uid, 'fournisseur', fournisseur)
        #     self.env['is.mem.var'].set(uid, 'type_commande', type_commande)
        #     self.env['is.mem.var'].set(uid, 'type_rapport', type_rapport)
        #     self.env['is.mem.var'].set(uid, 'calage', calage)
        #     self.env['is.mem.var'].set(uid, 'nb_semaines', nb_semaines)
        #     #*******************************************************************


        # #** Valeur par défaut **************************************************
        # code_pg_debut = code_pg_debut  or ''
        # gest          = gest           or ''
        # cat           = cat            or ''
        # moule         = moule          or ''
        # projet        = projet         or ''
        # client        = client         or ''
        # fournisseur   = fournisseur    or ''
        # type_commande = type_commande  or ''
        # type_rapport  = type_rapport   or 'Fabrication'
        # calage        = calage         or 'Date de fin'
        # nb_semaines   = nb_semaines    or 18
        # nb_semaines   = int(nb_semaines)
        # height        = filter.get('height')
        # #***********************************************************************


        # # ** Filtre pour les requêtes ******************************************
        # filtre=""

        # if product_id:
        #     filtre=filtre+" and pp.id="+str(product_id)+" "

        # if code_pg_debut:
        #     filtre=filtre+" and pt.is_code ilike '"+code_pg_debut+"%' "
        # if type_rapport=="Achat":
        #     filtre=filtre+" and pt.purchase_ok=true "
        # else:
        #     filtre=filtre+" and pt.purchase_ok<>true "
        # if cat:
        #     filtre=filtre+" and ic.name='"+cat+"' "
        # if moule:
        #     moules = moule.split(',')
        #     res=[]
        #     for m in moules:
        #         res.append("'"+str(m)+"'")
        #     moules=",".join(res)
        #     moules='('+moules+')'
        #     filtre=filtre+" and (im.name in "+moules+" or id.name in "+moules+" )"
        #     #filtre=filtre+" and (im.name='"+moule+"' or id.name='"+moule+"' )"
        # if projet:
        #     filtre=filtre+" and (imp1.name ilike '%"+projet+"%' or imp2.name ilike '%"+projet+"%') "
        # if client:
        #     filtre=filtre+" and rp.is_code='"+client+"' "
        # # **********************************************************************


        # #** Listes de choix des filtres ****************************************
        # select_nb_semaines=[4,8,12,16,18,20,25,30,40,60]
        # select_type_commande=['','ferme_uniquement','ferme','ouverte','cadencée']
        # select_type_rapport=['Fabrication','Achat']
        # select_calage=['Date de fin','Date de début']
        # #***********************************************************************


        #titre              = self._get_titre(type_rapport,valorisation)  # Titre du rapport
        # cat2id             = self._get_cat2id()                          # Catégories
        # Couts              = self._get_Couts()                           # Coûts
        # TypeCde            = self._get_TypeCde(type_rapport)             # Type de commande d'achat
        # select_gest        = self._get_select_gest(filtre,fournisseur)   # Liste des gestionnaires
        # select_fournisseur = self._get_select_fournisseur(filtre,gest)   # Liste des fournisseurs


        # if validation=='ko':
        #     html='Indiquez vos critères de filtre et validez'
        # else:
        #     # ** Filtre sur le fournisseur (partner_id) ****************************
        #     partner_id=False
        #     if fournisseur:
        #         tab=fournisseur.split('-')
        #         SQL="select id from res_partner where is_code='"+tab[0]+"' and is_adr_code='"+tab[1]+"' "
        #         cr.execute(SQL)
        #         result = cr.fetchall()
        #         for row in result:
        #             partner_id=row[0]
        #     if gest:
        #         filtre=filtre+" and ig.name='"+gest+"' "
        #     if partner_id:
        #         filtre=filtre+""" 
        #             and (
        #                     (   select rp2.id from product_supplierinfo ps inner join res_partner rp2 on ps.name=rp2.id   
        #                         where ps.product_tmpl_id=pt.id order by ps.sequence limit 1
        #                     )="""+str(partner_id)+"""
        #                 )
        #         """
        #     filtre=filtre+" AND ic.name!='80' "
        #     # **********************************************************************

            # TabSemaines = self._get_TabSemaines(nb_semaines) # Tableau des semaines
            # StocksA     = self._get_Stocks('f')              # StocksA (control_quality=f)
            # StocksQ     = self._get_Stocks('t')              # StocksQ (control_quality=t)
            # StocksSecu  = self._get_StocksSecu()             # StocksSecu
            # Fournisseurs, Delai_Fournisseurs = self._get_Fournisseurs_Delai_Fournisseurs() # Fournisseurs + Delai_Fournisseurs

            # # ** Recherche des Prévisions du CBN  ******************************
            # TabIni={};
            # result = self._get_FS_SA(filtre)
            # TabIni=self.RemplitTab2(TabIni, result, TabSemaines, type_rapport, 
            #     StocksA, StocksQ, StocksSecu, Fournisseurs, Delai_Fournisseurs, 
            #     calage, valorisation, Couts, fournisseur, TypeCde, type_commande)
            # # ******************************************************************

            # # ** Recherche des commandes client ********************************
            # result = self._get_CF_CP(filtre)
            # TabIni=self.RemplitTab2(TabIni, result, TabSemaines, type_rapport, 
            #     StocksA, StocksQ, StocksSecu, Fournisseurs, Delai_Fournisseurs, 
            #     calage, valorisation, Couts, fournisseur, TypeCde, type_commande)
            # # ******************************************************************

            # # ** Recherche des OF **********************************************
            # result = self._get_FL(filtre)
            # TabIni=self.RemplitTab2(TabIni, result, TabSemaines, type_rapport, 
            #     StocksA, StocksQ, StocksSecu, Fournisseurs, Delai_Fournisseurs, 
            #     calage, valorisation, Couts, fournisseur, TypeCde, type_commande)
            # # ******************************************************************

            # # ** Recherche des composants des OF *******************************
            # result = self._get_FM(filtre)
            # TabIni=self.RemplitTab2(TabIni, result, TabSemaines, type_rapport, 
            #     StocksA, StocksQ, StocksSecu, Fournisseurs, Delai_Fournisseurs, 
            #     calage, valorisation, Couts, fournisseur, TypeCde, type_commande)
            # # ******************************************************************

            # # ** Recherche des commandes fournisseurs  *************************
            # result = self._get_SF(filtre)
            # TabIni=self.RemplitTab2(TabIni, result, TabSemaines, type_rapport, 
            #     StocksA, StocksQ, StocksSecu, Fournisseurs, Delai_Fournisseurs, 
            #     calage, valorisation, Couts, fournisseur, TypeCde, type_commande)
            # # ******************************************************************

            # # ** Recherche pour avoir tous les articles dans le résultat  ******
            # if valorisation:
            #     result = self._get_stock(filtre)
            #     TabIni=self.RemplitTab2(TabIni, result, TabSemaines, type_rapport, 
            #         StocksA, StocksQ, StocksSecu, Fournisseurs, Delai_Fournisseurs, 
            #         calage, valorisation, Couts, fournisseur, TypeCde, type_commande)
            # # ******************************************************************

            # #** RemplitTab2Sho *************************************************
            # TabSho={};
            # lig=0;
            # Tab=TabIni
            # for key, val in Tab.iteritems():
            #     Type=Tab[key]['TYPE']
            #     if Type!='99-Stock':
            #         color=self.color_cel(Type)
            #         if 0 not in TabSho:
            #             TabSho[0]={}
            #         if 1 not in TabSho:
            #             TabSho[1]={}
            #         TabSho[0][lig]=Tab[key]["Code"]
            #         TabSho[1][lig]=Type
            #         Type=Type[3:]
            #         for i in range(0, nb_semaines):
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
            #             if Tab[key]['TYPE']=='90-Stock':
            #                 if i==0:
            #                     Stock=Tab[key][0]+Qt
            #                 else:
            #                     q=TabSho[1+i][lig]
            #                     Stock=TabSho[1+i][lig]+Qt
            #                 TabSho[2+i][lig]=Stock

            #             #*******************************************************

            #             #** Calcul du stock valorisé ***************************
            #             if Tab[key]['TYPE']=='92-Stock Valorisé':
            #                 if i==0:
            #                     Stock=Tab[key][0]+Qt;
            #                 else:
            #                    Stock=TabSho[1+i][lig]+Qt;
            #                 TabSho[2+i][lig]=round(Stock,2)
            #             #*******************************************************
            #         lig+=1
            # Tab=TabSho
            # # ******************************************************************

            NomCol = ["Sécu / Délai / Lot / Multi / Stock A/Q", "Type"]
            Style  = ["NormalLN", "NormalCN"]
            Format = ["TEXT"    , "TEXT"    ]
            Total  = [0         , 0         ]
            Lien   = [""        , ""        ]
            Size   = [220       , 40        ]


            # ** Tableau des semaines ******************************************
            date=datetime.datetime.now()
            jour=date.weekday()
            date = date - datetime.timedelta(days=jour)
            TabSemaines=[]
            for i in range(0,int(nb_semaines)):
                s='S'+str(date.isocalendar()[1])+'<br />'+date.strftime('%d.%m')
                TabSemaines.append(s)
                date = date + datetime.timedelta(days=7)
            # ******************************************************************


            for i in range(0,int(nb_semaines)):
                NomCol.append(TabSemaines[i])
                Style.append("NormalRN")
                Format.append("TEXT")
                Total.append(0)
                Lien.append("")
                Size.append(48)
            width=220+40+nb_semaines*(48+2)+22


            #** Création des listes et de la clé de tri  ***********************
            lst={}
            lst['key']=[]
            for col, v1 in Tab.iteritems():
                lst[col]=[]
                for lig, v2 in v1.iteritems():
                    if col==1:
                        key=Tab[0][lig]+Tab[1][lig]
                        lst['key'].append(key)
                    lst[col].append(v2)
            #*******************************************************************


            #** Tri des listes *************************************************
            z=[]
            z.append(lst['key'])
            for col in range(0,len(Tab)):
                z.append(lst[col])
            NewTab=zip(*z)
            NewTab.sort()
            #*******************************************************************


            #** Reconsctuction du Tab ******************************************
            Tab={}
            lig=0
            for row in NewTab:
                col=0
                for cel in row:
                    if col>0:
                        if lig==0:
                            Tab[col-1]={}
                        Tab[col-1][lig]=cel
                    col+=1

                lig+=1
            #*******************************************************************


            #** Génération du fichier CSV **************************************
            attachment_id=''

            if valorisation and Tab:
                csv={};
                for lig in range(0,len(Tab[0])):
                    #** Recherche du CodePG et de la désignation ***************
                    Key=Tab[0][lig]
                    Key=Key.split('</b>')
                    Key=Key[0]
                    Key=Key.split('<b>')
                    Key=Key[1]
                    CodePG=Key
                    Key=Tab[0][lig]
                    Key=Key.split('<br />')
                    Key=Key[1]
                    Designation=Key
                    #***********************************************************

                    if CodePG not in csv:
                        csv[CodePG]={}
                    csv[CodePG][0]=CodePG
                    csv[CodePG][1]=Designation
                    Type=Tab[1][lig]
                    if Type=='90-Stock':
                        for col in range(2,len(Tab)):
                            csv[CodePG][col*1000+1]=Tab[col][lig]
                    if Type=='92-Stock Valorisé':
                        for col in range(2,len(Tab)):
                            csv[CodePG][col*1000+2]=Tab[col][lig]


                #** Ecriture fichier CSV  **************************************
                user  = self.env['res.users'].browse(uid)
                name  = 'analyse-cbn-'+user.login+'.csv'
                path='/tmp/'+name
                f = open(path,'wb')
                txt=[];
                txt.append('CodePG')
                txt.append('Désignation')
                date=datetime.datetime.now()
                jour=date.weekday()
                date = date - datetime.timedelta(days=jour)
                for i in range(0,int(nb_semaines)):
                    v='Stock S'+str(date.isocalendar()[1])+' '+date.strftime('%d.%m')
                    txt.append(v)
                    v='Valorisé S'+str(date.isocalendar()[1])+' '+date.strftime('%d.%m')
                    txt.append(v)
                    date = date + datetime.timedelta(days=7)

                f.write(u'\t'.join(txt)+'\r\n')
                for k, v in csv.iteritems():
                    v=self.ksort(v)
                    txt=[]
                    for k2, v2 in v:
                        txt.append(str(v2).replace('.',','))
                    f.write(u'\t'.join(txt)+'\r\n')
                f.close()
                #***************************************************************


                # ** Creation ou modification de la pièce jointe *******************
                attachment_obj = self.env['ir.attachment']
                attachments = attachment_obj.search([('res_id','=',user.id),('name','=',name)])
                csv = open(path,'rb').read()
                vals = {
                    'name':        name,
                    'datas_fname': name,
                    'type':        'binary',
                    'res_id':      user.id,
                    'datas':       csv.encode('base64'),
                }
                attachment_id=False
                if attachments:
                    for attachment in attachments:
                        attachment.write(vals)
                        attachment_id=attachment.id
                else:
                    attachment = attachment_obj.create(vals)
                    attachment_id=attachment.id
                #*******************************************************************


            #*******************************************************************


            #** Code HTML ******************************************************
            if len(Tab)==0:
                html='Aucune donnée !'
            else:
                html=''
                alt=1
                if not product_id:
                    head="<thead><tr class=\"TitreTabC\">\n"
                    for col in range(0,len(Tab)):
                        align='left'
                        if col>1:
                            align='right'

                        head+="<th style=\"width:"+str(Size[col])+"px;text-align:"+align+"\">"+NomCol[col]+"</th>\n"
                    head+="</tr></thead>\n"
                    html+="<div style=\"width:"+str(width+20)+"px;\" id=\"table_head\">\n"
                    html+="<table style=\"border-width:0px;border-spacing:0px;padding:0px;width:"+str(width)+"px;\">\n"
                    html+=head
                    html+="</table>\n"
                    html+="</div>\n"
                    html+="<div style=\"width:"+str(width+20)+"px;\" id=\"table_body\">\n";
                    html+="<table style=\"border-width:0px;border-spacing:0px;padding:0px;width:"+str(width)+"px;\">\n";
                    html+=head;
                    html+="<tbody class=\"tbody\">\n"
                for lig in range(0,len(Tab[0])):
                    if lig>0:
                        if Tab[0][lig]!=Tab[0][lig-1]:
                            alt=-alt
                    if alt==1:
                        bgcolor="ffdec0"
                    else:
                        bgcolor="fae9da"

                    if trcolor:
                        bgcolor=trcolor[-6:]

                    if trid:
                        idtr=trid
                    else:
                        idtr=str(lig)


                    onclick = "onclick=\"clicktr('id"+idtr+"','"+bgcolor+"','2')\""

                    html+="<tr trcolor=\""+bgcolor+"\" style=\"background-color:#"+bgcolor+";\" id=\"id"+idtr+\
                        "\"onmouseover=\"clicktr('id"+idtr+"','ffff00','1')\"onmouseout=\"clicktr('id"+idtr+\
                        "','"+bgcolor+"','1')\" "+onclick+">\n"

                    for col in range(0,len(Tab)):
                        cel=Tab[col][lig]
                        if(col==1):
                            cel=cel[3:] 
                        if lig>0:
                            if col==0:
                                if Tab[0][lig]==Tab[0][lig-1]:
                                    cel="&nbsp;"
                        #** Recherche du nombre de lignes ayant le même code ***********
                        rowspan=1
                        if col==0:
                            if lig==0 or (lig>0 and Tab[0][lig]!=Tab[0][lig-1]):
                                while (lig+rowspan) in Tab[0] and Tab[0][lig]==Tab[0][lig+rowspan]:
                                    rowspan+=1
                        #***************************************************************
                        color="black"
                        if col>0:
                            color=self.color_cel(Tab[1][lig],cel)
                        if col>1:
                            if type(cel)==float:
                                if cel==0 and color!='Black':
                                    cel=''
                                else:
                                    cel="{:10.0f}".format(cel)
                            cel="<b>"+str(cel)+"</b>"
                        align='left'
                        if col>1:
                            align='right'
                        if lig==0 or col>0 or (lig>0 and Tab[0][lig]!=Tab[0][lig-1]):
                            html+="<td style=\"width:"+str(Size[col])+"px;color:"+color+";text-align:"+align+";\" rowspan=\""+str(rowspan)+"\" class=\""+Style[col]+"\">"+str(cel)+"</td>\n"
                    html+="</tr>\n"

                if not product_id:
                    html+="</tbody>\n"
                    html+="</table>\n"
                    html+="</div>"
                    if valorisation:
                        html+="<a class=\"info\" type='stock-valorise' attachment_id='"+str(attachment_id)+"'>Stock valorisé</a>\n"

            #***********************************************************************


        vals={
            'titre'               : titre,
            'code_pg_debut'       : code_pg_debut,
            'moule'               : moule,
            'cat'                 : cat,
            'projet'              : projet,
            'client'              : client,
            'valorisation'        : valorisation,
            'select_gest'         : select_gest,
            'gest'                : gest,
            'select_fournisseur'  : select_fournisseur,
            'fournisseur'         : fournisseur,
            'select_nb_semaines'  : select_nb_semaines,
            'nb_semaines'         : nb_semaines,
            'select_type_commande': select_type_commande,
            'type_commande'       : type_commande,
            'select_type_rapport' : select_type_rapport,
            'type_rapport'        : type_rapport,
            'select_calage'       : select_calage,
            'calage'              : calage,
            'html'                : html,
        }
        _logger.info('Fin requête '+_now(debut))
        return vals


    def ksort(self,d):
        return [(k,d[k]) for k in sorted(d.keys())]




