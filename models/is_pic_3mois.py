from odoo import models,fields,api,tools
from odoo import http
from datetime import datetime, timedelta
import math

# Cela permet de créer une route utilisée par le service  memoize pour le cache de Pic3Mois
class Pic3Mois(http.Controller):
    @http.route('/is_plastigray16/get_pic_3mois_route', type='json', auth='user')
    def get_pic_3mois(self):
        return http.request.env['sale.order'].get_pic_3mois()


#TODO : 
# - Pouvoir imprimer


class sale_order(models.Model):
    _inherit = "sale.order"

    def get_pic_3mois(self,
                      ok=False,
                      code_cli=False,
                      adr_cli=False,
                      code_pg=False,
                      cat=False,
                      gest=False,
                      ref_cli=False,
                      moule=False,
                      projet=False,
                      type_cde="Toutes",
                      type_client="90xx",
                      prod_st="",
                      nb_semaines=12,
                      periodicite=7,
                      affiche_col_vide="Oui",
                      nb_lig=100):
        if ok:
            self.env['is.mem.var'].set(self._uid, 'pic3mois_code_cli'        , code_cli)
            self.env['is.mem.var'].set(self._uid, 'pic3mois_adr_cli'         , adr_cli)
            self.env['is.mem.var'].set(self._uid, 'pic3mois_code_pg'         , code_pg)
            self.env['is.mem.var'].set(self._uid, 'pic3mois_cat'             , cat)
            self.env['is.mem.var'].set(self._uid, 'pic3mois_gest'            , gest)
            self.env['is.mem.var'].set(self._uid, 'pic3mois_ref_cli'         , ref_cli)
            self.env['is.mem.var'].set(self._uid, 'pic3mois_moule'           , moule)
            self.env['is.mem.var'].set(self._uid, 'pic3mois_projet'          , projet)
            self.env['is.mem.var'].set(self._uid, 'pic3mois_type_cde'        , type_cde)
            self.env['is.mem.var'].set(self._uid, 'pic3mois_type_client'     , type_client)
            self.env['is.mem.var'].set(self._uid, 'pic3mois_prod_st'         , prod_st)
            self.env['is.mem.var'].set(self._uid, 'pic3mois_nb_semaines'     , nb_semaines)
            self.env['is.mem.var'].set(self._uid, 'pic3mois_periodicite'     , periodicite)
            self.env['is.mem.var'].set(self._uid, 'pic3mois_affiche_col_vide', affiche_col_vide)
            self.env['is.mem.var'].set(self._uid, 'pic3mois_nb_lig'          , nb_lig)
        else:
            code_cli         = self.env['is.mem.var'].get(self._uid, 'pic3mois_code_cli')
            adr_cli          = self.env['is.mem.var'].get(self._uid, 'pic3mois_adr_cli')
            code_pg          = self.env['is.mem.var'].get(self._uid, 'pic3mois_code_pg')
            cat              = self.env['is.mem.var'].get(self._uid, 'pic3mois_cat')
            gest             = self.env['is.mem.var'].get(self._uid, 'pic3mois_gest')
            ref_cli          = self.env['is.mem.var'].get(self._uid, 'pic3mois_ref_cli')
            moule            = self.env['is.mem.var'].get(self._uid, 'pic3mois_moule')
            projet           = self.env['is.mem.var'].get(self._uid, 'pic3mois_projet')
            type_cde         = self.env['is.mem.var'].get(self._uid, 'pic3mois_type_cde')
            type_client      = self.env['is.mem.var'].get(self._uid, 'pic3mois_type_client')
            prod_st          = self.env['is.mem.var'].get(self._uid, 'pic3mois_prod_st')
            nb_semaines      = self.env['is.mem.var'].get(self._uid, 'pic3mois_nb_semaines')
            periodicite      = self.env['is.mem.var'].get(self._uid, 'pic3mois_periodicite')
            affiche_col_vide = self.env['is.mem.var'].get(self._uid, 'pic3mois_affiche_col_vide')
            nb_lig           = int(self.env['is.mem.var'].get(self._uid, 'pic3mois_nb_lig'))
        nb_semaines = nb_semaines or 12
        periodicite = periodicite or 7
        nb_lig      = nb_lig or 100


        #Liste de choix *******************************************************
        options = ["Ferme", "Prev", "Toutes"]
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

        #options = ["50xx","70xx","80xx","90xx","Tous","SaufPMTC"]
        options = ["80xx","90xx","Tous"]
        type_client_options=[]
        for o in options:
            selected=False
            if o==type_client:
                selected=True
            type_client_options.append({
                "id": o,
                "name": o,
                "selected": selected,
            })

        options = ["","PROD","ST"]
        prod_st_options=[]
        for o in options:
            selected=False
            if o==prod_st:
                selected=True
            prod_st_options.append({
                "id": o,
                "name": o,
                "selected": selected,
            })

        nb_semaines_options=[]
        for o in range(1,31):
            selected=False
            if o==int(nb_semaines):
                selected=True
            nb_semaines_options.append({
                "id": o,
                "name": o,
                "selected": selected,
            })

        options = [1,7,14,28]
        periodicite_options=[]
        for o in options:
            selected=False
            if o==int(periodicite):
                selected=True
            periodicite_options.append({
                "id": o,
                "name": o,
                "selected": selected,
            })

        options = ["Oui","Non"]
        affiche_col_vide_options=[]
        for o in options:
            selected=False
            if o==affiche_col_vide:
                selected=True
            affiche_col_vide_options.append({
                "id": o,
                "name": o,
                "selected": selected,
            })

        options = [10,20,50,100,200,300,400,500,1000,2000]
        nb_lig_options=[]
        for o in options:
            selected=False
            if o==int(nb_lig):
                selected=True
            nb_lig_options.append({
                "id": o,
                "name": o,
                "selected": selected,
            })
        #**********************************************************************


        #** Requête ***********************************************************
        cr = self._cr
        SQL="""
            SELECT 
                so.name,
                sol.id,
                so.partner_id,
                so.client_order_ref,
                rp.is_code code_client,
                rp.is_adr_code,
                rp.is_delai_transport,
                sol.product_id,
                pt.id product_tmpl_id,
                pt.is_code,
                pt.name->>'fr_FR' designation,
                pt.is_category_id,
                pt.lot_mini,
                pt.is_stock_secu,
                ig.name gestionnaire,
                -- concat (pt.is_code, ' ', pt.name, ' (', im.name, ')') description,
                pt.is_ref_client,
                pt.is_mold_id,
                sol.product_uom_qty,
                sol.is_date_livraison,
                sol.is_date_expedition,
                sol.is_type_commande,
                im.project,
                coalesce(im.name, id.name) moule,
                imp.name projet,
                (select route_id from stock_route_product srp where srp.product_id=pt.id  limit 1) route_id,
                COALESCE((   select round(sum(sq.quantity)) 
                    from stock_quant sq inner join stock_location sl on sq.location_id=sl.id 
                    where sl.usage='internal' and sl.active='t' and sq.product_id=pp.id and sl.control_quality='f' ),0) stocka,
                COALESCE((   select round(sum(sq.quantity))
                    from stock_quant sq inner join stock_location sl on sq.location_id=sl.id 
                    where sl.usage='internal' and sl.active='t' and sq.product_id=pp.id and sl.control_quality='t' ), 0) stockq
            FROM sale_order so inner join sale_order_line      sol on so.id=sol.order_id 
                            inner join res_partner           rp on so.partner_id=rp.id 
                            inner join product_product       pp on pp.id = sol.product_id
                            inner join product_template      pt on pt.id = pp.product_tmpl_id
                            left outer join is_mold          im on pt.is_mold_id = im.id
                            left outer join is_dossierf      id on pt.is_dossierf_id=id.id
                            left outer join is_mold_project imp on im.project=imp.id 
                            left outer join is_mold_project imp2 on id.project=imp2.id 
                            left outer join is_gestionnaire  ig on pt.is_gestionnaire_id=ig.id
                            left outer join is_category      ic on pt.is_category_id=ic.id
            WHERE so.state in('draft','sent') 
        """
        if code_cli:
            SQL+=" AND rp.is_code='%s' "%code_cli
        if adr_cli:
            SQL+=" AND rp.is_adr_code='%s' "%adr_cli 
        if code_pg:
            SQL+=" AND pt.is_code LIKE '%s%%' "%code_pg
        if cat:
            SQL+=" AND ic.name='%s' "%cat 
        if gest:
            SQL+=" AND ig.name='%s' "%gest; 
        if ref_cli:
            SQL+=" AND pt.is_ref_client LIKE '%%%s%%' "%ref_cli 
        rMoules=[]
        if moule:
            moule=moule.strip()
            tmoule=moule.split(",")
            for m in tmoule:
                rMoules.append("'%s'"%m.strip())
            moules = ",".join(rMoules)
            SQL+=" AND (im.name IN (%s) or id.name IN (%s)) "%(moules,moules)
        if projet:
            SQL+=" AND (imp.name ilike '%%%s%%' or imp2.name ilike '%%%s%%') "%(projet,projet)
        if type_cde=="Ferme":
            SQL+=" AND sol.is_type_commande='ferme' "
        if type_cde=="Prev":
            SQL+=" AND sol.is_type_commande='previsionnel' "
        if type_client=="50xx":
            SQL+=" AND rp.is_code>='500000' AND rp.is_code<='599999' "
        if type_client=="70xx":
            SQL+=" AND rp.is_code>='700000' AND rp.is_code<='799999' "
        if type_client=="80xx":
            SQL+=" AND rp.is_code>='800000' AND rp.is_code<='899999' "
        if type_client=="90xx":
            SQL+=" AND rp.is_code>='900000' AND rp.is_code<='999999' "
        if type_client=="SaufPMTC":
            SQL+=" AND rp.is_code>='900000' AND rp.is_code<>'907480' "

        if prod_st=="ST":
            SQL+=" AND ig.name IN     ('03', '06', '07', '10', '12', '14') "
        if prod_st=="PROD":
            SQL+=" AND ig.name NOT IN ('03', '06', '07', '10', '12', '14') "

        SQL+=" ORDER BY rp.is_code, im.name, pt.is_code limit %s"%(int(nb_lig)*100)
        #**********************************************************************

        periodicite=int(periodicite)
        NbColMax = math.floor(int(nb_semaines)*7/periodicite)
        LaDate = datetime.now()
        JourSem = LaDate.weekday()
        DebSem = LaDate
        if periodicite!=1:
            DebSem = LaDate - timedelta(days=JourSem)
        lig=0
        key=""
        cr.execute(SQL)
        result = cr.dictfetchall()
        lines={}
        trcolor=""
        TotalCol={}
        for row in result:
            DebSemTxt = DebSem.strftime("%Y%m%d")
            k="%s-%s-%s"%(row['code_client'],row['moule'],row['is_code'])
            #if key!=row['is_code']:
            #    key=row['is_code']
            if key!=k:
                key=k
                if trcolor=="#ffffff":
                    trcolor="#f2f3f4"
                else:
                    trcolor="#ffffff"
                trstyle="background-color:%s"%(trcolor)
                vals={
                    "key"        : key,
                    "product_tmpl_id": row["product_tmpl_id"],
                    "trstyle"    : trstyle,
                    "trstyle"    : trstyle,
                    "row"        : row,
                    "moule"      : row["moule"],
                    "lot_mini"   : row["lot_mini"],
                }
                cols={}
                for col in range(1, NbColMax+1):
                    cols[col] = {"key":col, "rows": [], "ids_ferme": [], "ids_prev": []} 
                vals["cols"] = cols
                lines[key]=vals
                lig+=1

            DateCde = row["is_date_livraison"] or datetime.now().date()
            DateCdeTxt =  DateCde.strftime("%Y%m%d")
            if DateCdeTxt<DebSemTxt:
                col=1
            else:
                nb_jours = (DateCde-DebSem.date()).days
                col=math.floor(nb_jours/int(periodicite))+1
            if col<=NbColMax:
                qt = row['product_uom_qty']
                lines[key]["cols"][col]["rows"].append(row)
                if row["is_type_commande"]=='ferme':
                    lines[key]["cols"][col]["ids_ferme"].append(row["id"])
                else:
                    lines[key]["cols"][col]["ids_prev"].append(row["id"])
                if col not in TotalCol:
                    TotalCol[col]=0
                TotalCol[col]+=qt
            #lines[key]["listcols"] = list(lines[key]["cols"].values())
            if lig>int(nb_lig):
                break

        #** Titres des colonnes ***********************************************
        date_cols=[]
        DateCol = DebSem
        for o in range(1,NbColMax+1):
            total=TotalCol.get(o, "")
            affiche_col=False
            if affiche_col_vide=="Oui" or total!="":
                affiche_col=True
            date_cols.append({
                "id"   : o,
                "jour" : DateCol.strftime("%d"),
                "mois" : DateCol.strftime("%m"),
                "total": total,
                "affiche_col": affiche_col,
            })
            DateCol = DateCol + timedelta(days=int(periodicite))
        #**********************************************************************

        #sorted_dict = dict(sorted(lines.items())) 
        res={
            #"lines"           : list(lines.values()),
            #dict"            : sorted_dict,
            "dict"            : lines,
            "date_cols"       : date_cols,
            "code_cli"        : code_cli,
            "adr_cli"         : adr_cli,
            "code_pg"         : code_pg,
            "cat"             : cat,
            "gest"            : gest,
            "ref_cli"         : ref_cli,
            "moule"           : moule,
            "projet"          : projet,
            "type_cde"        : type_cde,
            "type_client"     : type_client,
            "prod_st"         : prod_st,
            "nb_semaines"     : nb_semaines,
            "periodicite"     : periodicite,
            "affiche_col_vide": affiche_col_vide,
            "nb_lig"          : nb_lig,
            "type_cde_options"        : type_cde_options,
            "type_client_options"     : type_client_options,
            "prod_st_options"         : prod_st_options,
            "nb_semaines_options"     : nb_semaines_options,
            "periodicite_options"     : periodicite_options,
            "affiche_col_vide_options": affiche_col_vide_options,
            "nb_lig_options"          : nb_lig_options,
        }
        return res

