# -*- coding: utf-8 -*-
from odoo import models,fields,api # type: ignore
from odoo.tools.translate import _ # type: ignore
import datetime


_CINEMATIQUES={
    'standard':
"""- moule ouvert avec ejection contrôle rentré
- fermeture puis verrouillage
- cycle injection
- ouverture
- sortie ejection
- rentrée éjection
""",
    'avant_ejection':
"""- moule ouvert avec éjection contrôle rentrée et noyau sorti
- fermeture puis verrouillage
- cycle injection
- sortie noyau avec contrôle sortie
- ouverture
- sortie ejection
- rentrée éjection
""",
    'avant_ouverture':
"""- moule ouvert avec éjection contrôle rentré et noyau 1 rentré
- fermeture puis verrouillage
- cycle injection
- ouverture
- sortie noyau 1 avec contrôle sortie
- sortie éjection puis rentrée éjection avec contrôle rentré
- rentré noyau 1 avec contrôle rentré
""",
}

_NB_CIRCUIT_EAU = [
    ("0" , "0"),
    ("1" , "1"),
    ("2" , "2"),
    ("3" , "3"),
    ("4" , "4"),
    ("5" , "5"),
    ("6" , "6"),
    ("7" , "7"),
    ("8" , "8"),
    ("9" , "9"),
    ("10", "10"),
    ("11", "11"),
    ("12", "12"),
    ("13", "13"),
    ("14", "14"),
    ("15", "15"),
]


class is_mold_dateur(models.Model):
    _name='is.mold.dateur'
    _description = "Dateur Moule"
    _order='mold_id,type_dateur'

    mold_id = fields.Many2one('is.mold', 'Moule', required=True, ondelete='cascade', readonly=True)
    type_dateur = fields.Selection([
            ('dateur_grille'    , u'dateur à grille'),
            ('dateur_laiton'    , u'dateur laiton'),
            ('dateur_fleche'    , u'dateur à fleche'),
            ('dateur_specifique', u'dateur spécifique'),
            ('pas_de_dateur'    , u'pas de dateur'),
        ], "Type de dateur",required=True)
    qt_dans_moule   = fields.Integer("Quantité dans le moule",required=True)
    diametre_dateur = fields.Selection([
            ('d3' , u'Ø3'),
            ('d4' , u'Ø4'),
            ('d5' , u'Ø5'),
            ('d6' , u'Ø6'),
            ('d8' , u'Ø8'),
            ('d10', u'Ø10'),
            ('d12', u'Ø12'),
            ('d14', u'Ø14'),
            ('d16', u'Ø16'),
            ('d18', u'Ø18'),
            ('d20', u'Ø20'),
        ], "Diamètre dateur")
    date_peremption = fields.Date("Date de péremption")
    commentaire     = fields.Char("Commentaire")


class IsMoldBridage(models.Model):
    _name = 'is.mold.bridage'
    _description = u"Bridage moule"
    _order='name'
    name = fields.Char(u'Bridage',index=True,required=True)


