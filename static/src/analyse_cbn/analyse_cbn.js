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
            this.getAnalyseCbn();
        });
    } 

    OKclick(ev) {
        this.getAnalyseCbn(true);
    }


    ExcelClick(ev) {
        const excel_attachment_id = ev.target.attributes.excel_attachment_id.value;
        this.action.doAction({
            type: 'ir.actions.act_url',
            url: '/web/content/'+excel_attachment_id+'?download=true',
        });
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
        var pre = $(ev.target).parent().find('pre').first();
        if (pre.css('display', )=='none'){
            pre.css('display', 'inline'); /* on affiche l'infobulle */
        } else {
            pre.css('display', 'none');   /* on masque l'infobulle */
        }
    }


    DeleteClick(ev) {
        const key = ev.target.attributes.key.value;
        delete this.state.dict[key];
    }


    RefreshClick(ev) {
        const key = ev.target.attributes.key.value;
        this.state.dict[key];
        var Code = this.state.dict[key].Code+" => FAIT"
        this.state.dict[key].Code=Code;
        this.getAnalyseCbnProduct(key);
    }


    VoirODClick(ev) {
        const numod  = ev.target.attributes.numod.value;
        const typeod = ev.target.attributes.name_typeod.value;
        const pre = $(ev.target).parent().parent();
        pre.css('display', 'none');   /* on masque l'infobulle */
        this.VoirOD(typeod,numod)
        // const dict = {
        //     "CF": "sale.order",
        //     "CP": "sale.order",
        //     "FL": "mrp.production",
        //     "SF": "purchase.order",
        //     "FS": "mrp.prevision",
        //     "FM": "mrp.prevision",
        //     "FT": "mrp.prevision",
        //     "SA": "mrp.prevision",
        // };
        // const model = dict[typeod];
        // if (model!==undefined){
        //     this.action.doAction({
        //         type: 'ir.actions.act_window',
        //         target: 'new',
        //         res_id: parseInt(numod),
        //         res_model: model,
        //         views: [[false, 'form']],
        //     });
        // }
    }

    VoirOD(typeod,numod) {
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
            this.action.doAction({
                type: 'ir.actions.act_window',
                target: 'new',
                res_id: parseInt(numod),
                res_model: model,
                views: [[false, 'form']],
            });
        }
    }



    ProductClick(ev){
        const product_tmpl_id  = ev.target.attributes.product_tmpl_id.value;
        this.action.doAction({
            type: 'ir.actions.act_window',
            target: 'new',
            res_id: parseInt(product_tmpl_id),
            res_model: 'product.template',
            views: [[false, 'form']],
        });
    }


    ConvertirODClick(ev) {
        const pre = $(ev.target).parent().parent();
        pre.css('display', 'none');   /* on masque l'infobulle */
        const result = confirm("Voulez-vous vraiment convertir cet OD en FL ou SA ?");
        if (result){
            const key    = ev.target.attributes.key.value;
            const numod  = ev.target.attributes.numod.value;
            const typeod = ev.target.attributes.name_typeod.value;
            this.ConvertirOD(key,typeod,numod);
        }
    }
    async ConvertirOD(key,typeod,numod){
        if (typeod=='SA') {
            var res = await this.orm.call("mrp.prevision", 'convertir_sa', [parseInt(numod)]);
        }
        if (typeod=='FS') {
            var res = await this.orm.call("mrp.prevision", 'convertir_fs', [parseInt(numod)]);
        }
        this.getAnalyseCbnProduct(key);
    }


    DupliquerODClick(ev) {
        const pre = $(ev.target).parent().parent();
        pre.css('display', 'none');   /* on masque l'infobulle */
        const result = confirm("Voulez-vous vraiment dupliquer cet OD ?");
        if (result){
            const key    = ev.target.attributes.key.value;
            const numod  = ev.target.attributes.numod.value;
            const typeod = ev.target.attributes.name_typeod.value;
            this.DupliquerOD(key,typeod,numod);
        }
    }
    async DupliquerOD(key,typeod,numod){
        if (typeod=='FS' || typeod=='SA') {
            var res = await this.orm.call("mrp.prevision", 'copy', [parseInt(numod)]);
            console.log('res=',res);
            this.VoirOD(typeod,res)
            this.getAnalyseCbnProduct(key);
        }
    }

    DeleteODClick(ev) {
        const pre = $(ev.target).parent().parent();
        pre.css('display', 'none');   /* on masque l'infobulle */
        const result = confirm("Voulez-vous vraiment supprimer cet OD ?");
        if (result){
            const key    = ev.target.attributes.key.value;
            const numod  = ev.target.attributes.numod.value;
            const typeod = ev.target.attributes.name_typeod.value;
            this.DeleteOD(key,typeod,numod);
        }
    }
    async DeleteOD(key,typeod,numod){
        if (typeod=='FS' || typeod=='SA') {
            var res = await this.orm.call("mrp.prevision", 'unlink', [parseInt(numod)]);
            this.getAnalyseCbnProduct(key);
        }
    }


    async getAnalyseCbnProduct(key=false){
        const product_id =  this.state.dict[key].product_id
        const params={
            "product_id"  : product_id,
            "type_rapport": this.state.analyse_cbn_type_rapport,
        }
        var res = await this.orm.call("product.product", 'get_analyse_cbn', [false],params);
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
        this.state.titre                    = res.titre;
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
        this.state.excel_attachment_id      = res.excel_attachment_id


        // Tentative d'enregistrer dans un coockie, mais la limite de 4096 est bien trop faible (Besoin de 8 Mo)
        // var cookie = "analyse_cbn="+JSON.stringify(this.state.dict);
        // cookie = cookie.substring(0, 2000); 
        // document.cookie = cookie;
    }
}

AnalyseCbn.components = { Layout };
AnalyseCbn.template = "is_plastigray16.analyse_cbn_template";
registry.category("actions").add("is_plastigray16.analyse_cbn_registry", AnalyseCbn);

