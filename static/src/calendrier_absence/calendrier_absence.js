/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { getDefaultConfig } from "@web/views/view";
import { useService } from "@web/core/utils/hooks";

const { Component, useSubEnv, useState, onWillStart } = owl;

class CalendrierAbsence extends Component {
    setup() {
        this.user_id = useService("user").context.uid;
        this.action  = useService("action");
        this.orm     = useService("orm");
        this.state   = useState({
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
            this.getCalendrierAbsence();
        });
    } 


    
    
    SemainePrecedenteClick(ev) {
        console.log("SemainePrecedenteClick",ev);
        this.getCalendrierAbsence(true,true,false);


    }


    
    SemaineSuivanteClick(ev) {
        console.log("SemaineSuivanteClick",ev);
        this.getCalendrierAbsence(true,false,true);


    }


    OKclick(ev) {
        console.log("OKclick",ev);
        this.getCalendrierAbsence(true);
    }

    onChangeInput(ev) {
        console.log("onChangeInput",ev);
        this.state[ev.target.name] = ev.target.value;
    }

    OKkey(ev) {
        if (ev.keyCode === 13) {
            console.log("OKkey", ev.target.id, ev.target.value);
            this.getCalendrierAbsence(true);
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
        const res_model = ev.target.attributes.res_model.value;
        const res_id    = ev.target.attributes.res_id.value;
        console.log(res_model, res_id)
        this.action.doAction({
            type: 'ir.actions.act_window',
            target: 'current',
            res_id: parseInt(res_id),
            res_model: res_model,
            views: [[false, 'form']],
        });
    }


    async getCalendrierAbsence(ok=false, semaine_precedente=false, semaine_suivante=false){
        const params={
            "service"     : this.state.service,
            "poste"     : this.state.poste,
            "nom"     : this.state.nom,
            "n1"     : this.state.n1,
            "n2"     : this.state.n2,
            "date_debut"     : this.state.date_debut,
            "nb_jours"     : this.state.nb_jours,
            "ok"          : ok,
            "semaine_precedente": semaine_precedente,
            "semaine_suivante": semaine_suivante
        }

        var res = await this.orm.call("is.demande.conges", 'get_calendrier_absence', [false],params);

        this.state.titre            = res.titre;
        this.state.lines            = res.lines;
        this.state.date_cols        = res.date_cols;
        this.state.service          = res.service;
        this.state.poste            = res.poste;
        this.state.nom              = res.nom;
        this.state.n1               = res.n1;
        this.state.n2               = res.n2;
        this.state.date_debut       = res.date_debut;
        this.state.nb_jours         = res.nb_jours;
        this.state.nb_jours_options = res.nb_jours_options;
    }
}


CalendrierAbsence.components = { Layout };
CalendrierAbsence.template = "is_plastigray16.calendrier_absence_template";
registry.category("actions").add("is_plastigray16.calendrier_absence_registry", CalendrierAbsence);

// _name        = 'is.demande.conges'
