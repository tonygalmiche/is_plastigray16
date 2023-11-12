/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { getDefaultConfig } from "@web/views/view";
import { useService } from "@web/core/utils/hooks";
//import { memoize } from "@web/core/utils/functions";

const { Component, useSubEnv, useState, onWillStart } = owl;


class Pic3Ans extends Component {
    setup() {
        this.action  = useService("action");
        this.user_id = useService("user").context.uid;
        this.orm     = useService("orm");
        this.state   = useState({
            'pic3ans_client': false,
            'pic3ans_fournisseur': false,
            'pic3ans_codepg': false,
            'pic3ans_cat': false,
            'pic3ans_gest': false,
            'pic3ans_moule': false,
            'pic3ans_annee_realise': false,
            'pic3ans_annee_prev': false,
            //'lines': [],
            'dict':{},
        });
        // PIC/PDP
        // Nb Lignes/Page
        
        // The useSubEnv below can be deleted if you're > 16.0
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
            this.state.pic3ans_client        = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "pic3ans_client"]);
            this.state.pic3ans_fournisseur   = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "pic3ans_fournisseur"]);
            this.state.pic3ans_codepg        = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "pic3ans_codepg"]);
            this.state.pic3ans_cat           = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "pic3ans_cat"]);
            this.state.pic3ans_gest          = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "pic3ans_gest"]);
            this.state.pic3ans_moule         = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "pic3ans_moule"]);
            this.state.pic3ans_annee_realise = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "pic3ans_annee_realise"]);
            this.state.pic3ans_annee_prev    = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "pic3ans_annee_prev"]);
            //const memoized1 = memoize(this.getPic3ans());
            this.getPic3ans();

        });
    } 

    OKclick(ev) {
        this.getPic3ans();
    }

    OKclickQt(ev) {
        const product_id = parseInt(ev.target.attributes.productid.value);
        const mois       = ev.target.attributes.mois.value;
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: product_id,
            target: 'current',
            res_model: 'is.pic.3ans',
            views: [[false, 'tree'],[false, 'form']],
            domain: [
                ['mois'       ,'=',mois],
                ['product_id' ,'=',product_id],
                ['type_donnee','=','pic'],
            ],
        });
    }

    OKclickCode(ev) {
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
        this.state[ev.target.name] = ev.target.value;
        this.orm.call("is.mem.var", 'set', [false, this.user_id, ev.target.name, ev.target.value]);
    }

    OKkey(ev) {
        if (ev.keyCode === 13) {
            this.getPic3ans();
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

        var click=ev.target.parentElement.attributes.click
        if (click!==undefined){
            //var click=parseInt(ev.target.parentElement.attributes.click.value);
            click = click.value;
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


    async getPic3ans(){
        var res = await this.orm.call("is.pic.3ans", 'get_pic_3ans', [
            false,
            this.state.pic3ans_client,
            this.state.pic3ans_fournisseur,
            this.state.pic3ans_codepg,
            this.state.pic3ans_cat,
            this.state.pic3ans_gest,
            this.state.pic3ans_moule,
            this.state.pic3ans_annee_realise,
            this.state.pic3ans_annee_prev,
        ]);
        //this.state.lines=res.list;
        this.state.dict=res.dict;
        // console.log(Object.keys(res.dict));
        // console.log(Object.values(res.dict));
        // this.state.lines.forEach(function (line) {
        //     console.log("line=",line);
        // });
        
    }

}
Pic3Ans.components = {
    Layout,
};
Pic3Ans.template = "is_pic_3ans.pic_3ans_template";
registry.category("actions").add("is_pic_3ans.pic_3ans_registry", Pic3Ans);