class is_mold(models.Model):
    _name='is.mold'
    _inherit=['mail.thread']
    _description = "Moule"
    _order='name'
    _sql_constraints = [('name_uniq','UNIQUE(name)', 'Ce moule existe deja')]

    @api.depends('cinematique')
    def _compute_cinematique(self):
        for obj in self:
            description = ''
            if obj.cinematique in _CINEMATIQUES:
                description = _CINEMATIQUES[obj.cinematique]
            obj.cinematique_description = description

    @api.depends('bridage_ids')
    def _compute_bridage_specifique_vsb(self):
        for obj in self:
            vsb=False
            for line in obj.bridage_ids:
                if line.name=='Spécifique':
                    vsb=True
            obj.bridage_specifique_vsb = vsb

    name             = fields.Char("N°Moule",size=40,required=True, index=True)
    designation      = fields.Char("Désignation", tracking=True)
    project          = fields.Many2one('is.mold.project', 'Projet', tracking=True)
    client_id        = fields.Many2one('res.partner', 'Client'        , store=True, compute='_compute_chef_projet_id')
    chef_projet_id   = fields.Many2one('res.users'  , 'Chef de projet', store=True, compute='_compute_chef_projet_id')
    dossierf_id      = fields.Many2one('is.dossierf', 'Dossier F', tracking=True)
    dossierf_ids     = fields.Many2many("is.dossierf", "is_mold_dossierf_rel", "mold_id", "dossierf_id", u"Dossiers F")
    nb_empreintes    = fields.Char("Nb empreintes", tracking=True, help="Nombre d'empreintes du moule (Exemple : 1+1)")
    moule_a_version  = fields.Selection([('oui', u'Oui'),('non', u'Non')], "Moule à version", tracking=True)
    lieu_changement  = fields.Selection([('sur_presse', u'sur presse'),('en_mecanique', u'en mécanique')], "Lieu de changement", tracking=True)
    temps_changement = fields.Float("Temps de changement de la version (H)", tracking=True)
    nettoyer         = fields.Boolean('Nettoyage moule avant production', tracking=True)
    nettoyer_vis     = fields.Boolean('Nettoyage vis avant production', tracking=True)
    date_creation    = fields.Date("Date de création", default=lambda *a: fields.datetime.now(), tracking=True)
    date_fin         = fields.Date("Date de fin", tracking=True)
    mouliste_id      = fields.Many2one('res.partner', 'Mouliste', tracking=True)
    carcasse         = fields.Char("Carcasse", tracking=True)
    emplacement      = fields.Char("Emplacement", tracking=True)
    type_dateur      = fields.Selection([
            ('dateur_grille'    , u'dateur à grille'),
            ('dateur_laiton'    , u'dateur laiton'),
            ('dateur_fleche'    , u'dateur à fleche'),
            ('dateur_specifique', u'dateur spécifique'),
            ('pas_de_dateur'    , u'pas de dateur'),
        ], "Type de dateur", tracking=True)
    dateur_specifique = fields.Char("Commentaire sur dateur spécifique", tracking=True)
    date_peremption   = fields.Date("Date de péremption", tracking=True)
    qt_dans_moule     = fields.Integer("Quantité dans le moule", tracking=True)
    diametre_laiton   = fields.Selection([
            ('d3' , u'Ø3'),
            ('d4' , u'Ø4'),
            ('d5' , u'Ø5'),
            ('d6' , u'Ø6'),
            ('d8' , u'Ø8'),
            ('d10', u'Ø10'),
            ('d12', u'Ø12'),
        ], "Diamètre dateur laiton", tracking=True)
    diametre_fleche  = fields.Selection([
            ('d4' , u'Ø4'),
            ('d5' , u'Ø5'),
            ('d6' , u'Ø6'),
            ('d8' , u'Ø8'),
            ('d10', u'Ø10'),
            ('d12', u'Ø12'),
            ('d14', u'Ø14'),
            ('d16', u'Ø16'),
            ('d18', u'Ø18'),
            ('d20', u'Ø20'),
        ], "Diamètre dateur fleche", tracking=True)
    dateur_ids     = fields.One2many('is.mold.dateur', 'mold_id', u"Dateurs", tracking=True)
    dateur_ids_vsb = fields.Boolean('Dateurs vsb', store=False, compute='_compute_dateur_ids_vsb')
    is_database_id         = fields.Many2one('is.database', "Site", tracking=True)
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True, copy=False)

    numero_plaquette_interne = fields.Char(u"N° Plaquette interne client", tracking=True)

    largeur   = fields.Integer(u"Largeur (mm)", tracking=True)
    hauteur   = fields.Integer(u"Hauteur (mm)", tracking=True)
    epaisseur = fields.Integer(u"Epaisseur (mm)", tracking=True)

    largeur_hors_tout   = fields.Integer(u"Largeur hors tout (mm)", tracking=True)
    hauteur_hors_tout   = fields.Integer(u"Hauteur hors tout (mm)", tracking=True)
    epaisseur_hors_tout = fields.Integer(u"Epaisseur hors tout (mm)", tracking=True)

    poids = fields.Integer(u"Poids (Kg)", tracking=True)

    nb_zones_utiles = fields.Char(u"Nombre de zones utiles sur le bloc chaud", tracking=True)

    recu_de_buse = fields.Selection([
            ("standard"  , u"Standard = cône 90°"),
            ("spherique" , u"Standard = sphérique"),
            ("specifique", u"Spécifique"),
        ], "Reçu de buse", tracking=True)
    recu_de_buse_specifique = fields.Char(u"Reçu de buse spécifique", tracking=True)

    diametre_entree_cheminee = fields.Selection([
            ("04"        , u"4.5 = Standard Plastigray"),
            ("05"        , u"5.5 = Standard Plastigray"),
            ("06"        , u"6.5 = Standard Plastigray"),
            ("specifique", u"Spécifique"),
        ], u"Diamètre entrée cheminée", tracking=True)
    diametre_entree_cheminee_specifique = fields.Char(u"Diamètre entrée cheminée spécifique", tracking=True)

    bridage_ids            = fields.Many2many("is.mold.bridage", "is_mold_bridage_rel", "mold_id", "bridage_id", u"Bridage")
    bridage_specifique_vsb = fields.Text(u"Bridage spécifique vsb", compute='_compute_bridage_specifique_vsb')
    bridage_specifique     = fields.Char(u"Bridage spécifique", tracking=True)

    ejection = fields.Selection([
            ("standard"    , u"Standard Plastigray (queue diam 60)"),
            ("autonome"    , u"Autonome (hydraulique)"),
            ("pas_ejection", u"Pas d'éjection"),
            ("specifique"  , u"Spécifique"),
        ], "Ejection", tracking=True)
    ejection_specifique = fields.Char(u"Ejection spécifique", tracking=True)

    diametre_passage_matiere = fields.Integer(u"Ø de passage matière", tracking=True)
    type_matiere_transformee = fields.Selection([
            ("amorphe"    , u"amorphe"),
            ("cristalline", u"cristalline"),
        ], u"Type de matière transformée", tracking=True)
    embout_buse_longueur = fields.Selection([
            ("38mm", u"38mm"),
            ("70mm", u"70mm"),
            ("95mm", u"95mm"),
        ], u"Longueur ", tracking=True)
    type_de_portee = fields.Selection([
            ("conique90", u"conique à 90°"),
            ("rayon9"   , u"rayon de 9mm"),
        ], u"Type de portée", tracking=True)

    rondelle_centrage_fixe = fields.Selection([
            ("standard"     , u"Standard Plastigray : 100"),
            ("specifique"   , u"Spécifique"),
            ("sans_rondelle", u"Sans rondelle"),
        ], "Rondelle de centrage - Partie fixe", tracking=True)
    rondelle_centrage_fixe_specifique = fields.Char(u"Rondelle de centrage - Partie fixe spécifique")

    rondelle_centrage_mobile = fields.Selection([
            ("standard"     , u"Standard Plastigray : 100"),
            ("specifique"   , u"Spécifique"),
            ("sans_rondelle", u"Sans rondelle"),
        ], "Rondelle de centrage - Partie mobile", tracking=True)
    rondelle_centrage_mobile_specifique = fields.Char(u"Rondelle de centrage - Partie mobile spécifique", tracking=True)

    presse_ids = fields.Many2many("is.equipement", "is_mold_presse_rel", "mold_id", "presse_id", u"Presses", domain=[('type_id.code', '=', 'PE')])

    nb_noyaux_fixe = fields.Selection([
            ("0", "0"),
            ("1", "1"),
            ("2", "2"),
            ("3", "3"),
        ], "Nombre de noyaux - Partie fixe", tracking=True)
    nb_noyaux_fixe_commentaire = fields.Char(u"Nombre de noyaux - Partie fixe - Commentaire", tracking=True)
    nb_noyaux_mobile = fields.Selection([
            ("0", "0"),
            ("1", "1"),
            ("2", "2"),
            ("3", "3"),
        ], "Nombre de noyaux - Partie mobile", tracking=True)
    nb_noyaux_mobile_commentaire = fields.Char(u"Nombre de noyaux - Partie mobile - Commentaire", tracking=True)

    nb_circuit_eau_fixe = fields.Selection(_NB_CIRCUIT_EAU, "Nombre de circuits d'eau - Partie fixe", tracking=True)
    nb_circuit_eau_fixe_commentaire = fields.Char(u"Nombre de circuits d'eau - Partie fixe - Commentaire", tracking=True)
    nb_circuit_eau_mobile = fields.Selection(_NB_CIRCUIT_EAU, "Nombre de circuits d'eau - Partie mobile", tracking=True)
    nb_circuit_eau_mobile_commentaire = fields.Char(u"Nombre de circuits d'eau - Partie mobile - Commentaire", tracking=True)

    cinematique = fields.Selection([
            ("standard"  , u"Standard : Cycle sans HM"),
            ("specifique", u"Spécifique"),
        ], "Cinématique", tracking=True)
    cinematique_description = fields.Text(u"Cinématique - Description", compute='_compute_cinematique', readonly=True, store=True)
    cinematique_specifique  = fields.Text(u"Cinématique - Spécifique", tracking=True)

    fiche_description_commentaire = fields.Text(u"Commentaire", tracking=True)

    fiche_description_indice        = fields.Char(u"Indice", tracking=True)
    fiche_description_createur_id   = fields.Many2one("res.users", "Créateur", tracking=True)
    fiche_description_date_creation = fields.Date(u"Date de création fiche", tracking=True)
    fiche_description_date_modif    = fields.Date(u"Date de modification", tracking=True)

    date_dernier_preventif        = fields.Date(u"Date dernier préventif", tracking=True, copy=False)
    nb_cycles_dernier_preventif   = fields.Integer(u"Nb cycles dernier préventif", tracking=True, copy=False)
    nb_cycles_actuel              = fields.Integer(u"Nb cycles actuel", tracking=True, copy=False)
    nb_cycles_avant_preventif     = fields.Integer(u"Nb cycles avant préventif", tracking=True, copy=False)
    periodicite_maintenance_moule = fields.Integer(u"Périodicité maintenance moule (nb cycles)", tracking=True)
    gamme_preventif_ids           = fields.Many2many('ir.attachment', 'is_mold_attachment_rel', 'mold_id', 'file_id', u"Gamme préventif")
    preventif_inactif             = fields.Boolean(u"Préventif inactif suite FDV", tracking=True, default=False)
    is_base_check                 = fields.Boolean(string="Is Base", compute="_check_base_db")
    is_preventif_moule            = fields.One2many('is.preventif.moule', 'moule', u'Préventif Moule')
    systematique_ids              = fields.One2many('is.mold.systematique.array', 'mold_id',  u'Opérations systématiques')
    specifique_ids                = fields.One2many('is.mold.specifique.array', 'mold_id',  u'Opérations spécifiques')
    specification_ids             = fields.One2many('is.mold.specification.array', 'mold_id',  u'Spécifications particulières')
    piece_specifique_ids          = fields.Many2many('is.mold.piece.specifique', 'is_mold_piece_specifique_rel', 'mold_id', 'piece_spec_id', u"Pièces spécifiques de rechange en stock")
    surface_aspect_id             = fields.Many2one('is.mold.surface.aspect', u"Surface d'aspect", tracking=True)
    reference_grain               = fields.Char(string=u'Référence du grain utilisé', tracking=True)
    graineur_id                   = fields.Many2one('res.partner', string='Graineur', domain="[('supplier','=',True)]", tracking=True)
    diametre_seuil                = fields.Char(string=u'Diamètre seuil', tracking=True)
    fournisseur_bloc_chaud_id     = fields.Many2one('res.partner', string='Fournisseur du bloc chaud', domain="[('supplier','=',True)]", tracking=True)
    num_systeme                   = fields.Char(string=u'N° du système', tracking=True)
    garantie_outillage            = fields.Char(string=u"Garantie de l'outillage (en nombre de cycles)", tracking=True)
    extension_garantie            = fields.Char(string=u"Extension de garantie", tracking=True)
    indice_creation_fiche         = fields.Char(string='Indice Fiche', default='A', tracking=True)
    createur_fiche_id             = fields.Many2one("res.users", string=u'Créateur Fiche', tracking=True)
    date_creation_fiche           = fields.Date(string=u'Date Création Fiche', tracking=True)
    date_modification_fiche       = fields.Date(string='Date Modfication Fiche', tracking=True)
    active      = fields.Boolean("Active", default=True, copy=False, tracking=True)
    dynacase_id = fields.Integer(string="Id Dynacase",index=True,copy=False)


    def write(self, vals):
        res=super().write(vals)
        for obj in self:
            self.env['is.database'].copy_other_database(obj)
        return res
            
    @api.model_create_multi
    def create(self, vals_list):
        res=super().create(vals_list)
        self.env['is.database'].copy_other_database(res)
        return res

    def get_copy_other_database_vals(self, DB, USERID, USERPASS, sock):
        vals ={
            'name'             : self.name,
            'designation'      : self.designation,
            'project'          : self._get_project(DB, USERID, USERPASS, sock),
            'dossierf_id'      : self._get_dossierf_id(DB, USERID, USERPASS, sock),
            'dossierf_ids'     : self._get_dossierf_ids(DB, USERID, USERPASS, sock),
            'nb_empreintes'    : self.nb_empreintes,
            'moule_a_version'  : self.moule_a_version,
            'lieu_changement'  : self.lieu_changement,
            'temps_changement' : self.temps_changement,
            'nettoyer'         : self.nettoyer,
            'nettoyer_vis'     : self.nettoyer_vis,
            'date_creation'    : self.date_creation,
            'date_fin'         : self.date_fin,
            'mouliste_id'      : self._get_mouliste_id(DB, USERID, USERPASS, sock),
            'carcasse'         : self.carcasse,
            'emplacement'      : self.emplacement or '',
            'type_dateur'      : self.type_dateur,
            'dateur_specifique': self.dateur_specifique,
            'date_peremption'  : self.date_peremption,
            'qt_dans_moule'    : self.qt_dans_moule,
            'diametre_laiton'  : self.diametre_laiton,
            'diametre_fleche'  : self.diametre_fleche,
            'garantie_outillage': self.garantie_outillage,
            'extension_garantie': self.extension_garantie,
            'is_database_id'        : self._get_is_database_id(DB, USERID, USERPASS, sock),
            'is_database_origine_id': self.id,
            'active'                : self.active,
        }
        return vals

    def _get_project(self, DB, USERID, USERPASS, sock):
        if self.project:
            ids = sock.execute(DB, USERID, USERPASS, 'is.mold.project', 'search', [('is_database_origine_id', '=', self.project.id)])
            if not ids:
                self.env['is.database'].copy_other_database(self.projec)
                ids = sock.execute(DB, USERID, USERPASS, 'is.mold.project', 'search', [('is_database_origine_id', '=', self.project.id)])
            if ids:
                return ids[0]
        return False

    def _get_dossierf_id(self, DB, USERID, USERPASS, sock):
        if self.dossierf_id:
            ids = sock.execute(DB, USERID, USERPASS, 'is.dossierf', 'search', [('is_database_origine_id', '=', self.dossierf_id.id)])
            if ids:
                self.env['is.database'].copy_other_database(self.dossierf_id)
                ids = sock.execute(DB, USERID, USERPASS, 'is.dossierf', 'search', [('is_database_origine_id', '=', self.dossierf_id.id)])
            if ids:
                return ids[0]
        return False

    def _get_dossierf_ids(self, DB, USERID, USERPASS, sock):
        list_dossierf_ids =[]
        for dossierf in self.dossierf_ids:
            ids = sock.execute(DB, USERID, USERPASS, 'is.dossierf', 'search', [('is_database_origine_id', '=', dossierf.id)])
            if ids:
                list_dossierf_ids.append(ids[0])
        return [(6, 0, list_dossierf_ids)]

    def _get_mouliste_id(self, DB, USERID, USERPASS, sock):
        if self.mouliste_id:
            ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', self.mouliste_id.id),'|',('active','=',True),('active','=',False)])
            if not ids:
                self.env['is.database'].copy_other_database(self.mouliste_id)
                ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', self.mouliste_id.id),'|',('active','=',True),('active','=',False)])
            if ids:
                return ids[0]
        return False


    def _get_is_database_id(self, DB, USERID, USERPASS, sock):
        if self.is_database_id:
            ids = sock.execute(DB, USERID, USERPASS, 'is.database', 'search', [('is_database_origine_id', '=', self.is_database_id.id)])
            if ids:
                return ids[0]
        return False


    def vers_nouveau_preventif_mold(self):
        for data in self:
            context = dict(self.env.context or {})
            context['moule'] = data.id
            return {
                'name': u"Préventif Moule",
                'view_mode': 'form',
                'res_model': 'is.preventif.moule',
                'type': 'ir.actions.act_window',
                'domain': '[]',
                'context': context,
            }
        return True


    def default_get(self, default_fields):
        res = super(is_mold, self).default_get(default_fields)
        res['is_base_check'] = False
        user_obj = self.env['res.users']
        user_data = user_obj.browse(self._uid)
        if user_data and user_data.company_id.is_base_principale:
            res['is_base_check'] = True
        systematique_obj = self.env['is.mold.operation.systematique']
        systematique_ids = systematique_obj.search([('active', '=', True)])
        systematique_lst = []
        for num in systematique_ids:
            systematique_lst.append((0,0, {
                'operation_systematique_id': num.id,
                'activer'                  : True,
            }))
        res['systematique_ids'] = systematique_lst
        specifique_obj = self.env['is.mold.operation.specifique']
        specifique_ids = specifique_obj.search([('active', '=', True)])
        specifique_lst = []
        for num in specifique_ids:
            specifique_lst.append((0,0, {
                'operation_specifique_id': num.id,
                'activer'                : False,
            }))
        res['specifique_ids'] = specifique_lst
        specification_obj = self.env['is.mold.specification.particuliere']
        specification_ids = specification_obj.search([('active', '=', True)])
        specification_lst = []
        for num in specification_ids:
            specification_lst.append((0,0, {
                'specification_particuliere_id': num.id,
                'activer'                      : False,
            }))
        res['specification_ids'] = specification_lst
        return res

    @api.depends()
    def _check_base_db(self):
        for obj in self:
            user_obj = self.env['res.users']
            user_data = user_obj.browse(self._uid)
            check=False
            if user_data and user_data.company_id.is_base_principale:
                check = True
            obj.is_base_check = check

    @api.depends('project','project.client_id','project.chef_projet_id')
    def _compute_chef_projet_id(self):
        for obj in self:
            client_id=chef_projet_id=False
            if obj.project:
                client_id      = obj.project.client_id
                chef_projet_id = obj.project.chef_projet_id
            obj.client_id      = client_id
            obj.chef_projet_id = chef_projet_id


    @api.depends('name')
    def _compute_dateur_ids_vsb(self):
        for obj in self:
            uid=self._uid
            user=self.env['res.users'].browse(uid)
            company=user.company_id
            vsb=False
            if company.is_base_principale:
                vsb=True
            obj.dateur_ids_vsb=vsb


    def copy(self, default=None):
        if not default:
            default={}
        default["name"] = '%s (copy)'%(self.name)
        return super(is_mold, self).copy(default=default)


    def actualiser_chef_de_projet_action(self):
        for obj in self:
            if obj.project:
                if not obj.client_id:
                    obj.client_id = obj.project.client_id.id
                if not obj.chef_projet_id:
                    obj.chef_projet_id = obj.project.chef_projet_id.id


    def action_acceder_moule(self):
        for obj in self:
            return {
                'name': "Moule",
                'view_mode': 'form',
                'res_model': 'is.mold',
                'type': 'ir.actions.act_window',
                'res_id': obj.id,
                'domain': '[]',
            }


