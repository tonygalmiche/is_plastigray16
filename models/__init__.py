# -*- coding: utf-8 -*-
from . import account_invoice
from . import hr
from . import ir_actions_act_url
from . import is_analyse_cbn
from . import is_article
from . import is_bl_manuel
from . import is_bon_achat_ville
from . import is_bon_transfert
from . import is_capteur
from . import is_commande_externe
from . import is_cde_ferme_cadencee
from . import is_cde_ouverte_fournisseur  # TODO à finaliser
from . import is_certificat_conformite
from . import is_consigne_journaliere     # TODO : Liens avec odoo0, dynacase et les ordres de travaux => A revoir plus tard
from . import is_cout                     # TODO à finaliser
from . import is_ctrl100
from . import is_ctrl_budget_ana
from . import is_ctrl_budget_tdb
from . import is_database
from . import is_deb                      # TODO A revoir après la facturation client
from . import is_demande_achat_fg
from . import is_demande_achat_invest
from . import is_demande_achat_moule
from . import is_demande_achat_serie
from . import is_demande_transport
from . import is_donnee_machine
from . import is_dossier_appel_offre
from . import is_dossier_article
from . import is_dossierf
from . import is_edi_cde_cli          # TODO à finaliser
from . import is_equipement
from . import is_etuve
from . import is_export_cegid         # TODO à finaliser après la facturation
from . import is_export_edi           # TODO à finaliser
from . import is_facturation_fournisseur
from . import is_facture_pk
from . import is_facture_proforma
from . import is_facture_proforma_outillage
from . import is_fiche_tampographie
from . import is_gabarit_controle
from . import is_galia_base
from . import is_gestion_des_absences
from . import is_gestion_lot
from . import is_historique_controle
from . import is_import_budget_pk
from . import is_indicateur_revue_jalon
from . import is_instruction_particuliere
from . import is_instrument_mesure
from . import is_inventaire           # TODO à finaliser => Il n'y a plus le modele stock.inventory...
from . import is_invest
from . import is_liste_servir
from . import is_mem_var
from . import is_mini_delta_dore      # TODO à finaliser
from . import is_mode_operatoire
from . import is_mold
from . import is_mold_project
from . import is_ot
from . import is_pdc
from . import is_pic_3ans
from . import is_pic_3mois
from . import is_piece_montabilite
from . import is_plaquette_etalon
from . import is_pointage
from . import is_preventif
from . import is_preventif_equipement
from . import is_proforma_chine
from . import is_reach                # TODO A revoir après stock_picking
from . import is_resource
from . import is_rgpd
from . import is_tarif_cial
from . import is_theia
from . import is_taux_rotation_stock  # TODO A revoir plus tard
from . import mrp
from . import mrp_prevision
from . import mrp_production
from . import product
from . import product_pricelist
from . import purchase
from . import res_company
from . import res_country
from . import res_partner
from . import res_users
from . import sale
from . import stock



# TODO : is_pg_2019
# import is_gestion_des_absences_report TODO : A revoir avec l'analyse du CBN (Javascript)
# from . import is_head_model           TODO : Ne pas migrer pour le moment
# import auditlog                       TODO : A revoir avec l'installation du moule auditlog quant il sera dispo

# TODO : is_plastigray
# is_type_equipement                 TODO : N'est plus utilisé => Ne pas migrer
# import is_demande_achat            TODO : N'est plus utilisé => Ne pas migrer
# import is_moyen_fabrication        TODO : N'est plus utilisé => Ne pas migrer
# import is_moyen_fabrication_autre  TODO : N'est plus utilisé => Ne pas migrer
# import calendar                    TODO : N'est plus utilisé => Ne pas migrer
# import is_config                   TODO : Permet de configurer les modules après l'installation => Ne pas migrer
# import is_cout2                    TODO : A été ré-intégré dans is_cout
# import log                         TODO : A revoir avec l'installation du moule auditlog quant il sera dispo
# import sale_stock                  TODO : Il n'y rien à migrer dans ce fichier
# import sale_picking                TODO : à été migré dans stock.py
# from . import is_prechauffeur      TODO : Ce model est migré dans is_equipement
# from . import is_presse            TODO : Ce model est migré dans is_equipement

