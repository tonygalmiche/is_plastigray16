/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { getDefaultConfig } from "@web/views/view";
import { useService } from "@web/core/utils/hooks";
import { memoize } from "@web/core/utils/functions";

export const Pic3MoisService = {
    dependencies: ["rpc"],
    async: ["loadPic3Mois"],
    start(env, { rpc }) {
        return {
            loadPic3Mois: memoize(() => rpc("/is_plastigray16/get_pic_3mois_route")),
        };
    },
};
registry.category("services").add("Pic3MoisService", Pic3MoisService);


const { Component, useSubEnv, useState, onWillStart } = owl;

class Pic3Mois extends Component {
    setup() {
        this.action  = useService("action");
        this.user_id = useService("user").context.uid;
        this.orm     = useService("orm");
        this.Pic3MoisService = useService("Pic3MoisService"); // Cache network calls with a service 
        this.state   = useState({
            //'lines': [],
            'dict' : {},
        });
        useSubEnv({
            config: {
                ...getDefaultConfig(),
                ...this.env.config,
            },
        });
        this.display = {
            controlPanel: { "top-right": false, "bottom-right": false },
        };
        onWillStart(async () => {
            console.log("onWillStart");
            //const res = await this.Pic3MoisService.loadPic3Mois(); //2.4 Cache network calls, create a service 
            //this.state.lines = res.lines;
            this.getPic3mois();
        });
    } 

    OKclick(ev) {
        //const res = $("[name='pic3mois_client']"); //$() permet de passer par jquery pour accèder au DOM, mais ce n'est pas conseillé
        this.getPic3mois(true);
    }

    clickCode(ev) {
        const product_id = parseInt(ev.target.attributes.productid.value);
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: product_id,
            target: 'current',
            res_id: product_id,
            res_model: 'product.template',
            views: [[false, 'form']],
        });

    }

    onChangeInput(ev) {
        console.log("onChangeInput",ev.target.name,ev.target.value);
        this.state[ev.target.name] = ev.target.value;
    }

    OKkey(ev) {
        if (ev.keyCode === 13) {
            this.getPic3mois(true);
        }
    }

    
    TrMouseLeave(ev) {
        const click=ev.target.attributes.click.value;
        if (click!="1"){
            const memstyle = ev.target.attributes.memstyle.value;
            ev.target.style=memstyle;
        }
    }

    TrMouseEnter(ev) {
        const click=ev.target.attributes.click.value;
        if (click!="1"){
            ev.target.style="background-color:#FFFF00";
        }
    }

    TrClick(ev) {

        console.log(ev.target.parentElement.attributes);
        console.log(ev.target.parentElement.attributes.click);

        var click=ev.target.parentElement.attributes.click
        if (click!==undefined){
            //var click=parseInt(ev.target.parentElement.attributes.click.value);
            click = click.value;

            // TypeError: ev.target.parentElement.attributes.click is undefined

            click=-click
            if (click==1){
                ev.target.parentElement.style="background-color:rgb(204, 255, 204)";
            } else {
                const memstyle = ev.target.parentElement.attributes.memstyle.value;
                ev.target.parentElement.style=memstyle;
            }
            ev.target.parentElement.attributes.click.value=click;
        }
    }
    


    QtClick(ev) {
        console.log(ev);
        //const typeod = ev.target.attributes.name_typeod.value;
        const ids = ev.target.attributes.ids.value;
        const tids = ids.split(","); 
        const model = "sale.order.line";
        if(tids.length>1){
            this.action.doAction({
                type: 'ir.actions.act_window',
                target: 'current',
                res_model: model,
                views: [[false, 'list'], [false, 'form']],
                domain: [['id', 'in', tids]],
            });
        } else {
            this.action.doAction({
                type: 'ir.actions.act_window',
                target: 'current',
                res_id: parseInt(tids[0]),
                res_model: model,
                views: [[false, 'form']],
            });
        }
    }




    async getPic3mois(ok=false){
        const params={
            "code_cli"        : this.state.pic3mois_code_cli,
            "adr_cli"         : this.state.pic3mois_adr_cli,
            "code_pg"         : this.state.pic3mois_code_pg,
            "cat"             : this.state.pic3mois_cat,
            "gest"            : this.state.pic3mois_gest,
            "ref_cli"         : this.state.pic3mois_ref_cli,
            "moule"           : this.state.pic3mois_moule,
            "projet"          : this.state.pic3mois_projet,
            "type_cde"        : this.state.pic3mois_type_cde,
            "type_client"     : this.state.pic3mois_type_client,
            "prod_st"         : this.state.pic3mois_prod_st,
            "nb_semaines"     : this.state.pic3mois_nb_semaines,
            "periodicite"     : this.state.pic3mois_periodicite,
            "affiche_col_vide": this.state.pic3mois_affiche_col_vide,
            "nb_lig"          : this.state.pic3mois_nb_lig,
            "ok"              : ok,
        }
        var res = await this.orm.call("sale.order", 'get_pic_3mois', [false],params);
        //this.state.lines                     = res.lines;
        this.state.dict                      = res.dict;
        this.state.date_cols                 = res.date_cols;
        this.state.pic3mois_code_cli         = res.code_cli;
        this.state.pic3mois_adr_cli          = res.adr_cli;
        this.state.pic3mois_code_pg          = res.code_pg;
        this.state.pic3mois_cat              = res.cat;
        this.state.pic3mois_gest             = res.gest;
        this.state.pic3mois_ref_cli          = res.ref_cli;
        this.state.pic3mois_moule            = res.moule;
        this.state.pic3mois_projet           = res.projet;
        this.state.pic3mois_type_cde          = res.type_cde;
        this.state.pic3mois_type_client       = res.type_client;
        this.state.pic3mois_prod_st           = res.prod_st;
        this.state.pic3mois_nb_semaines       = res.nb_semaines;
        this.state.pic3mois_periodicite       = res.periodicite;
        this.state.pic3mois_affiche_col_vide  = res.affiche_col_vide;
        this.state.pic3mois_nb_lig            = res.nb_lig;
        this.state.type_cde_options          = res.type_cde_options;
        this.state.type_client_options       = res.type_client_options;
        this.state.prod_st_options           = res.prod_st_options;
        this.state.nb_semaines_options       = res.nb_semaines_options;
        this.state.periodicite_options       = res.periodicite_options;
        this.state.affiche_col_vide_options  = res.affiche_col_vide_options;
        this.state.nb_lig_options            = res.nb_lig_options;
    }
}
Pic3Mois.components = {
    Layout,
};
Pic3Mois.template = "is_plastigray16.pic_3mois_template";
registry.category("actions").add("is_plastigray16.pic_3mois_registry", Pic3Mois);

