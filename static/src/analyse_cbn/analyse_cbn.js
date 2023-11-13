/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { getDefaultConfig } from "@web/views/view";
import { useService } from "@web/core/utils/hooks";

const { Component, useSubEnv, useState, onWillStart } = owl;

class AnalyseCbn extends Component {
    setup() {
        this.user_id = useService("user").context.uid;
        this.action  = useService("action");
        this.orm     = useService("orm");
        this.state   = useState({
            // 'analyse_cbn_code_pg': false,
            // 'analyse_cbn_gest': false,
            // 'analyse_cbn_cat': false,
            // 'analyse_cbn_moule': false,
            // 'analyse_cbn_projet': false,
            // 'analyse_cbn_client': false,
            // 'analyse_cbn_fournisseur': false,
            // 'analyse_cbn_semaines': false,
            // 'analyse_cbn_type_cde': false,
            // 'analyse_cbn_type_rapport': false,
            // 'analyse_cbn_calage': false,
            // 'analyse_cbn_val': false,
            //'lines': [],
            'dict': {},
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
            // this.state.analyse_cbn_code_pg = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "analyse_cbn_code_pg"]);
            // this.state.analyse_cbn_gest = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "analyse_cbn_gest"]);
            // this.state.analyse_cbn_cat = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "analyse_cbn_cat"]);
            // this.state.analyse_cbn_moule = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "analyse_cbn_moule"]);
            // this.state.analyse_cbn_projet = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "analyse_cbn_projet"]);
            // this.state.analyse_cbn_client = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "analyse_cbn_client"]);
            // this.state.analyse_cbn_fournisseur = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "analyse_cbn_fournisseur"]);
            // this.state.analyse_cbn_semaines = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "analyse_cbn_semaines"]);
            // this.state.analyse_cbn_type_cde = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "analyse_cbn_type_cde"]);
            // this.state.analyse_cbn_type_rapport = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "analyse_cbn_type_rapport"]);
            // this.state.analyse_cbn_calage = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "analyse_cbn_calage"]);
            // this.state.analyse_cbn_val = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "analyse_cbn_val"]);
            this.getAnalyseCbn();
        });
    } 

    OKclick(ev) {
        this.getAnalyseCbn(true);
    }

    onChangeInput(ev) {
        this.state[ev.target.name] = ev.target.value;
        //this.orm.call("is.mem.var", 'set', [false, this.user_id, ev.target.name, ev.target.value]);
    }

