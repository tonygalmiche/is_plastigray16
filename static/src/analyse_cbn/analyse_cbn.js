/** @odoo-module **/
import { AnalyseCbnTr } from "../analyse_cbn/analyse_cbn_tr";
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
            'analyse_cbn_codepg': false,
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
            this.state.analyse_cbn_codepg = await this.orm.call("is.mem.var", 'get', [false, this.user_id, "analyse_cbn_codepg"]);
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
            this.state.analyse_cbn_codepg,
        ]);
        this.state.lines=lines;
        console.log("lines=",lines);
    }
}




AnalyseCbn.components = {
    Layout,
    AnalyseCbnTr,
};
AnalyseCbn.template = "is_plastigray16.analyse_cbn_template";
registry.category("actions").add("is_plastigray16.analyse_cbn_registry", AnalyseCbn);

