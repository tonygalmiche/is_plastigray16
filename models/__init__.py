# -*- coding: utf-8 -*-
from . import is_bl_manuel
from . import is_bon_transfert
from . import is_commande_externe
from . import is_cde_ouverte_fournisseur  # TODO à finaliser
#from . import is_consigne_journaliere      TODO : Liens avec odoo0, dynacase et les ordres de travaux => A revoir plus tard
from . import is_copy_other_database
from . import is_deb                      # TODO A revoir après la facturation client
from . import is_demande_achat_fg
from . import is_demande_achat_invest
from . import is_demande_achat_moule
from . import is_demande_achat_serie
from . import is_demande_transport
from . import is_dossierf
from . import is_export_cegid         # TODO à finaliser après la facturation
from . import is_export_edi           # TODO à finaliser
from . import is_facture_pk
from . import is_gabarit_controle
from . import is_galia_base
from . import is_historique_controle
from . import is_instruction_particuliere
from . import is_instrument_mesure
from . import is_liste_servir
from . import is_mem_var
from . import is_mini_delta_dore      # TODO à finaliser
from . import is_mold
from . import is_mold_project
from . import is_piece_montabilite
from . import is_plaquette_etalon
from . import is_pointage
from . import is_prechauffeur
from . import is_presse
from . import is_reach               #TODO A revoir après stock_picking
from . import is_rgpd
#from . import is_taux_rotation_stock TODO A revoir plus tard
from . import product
from . import res_company
from . import res_partner
from . import is_tarif_cial
from . import is_etuve

#TODO model à migrer de is_plastigray

# import is_edi_cde_cli
# import is_inventaire
# import is_cout
# import is_cout2
# import is_pdc
# import is_cde_ferme_cadencee
# import is_pic_3ans
# import is_facturation_fournisseur
# import is_article
# import mrp_prevision


# import product_pricelist
# import product_pricelist_new_api
# import sale
# import sale_picking
# import sale_stock
# import mrp
# import stock
# import account_invoice
# import mrp_production
# import purchase
# import res_country
# import res_users
# import log
# import ir_actions_act_url
# import hr
# import calendar

# #TODO : Une fois la période de tests terminé, il faudra supprimer l'ancienne version
# import is_analyse_cbn
# import is_analyse_cbn2

# import report
# import wizard

# import is_resource                 TODO : Voir s'il faut migrer ce module ou pas
# import is_demande_achat            TODO : N'est plus utilisé => Ne pas migrer
# import is_moyen_fabrication        TODO : N'est plus utilisé => Ne pas migrer
# import is_moyen_fabrication_autre  TODO : N'est plus utilisé => Ne pas migrer
# import is_config                   TODO : Permet de configurer les modules après l'installation => Ne pas migrer