    OKkey(ev) {
        if (ev.keyCode === 13) {
            this.getAnalyseCbn(true);
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
        //var click=parseInt(ev.target.parentElement.attributes.click.value);
        var click=ev.target.parentElement.attributes.click;
        if (click!==undefined){
            click.value=-click.value
            if (click.value==1){
                ev.target.parentElement.style="background-color:rgb(204, 255, 204)";
            } else {
                const memstyle = ev.target.parentElement.attributes.memstyle.value;
                ev.target.parentElement.style=memstyle;
            }
            ev.target.parentElement.attributes.click.value=click.value;
        }
    }





    QtClick(ev) {
        const typeod = ev.target.attributes.name_typeod.value;
        const ids = ev.target.attributes.ids.value;
        const tids = ids.split(","); 
        const dict = {
            "CF": "sale.order",
            "CP": "sale.order",
            "FL": "mrp.production",
            "SF": "purchase.order",
            "FS": "mrp.prevision",
            "FM": "mrp.prevision",
            "FT": "mrp.prevision",
            "SA": "mrp.prevision",
        };
        const model = dict[typeod];
        if (model!==undefined){
            if(tids.length>1){
                this.action.doAction({
                    type: 'ir.actions.act_window',
                    //target: 'current',
                    target: 'new',
                    res_model: model,
                    views: [[false, 'list'], [false, 'form']],
                    domain: [['id', 'in', tids]],
                });
            } else {
                this.action.doAction({
                    type: 'ir.actions.act_window',
                    //target: 'current',
                    target: 'new',
                    res_id: parseInt(tids[0]),
                    res_model: model,
                    views: [[false, 'form']],
                });
            }
        }
    }


    // DeleteClick(ev) {
    //     const product_id = ev.target.attributes.productid.value;
    //     this.state.lines.forEach((item, index) => {
    //         if (item.product_id==product_id){
    //             this.state.lines.splice(index, 1);
    //         }
    //     })
    // }


    DeleteClick(ev) {
        const key = ev.target.attributes.key.value;
        console.log(key);
        console.log(this.state.dict);
        delete this.state.dict[key];
        //this.state.dict.splice(key, 1);
        // this.state.lines.forEach((item, index) => {
        //     if (item.product_id==product_id){
        //         this.state.lines.splice(index, 1);
        //     }
        // })
    }


    RefreshClick(ev) {
        const key = ev.target.attributes.key.value;
        //const product_id = ev.target.attributes.productid.value;
        this.state.dict[key];

        var Code = this.state.dict[key].Code+" => FAIT"
        this.state.dict[key].Code=Code;
        this.getAnalyseCbnProduct(key);


        // this.state.lines.forEach((item, index) => {
        //     if (item.product_id==product_id){
        //         var Code = this.state.lines[index].Code+" => FAIT"
        //         this.state.lines[index].Code=Code;
        //         this.getAnalyseCbnProduct(product_id);
        //     }
        // })
    }



    // RefreshClick(ev) {
    //     const product_id = ev.target.attributes.productid.value;
    //     this.state.lines.forEach((item, index) => {
    //         if (item.product_id==product_id){
    //             var Code = this.state.lines[index].Code+" => FAIT"
    //             this.state.lines[index].Code=Code;
    //             this.getAnalyseCbnProduct(product_id);
    //             //this.state.lines[index].typeodlist=[];
    //             //this.getAnalyseCbnProduct(true);
    //         }
    //     })
    // }



    async getAnalyseCbnProduct(key=false){
        const product_id =  this.state.dict[key].product_id
        const params={
            "product_id"  : product_id,
            "type_rapport": this.state.analyse_cbn_type_rapport,
        }
        var res = await this.orm.call("product.product", 'get_analyse_cbn', [false],params);
        console.log(res);
        this.state.dict[key] = res.dict[key];
    }

    async getAnalyseCbn(ok=false){
        const params={
            "code_pg"     : this.state.analyse_cbn_code_pg,
            "gest"        : this.state.analyse_cbn_gest,
            "cat"         : this.state.analyse_cbn_cat,
            "moule"       : this.state.analyse_cbn_moule,
            "projet"      : this.state.analyse_cbn_projet,
            "client"      : this.state.analyse_cbn_client,
            "fournisseur" : this.state.analyse_cbn_fournisseur,
            "semaines"    : this.state.analyse_cbn_semaines,
            "type_cde"    : this.state.analyse_cbn_type_cde,
            "type_rapport": this.state.analyse_cbn_type_rapport,
            "calage"      : this.state.analyse_cbn_calage,
            "valorisation": this.state.analyse_cbn_valorisation,
            "ok"          : ok,
        }
        var res = await this.orm.call("product.product", 'get_analyse_cbn', [false],params);

        // var lines = await this.orm.call("product.product", 'get_analyse_cbn', [
        //     false,
        //     this.state.analyse_cbn_code_pg,
        //     this.state.analyse_cbn_gest,
        //     this.state.analyse_cbn_cat,
        //     this.state.analyse_cbn_moule,
        //     this.state.analyse_cbn_projet,
        //     this.state.analyse_cbn_client,
        //     this.state.analyse_cbn_fournisseur,
        //     this.state.analyse_cbn_semaines,
        //     this.state.analyse_cbn_type_cde,
        //     this.state.analyse_cbn_type_rapport,
        //     this.state.analyse_cbn_calage,
        //     this.state.analyse_cbn_val,
        // ]);


        this.state.titre                    = res.titre;
        //this.state.lines                    = res.lines;
        this.state.dict                     = res.dict;
        this.state.date_cols                = res.date_cols;
        this.state.analyse_cbn_code_pg      = res.code_pg;
        this.state.analyse_cbn_gest         = res.gest;
        this.state.analyse_cbn_cat          = res.cat;
        this.state.analyse_cbn_moule        = res.moule;
        this.state.analyse_cbn_projet       = res.projet;
        this.state.analyse_cbn_client       = res.client;
        this.state.analyse_cbn_fournisseur  = res.fournisseur;
        this.state.analyse_cbn_semaines     = res.semaines;
        this.state.analyse_cbn_type_cde     = res.type_cde;
        this.state.analyse_cbn_type_rapport = res.type_rapport;
        this.state.analyse_cbn_calage       = res.calage;
        this.state.analyse_cbn_valorisation = res.valorisation;

        this.state.gest_options             = res.gest_options;
        this.state.fournisseur_options      = res.fournisseur_options;
        this.state.semaines_options         = res.semaines_options;
        this.state.type_cde_options         = res.type_cde_options;
        this.state.type_rapport_options     = res.type_rapport_options;
        this.state.calage_options           = res.calage_options;
        this.state.valorisation_options     = res.valorisation_options;

        console.log(this.state.dict);



    }
}




AnalyseCbn.components = { Layout };
AnalyseCbn.template = "is_plastigray16.analyse_cbn_template";
registry.category("actions").add("is_plastigray16.analyse_cbn_registry", AnalyseCbn);

