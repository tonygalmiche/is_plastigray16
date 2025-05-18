# -*- coding: utf-8 -*-

from odoo import models,fields,api


class res_company(models.Model):
    _inherit = 'res.company'

    is_mysql_pwd    = fields.Char('Mot de passe MySQL')
    is_dynacase_pwd = fields.Char('Mot de passe Dynacase')
    is_cpta_pwd     = fields.Char('Mot de passe AS400 CPTA')

    is_postgres_host = fields.Char('Serveur Postgres')
    is_postgres_user = fields.Char('Utilisateur Postgres')
    is_postgres_pwd  = fields.Char('Mot de passe Postgres')

    is_logo         = fields.Binary("Logo", help="Logo utilisé dans les documents (BL, facures,..)")
    bg_color        = fields.Char('Background color')
    text_color      = fields.Char('Text color')
    is_nb_threads   = fields.Integer('Nombre de coeurs à utiliser dans les programmes', default=1)

    is_url_intranet_odoo  = fields.Char('URL Intranet Odoo' , default='http://odoo')
    is_url_intranet_theia = fields.Char('URL Intranet THEIA', default='http://raspberry-cpi')
    is_url_odoo_theia     = fields.Char('URL Odoo THEIA')

    is_directeur_general_id      = fields.Many2one('res.users', 'Directeur Général'                     , help="Utilisé en particulier pour les DA Investissements")
    is_directeur_technique_id    = fields.Many2one('res.users', 'Directeur Technique'                   , help="Utilisé en particulier pour les DA Moules")
    is_acheteur_id               = fields.Many2one('res.users', 'Acheteur'                              , help="Utilisé en particulier pour transformer les SA en DAS")
    is_gest_demande_transport_id = fields.Many2one('res.users', 'Gestionnaire des demandes de transport', help="Utilisé pour envoyer un mail lors de la création d'une demande de transport")
    is_assistante_commerciale_id = fields.Many2one('res.users', 'Assistante commerciale'                , help="Utilisé pour envoyer un mail dans les dossiers commerciaux")

    is_base_principale = fields.Boolean('Base principale (Primaire)', help="Cette case permet de masquer certains champs sur les bases répliquées si elle n'est pas cochée")

    is_code_societe      = fields.Char('Code société')
    is_dest_bilan_of_ids = fields.Many2many('res.users', 'is_res_company_users_rel', 'res_company_id','user_id', string="Destinataires du bilan de fin d'OF")
    is_cout_ctrl_qualite = fields.Float("Coût horaire vendu contrôle qualité", digits=(12, 2))

    is_dossier_interface_cegid = fields.Char("Dossier de destination pour le fichier d'interface de CEGID")

    is_sms_account  = fields.Char('SMS account')
    is_sms_login    = fields.Char('SMS login')
    is_sms_password = fields.Char('SMS password')
    is_sms_from     = fields.Char('SMS from')

    is_calendrier_expedition_id = fields.Many2one('res.partner', 'Calendrier Expéditions', domain=[('is_company','=',True),('is_adr_code','=','EXP')], help="Calendrier utilisé dans le calcul de la date d'expédition des commandes des clients (code adresse=EXP)")
    is_annee_pic_3ans           = fields.Char('Année PIC à 3 ans', help='Paramètre utilisé en particulier pour Analyse / Taux de rotation des stocks')
    is_cachet_plastigray        = fields.Binary("Cachet de Plastigray", help="Utilisé pour imprimer les certificats matière fournisseur")

    is_agenda_url = fields.Char('URL Google Agenda')
    is_agenda_pwd = fields.Char('Mot de passe admin Google Agenda')

    is_responsable_rh_id = fields.Many2one('res.users', string='Responsable RH')
    is_zebra_id = fields.Many2one('is.raspberry.zebra', "Imprimante Zebra", help="Utilisé pour imprimer les étiquettes des équipements")
    is_activer_init = fields.Boolean('Activer les fonctions init des modèles', default=True, help="Désactiver cette option en mode développement pour accélérer la mise à jour du module")
    
    is_temps_effectif_par_jour = fields.Float("Temps effectif par jour (H)", digits=(12, 2), default=7.66, help="Utilisé dans la gestion des congés")

    is_mdp_reimprimer = fields.Char('Mot de passe pour ré-imprimer étiquette Galia')
    is_mdp_quantite   = fields.Char('Mot de passe pour modifier quantité étiquette Galia')

    is_nom_base_odoo0 = fields.Char('Nom de la base principale (odoo0)')
    is_url_odoo0      = fields.Char('URL base principale pour XMLRCP (odoo0)')
    is_login_admin    = fields.Char('Login admin Odoo')
    is_mdp_admin      = fields.Char('Mot de passe admin Odoo')

    is_url_facture_owork = fields.Char("URL factures O'Work")

    is_taux_devise_dinar = fields.Float("Taux devise dinar" , digits=(12, 4), help="Utilisé pour la facturation PK")
    is_taux_commission   = fields.Float("Taux de commission", digits=(12, 4), help="Utilisé pour la facturation PK")

    is_cegid_ip    = fields.Char('IP du serveur CEGID')
    is_cegid_base  = fields.Char('Nom base CEGID')
    is_cegid_login = fields.Char('Login base CEGID')
    is_cegid_mdp   = fields.Char('Mot de passe base CEGID')


    def write(self, vals):
        base_group_id = self.env.ref('base.group_user')
        principale_grp_id = self.env.ref('is_plastigray16.is_base_principale_grp')
        secondaire_grp_id = self.env.ref('is_plastigray16.is_base_secondaire_grp')
        if vals and vals.get('is_base_principale'):
            principale_grp_id.write({'users': [(4, user) for user in base_group_id.users.ids]})
            secondaire_grp_id.write({'users': [(5, user) for user in base_group_id.users.ids]})
        if vals.get('is_base_principale') == False:
            secondaire_grp_id.write({'users': [(4, user) for user in base_group_id.users.ids]})
            principale_grp_id.write({'users': [(5, user) for user in base_group_id.users.ids]})
        return super(res_company, self).write(vals)


    def annee_pic_3ans_action(self):
        for obj in self:
            self.env['is.taux.rotation.stock.new'].annee_pic_3ans_action()


class res_partner_bank(models.Model):
    _inherit = 'res.partner.bank'

    is_bank_swift = fields.Char('Code swift')
