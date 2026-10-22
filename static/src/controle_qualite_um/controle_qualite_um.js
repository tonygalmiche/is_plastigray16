/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";

// Contrôle qualité des UM par scan : au toucher du champ Quantité (prérempli avec la quantité de l'UC),
// tout le contenu est sélectionné pour que la saisie le remplace au lieu de s'ajouter derrière
document.addEventListener("focusin", (ev) => {
    const input = ev.target;
    if (input instanceof HTMLInputElement && input.closest(".o_is_controle_qualite_um .o_field_widget[name='qt_saisie']")) {
        // Après le focus, sinon Chrome Android annule la sélection en plaçant le curseur
        setTimeout(() => input.select(), 0);
    }
});

// Sur smartphone (Zebra TC22), pas de barre du haut (fil d'Ariane, roue crantée, pager) pour gagner de la place,
// comme Odoo le fait dans les fenêtres popup. Le retour à la liste se fait par un bouton en bas de la fiche
patch(FormController.prototype, "is_plastigray16.controle_qualite_um", {
    setup() {
        this._super(...arguments);
        if (this.props.resModel === "is.controle.qualite.um" && this.env.isSmall) {
            this.display.controlPanel = false;
        }
    },
});
