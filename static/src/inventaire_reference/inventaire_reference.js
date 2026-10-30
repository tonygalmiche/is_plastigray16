/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";

// Inventaire d'une référence : sur smartphone (Zebra TC22), pas de barre du haut (fil d'Ariane, roue crantée, pager)
// pour gagner de la place. Le retour à la liste se fait par un bouton en bas de la fiche
patch(FormController.prototype, "is_plastigray16.inventaire_reference", {
    setup() {
        this._super(...arguments);
        if (this.props.resModel === "is.inventaire.reference" && this.env.isSmall) {
            this.display.controlPanel = false;
        }
    },
});
