# -*- coding: utf-8 -*-
from odoo import models,fields,api,tools,SUPERUSER_ID
from datetime import datetime
#import xmlrpclib


class is_presse_classe(models.Model):
    _name='is.presse.classe'
    _description="Classe presse"
    _order='name'

    name = fields.Char(string='Classe commerciale')
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
   
    # def write(self, vals):
    #     try:
    #         res=super(is_presse_classe, self).write(vals)
    #         for obj in self:
    #             obj.copy_other_database_presse_classe()
    #         return res
    #     except Exception as e:
    #         raise osv.except_osv(_('Classe!'),
    #                          _('(%s).') % str(e).decode('utf-8'))


    # def create(self, vals):
    #     try:
    #         obj=super(is_presse_classe, self).create(vals)
    #         obj.copy_other_database_presse_classe()
    #         return obj
    #     except Exception as e:
    #         raise osv.except_osv(_('Classe!'),
                            #  _('(%s).') % str(e).decode('utf-8'))
            
    def copy_other_database_presse_classe(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for classe in self:
            for database in database_lines:
                if not database.ip_server or not database.database or not database.port_server or not database.login or not database.password:
                    continue
                DB = database.database
                USERID = SUPERUSER_ID
                DBLOGIN = database.login
                USERPASS = database.password
                DB_SERVER = database.ip_server
                DB_PORT = database.port_server
                sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object' % (DB_SERVER, DB_PORT))
                presse_classe_vals = self.get_presse_classe_vals(classe, DB, USERID, USERPASS, sock)
                dest_presse_classe_ids = sock.execute(DB, USERID, USERPASS, 'is.presse.classe', 'search', [('is_database_origine_id', '=', classe.id)], {})
                if not dest_presse_classe_ids:
                    dest_presse_classe_ids = sock.execute(DB, USERID, USERPASS, 'is.presse.classe', 'search', [('name', '=', classe.name)], {})
                if dest_presse_classe_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.presse.classe', 'write', dest_presse_classe_ids, presse_classe_vals, {})
                    presse_classe_created_id = dest_presse_classe_ids[0]
                else:
                    presse_classe_created_id = sock.execute(DB, USERID, USERPASS, 'is.presse.classe', 'create', presse_classe_vals, {})
        return True


    def get_presse_classe_vals(self, classe, DB, USERID, USERPASS, sock):
        controle_gabarit_vals ={
                     'name' : tools.ustr(classe.name),
                     'is_database_origine_id':classe.id,
                     }
        return controle_gabarit_vals
   



class is_presse_puissance(models.Model):
    _name='is.presse.puissance'
    _description="Puissance presse"
    _order='name'

    name                   = fields.Char(string='Puissance')
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    
    
    # def write(self, vals):
    #     try:
    #         res=super(is_presse_puissance, self).write(vals)
    #         for obj in self:
    #             obj.copy_other_database_presse_puissance()
    #         return res
    #     except Exception as e:
    #         raise osv.except_osv(_('Puissance!'),
    #                          _('(%s).') % str(e).decode('utf-8'))

    # def create(self, vals):
    #     try:
    #         obj=super(is_presse_puissance, self).create(vals)
    #         obj.copy_other_database_presse_puissance()
    #         return obj
    #     except Exception as e:
    #         raise osv.except_osv(_('Puissance!'),
    #                          _('(%s).') % str(e).decode('utf-8'))
            
    def copy_other_database_presse_puissance(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for puissance in self:
            for database in database_lines:
                if not database.ip_server or not database.database or not database.port_server or not database.login or not database.password:
                    continue
                DB = database.database
                USERID = SUPERUSER_ID
                DBLOGIN = database.login
                USERPASS = database.password
                DB_SERVER = database.ip_server
                DB_PORT = database.port_server
                sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object' % (DB_SERVER, DB_PORT))
                presse_puissance_vals = self.get_presse_puissance_vals(puissance, DB, USERID, USERPASS, sock)
                dest_presse_puissance_ids = sock.execute(DB, USERID, USERPASS, 'is.presse.puissance', 'search', [('is_database_origine_id', '=', puissance.id)], {})
                if not dest_presse_puissance_ids:
                    dest_presse_puissance_ids = sock.execute(DB, USERID, USERPASS, 'is.presse.puissance', 'search', [('name', '=', puissance.name)], {})
                if dest_presse_puissance_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.presse.puissance', 'write', dest_presse_puissance_ids, presse_puissance_vals, {})
                    presse_puissance_created_id = dest_presse_puissance_ids[0]
                else:
                    presse_puissance_created_id = sock.execute(DB, USERID, USERPASS, 'is.presse.puissance', 'create', presse_puissance_vals, {})
        return True

    @api.model
    def get_presse_puissance_vals(self, puissance, DB, USERID, USERPASS, sock):
        presse_puissance_vals ={
                     'name' : tools.ustr(puissance.name),
                     'is_database_origine_id':puissance.id,
                     }
        return presse_puissance_vals


class is_outillage_constructeur(models.Model):
    _name='is.outillage.constructeur'
    _description="Outillage constructeur"
    _order='name'

    name = fields.Char(string='Name')
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    
    # def write(self, vals):
    #     try:
    #         res=super(is_outillage_constructeur, self).write(vals)
    #         for obj in self:
    #             obj.copy_other_database_outillage_constructeur()
    #         return res
    #     except Exception as e:
    #         raise osv.except_osv(_('Constructeur!'),
    #                          _('(%s).') % str(e).decode('utf-8'))


    # def create(self, vals):
    #     try:
    #         obj=super(is_outillage_constructeur, self).create(vals)
    #         obj.copy_other_database_outillage_constructeur()
    #         return obj
    #     except Exception as e:
    #         raise osv.except_osv(_('Constructeur!'),
    #                          _('(%s).') % str(e).decode('utf-8'))
            
    def copy_other_database_outillage_constructeur(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for constructeur in self:
            for database in database_lines:
                if not database.ip_server or not database.database or not database.port_server or not database.login or not database.password:
                    continue
                DB = database.database
                USERID = SUPERUSER_ID
                DBLOGIN = database.login
                USERPASS = database.password
                DB_SERVER = database.ip_server
                DB_PORT = database.port_server
                sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object' % (DB_SERVER, DB_PORT))
                outillage_constructeur_vals = self.get_outillage_constructeur_vals(constructeur, DB, USERID, USERPASS, sock)
                dest_outillage_constructeur_ids = sock.execute(DB, USERID, USERPASS, 'is.outillage.constructeur', 'search', [('is_database_origine_id', '=', constructeur.id)], {})
                if not dest_outillage_constructeur_ids:
                    dest_outillage_constructeur_ids = sock.execute(DB, USERID, USERPASS, 'is.outillage.constructeur', 'search', [('name', '=', constructeur.name)], {})
                if dest_outillage_constructeur_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.outillage.constructeur', 'write', dest_outillage_constructeur_ids, outillage_constructeur_vals, {})
                    outillage_constructeur_created_id = dest_outillage_constructeur_ids[0]
                else:
                    outillage_constructeur_created_id = sock.execute(DB, USERID, USERPASS, 'is.outillage.constructeur', 'create', outillage_constructeur_vals, {})
        return True

    def get_outillage_constructeur_vals(self, constructeur, DB, USERID, USERPASS, sock):
        outillage_constructeur_vals ={
                     'name' : tools.ustr(constructeur.name),
                     'is_database_origine_id':constructeur.id,
                     }
        return outillage_constructeur_vals


class is_presse(models.Model):
    _name='is.presse'
    _description="Presse"
    _order='name'
    _sql_constraints = [('name_uniq','UNIQUE(name)', u'Ce code existe déjà')]

    name        = fields.Char(string='Numéro de presse')
    designation = fields.Char(string='Désignation')
    classe = fields.Selection([
        ('1','1'),
        ('2','2'),
        ('3','3'),
        ('4','4'),
        ('5','5'),
        ('6','6'),
    ], string='Classe')
    emplacement        = fields.Many2one('is.emplacement.outillage', string='Emplacement ')
    classe_commerciale = fields.Many2one('is.presse.classe'        , string='Classe commerciale')
    puissance          = fields.Many2one('is.presse.puissance'     , string='Puissance')
    puissance_reelle   = fields.Char(string='Puissance réelle (T)')
    type_de_presse     = fields.Char(string='Type de presse')
    constructeur       = fields.Many2one('is.outillage.constructeur', string='Constructeur')
    num_construceur    = fields.Char(string='N° constructeur')
    type_commande      = fields.Char(string='Type de commande')
    annee              = fields.Char(string='Année')
    energie = fields.Selection([
        ('electrique' , 'Electrique'),
        ('hydraulique', 'Hydraulique'),
        ('hybride'    , 'Hybride'),
    ], string='Energie')
    volume_tremie       = fields.Char(string='Volume trémie')
    volume_alimentateur = fields.Char(string='Volume alimentateur')
    dimension_col_h     = fields.Char(string='Dimension entre col H')
    dimension_col_v     = fields.Char(string='Dimension entre col V')
    diametre_colonne    = fields.Char(string='Ø colonne')
    epaisseur_moule     = fields.Char(string='Épaisseur moule Mini presse')
    faux_plateau = fields.Selection([
        ('oui','Oui'),
        ('non','Non'),
    ], string='Faux plateau')
    epaisseur_faux_plateau   = fields.Char(string='Épaisseur faux plateau')
    epaisseur_moule_mini     = fields.Char(string='Épaisseur moule mini réel')
    epaisseur_moule_maxi     = fields.Char(string='Épaisseur moule Maxi')
    dimension_plateau_h      = fields.Char(string='Dimension demi plateau H')
    dimension_plateau_v      = fields.Char(string='Dimension demi plateau V')
    dimension_hors_tout_haut = fields.Char(string='Dimension hors tout Haut')
    dimension_hors_tout_bas  = fields.Char(string='Dimension hors tout Bas')
    coefficient_vis          = fields.Char(string='Coefficient de vis')
    diametre_vis             = fields.Char(string='Ø Vis')
    type_clapet = fields.Selection([
        ('clapet_bille','clapet à bille'),
        ('clapet_2_branches','clapet à bague 2 branches'),
        ('clapet_3_branches','clapet à bague 3 branches'),
        ('clapet_4_branches','clapet à bague 4 branches'),
    ], string='Type de clapet')
    volume_injectable        = fields.Char(string='Volume injectable (cm3)')
    presse_matiere           = fields.Char(string='Pression matière (bar)')
    course_ejection          = fields.Char(string='Course éjection')
    course_ouverture         = fields.Char(string='Course ouverture')
    diametre_centrage_moule  = fields.Char(string='Ø centrage moule')
    diametre_centrage_presse = fields.Char(string='Ø centrage presse')
    hauteur_porte_sol        = fields.Char(string='Hauteur porte / sol')
    bridage_rapide           = fields.Char(string='Bridage rapide entre axe')
    diametre_bridage         = fields.Char(string='Ø')
    pas_bridage              = fields.Char(string='Pas')
    type_huile_hydraulique = fields.Selection([
        ('RSL46','RSL46'),
        ('RSL68','RSL68'),
    ], string='Type huile hydraulique')
    volume_reservoir     = fields.Char(string='Volume réservoir')
    longueur             = fields.Integer(string='Longueur (mm)')
    largeur              = fields.Integer(string='Largeur (mm)')
    hauteur              = fields.Integer(string='Hauteur (mm)')
    puissance_electrique = fields.Char(string='Puissance électrique moteur')
    type_huile_graissage = fields.Selection([
        ('sans','sans'),
        ('RSL68SG','RSL68SG'),
        ('RSL150SG','RSL150SG'),
        ('RSL220SG','RSL220SG'),
        ('RSX220','RSX220'),
    ], string='Type huile graissage centralisé')
    puissance_electrique_chauffe = fields.Char(string='Puissance électrique chauffe')
    nombre_noyau                 = fields.Char(string='Nbre Noyau Total')
    compensation_cosinus = fields.Selection([
        ('oui','Oui'),
        ('non','Non'),
    ], string='Compensation cosinus')
    nb_noyau_pf           = fields.Char(string='Nbre Noyau PF')
    nb_noyau_pm           = fields.Char(string='Nbre Noyau PM')
    nombre_circuit_haut   = fields.Char(string='Nbre circuit Eau')
    diametre_passage_buse = fields.Char(string='Ø Passage Buse')
    zone_chauffe          = fields.Char(string='Zones de chauffe')
    poids                 = fields.Char(string='Poids')
    site_id               = fields.Many2one('is.database','Site')
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    active = fields.Boolean('Active', default=True)
    
    
    # def write(self, vals):
    #     try:
    #         res=super(is_presse, self).write(vals)
    #         for obj in self:
    #             obj.copy_other_database_is_presse()
    #         return res
    #     except Exception as e:
    #         raise osv.except_osv(_('Presse!'),
    #                          _('(%s).') % str(e).decode('utf-8'))

    # def create(self, vals):
    #     try:
    #         obj=super(is_presse, self).create(vals)
    #         obj.copy_other_database_is_presse()
    #         return obj
    #     except Exception as e:
    #         raise osv.except_osv(_('Presse!'),
    #                          _('(%s).') % str(e).decode('utf-8'))
            
    def copy_other_database_is_presse(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for presse in self:
            for database in database_lines:
                if not database.ip_server or not database.database or not database.port_server or not database.login or not database.password:
                    continue
                DB = database.database
                USERID = SUPERUSER_ID
                DBLOGIN = database.login
                USERPASS = database.password
                DB_SERVER = database.ip_server
                DB_PORT = database.port_server
                sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object' % (DB_SERVER, DB_PORT))
                is_presse_vals = self.get_is_presse_vals(presse, DB, USERID, USERPASS, sock)
                dest_is_presse_ids = sock.execute(DB, USERID, USERPASS, 'is.presse', 'search', [('is_database_origine_id', '=', presse.id),
                                                                                                '|',('active','=',True),('active','=',False)], {})
                if dest_is_presse_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.presse', 'write', dest_is_presse_ids, is_presse_vals, {})
                    is_presse_created_id = dest_is_presse_ids[0]
                else:
                    is_presse_created_id = sock.execute(DB, USERID, USERPASS, 'is.presse', 'create', is_presse_vals, {})
        return True

    def get_is_presse_vals(self, presse, DB, USERID, USERPASS, sock):
        is_presse_vals ={
                     'name' : tools.ustr(presse.name or ''),
                     'designation':tools.ustr(presse.designation or ''),
                     'classe':tools.ustr(presse.classe or ''),
                    'emplacement':self._get_emplacement(presse, DB, USERID, USERPASS, sock),
                    'classe_commerciale':self._get_classe_commerciale(presse, DB, USERID, USERPASS, sock),
                    'puissance' : self._get_puissance(presse, DB, USERID, USERPASS, sock),
                     'puissance_reelle':tools.ustr(presse.puissance_reelle or ''),
                     'type_de_presse':tools.ustr(presse.type_de_presse or ''),
                    'constructeur': self._get_constructeur(presse, DB, USERID, USERPASS, sock),
                     'num_construceur':tools.ustr(presse.num_construceur or ''),
                     'type_commande':tools.ustr(presse.type_commande or ''),
                     'annee':tools.ustr(presse.annee or ''),
                     'energie':presse.energie,
                     'volume_tremie':tools.ustr(presse.volume_tremie or ''),
                     'volume_alimentateur':tools.ustr(presse.volume_alimentateur or ''),
                     'dimension_col_h':tools.ustr(presse.dimension_col_h or ''),
                     'dimension_col_v':tools.ustr(presse.dimension_col_v or ''),
                     'diametre_colonne':tools.ustr(presse.diametre_colonne or ''),
                     'epaisseur_moule':tools.ustr(presse.epaisseur_moule or ''),
                     'faux_plateau':presse.faux_plateau,
                     'epaisseur_faux_plateau': tools.ustr(presse.epaisseur_faux_plateau or ''),
                     'epaisseur_moule_mini':tools.ustr(presse.epaisseur_moule_mini or ''),
                     'epaisseur_moule_maxi':tools.ustr(presse.epaisseur_moule_maxi or ''),
                     'dimension_plateau_h':tools.ustr(presse.dimension_plateau_h or ''),
                     'dimension_plateau_v':tools.ustr(presse.dimension_plateau_v or ''),
                     'dimension_hors_tout_haut':tools.ustr(presse.dimension_hors_tout_haut or ''),
                     'dimension_hors_tout_bas':tools.ustr(presse.dimension_hors_tout_bas or ''),
                     'coefficient_vis':tools.ustr(presse.coefficient_vis or ''),
                     'diametre_vis':tools.ustr(presse.diametre_vis or ''),
                     'type_clapet':tools.ustr(presse.type_clapet or ''),
                     'volume_injectable':tools.ustr(presse.volume_injectable or ''),
                     'presse_matiere':tools.ustr(presse.presse_matiere or ''),
                     'course_ejection':tools.ustr(presse.course_ejection or ''),
                     'course_ouverture':tools.ustr(presse.course_ouverture or ''),
                     'diametre_centrage_moule':tools.ustr(presse.diametre_centrage_moule or ''),
                     'diametre_centrage_presse':tools.ustr(presse.diametre_centrage_presse or ''),
                     'hauteur_porte_sol':tools.ustr(presse.hauteur_porte_sol or ''),
                     'bridage_rapide':tools.ustr(presse.bridage_rapide or ''),
                     'diametre_bridage':tools.ustr(presse.diametre_bridage or ''),
                     'pas_bridage':tools.ustr(presse.pas_bridage or ''),
                     'type_huile_hydraulique':tools.ustr(presse.type_huile_hydraulique or ''),
                     'volume_reservoir':tools.ustr(presse.volume_reservoir or ''),
                     'longueur':presse.longueur,
                     'largeur':presse.largeur,
                     'hauteur':presse.hauteur,
                     'puissance_electrique': tools.ustr(presse.puissance_electrique or ''),
                     'type_huile_graissage':presse.type_huile_graissage,
                     'puissance_electrique_chauffe':tools.ustr(presse.puissance_electrique_chauffe or ''),
                     'nombre_noyau':tools.ustr(presse.nombre_noyau or ''),
                     'compensation_cosinus': presse.compensation_cosinus,
                     'nb_noyau_pf':tools.ustr(presse.nb_noyau_pf or ''),
                     'nb_noyau_pm':tools.ustr(presse.nb_noyau_pm or ''),
                     'nombre_circuit_haut':tools.ustr(presse.nombre_circuit_haut or ''),
                     'diametre_passage_buse':tools.ustr(presse.diametre_passage_buse or ''),
                     'zone_chauffe':tools.ustr(presse.zone_chauffe or ''),
                     'poids':tools.ustr(presse.poids or ''),
                     'site_id':self._get_site_id(presse, DB, USERID, USERPASS, sock),
                     'active':presse.site_id and presse.site_id.database == DB and True or False,
                     'is_database_origine_id':presse.id,
                     }
        return is_presse_vals

    def _get_site_id(self, presse, DB, USERID, USERPASS, sock):
        if presse.site_id:
            ids = sock.execute(DB, USERID, USERPASS, 'is.database', 'search', [('is_database_origine_id', '=', presse.site_id.id)], {})
            if ids:
                return ids[0]
        return False

    def _get_emplacement(self, presse, DB, USERID, USERPASS, sock):
        if presse.emplacement:
            emplacement_ids = sock.execute(DB, USERID, USERPASS, 'is.emplacement.outillage', 'search', [('is_database_origine_id', '=', presse.emplacement.id)], {})
            if not emplacement_ids:
                presse.emplacement.copy_other_database_emplacement_outillage()
                emplacement_ids = sock.execute(DB, USERID, USERPASS, 'is.emplacement.outillage', 'search', [('is_database_origine_id', '=', presse.emplacement.id)], {})
            if emplacement_ids:
                return emplacement_ids[0]
        return False
    
    def _get_classe_commerciale(self, presse, DB, USERID, USERPASS, sock):
        if presse.classe_commerciale:
            classe_commerciale_ids = sock.execute(DB, USERID, USERPASS, 'is.presse.classe', 'search', [('is_database_origine_id', '=', presse.classe_commerciale.id)], {})
            if not classe_commerciale_ids:
                presse.classe_commerciale.copy_other_database_presse_classe()
                classe_commerciale_ids = sock.execute(DB, USERID, USERPASS, 'is.presse.classe', 'search', [('is_database_origine_id', '=', presse.classe_commerciale.id)], {})
            if classe_commerciale_ids:
                return classe_commerciale_ids[0]
        return False

    def _get_puissance(self, presse, DB, USERID, USERPASS, sock):
        if presse.puissance:
            puissance_ids = sock.execute(DB, USERID, USERPASS, 'is.presse.puissance', 'search', [('is_database_origine_id', '=', presse.puissance.id)], {})
            if not puissance_ids:
                presse.puissance.copy_other_database_presse_puissance()
                puissance_ids = sock.execute(DB, USERID, USERPASS, 'is.presse.puissance', 'search', [('is_database_origine_id', '=', presse.puissance.id)], {})
            if puissance_ids:
                return puissance_ids[0]
        return False

    def _get_constructeur(self, presse, DB, USERID, USERPASS, sock):
        if presse.constructeur:
            constructeur_ids = sock.execute(DB, USERID, USERPASS, 'is.outillage.constructeur', 'search', [('is_database_origine_id', '=', presse.constructeur.id)], {})
            if not constructeur_ids:
                presse.constructeur.copy_other_database_outillage_constructeur()
                constructeur_ids = sock.execute(DB, USERID, USERPASS, 'is.outillage.constructeur', 'search', [('is_database_origine_id', '=', presse.constructeur.id)], {})
            if constructeur_ids:
                return constructeur_ids[0]
        return False
