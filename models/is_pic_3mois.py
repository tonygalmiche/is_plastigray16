from odoo import models,fields,api,tools
from odoo import http
from datetime import datetime, timedelta
import math

# Cela permet de créer une route utilisée par le service  memoize pour le cache de Pic3Mois
class Pic3Mois(http.Controller):
    @http.route('/is_plastigray16/get_pic_3mois_route', type='json', auth='user')
    def get_pic_3mois(self):
        return http.request.env['sale.order'].get_pic_3mois()


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
                      type_cde=False,
                      type_client=False,
                      prod_st=False,
                      nb_semaines=False,
                      periodicite=False,
                      affiche_col_vide=False,
                      nb_lig=False):


        # this.state.pic3mois_code_cli         = res.code_cli;
        # this.state.pic3mois_adr_cli          = res.adr_cli;
        # this.state.pic3mois_code_pg          = res.code_pg;
        # this.state.pic3mois_cat              = res.cat;
        # this.state.pic3mois_gest             = res.gest;
        # this.state.pic3mois_ref_cli          = res.ref_cli;
        # this.state.pic3mois_moule            = res.moule;
        # this.state.pic3mois_projet           = res.projet;
        # this.state.pic3mois_type_cde         = res.type_cde;
        # this.state.pic3mois_type_client      = res.type_client;
        # this.state.pic3mois_prod_st          = res.prod_st;
        # this.state.pic3mois_nb_semaines      = res.nb_semaines;
        # this.state.pic3mois_periodicite      = res.periodicite;
        # this.state.pic3mois_affiche_col_vide = res.affiche_col_vide;
        # this.state.pic3mois_nb_lig           = res.nb_lig;


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
            nb_lig           = self.env['is.mem.var'].get(self._uid, 'pic3mois_nb_lig')

        cr = self._cr





        SQL="""
            SELECT 
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
                concat (pt.is_code, ' ', pt.name, ' (', im.name, ')') description,
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
                (   select sum(sq.quantity) 
                    from stock_quant sq inner join stock_location sl on sq.location_id=sl.id 
                    where sl.usage='internal' and sl.active='t' and sq.product_id=pp.id and sl.control_quality='f' ) stocka,
                (   select sum(sq.quantity)
                    from stock_quant sq inner join stock_location sl on sq.location_id=sl.id 
                    where sl.usage='internal' and sl.active='t' and sq.product_id=pp.id and sl.control_quality='t' ) stockq
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

        # code_cli         = self.env['is.mem.var'].get(self._uid, 'pic3mois_code_cli')
        # adr_cli          = self.env['is.mem.var'].get(self._uid, 'pic3mois_adr_cli')
        # code_pg          = self.env['is.mem.var'].get(self._uid, 'pic3mois_code_pg')
        # cat              = self.env['is.mem.var'].get(self._uid, 'pic3mois_cat')
        # gest             = self.env['is.mem.var'].get(self._uid, 'pic3mois_gest')
        # ref_cli          = self.env['is.mem.var'].get(self._uid, 'pic3mois_ref_cli')
        # moule            = self.env['is.mem.var'].get(self._uid, 'pic3mois_moule')
        # projet           = self.env['is.mem.var'].get(self._uid, 'pic3mois_projet')
        # type_cde         = self.env['is.mem.var'].get(self._uid, 'pic3mois_type_cde')
        # type_client      = self.env['is.mem.var'].get(self._uid, 'pic3mois_type_client')
        # prod_st          = self.env['is.mem.var'].get(self._uid, 'pic3mois_prod_st')
        # nb_semaines      = self.env['is.mem.var'].get(self._uid, 'pic3mois_nb_semaines')
        # periodicite      = self.env['is.mem.var'].get(self._uid, 'pic3mois_periodicite')
        # affiche_col_vide = self.env['is.mem.var'].get(self._uid, 'pic3mois_affiche_col_vide')
        # nb_lig           = self.env['is.mem.var'].get(self._uid, 'pic3mois_nb_lig')

        if code_cli:
            SQL+=" AND rp.is_code='%s' "%(code_cli) 
        # if ($AdrCli!="")     $SQL="$SQL AND rp.is_adr_code='$AdrCli' "; 
        if code_pg:
            SQL+=" AND pt.is_code LIKE '%s%%' "%(code_pg) 
        # if ($Cat!="")        $SQL="$SQL AND ic.name='$Cat' "; 
        # if ($Gest!="")       $SQL="$SQL AND ig.name='$Gest' "; 
        # if ($RefCli!="")     $SQL="$SQL AND pt.is_ref_client LIKE '%$RefCli%' "; 
        # if ($ProdST=="ST")   $SQL="$SQL AND ig.name IN     ('03', '06', '07', '10', '12', '14') "; 
        # if ($ProdST=="PROD") $SQL="$SQL AND ig.name NOT IN ('03', '06', '07', '10', '12', '14') "; 


        # if ($Moule!="") {
        #     $Moule=trim($Moule);
        #     $tMoule=explode(",",$Moule);
        #     for ($i=0;$i<count($tMoule);$i++) {
        #         $rMoule=$rMoule."'".$tMoule[$i]."',";
        #     }
        #     $rMoule=substr($rMoule,0,strlen($r)-1);
        #     $SQL="$SQL AND (im.name IN ($rMoule) or id.name IN ($rMoule)) ";
        # }

        # if ($Projet!="")      { $SQL="$SQL AND (imp.name ilike '%$Projet%' or imp2.name ilike '%$Projet%') "; }
        # if ($TypeFP=="Ferme") { $SQL="$SQL AND sol.is_type_commande='ferme' "; }
        # if ($TypeFP=="Prev")  { $SQL="$SQL AND sol.is_type_commande='previsionnel' "; }

        # if ($TypeClient=="50xx")     $SQL="$SQL AND rp.is_code>='500000' AND rp.is_code<='599999' ";
        # if ($TypeClient=="70xx")     $SQL="$SQL AND rp.is_code>='700000' AND rp.is_code<='799999' ";
        # if ($TypeClient=="80xx")     $SQL="$SQL AND rp.is_code>='800000' AND rp.is_code<='899999' ";
        # if ($TypeClient=="90xx")     $SQL="$SQL AND rp.is_code>='900000' AND rp.is_code<='999999' ";
        # if ($TypeClient=="SaufPMTC") $SQL="$SQL AND rp.is_code>='900000' AND rp.is_code<>'907480' ";

        SQL+=" ORDER BY rp.is_code, im.name, pt.is_code limit 500"



        # $lig=0; $MemCodePG=""; $Qt=array(); $TotalCol=array();

        NbColMax = math.floor(int(nb_semaines)*7/int(periodicite))
        LaDate = datetime.now()
        JourSem = LaDate.weekday()
        DebSem = LaDate
        if periodicite!=1:
            DebSem = LaDate - timedelta(days=JourSem)
        print(nb_semaines, periodicite, NbColMax, LaDate, JourSem, DebSem, DebSem.strftime("%Y%m%d"))

        lig=0
        key=""
        

        cr.execute(SQL)
        result = cr.dictfetchall()
        lines={}
        trcolor=""
        #odoo={}

        for row in result:
            DebSemTxt = DebSem.strftime("%Y%m%d")
            if key!=row['is_code']:
                key=row['is_code']

                if trcolor=="#ffffff":
                    trcolor="#f2f3f4"
                else:
                    trcolor="#ffffff"
                trstyle="background-color:%s"%(trcolor)

                moule    = "LeMoule"
                lot_mini = "LotMini"
                vals={
                    "key"        : key,
                    "product_tmpl_id": row["product_tmpl_id"],
                    "trstyle"    : trstyle,
                    "trstyle"    : trstyle,
                    "row"        : row,
                    "moule"      : moule,
                    "lot_mini"   : lot_mini,
                }
                cols={}
                for col in range(1, NbColMax):
                    cols[col] = {"key":col, "qt":""}
                vals["cols"] = cols
                lines[key]=vals


            DateCde = row["is_date_livraison"] or datetime.now().date()
            DateCdeTxt =  DateCde.strftime("%Y%m%d")
            if DateCdeTxt<DebSemTxt:
                col=0
            else:
                nb_jours = (DateCde-DebSem.date()).days
                col=math.floor(nb_jours/int(periodicite))
                print( DateCde,DebSem,nb_jours,col)

            if col<NbColMax:
                qt = row['product_uom_qty']
                lines[key]["cols"][col] =  {"key":col, "qt":qt}

            lines[key]["listcols"] = list(lines[key]["cols"].values())




            # $T=$row['is_type_commande'];
            # $TheQt=$row['product_uom_qty']; // TODO: L'ancien programme tient compte des commandes déja livrées
            # $Qt[$lig][$col][$T]=$Qt[$lig][$col][$T]+$TheQt;
            # $Total=$Total+$TheQt;
            # $TotalCol[$col]=$TotalCol[$col]+$TheQt;
            # $TotalCol[$NbColMax]=$TotalCol[$NbColMax]+$TheQt;


            # $odoo[$i]['code_client']." / ".
            # $odoo[$i]['is_ref_client']." / ".
            # $odoo[$i]['client_order_ref']."<br />".
            # $Moule." / ".
            # $odoo[$i]['is_code']." / ".
            # $odoo[$i]['gestionnaire'].
            # " / <B>".number_format($odoo[$i]['stocka'],0,'.',' ')."</B> / ".
            # " / <B>".number_format($odoo[$i]['stockq'],0,'.',' ')."</B> / ".
            # number_format($lot_mini,0,'.',' ')." / ".
            # number_format($odoo[$i]['is_stock_secu'],0,'.',' ')." / ".
            # number_format($odoo[$i]['is_delai_transport'],0,'.',' ')."<br />".
            # $odoo[$i]['designation']."</td>";



            # code  = row["code"][0:6]
            # annee = row["annee"]
            # key = "%s-%s"%(code,annee)
            # mois  = row["mois"] and "m"+row["mois"][-2:] or ''
            # if key not in TabTmp1:
            #     if trcolor=="#ffffff":
            #         trcolor="#f2f3f4"
            #     else:
            #         trcolor="#ffffff"
            #     trstyle="background-color:%s"%(trcolor)
            #     vals={
            #         "key"            : key,
            #         "product_tmpl_id": row["product_tmpl_id"],
            #         "product_id"     : row["product_id"],
            #         "code"           : row["code"],
            #         "cat"            : row["cat"],
            #         "gest"           : row["gest"],
            #         "designation"    : row["designation"],
            #         "moule"          : row["moule"],
            #         "us"             : row["us"],
            #         "annee"          : row["annee"],
            #         "mois"           : row["mois"],
            #         "trstyle"        : trstyle,
            #     }
            #     cols={}
            #     for x in range(1, 13):
            #         col="m%02d"%(x)
            #         vals[col]=''
            #         cols[col] = {"key":col, "quantite":"", "mois":""}

            #     vals["cols"]=cols
            #     TabTmp1[key]=vals

            # if row["quantite"]:
            #     quantite = "{:,.0f}".format(row["quantite"]).replace(",", " ")
            #     TabTmp1[key]["cols"][mois] = {"key":mois, "mois":row["mois"], "quantite":quantite}
            # TabTmp1[key]["listcols"] = list(TabTmp1[key]["cols"].values())

        res={
            "lines"           : list(lines.values()),
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
        }
        return res

