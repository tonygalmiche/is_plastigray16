/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { getDefaultConfig } from "@web/views/view";
import { useService } from "@web/core/utils/hooks";

const { Component, useSubEnv, useState, onWillStart } = owl;

class AnalyseCbn extends Component {
    setup() {
        this.user_id = useService("user").context.uid;
        this.orm     = useService("orm");
        this.state   = useState({
            'analyse_cbn_code_pg': false,
            'analyse_cbn_gest': false,
            'analyse_cbn_cat': false,
            'analyse_cbn_moule': false,
            'analyse_cbn_projet': false,
            'analyse_cbn_client': false,
            'analyse_cbn_fournisseur': false,
            'analyse_cbn_semaines': false,
            'analyse_cbn_type_cde': false,
            'analyse_cbn_type_rapport': false,
            'analyse_cbn_calage': false,
            'analyse_cbn_val': false,
            'lines': [],
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
            this.state.analyse_cbn_code_pg = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "analyse_cbn_code_pg"]);
            this.state.analyse_cbn_gest = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "analyse_cbn_gest"]);
            this.state.analyse_cbn_cat = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "analyse_cbn_cat"]);
            this.state.analyse_cbn_moule = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "analyse_cbn_moule"]);
            this.state.analyse_cbn_projet = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "analyse_cbn_projet"]);
            this.state.analyse_cbn_client = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "analyse_cbn_client"]);
            this.state.analyse_cbn_fournisseur = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "analyse_cbn_fournisseur"]);
            this.state.analyse_cbn_semaines = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "analyse_cbn_semaines"]);
            this.state.analyse_cbn_type_cde = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "analyse_cbn_type_cde"]);
            this.state.analyse_cbn_type_rapport = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "analyse_cbn_type_rapport"]);
            this.state.analyse_cbn_calage = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "analyse_cbn_calage"]);
            this.state.analyse_cbn_val = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "analyse_cbn_val"]);
            this.getAnalyseCbn();
        });
    } 

    OKclick(ev) {
        console.log("OKclick",ev);
        this.getAnalyseCbn();
    }

    onChangeInput(ev) {
        console.log("onChangeInput",ev);
        this.state[ev.target.name] = ev.target.value;
        this.orm.call("is.mem.var", 'set', [false, this.user_id, ev.target.name, ev.target.value]);
    }

    OKkey(ev) {
        if (ev.keyCode === 13) {
            console.log("OKkey", ev.target.id, ev.target.value);
            this.getAnalyseCbn();
        }
    }


    async getAnalyseCbn(){
        var lines = await this.orm.call("product.product", 'get_analyse_cbn', [
            false,
            this.state.analyse_cbn_code_pg,
            this.state.analyse_cbn_gest,
            this.state.analyse_cbn_cat,
            this.state.analyse_cbn_moule,
            this.state.analyse_cbn_projet,
            this.state.analyse_cbn_client,
            this.state.analyse_cbn_fournisseur,
            this.state.analyse_cbn_semaines,
            this.state.analyse_cbn_type_cde,
            this.state.analyse_cbn_type_rapport,
            this.state.analyse_cbn_calage,
            this.state.analyse_cbn_val,
        ]);

        this.state.lines=lines;
        console.log("lines=",lines);
    }
}




AnalyseCbn.components = { Layout };
AnalyseCbn.template = "is_plastigray16.analyse_cbn_template";
registry.category("actions").add("is_plastigray16.analyse_cbn_registry", AnalyseCbn);

