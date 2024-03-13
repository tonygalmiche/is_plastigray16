# -*- coding: utf-8 -*-
#from . import is_create_postgres_function # => J'ai déplacé les fonctions dans is_purchase_order_line.py en attendant de trovuer mieux

from . import is_purchase_order_line


from . import is_comparatif_tarif_reception
from . import is_comparatif_lot_prix
from . import is_comparatif_lot_appro_prix
from . import is_nomenclature_sans_gamme
from . import is_comparatif_tps_article_gamme
from . import is_comparatif_cout_pk_tarif
from . import is_comparatif_tarif_commande
from . import is_comparatif_tarif_cial_vente

from . import is_stock_valorise
from . import is_taux_rotation_stock
from . import is_account_invoice_line
from . import is_comparatif_livraison_facture
from . import is_article_sans_fournisseur
from . import is_article_sans_nomenclature
from . import is_certifications_qualite_suivi
from . import is_comparatif_article_tarif_cial
from . import is_comparatif_tarif_facture
from . import is_comparatif_uc_lot
from . import is_comparatif_uc_lot_mini
from . import is_encres_utilisees
from . import is_ligne_livraison
from . import is_ligne_reception
from . import is_livraison_gefco
from . import is_mrp_production_workcenter_line
from . import is_pricelist_item
from . import is_product_packaging
from . import is_res_partner
from . import is_sale_order_line
from . import is_stock_move
from . import is_stock_quant
from . import is_users_groups
from . import is_anomalie_position_fiscale
from . import is_marge_contributive
from . import is_article_sans_cde_ouverte_fou
from . import is_comparatif_gamme_standard_generique



# from . import is_anomalie_declar_prod
# import stock_debloquer_lot
# import stock_change_location_lot
# import stock_rebut_lot
# import is_pic_3mois
# import is_mouvement_stock
# import is_model_groups
# import is_comparatif_cde_draft_done
# import is_marge_contributive
# import is_suivi_budget_analytique



# import bom_structure TODO : Ne pas migrer pour le moment


