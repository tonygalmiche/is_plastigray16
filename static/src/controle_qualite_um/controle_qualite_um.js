/** @odoo-module **/

// Contrôle qualité des UM par scan : au toucher du champ Quantité (prérempli avec la quantité de l'UC),
// tout le contenu est sélectionné pour que la saisie le remplace au lieu de s'ajouter derrière
document.addEventListener("focusin", (ev) => {
    const input = ev.target;
    if (input instanceof HTMLInputElement && input.closest(".o_is_controle_qualite_um .o_field_widget[name='qt_saisie']")) {
        // Après le focus, sinon Chrome Android annule la sélection en plaçant le curseur
        setTimeout(() => input.select(), 0);
    }
});
