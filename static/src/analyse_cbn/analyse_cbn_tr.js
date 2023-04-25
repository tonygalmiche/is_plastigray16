/** @odoo-module */
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const { onWillStart } = owl;

export class AnalyseCbnTr extends Component {

    setup() {
        this.user_id = useService("user").context.uid;
        this.orm     = useService("orm");
        this.is_code = "";
        this.designation = "";

        onWillStart(async () => {
            this.getAnalyseCbnTr();
        });
    } 

    async getAnalyseCbnTr(){
        var data = await this.orm.call("product.product", 'get_analyse_cbn_tr', [
            false,
            this.props.id,
        ]);
        //this.state.data=data;
        console.log("data=",data);
    }


    // onClick(ev) {
    //     console.log(ev);
    //     this.props.toggleState(this.props.id);
    // }
}
AnalyseCbnTr.template = "is_plastigray16.analyse_cbn_tr_template";
AnalyseCbnTr.props = {
    id: { type: Number },
    is_code: { type: String },
    designation: { type: String },
};







/*
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { getDefaultConfig } from "@web/views/view";
import { useService } from "@web/core/utils/hooks";

const { Component, useSubEnv, useState, onWillStart } = owl;

class AnalyseCbnTr extends Component {
    setup() {
        this.user_id = useService("user").context.uid;
        this.orm     = useService("orm");
        this.state   = useState({
            'analyse_cbn_codepg': '262703G',
            'data': false,
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
            this.getAnalyseCbnTr();
        });
    } 

    OKclick(ev) {
        console.log("OKclick",ev);
        this.getAnalyseCbnTr();
    }

    onChangeInput(ev) {
        console.log("onChangeInput",ev);
        this.state[ev.target.name] = ev.target.value;
        this.orm.call("is.mem.var", 'set', [false, this.user_id, ev.target.name, ev.target.value]);
    }

    OKkey(ev) {
        if (ev.keyCode === 13) {
            console.log("OKkey", ev.target.id, ev.target.value);
            this.getAnalyseCbnTr();
        }
    }


    async getAnalyseCbnTr(){
        var data = await this.orm.call("product.product", 'get_analyse_cbn_tr', [
            false,
            this.state.analyse_cbn_codepg,
        ]);
        this.state.data=data;
        console.log("data=",data);
    }
}
AnalyseCbnTr.components = {
    Layout,
};
AnalyseCbnTr.template = "is_plastigray16.analyse_cbn_tr_template";
registry.category("actions").add("is_plastigray16.analyse_cbn_registry", AnalyseCbnTr);
*/
