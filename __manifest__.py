# -*- coding: utf-8 -*-
{
    "name"     : "Module Odoo 16 pour Plastigray",
    "version"  : "0.1",
    "author"   : "InfoSaône",
    "category" : "InfoSaône",
    "description": """
Module Odoo 16 pour Plastigray
===================================================
""",
    "maintainer" : "InfoSaône",
    "website"    : "http://www.infosaone.com",
    "depends"    : [
        "base",
        "sale_management",
        "purchase",
        "hr",
        "stock",
        "mrp",
        "account",
        "l10n_fr",
        "l10n_fr_fec",
    ],
    "data" : [
        "security/res.groups.xml",
        #"security/res.groups.csv",

        "security/ir.model.access.csv",
        "security/is_demande_conges_security.xml",


        "report/is_stock_quant.xml",


        "views/is_gestion_lot_view.xml",




        "views/stock_view.xml",
        "views/stock_move_view.xml",


        "report/is_purchase_order_line.xml",


        "views/purchase_view.xml",


        "views/sale_view.xml",   # TODO : Il faut tout revoir dans les vues
        "views/resource_view.xml",



        "views/hr_view.xml",


        "views/is_article_view.xml",
        "views/is_bl_manuel_view.xml",
        "views/is_bon_achat_ville_view.xml",
        "views/is_bon_transfert_view.xml",
        "views/is_commande_externe_view.xml",
        "views/is_cde_ferme_cadencee_view.xml",
        "views/is_cde_ouverte_fournisseur_view.xml",
        "views/is_certificat_conformite_view.xml",
        #"views/is_consigne_journaliere_view.xml", TODO : Liens avec odoo0, dynacase et les ordres de travaux => A revoir plus tard
        "views/is_cout_view.xml",
        "views/is_ctrl100_view.xml",
        "views/is_ctrl_budget_ana_view.xml",
        "views/is_ctrl_budget_tdb_view.xml",
        "views/is_database_view.xml",
        "views/is_deb_view.xml",
        "views/is_demande_achat_fg_view.xml",
        "views/is_demande_achat_invest_view.xml",
        "views/is_demande_achat_moule_view.xml",
        "views/is_demande_achat_serie_view.xml",
        "views/is_demande_transport_view.xml",
        "views/is_dossier_appel_offre_view.xml",
        "views/is_dossier_article_view.xml",
        "views/is_dossierf_view.xml",
        "views/is_edi_cde_cli_view.xml",
        "views/is_export_cegid_view.xml",
        "views/is_export_edi_view.xml",
        "views/is_gabarit_controle_view.xml",
        # "views/is_gestion_des_absences_workflow.xml",
        "views/is_gestion_des_absences_view.xml",
        "views/is_import_budget_pk_view.xml",
        "views/is_indicateur_revue_jalon_view.xml",
        "views/is_instruction_particuliere_view.xml",
        "views/is_instrument_mesure_view.xml",
        "views/is_inventaire_view.xml",
        "views/is_invest_view.xml",
        "views/is_equipement_view.xml",
        "views/is_etuve_view.xml",
        "views/is_facturation_fournisseur_view.xml",
        "views/is_facture_proforma_view.xml",
        "views/is_facture_proforma_outillage_view.xml",
        "views/is_facture_pk_view.xml",
        "views/is_fiche_tampographie_view.xml",
        "views/is_galia_base_view.xml",
        "views/is_historique_controle_view.xml",
        "views/is_liste_servir_view.xml",


        "views/is_mem_var_view.xml",
        "views/is_mini_delta_dore_view.xml",
        "views/is_mode_operatoire_view.xml",
        "views/is_mold_view.xml",
        "views/is_mold_project_view.xml",
        #"views/is_ot_workflow.xml",
        "views/is_ot_view.xml",
        "views/is_pdc_view.xml",
        "views/is_pic_3ans.xml",
        "views/is_piece_montabilite_view.xml",
        "views/is_plaquette_etalon_view.xml",
        "views/is_pointage_view.xml",
        "views/is_preventif_view.xml",
        "views/is_preventif_equipement_view.xml",
        "views/is_proforma_chine_view.xml",
        "views/is_reach_view.xml",
        "views/is_rgpd_view.xml",
        "views/is_tarif_cial_view.xml",
        "views/is_theia_view.xml",
        "views/mrp_prevision_view.xml",
        "views/mrp_view.xml",
        "views/product_view.xml",
        "views/product_pricelist_view.xml", #TODO : A revoir car il y a eu besaucoup de changement sur les pricelist 

        "views/res_company_view.xml",
        "views/res_country_view.xml",
        "views/res_partner_view.xml",
        "views/res_users_view.xml",


        "views/is_donnee_machine_view.xml",
        "views/is_capteur_view.xml",

        "report/is_certifications_qualite_suivi.xml",
        "report/is_encres_utilisees_view.xml",
        "report/is_ligne_livraison.xml",
        "report/is_ligne_reception.xml",
        "report/is_livraison_gefco.xml",
        "report/is_pricelist_item.xml",
        "report/is_product_packaging.xml",

        "wizard/is_cas_emploi_wizard_new.xml",
        "wizard/is_liste_servir_wizard_view.xml",

        "views/menu.xml",





        # TODO is_pg_2019
        # "data/sequence.xml",
        # "security/res_groups.xml",
        # "security/ir_model_access_is_fiche_tampographie.xml",
        # "security/ir_model_access_is_ctrl100.xml",
        # "security/ot_security_view.xml",
        # "security/ir_model_access_is_bon_achat_ville.xml",
        # "views/auditlog_view.xml",
        # "views/bilan_fin_of_report.xml",
        # 'views/is_head_model_view.xml',
        # "views/is_ot_report.xml",
        # "views/is_presse_report.xml",
        # "views/is_proforma_chine_report.xml",
        # "views/report_gamme_defautheque.xml",
        # "views/report_gamme_qualite.xml",
        # "views/report_is_certificat_conformite.xml",
        # "views/report_is_ctrl100_rapport_controle.xml",
        # "views/report_is_ot_indicateur.xml",
        # "views/report_is_fiche_tampographie.xml",
        # "views/report_maintenance_preventive_niv2_a.xml",
        # "views/report_maintenance_preventive_niv2_b.xml",
        # "views/report_fiche_description_moule.xml",
        # "views/report_is_ctrl100_pareto.xml",
        # "views/report_is_bon_achat_ville.xml",
        # "views/report_is_facture_proforma.xml",
        # "views/report_is_facture_proforma_outillage.xml",
        # "views/report_preventif_equipement_zone.xml",
        # "views/report_paperformat.xml",
        # "views/report.xml",
        # "report/is_encres_utilisees_view.xml",
        # "wizard/server_action_view.xml",
        # "wizard/is_gestion_des_absences_wiz_view.xml",


        # "views/menu.xml",
        # "security/ir.model.access.csv",
        # "views/assets.xml",



        # TODO is_plastigray
        # "security/ir.model.access.csv",
        # "security/ir.model.access.xml", 
        # "security/ir.model.access.is.demande.achat.xml",
        # "security/ir.model.access.is.liste.servir.xml",
        # "assets.xml",
        # "account_invoice_view.xml",
        # "sale_picking_view.xml",
        # "mrp_production_view.xml",
        # "account_invoice_sequence.xml",
        # "log_view.xml",
        # "purchase_workflow.xml",
        # "email_template.xml",
        # "is_taux_rotation_stock_view.xml",
        # "calendar_view.xml",
        # "wizard/is_stock_mise_rebut_view.xml",
        # "wizard/generate_previsions_view.xml",
        # "wizard/mrp_product_produce_view.xml",
        # "wizard/is_export_seriem_view.xml",
        # "wizard/stock_transfer_details.xml",
        # "wizard/audit_log_wizard.xml",
        # "wizard/is_cas_emploi_wizard.xml",
        # "wizard/set_sheduler_cout_article.xml",
        # "wizard/assistent_report_view.xml",
        # "wizard/is_change_emplacement_wizard_view.xml",
        # "views/web_view.xml",
        # "views/layouts.xml",
        # "views/report_mrpbomstructure.xml",
        # "views/webclient_templates.xml",
        # "views/report_paperformat.xml",
        # "views/report_liste_servir.xml",
        # "views/report_inventaire.xml",
        # "views/report_inventaire_ecart.xml",
        # "views/report_stockpicking.xml",
        # "views/report_invoice.xml",
        # "views/report_cde_ouverte_fournisseur.xml",
        # "views/report_relance_fournisseur.xml",
        # "views/report_cde_ferme_cadencee.xml",
        # "views/report_appel_de_livraison.xml",
        # "views/report_document_fabrication.xml",
        # "views/report_plan_de_charge.xml",
        # "views/report_bon_transfert.xml",
        # "views/report_purchaseorder.xml",
        # "views/report_devis_commande.xml",
        # "views/report_ar_commande.xml",
        # "views/report_liste_article.xml",
        # "views/report_is_cout.xml",
        # "views/report_pricelist_version.xml",
        # "views/report_stockdetails_tree.xml",
        # "views/report_stockmovement_tree.xml",
        # "views/report_feuilles_inventaire.xml",
        # "views/report_is_instrument_mesure.xml",
        # "views/report_is_gabarit_controle.xml",
        # "views/report_is_plaquette_etalon.xml",
        # "views/report_is_demande_achat.xml",
        # "views/report_is_facture_pk.xml",
        # "views/report_is_consigne_journaliere.xml",
        # "views/report_is_inventaire_line_tree.xml",
        # "views/report_is_bl_manuel.xml",
        # "views/report_proforma.xml",
        # "views/report_is_facture_pk_line_tree.xml",
        # "views/report_emballage.xml",
        # "views/report_ligne_reception_tree.xml",
        # 'views/report_is_reach.xml',
        # 'views/report_is_livraison_gefbox_tree.xml',
        # 'views/report_galia_base.xml',
        # "views/report.xml",
        # "report/stock_debloquer_lot.xml",
        # "report/stock_change_location_lot.xml",
        # "report/stock_rebut_lot.xml",
        # "report/is_pic_3mois.xml",
        # "report/is_comparatif_gamme_standard_generique.xml",
        # "report/is_comparatif_tps_article_gamme.xml",
        # "report/is_comparatif_tarif_cial_vente.xml",
        # "report/is_comparatif_tarif_facture.xml",
        # "report/is_comparatif_tarif_commande.xml",
        # "report/is_comparatif_uc_lot.xml",
        # "report/is_comparatif_uc_lot_mini.xml",
        # "report/is_comparatif_lot_prix.xml",
        # "report/is_article_sans_nomenclature.xml",
        # "report/is_article_sans_fournisseur.xml",
        # "report/is_nomenclature_sans_gamme.xml",
        # "report/is_stock_valorise.xml",
        # "report/is_mouvement_stock.xml",
        # "report/is_users_groups.xml",
        # "report/is_model_groups.xml",
        # "report/is_stock_move.xml",
        # "report/is_comparatif_tarif_reception.xml",
        # "report/is_comparatif_livraison_facture.xml",
        # "report/is_comparatif_cde_draft_done.xml",
        # "report/is_account_invoice_line.xml",
        # "report/is_marge_contributive.xml",
        # "report/is_suivi_budget_analytique.xml",
        # "report/is_comparatif_lot_appro_prix.xml",
        # "report/is_comparatif_article_tarif_cial.xml",
        # "report/is_res_partner.xml",
        # "report/is_article_sans_cde_ouverte_fou.xml",
        # "report/is_anomalie_position_fiscale.xml",
        # "report/is_sale_order_line.xml",
        # "report/is_mrp_production_workcenter_line.xml",
        # "report/is_anomalie_declar_prod.xml",
        # "report/is_comparatif_cout_pk_tarif.xml",



    ], 
    "qweb": [
    ],
    "assets": {
         'web.assets_backend': [
            'is_plastigray16/static/src/styles.css',
            'is_plastigray16/static/src/scripts.js',
            'is_plastigray16/static/src/templates.xml',
         ]
    },
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}


        #"views/is_prechauffeur_view.xml",        TODO : Ce model est migré dans is_equipement
        #"views/is_presse_view.xml",              TODO : Ce model est migré dans is_equipement
        # "is_moyen_fabrication_view.xml"         TODO : Ce model est migré dans is_equipement
        # "is_moyen_fabrication_autre_view.xml",  TODO : Ce model est migré dans is_equipement
