# -*- coding: utf-8 -*-
from odoo import models,fields,api,tools,SUPERUSER_ID
from odoo.exceptions import ValidationError
import datetime
import logging
_logger = logging.getLogger(__name__)


class is_equipement_champ_line(models.Model):
    _name = "is.equipement.champ.line"
    _description="is_equipement_champ_line"
    _order = "name"

    name = fields.Many2one("ir.model.fields", "Champ", domain=[
            ('model_id.model', '=', 'is.equipement'),
            ('ttype', '!=', 'boolean')
        ])
    vsb                    = fields.Boolean("Visible", default=True)
    obligatoire            = fields.Boolean("Obligatoire", default=False)
    equipement_type_id     = fields.Many2one("is.equipement.type", "Type Equipement")
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True, index=True)
    active                 = fields.Boolean('Active', default=True)

    def write(self, vals):
        res=super().write(vals)
        for obj in self:
            filtre=[('is_database_origine_id', '=', obj.is_database_origine_id),'|',('active','=',True),('active','=',False)]
            self.env['is.database'].copy_other_database(obj,filtre)
        return res
            
    @api.model_create_multi
    def create(self, vals_list):
        res=super().create(vals_list)
        for obj in res:
            filtre=[('is_database_origine_id', '=', obj.is_database_origine_id),'|',('active','=',True),('active','=',False)]
            self.env['is.database'].copy_other_database(obj,filtre)
        return res

    def unlink(self):
        res=super().unlink()
        self.env['is.database'].unlink_other_database(self)
        return(res)

    def get_copy_other_database_vals(self, DB, USERID, USERPASS, sock):
        vals ={
            'name'                  : self._get_name(DB, USERID, USERPASS, sock),
            'vsb'                   : self.vsb,
            'obligatoire'           : self.obligatoire,
            'equipement_type_id'    : self._get_equipement_type_id(DB, USERID, USERPASS, sock),
            'active'                : self.active,
            'is_database_origine_id': self.id
        }
        return vals

    def _get_name(self, DB, USERID, USERPASS, sock):
        if self.name:
            ids = sock.execute(DB, USERID, USERPASS, 'ir.model.fields', 'search', [('model_id.model', '=', 'is.equipement'),('name', '=', self.name.name)])
            if ids:
                return ids[0]
        return False

    def _get_equipement_type_id(self, DB, USERID, USERPASS, sock):
        if self.equipement_type_id:
            ids = sock.execute(DB, USERID, USERPASS, 'is.equipement.type', 'search', [('is_database_origine_id', '=', self.equipement_type_id.id)])
            if not ids:
                self.env['is.database'].copy_other_database(self.equipement_type_id)
                ids = sock.execute(DB, USERID, USERPASS, 'is.equipement.type', 'search', [('is_database_origine_id', '=', self.equipement_type_id.id)])
            if ids:
                return ids[0]
        return False

    @api.constrains('name', 'equipement_type_id')
    def check_unique_so_record(self):
        for obj in self:
            if obj.name and obj.equipement_type_id:
                filters = [('name', '=', obj.name.id),
                        ('equipement_type_id', '=', obj.equipement_type_id.id)]
                champ_ids = obj.search(filters)
                if len(champ_ids) > 1:
                    raise ValidationError(('Le champ "%s" existe déjà' % champ_ids[0].name.field_description))


class is_equipement_type(models.Model):
    _name = 'is.equipement.type'
    _description="is_equipement_type"
    _order = 'name'

    name                   = fields.Char(u"Type d'équipement", required=True)
    code                   = fields.Char("Code", required=True)
    champ_line_ids         = fields.One2many("is.equipement.champ.line", "equipement_type_id", "Champs")
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True, index=True)
    active                 = fields.Boolean('Active', default=True)

    def add_champs_action(self):
        for obj in self:
            champ_line_obj = self.env['is.equipement.champ.line']
            equp_field_ids = self.env['ir.model.fields'].search([
                    ('ttype','!=','boolean'),
                    ('model_id.model', '=', 'is.equipement'),
                    ('name', 'not in', ['create_date','create_uid','write_date','write_uid','is_database_origine_id','type_id','numero_equipement','designation','database_id']),
                ])
            for equ in equp_field_ids:
                champ_line_obj.create({
                    'name'              : equ.id,
                    'equipement_type_id': obj.id
                })
            return True


    def write(self, vals):
        res=super().write(vals)
        for obj in self:
            filtre=[('code', '=', obj.code),'|',('active','=',True),('active','=',False)]
            self.env['is.database'].copy_other_database(obj,filtre)
        return res
            
    @api.model_create_multi
    def create(self, vals_list):
        res=super().create(vals_list)
        for obj in res:
            filtre=[('code', '=', obj.code),'|',('active','=',True),('active','=',False)]
            self.env['is.database'].copy_other_database(obj,filtre)
        return res

    def unlink(self):
        res=super().unlink()
        self.env['is.database'].unlink_other_database(self)
        return(res)

    def get_copy_other_database_vals(self, DB, USERID, USERPASS, sock):
        vals ={
            'name'                  : self.name,
            'code'                  : self.code,
            'active'                : self.active,
            'champ_line_ids'        : self._get_champ_line_ids(DB, USERID, USERPASS, sock),
            'is_database_origine_id': self.id
        }
        return vals

    def _get_champ_line_ids(self,  DB, USERID, USERPASS, sock):
        list_champ_line_ids =[]
        for line in self.champ_line_ids:
            ids = sock.execute(DB, USERID, USERPASS, 'is.equipement.champ.line', 'search', [('is_database_origine_id', '=', line.id)])
            if ids:
                list_champ_line_ids.append(ids[0])
        return [(6, 0, list_champ_line_ids)]


class is_presse_classe(models.Model):
    _name='is.presse.classe'
    _description="Classe presse"
    _order='name'

    name = fields.Char(string='Classe commerciale')
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
   
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
            'name'                  : self.name,
            'is_database_origine_id': self.id
        }
        return vals


class is_presse_puissance(models.Model):
    _name='is.presse.puissance'
    _description="Puissance presse"
    _order='name'

    name                   = fields.Char(string='Puissance')
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    
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
            'name'                  : self.name,
            'is_database_origine_id': self.id
        }
        return vals

class is_outillage_constructeur(models.Model):
    _name='is.outillage.constructeur'
    _description="Outillage constructeur"
    _order='name'

    name = fields.Char(string='Name')
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    
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
            'name'                  : self.name,
            'is_database_origine_id': self.id
        }
        return vals


class is_equipement(models.Model):
    _name = "is.equipement"
    _description="is_equipement"
    _order = 'type_id,numero_equipement,designation'

    def name_get(self):
        res = []
        for obj in self:
            name=obj.numero_equipement
            res.append((obj.id,name))
        return res


    # def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
    #     if not args:
    #         args = []
    #     if name:
    #         args.append(['numero_equipement','ilike', name])
    #         #ids = self.search(cr, user, ['|',('numero_equipement','ilike', name),('designation','ilike', name)], limit=limit, context=context)
    #         ids = self.search(cr, user, args, limit=limit, context=context)
    #     else:
    #         ids = self.search(cr, user, args, limit=limit, context=context)
    #     result = self.name_get(cr, user, ids, context=context)
    #     return result


    @api.depends('type_id')
    def _compute(self):
        for obj in self:
            for cl in obj.type_id.champ_line_ids:
                if cl.vsb:
                    setattr(obj, cl.name.name + '_vsb', True)
                if cl.obligatoire:
                    setattr(obj, cl.name.name + '_obl', True)

    def write(self, vals):
        try:
            res=super(is_equipement, self).write(vals)
            for obj in self:
                obj.copy_other_database_is_equipement()
            return res
        except Exception as e:
            raise except_orm(_('Equipement!'),
                             _(" %s ") % (str(e).decode('utf-8'),))

    def create(self, vals):
        try:
            obj=super(is_equipement, self).create(vals)
            obj.copy_other_database_is_equipement()
            return obj
        except Exception as e:
            raise except_orm(_('Equipement!'),
                             _(" %s ") % (str(e).decode('utf-8'),))

    def unlink(self):
        super(is_equipement, self).unlink()
        for obj in self:
            cr , uid, context = self.env.args
            context = dict(context)
            database_obj = self.env['is.database']
            database_lines = database_obj.search([])
            for equp in self:
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
                    dest_is_equipement_ids = sock.execute(DB, USERID, USERPASS, 'is.equipement', 'search', [('is_database_origine_id', '=', equp.id),
                                                                                                    '|',('active','=',True),('active','=',False)], {})
                    if dest_is_equipement_ids:
                        res = sock.execute(DB, USERID, USERPASS, 'is.equipement', 'unlink', dest_is_equipement_ids,)
        return True

    def copy_other_database_is_equipement(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for equp in self:
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
                is_equipement_vals = self.get_is_equipement_vals(equp, DB, USERID, USERPASS, sock)
                dest_is_equipement_ids = sock.execute(DB, USERID, USERPASS, 'is.equipement', 'search', [('is_database_origine_id', '=', equp.id),
                                                                                                '|',('active','=',True),('active','=',False)], {})
                if dest_is_equipement_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.equipement', 'write', dest_is_equipement_ids, is_equipement_vals, {})
                    is_equipement_created_id = dest_is_equipement_ids[0]
                else:
                    is_equipement_created_id = sock.execute(DB, USERID, USERPASS, 'is.equipement', 'create', is_equipement_vals, {})
        return True

    def get_is_equipement_vals(self, equp, DB, USERID, USERPASS, sock):
        is_equipement_vals = {
            'numero_equipement'                     : tools.ustr(equp.numero_equipement),
            'designation'                           : tools.ustr(equp.designation),
            'database_id'                           : self._get_database_id(equp, DB, USERID, USERPASS, sock),
            'active'                                : equp.database_id and equp.database_id.database == DB and equp.active or False,
            'is_database_origine_id'                : equp.id,
            'equipement_cle'                        : equp.equipement_cle,
            'type_id'                               : self._get_type_id(equp, DB, USERID, USERPASS, sock),
            'constructeur'                          : tools.ustr(equp.constructeur or ''),
            'constructeur_serie'                    : tools.ustr(equp.constructeur_serie or ''),
            'partner_id'                            : self._get_partner_id(equp, DB, USERID, USERPASS, sock),
            'date_fabrication'                      : equp.date_fabrication,
            'date_de_fin'                           : equp.date_de_fin,
            'maintenance_preventif_niveau1'         : tools.ustr(equp.maintenance_preventif_niveau1),
            'maintenance_preventif_niveau2'         : tools.ustr(equp.maintenance_preventif_niveau2),
            'maintenance_preventif_niveau3'         : tools.ustr(equp.maintenance_preventif_niveau3),
            'maintenance_preventif_niveau4'         : tools.ustr(equp.maintenance_preventif_niveau4),
            'type_presse_commande'                  : tools.ustr(equp.type_presse_commande or ''),
            'classe_id'                             : self._get_classe_id(equp, DB, USERID, USERPASS, sock),
            'classe_commerciale'                    : tools.ustr(equp.classe_commerciale or ''),
            'force_fermeture'                       : tools.ustr(equp.force_fermeture),
            'energie'                               : tools.ustr(equp.energie or ''),
            'dimension_entre_col_h'                 : tools.ustr(equp.dimension_entre_col_h),
            'faux_plateau'                          : tools.ustr(equp.faux_plateau),
            'dimension_demi_plateau_h'              : tools.ustr(equp.dimension_demi_plateau_h),
            'dimension_hors_tout_haut'              : tools.ustr(equp.dimension_hors_tout_haut),
            'dimension_entre_col_v'                 : tools.ustr(equp.dimension_entre_col_v),
            'epaisseur_moule_mini_presse'           : tools.ustr(equp.epaisseur_moule_mini_presse),
            'epaisseur_faux_plateau'                : tools.ustr(equp.epaisseur_faux_plateau),
            'epaisseur_moule_maxi'                  : tools.ustr(equp.epaisseur_moule_maxi),
            'dimension_demi_plateau_v'              : tools.ustr(equp.dimension_demi_plateau_v),
            'dimension_hors_tout_bas'               : tools.ustr(equp.dimension_hors_tout_bas),
            'coefficient_vis'                       : tools.ustr(equp.coefficient_vis or ''),
            'type_de_clapet'                        : equp.type_de_clapet,
            'pression_maximum'                      : tools.ustr(equp.pression_maximum),
            'pression_maximum2'                     : tools.ustr(equp.pression_maximum2),
            'vis_mn'                                : tools.ustr(equp.vis_mn),
            'vis_mn2'                               : tools.ustr(equp.vis_mn2),
            'volume_injectable'                     : tools.ustr(equp.volume_injectable),
            'volume_injectable2'                    : tools.ustr(equp.volume_injectable2),
            'course_ejection'                       : tools.ustr(equp.course_ejection),
            'course_ouverture'                      : tools.ustr(equp.course_ouverture),
            'centrage_moule'                        : tools.ustr(equp.centrage_moule),
            'centrage_moule2'                       : tools.ustr(equp.centrage_moule2),
            'centrage_presse'                       : tools.ustr(equp.centrage_presse),
            'hauteur_porte_sol'                     : tools.ustr(equp.hauteur_porte_sol),
            'bridage_rapide_entre_axe'              : tools.ustr(equp.bridage_rapide_entre_axe),
            'bridage_rapide_pas'                    : tools.ustr(equp.bridage_rapide_pas),
            'bridage_rapide'                        : tools.ustr(equp.bridage_rapide),
            'type_huile_hydraulique'                : tools.ustr(equp.type_huile_hydraulique or ''),
            'volume_reservoir'                      : tools.ustr(equp.volume_reservoir),
            'type_huile_graissage_centralise'       : tools.ustr(equp.type_huile_graissage_centralise or ''),
            'nbre_noyau_total'                      : tools.ustr(equp.nbre_noyau_total),
            'nbre_noyau_pf'                         : tools.ustr(equp.nbre_noyau_pf),
            'nbre_noyau_pm'                         : tools.ustr(equp.nbre_noyau_pm),
            'nbre_circuit_eau'                      : tools.ustr(equp.nbre_circuit_eau),
            'nbre_zone_de_chauffe_moule'            : tools.ustr(equp.nbre_zone_de_chauffe_moule),
            'puissance_electrique_installee'        : tools.ustr(equp.puissance_electrique_installee),
            'puissance_electrique_moteur'           : tools.ustr(equp.puissance_electrique_moteur),
            'puissance_de_chauffe'                  : tools.ustr(equp.puissance_de_chauffe),
            'compensation_cosinus'                  : equp.compensation_cosinus,
            'passage_buse'                          : tools.ustr(equp.passage_buse),
            'option_rotation_r1'                    : equp.option_rotation_r1,
            'option_rotation_r2'                    : equp.option_rotation_r2,
            'option_arret_intermediaire'            : equp.option_arret_intermediaire,
            'nbre_circuit_vide'                     : tools.ustr(equp.nbre_circuit_vide),
            'nbre_circuit_pression'                 : tools.ustr(equp.nbre_circuit_pression),
            'nbre_dentrees_automate_disponibles'    : tools.ustr(equp.nbre_dentrees_automate_disponibles),
            'nbre_de_sorties_automate_disponibles'  : tools.ustr(equp.nbre_de_sorties_automate_disponibles),
            'dimension_chambre'                     : tools.ustr(equp.dimension_chambre),
            'nbre_de_voie'                          : tools.ustr(equp.nbre_de_voie),
            'capacite_de_levage'                    : tools.ustr(equp.capacite_de_levage),
            'dimension_bande'                       : tools.ustr(equp.dimension_bande),
            'dimension_cage'                        : tools.ustr(equp.dimension_cage),
            'poids_kg'                              : tools.ustr(equp.poids_kg),
            'affectation_sur_le_site'               : tools.ustr(equp.affectation_sur_le_site or ''),
            'is_mold_ids'                           : self._get_mold_ids(equp, DB, USERID, USERPASS, sock),
            'is_dossierf_ids'                       : self._get_dossierf_ids(equp, DB, USERID, USERPASS, sock),
            'type_de_fluide'                        : equp.type_de_fluide,
            'temperature_maximum'                   : tools.ustr(equp.temperature_maximum),
            'puissance_de_refroidissement'          : tools.ustr(equp.puissance_de_refroidissement),
            'debit_maximum'                         : tools.ustr(equp.debit_maximum),
            'volume_l'                              : tools.ustr(equp.volume_l),
            'option_depresssion'                    : equp.option_depresssion,
            'mesure_debit'                          : equp.mesure_debit,
            'base_capacitaire'                      : tools.ustr(equp.base_capacitaire),
            'emplacement_affectation_pe'            : tools.ustr(equp.emplacement_affectation_pe or ''),
            'adresse_ip_mac'                        : tools.ustr(equp.adresse_ip_mac or ''),
        }
        return is_equipement_vals

    def _get_database_id(self, equp, DB, USERID, USERPASS, sock):
        if equp.database_id:
            ids = sock.execute(DB, USERID, USERPASS, 'is.database', 'search', [('is_database_origine_id', '=', equp.database_id.id)], {})
            if ids:
                return ids[0]
        return False

    def _get_dossierf_ids(self, equp, DB, USERID, USERPASS, sock):
        list_dossierf_ids =[]
        for doss in equp.is_dossierf_ids:
            dest_dossierf_ids = sock.execute(DB, USERID, USERPASS, 'is.dossierf', 'search', [('is_database_origine_id', '=', doss.id)], {})
            if dest_dossierf_ids:
                list_dossierf_ids.append(dest_dossierf_ids[0])
        return [(6, 0, list_dossierf_ids)]

    def _get_mold_ids(self, equp, DB, USERID, USERPASS, sock):
        list_mold_ids =[]
        for mold in equp.is_mold_ids:
            dest_mold_ids = sock.execute(DB, USERID, USERPASS, 'is.mold', 'search', [('is_database_origine_id', '=', mold.id)], {})
            if dest_mold_ids:
                list_mold_ids.append(dest_mold_ids[0])
        return [(6, 0, list_mold_ids)]

    def _get_type_id(self, equp, DB, USERID, USERPASS, sock):
        if equp.type_id:
            ids = sock.execute(DB, USERID, USERPASS, 'is.equipement.type', 'search', [('is_database_origine_id', '=', equp.type_id.id), '|',('active','=',True),('active','=',False)], {})
            if not ids:
                equp.type_id.copy_other_database_equipement_type()
                ids = sock.execute(DB, USERID, USERPASS, 'is.equipement.type', 'search', [('is_database_origine_id', '=', equp.type_id.id), '|',('active','=',True),('active','=',False)], {})
            if ids:
                return ids[0]
        return False

    def _get_partner_id(self, equp, DB, USERID, USERPASS, sock):
        if equp.partner_id:
            equp_ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', equp.partner_id.id),'|',('active','=',True),('active','=',False)], {})
            if not equp_ids:
                self.env['is.database'].copy_other_database(equp.partner_id)
                equp_ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', equp.partner_id.id),'|',('active','=',True),('active','=',False)], {})
            if equp_ids:
                return equp_ids[0]
        return False

    def _get_classe_id(self, equp, DB, USERID, USERPASS, sock):
        if equp.classe_id:
            equp_ids = sock.execute(DB, USERID, USERPASS, 'is.presse.classe', 'search', [('is_database_origine_id', '=', equp.classe_id.id)], {})
            if not equp_ids:
                self.env['is.database'].copy_other_database_presse_classe(equp.classe_id)
                equp_ids = sock.execute(DB, USERID, USERPASS, 'is.presse.classe', 'search', [('is_database_origine_id', '=', equp.classe_id.id)], {})
            if equp_ids:
                return equp_ids[0]
        return False


    def arret_raspberry(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.raspberry_id:
                IP=obj.raspberry_id.name
                cmd="ssh root@"+IP+" halt"
                os.system(cmd)
        return

    def reboot_raspberry(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.raspberry_id:
                IP=obj.raspberry_id.name
                cmd="ssh root@"+IP+" reboot"
                os.system(cmd)
        return

    def rafraichir_raspberry(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.raspberry_id:
                IP=obj.raspberry_id.name
                cmd="ssh root@"+IP+" killall midori"
                os.system(cmd)
        return

    def interface_presse(self, cr, uid, ids, context=None):
        presse=""
        for obj in self.browse(cr, uid, ids, context=context):
            presse = obj.numero_equipement
            user   = self.pool['res.users'].browse(cr, uid, [uid], context=context)[0]
            soc    = user.company_id.is_code_societe
        url = "http://raspberry-cpi/presse.php?soc="+str(soc)+"&presse="+presse
        return {
            'name'     : 'Go to website',
            'res_model': 'ir.actions.act_url',
            'type'     : 'ir.actions.act_url',
            'target'   : 'current',
            'url'      : url
        }


    def acceder_equipement_action(self):
        for obj in self:
            return {
                'name': "Equipement",
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'is.equipement',
                'type': 'ir.actions.act_window',
                'res_id': obj.id,
                'domain': '[]',
            }


    def imprimer_etiquette_equipement(self):
        for obj in self:
            user=self.env['res.users'].browse(self._uid)
            imprimante=user.company_id.is_zebra_id.name
            if imprimante:
                Msg          = ""
                FN1 = obj.numero_equipement or ''
                FN2 = obj.designation or ''
                FN3 = "Z"+FN1

                ZPL="""
                ^XA
                ^A0R,100,100^FO650,50               ^FD%s   ^FS
                ^A0R,70,70^FO570,50                 ^FD%s   ^FS
                ^BY5,1.0^FO370,50^BC R,159,N,Y,Y,N  ^FD%s   ^FS
                ^MMC
                ^XZ
                """%(FN1,FN2,FN3)
                cmd='echo "'+ZPL+'" | lpr -P '+imprimante
                res = subprocess.call(cmd, shell=True)
                _logger.info(cmd)


    @api.depends('numero_equipement')
    def _couleur(self):
        colors=[
            ("blanc"  , "white"),
            ("bleu"   , "#5BC0DE"),
            ("orange" , "#F0AD4E"),
            ("rouge"  , "#D9534F"),
            ("vert"   , "#5CB85C"),
        ]
        for obj in self:
            couleur=""
            for color in colors:
                if obj.etat_presse_id.couleur==color[0]:
                    couleur=color[1]
            obj.couleur=couleur

    is_database_origine_id                   = fields.Integer("Id d'origine", readonly=True, index=True)
    active                                   = fields.Boolean('Active', default=True)
    type_id                                  = fields.Many2one("is.equipement.type", u"Type équipement", required=True, index=True)
    numero_equipement                        = fields.Char(u"Numéro d'équipement", required=True, index=True)
    designation                              = fields.Char(u"Désignation", required=True)
    database_id                              = fields.Many2one("is.database", "Site", required=True)

    equipement_cle_vsb                       = fields.Boolean("Equipement clé vsb", compute='_compute')
    equipement_cle_obl                       = fields.Boolean("Equipement clé obl", compute='_compute')
    equipement_cle                           = fields.Selection([
            ("oui", "oui"),
            ("non", "non"),
        ], "Equipement clé")

    constructeur_vsb                         = fields.Boolean("Constructeur vsb", compute='_compute')
    constructeur_obl                         = fields.Boolean("Constructeur obl", compute='_compute')
    constructeur                             = fields.Char("Constructeur")
    
    constructeur_serie_vsb                   = fields.Boolean(u"N° constructeur/N°série vsb", compute='_compute')
    constructeur_serie_obl                   = fields.Boolean(u"N° constructeur/N°série obl", compute='_compute')
    constructeur_serie                       = fields.Char(u"N° constructeur/N°série")
    
    partner_id_vsb                           = fields.Boolean("Fournisseur vsb", compute='_compute')
    partner_id_obl                           = fields.Boolean("Fournisseur obl", compute='_compute')
    partner_id                               = fields.Many2one("res.partner", "Fournisseur", domain=[('is_company', '=', True), ('supplier', '=', True)])
    
    date_fabrication_vsb                     = fields.Boolean("Date de fabrication vsb", compute='_compute')
    date_fabrication_obl                     = fields.Boolean("Date de fabrication obl", compute='_compute')
    date_fabrication                         = fields.Date("Date de fabrication")
    
    date_de_fin_vsb                          = fields.Boolean("Date de fin vsb", compute='_compute')
    date_de_fin_obl                          = fields.Boolean("Date de fin obl", compute='_compute')
    date_de_fin                              = fields.Date("Date de fin")
    
    maintenance_preventif_niveau1_vsb        = fields.Boolean(u"Maintenance préventif niveau 1 (h) vsb", compute='_compute')
    maintenance_preventif_niveau1_obl        = fields.Boolean(u"Maintenance préventif niveau 1 (h) obl", compute='_compute')
    maintenance_preventif_niveau1            = fields.Float(u"Maintenance préventif niveau 1 (h)", digits=(14, 1))
    
    maintenance_preventif_niveau2_vsb        = fields.Boolean(u"Maintenance préventif niveau 2 (h) vsb", compute='_compute')
    maintenance_preventif_niveau2_obl        = fields.Boolean(u"Maintenance préventif niveau 2 (h) obl", compute='_compute')
    maintenance_preventif_niveau2            = fields.Float(u"Maintenance préventif niveau 2 (h)", digits=(14, 1))
    
    maintenance_preventif_niveau3_vsb        = fields.Boolean(u"Maintenance préventif niveau 3 (h) vsb", compute='_compute')
    maintenance_preventif_niveau3_obl        = fields.Boolean(u"Maintenance préventif niveau 3 (h) obl", compute='_compute')
    maintenance_preventif_niveau3            = fields.Float(u"Maintenance préventif niveau 3 (h)", digits=(14, 1))
    
    maintenance_preventif_niveau4_vsb        = fields.Boolean(u"Maintenance préventif niveau 4 (h) vsb", compute='_compute')
    maintenance_preventif_niveau4_obl        = fields.Boolean(u"Maintenance préventif niveau 4 (h) obl", compute='_compute')
    maintenance_preventif_niveau4            = fields.Float(u"Maintenance préventif niveau 4 (h)", digits=(14, 1))
    
    type_presse_commande_vsb                 = fields.Boolean("Type de presse/type de commande/Generation vsb", compute='_compute')
    type_presse_commande_obl                 = fields.Boolean("Type de presse/type de commande/Generation obl", compute='_compute')
    type_presse_commande                     = fields.Char("Type de presse/type de commande/Generation")
    
    classe_id_vsb                            = fields.Boolean("Classe vsb", compute='_compute')
    classe_id_obl                            = fields.Boolean("Classe obl", compute='_compute')
    classe_id                                = fields.Many2one("is.presse.classe", "Classe")
    
    classe_commerciale_vsb                   = fields.Boolean("Classe commerciale vsb", compute='_compute')
    classe_commerciale_obl                   = fields.Boolean("Classe commerciale obl", compute='_compute')
    classe_commerciale                       = fields.Char("Classe commerciale")
    
    force_fermeture_vsb                      = fields.Boolean("Force de Fermeture (kg) vsb", compute='_compute')
    force_fermeture_obl                      = fields.Boolean("Force de Fermeture (kg) obl", compute='_compute')
    force_fermeture                          = fields.Integer("Force de Fermeture (kg)")
    
    energie_vsb                              = fields.Boolean("Energie vsb", compute='_compute')
    energie_obl                              = fields.Boolean("Energie obl", compute='_compute')
    energie                                  = fields.Char("Energie")
    
    dimension_entre_col_h_vsb                = fields.Boolean("Dimension entre col H (mm) vsb", compute='_compute')
    dimension_entre_col_h_obl                = fields.Boolean("Dimension entre col H (mm) obl", compute='_compute')
    dimension_entre_col_h                    = fields.Integer("Dimension entre col H (mm)")
    
    faux_plateau_vsb                         = fields.Boolean("Faux plateau (mm) vsb", compute='_compute')
    faux_plateau_obl                         = fields.Boolean("Faux plateau (mm) obl", compute='_compute')
    faux_plateau                             = fields.Integer("Faux plateau (mm)")
    
    dimension_demi_plateau_h_vsb             = fields.Boolean("Dimension demi plateau H (mm) vsb", compute='_compute')
    dimension_demi_plateau_h_obl             = fields.Boolean("Dimension demi plateau H (mm) obl", compute='_compute')
    dimension_demi_plateau_h                 = fields.Integer("Dimension demi plateau H (mm)")
    
    dimension_hors_tout_haut_vsb             = fields.Boolean("Dimension hors tout Haut (mm) vsb", compute='_compute')
    dimension_hors_tout_haut_obl             = fields.Boolean("Dimension hors tout Haut (mm) obl", compute='_compute')
    dimension_hors_tout_haut                 = fields.Integer("Dimension hors tout Haut (mm)")
    
    dimension_entre_col_v_vsb                = fields.Boolean("Dimension entre col V (mm) vsb", compute='_compute')
    dimension_entre_col_v_obl                = fields.Boolean("Dimension entre col V (mm) obl", compute='_compute')
    dimension_entre_col_v                    = fields.Integer("Dimension entre col V (mm)")
    
    epaisseur_moule_mini_presse_vsb          = fields.Boolean(u"Épaisseur moule Mini presse (mm) vsb", compute='_compute')
    epaisseur_moule_mini_presse_obl          = fields.Boolean(u"Épaisseur moule Mini presse (mm) obl", compute='_compute')
    epaisseur_moule_mini_presse              = fields.Integer(u"Épaisseur moule Mini presse (mm)")
    
    epaisseur_faux_plateau_vsb               = fields.Boolean(u"Épaisseur faux plateau (mm) vsb", compute='_compute')
    epaisseur_faux_plateau_obl               = fields.Boolean(u"Épaisseur faux plateau (mm) obl", compute='_compute')
    epaisseur_faux_plateau                   = fields.Integer(u"Épaisseur faux plateau (mm)")
    
    epaisseur_moule_maxi_vsb                 = fields.Boolean(u"Épaisseur moule Maxi (mm) vsb", compute='_compute')
    epaisseur_moule_maxi_obl                 = fields.Boolean(u"Épaisseur moule Maxi (mm) obl", compute='_compute')
    epaisseur_moule_maxi                     = fields.Integer(u"Épaisseur moule Maxi (mm)")
    
    dimension_demi_plateau_v_vsb             = fields.Boolean("Dimension demi plateau V (mm) vsb", compute='_compute')
    dimension_demi_plateau_v_obl             = fields.Boolean("Dimension demi plateau V (mm) obl", compute='_compute')
    dimension_demi_plateau_v                 = fields.Integer("Dimension demi plateau V (mm)")
    
    dimension_hors_tout_bas_vsb              = fields.Boolean("Dimension hors tout Bas (mm) vsb", compute='_compute')
    dimension_hors_tout_bas_obl              = fields.Boolean("Dimension hors tout Bas (mm) obl", compute='_compute')
    dimension_hors_tout_bas                  = fields.Integer("Dimension hors tout Bas (mm)")
    
    coefficient_vis_vsb                      = fields.Boolean("Coefficient de vis vsb", compute='_compute')
    coefficient_vis_obl                      = fields.Boolean("Coefficient de vis obl", compute='_compute')
    coefficient_vis                          = fields.Char("Coefficient de vis")
    
    type_de_clapet_vsb                       = fields.Boolean("Type de clapet vdb", compute='_compute')
    type_de_clapet_obl                       = fields.Boolean("Type de clapet obl", compute='_compute')
    type_de_clapet                           = fields.Selection([
            ("1", u"à bague à 2 ailettes"),
            ("2", u"à bague à 3 ailettes"),
            ("3", u"à bague à 4 ailettes"),
            ("4", u"à bille"),
        ], "Type de clapet")
    
    pression_maximum_vsb                     = fields.Boolean("Pression matière 1 maximum (bar) vsb", compute='_compute')
    pression_maximum_obl                     = fields.Boolean("Pression matière 1 maximum (bar) obl", compute='_compute')
    pression_maximum                         = fields.Integer("Pression matière 1 maximum (bar)")
    
    pression_maximum2_vsb                    = fields.Boolean("Pression matière 2 maximum (bar) vsb", compute='_compute')
    pression_maximum2_obl                    = fields.Boolean("Pression matière 2 maximum (bar) obl ", compute='_compute')
    pression_maximum2                        = fields.Integer("Pression matière 2 maximum (bar)")

    vis_mn_vsb                               = fields.Boolean("Ø Vis 1 (mm) vsb", compute='_compute')
    vis_mn_obl                               = fields.Boolean("Ø Vis 1 (mm) obl", compute='_compute')
    vis_mn                                   = fields.Integer("Ø Vis 1 (mm)")
    
    vis_mn2_vsb                              = fields.Boolean("Ø Vis 2 (mm) vsb", compute='_compute')
    vis_mn2_obl                              = fields.Boolean("Ø Vis 2 (mm) obl", compute='_compute')
    vis_mn2                                  = fields.Integer("Ø Vis 2 (mm)")

    volume_injectable_vsb                    = fields.Boolean("Volume injectable 1 (cm3) vsb", compute='_compute')
    volume_injectable_obl                    = fields.Boolean("Volume injectable 1 (cm3) obl", compute='_compute')
    volume_injectable                        = fields.Integer("Volume injectable 1 (cm3)")
    
    volume_injectable2_vsb                    = fields.Boolean("Volume injectable 2 (cm3) vsb", compute='_compute')
    volume_injectable2_obl                    = fields.Boolean("Volume injectable 2 (cm3) obl", compute='_compute')
    volume_injectable2                        = fields.Integer("Volume injectable 2 (cm3)")

    course_ejection_vsb                      = fields.Boolean(u"Course éjection (mm) vsb", compute='_compute')
    course_ejection_obl                      = fields.Boolean(u"Course éjection (mm) obl", compute='_compute')
    course_ejection                          = fields.Integer(u"Course éjection (mm)")
    
    course_ouverture_vsb                     = fields.Boolean("Course ouverture (mm) vsb", compute='_compute')
    course_ouverture_obl                     = fields.Boolean("Course ouverture (mm) obl", compute='_compute')
    course_ouverture                         = fields.Integer("Course ouverture (mm)")
    
    centrage_moule_vsb                       = fields.Boolean("Ø centrage moule 1 (mm) vsb", compute='_compute')
    centrage_moule_obl                       = fields.Boolean("Ø centrage moule 1 (mm) obl", compute='_compute')
    centrage_moule                           = fields.Integer("Ø centrage moule 1 (mm)")

    centrage_moule2_vsb                      = fields.Boolean("Ø centrage moule 2 (mm) vsb ", compute='_compute')
    centrage_moule2_obl                      = fields.Boolean("Ø centrage moule 2 (mm) obl", compute='_compute')
    centrage_moule2                          = fields.Integer("Ø centrage moule 2 (mm)")
    
    centrage_presse_vsb                      = fields.Boolean("Ø centrage presse (mm) vsb", compute='_compute')
    centrage_presse_obl                      = fields.Boolean("Ø centrage presse (mm) obl", compute='_compute')
    centrage_presse                          = fields.Integer("Ø centrage presse (mm)")
    
    hauteur_porte_sol_vsb                    = fields.Boolean("Hauteur porte / sol (mm) vsb", compute='_compute')
    hauteur_porte_sol_obl                    = fields.Boolean("Hauteur porte / sol (mm) obl", compute='_compute')
    hauteur_porte_sol                        = fields.Integer("Hauteur porte / sol (mm)")
    
    bridage_rapide_entre_axe_vsb             = fields.Boolean("Bridage rapide entre axe (mm) vsb", compute='_compute')
    bridage_rapide_entre_axe_obl             = fields.Boolean("Bridage rapide entre axe (mm) obl", compute='_compute')
    bridage_rapide_entre_axe                 = fields.Integer("Bridage rapide entre axe (mm)")
    
    bridage_rapide_pas_vsb                   = fields.Boolean("Bridage rapide Pas (mm) vsb", compute='_compute')
    bridage_rapide_pas_obl                   = fields.Boolean("Bridage rapide Pas (mm) obl", compute='_compute')
    bridage_rapide_pas                       = fields.Integer("Bridage rapide Pas (mm)")
    
    bridage_rapide_vsb                       = fields.Boolean("Bridage rapide Ø (mm) vsb", compute='_compute')
    bridage_rapide_obl                       = fields.Boolean("Bridage rapide Ø (mm) obl", compute='_compute')
    bridage_rapide                           = fields.Integer("Bridage rapide Ø (mm)")
    
    type_huile_hydraulique_vsb               = fields.Boolean("Type huile hydraulique vsb", compute='_compute')
    type_huile_hydraulique_obl               = fields.Boolean("Type huile hydraulique obl", compute='_compute')
    type_huile_hydraulique                   = fields.Char("Type huile hydraulique")
    
    volume_reservoir_vsb                     = fields.Boolean(u"Volume réservoir (L) vsb", compute='_compute')
    volume_reservoir_obl                     = fields.Boolean(u"Volume réservoir (L) obl", compute='_compute')
    volume_reservoir                         = fields.Integer(u"Volume réservoir (L)")
    
    type_huile_graissage_centralise_vsb      = fields.Boolean(u"Type huile graissage centralisé vsb", compute='_compute')
    type_huile_graissage_centralise_obl      = fields.Boolean(u"Type huile graissage centralisé obl", compute='_compute')
    type_huile_graissage_centralise          = fields.Char(u"Type huile graissage centralisé")
    
    nbre_noyau_total_vsb                     = fields.Boolean("Nbre Noyau Total vsb", compute='_compute')
    nbre_noyau_total_obl                     = fields.Boolean("Nbre Noyau Total obl", compute='_compute')
    nbre_noyau_total                         = fields.Integer("Nbre Noyau Total")
    
    nbre_noyau_pf_vsb                        = fields.Boolean("Nbre Noyau PF vsb", compute='_compute')
    nbre_noyau_pf_obl                        = fields.Boolean("Nbre Noyau PF obl", compute='_compute')
    nbre_noyau_pf                            = fields.Integer("Nbre Noyau PF")
    
    nbre_noyau_pm_vsb                        = fields.Boolean("Nbre Noyau PM vsb", compute='_compute')
    nbre_noyau_pm_obl                        = fields.Boolean("Nbre Noyau PM obl", compute='_compute')
    nbre_noyau_pm                            = fields.Integer("Nbre Noyau PM")
    
    nbre_circuit_eau_vsb                     = fields.Boolean("Nbre circuit Eau vsb", compute='_compute')
    nbre_circuit_eau_obl                     = fields.Boolean("Nbre circuit Eau obl", compute='_compute')
    nbre_circuit_eau                         = fields.Integer("Nbre circuit Eau")
    
    nbre_zone_de_chauffe_moule_vsb           = fields.Boolean("Nbre de zone de chauffe moule vsb", compute='_compute')
    nbre_zone_de_chauffe_moule_obl           = fields.Boolean("Nbre de zone de chauffe moule obl", compute='_compute')
    nbre_zone_de_chauffe_moule               = fields.Integer("Nbre de zone de chauffe moule")
    
    puissance_electrique_installee_vsb       = fields.Boolean("Puissance Electrique Installee (kw) vsb", compute='_compute')
    puissance_electrique_installee_obl       = fields.Boolean("Puissance Electrique Installee (kw) obl", compute='_compute')
    puissance_electrique_installee           = fields.Float("Puissance Electrique Installee (kw)", digits=(14, 2))
    
    puissance_electrique_moteur_vsb          = fields.Boolean(u"Puissance électrique moteur (kw) vsb", compute='_compute')
    puissance_electrique_moteur_obl          = fields.Boolean(u"Puissance électrique moteur (kw) obl", compute='_compute')
    puissance_electrique_moteur              = fields.Float(u"Puissance électrique moteur (kw)", digits=(14, 2))
    
    puissance_de_chauffe_vsb                 = fields.Boolean("Puissance de chauffe (kw) vsb", compute='_compute')
    puissance_de_chauffe_obl                 = fields.Boolean("Puissance de chauffe (kw) obl", compute='_compute')
    puissance_de_chauffe                     = fields.Float("Puissance de chauffe (kw)", digits=(14, 2))
    
    compensation_cosinus_vsb                 = fields.Boolean("Compensation cosinus vsb", compute='_compute')
    compensation_cosinus_obl                 = fields.Boolean("Compensation cosinus obl", compute='_compute')
    compensation_cosinus                     = fields.Selection([
            ("oui", "oui"),
            ("non", "non"),
        ], "Compensation cosinus")
    
    passage_buse_vsb                         = fields.Boolean("Ø Passage Buse (mm) vsb", compute='_compute')
    passage_buse_obl                         = fields.Boolean("Ø Passage Buse (mm) obl", compute='_compute')
    passage_buse = fields.Integer("Ø Passage Buse (mm)")
    
    option_rotation_r1_vsb                   = fields.Boolean("Option Rotation R1 (vert/horiz) vsb", compute='_compute')
    option_rotation_r1_obl                   = fields.Boolean("Option Rotation R1 (vert/horiz) obl", compute='_compute')
    option_rotation_r1                       = fields.Selection([
            ("oui", "oui"),
            ("non", "non"),
        ], "Option Rotation R1 (vert/horiz)")
    
    option_rotation_r2_vsb                   = fields.Boolean("Option Rotation R2 vsb", compute='_compute')
    option_rotation_r2_obl                   = fields.Boolean("Option Rotation R2 obl", compute='_compute')
    option_rotation_r2                       = fields.Selection([
            ("oui", "oui"),
            ("non", "non"),
        ], "Option Rotation R2")
    
    option_arret_intermediaire_vsb           = fields.Boolean(u"Option Arrêt Intermédiaire vsb", compute='_compute')
    option_arret_intermediaire_obl           = fields.Boolean(u"Option Arrêt Intermédiaire obl", compute='_compute')
    option_arret_intermediaire               = fields.Selection([
            ("oui", "oui"),
            ("non", "non"),
        ], u"Option Arrêt Intermédiaire")
    
    nbre_circuit_vide_vsb                    = fields.Boolean("Nbre de circuit de vide vsb", compute='_compute')
    nbre_circuit_vide_obl                    = fields.Boolean("Nbre de circuit de vide obl", compute='_compute')
    nbre_circuit_vide                        = fields.Integer("Nbre de circuit de vide")
    
    nbre_circuit_pression_vsb                = fields.Boolean("Nbre de circuit pression vsb", compute='_compute')
    nbre_circuit_pression_obl                = fields.Boolean("Nbre de circuit pression obl", compute='_compute')
    nbre_circuit_pression                    = fields.Integer("Nbre de circuit pression")
    
    nbre_dentrees_automate_disponibles_vsb   = fields.Boolean(u"Nbre d'entrées automate disponibles vsb", compute='_compute')
    nbre_dentrees_automate_disponibles_obl   = fields.Boolean(u"Nbre d'entrées automate disponibles obl", compute='_compute')
    nbre_dentrees_automate_disponibles       = fields.Integer(u"Nbre d'entrées automate disponibles")
    
    nbre_de_sorties_automate_disponibles_vsb = fields.Boolean("Nbre de sorties automate disponibles vsb", compute='_compute')
    nbre_de_sorties_automate_disponibles_obl = fields.Boolean("Nbre de sorties automate disponibles obl", compute='_compute')
    nbre_de_sorties_automate_disponibles     = fields.Integer("Nbre de sorties automate disponibles")
    
    dimension_chambre_vsb                    = fields.Boolean("Dimension chambre (mm) vsb", compute='_compute')
    dimension_chambre_obl                    = fields.Boolean("Dimension chambre (mm) obl", compute='_compute')
    dimension_chambre                        = fields.Integer("Dimension chambre (mm)")
    
    nbre_de_voie_vsb                         = fields.Boolean("Nbre de voie vsb", compute='_compute')
    nbre_de_voie_obl                         = fields.Boolean("Nbre de voie obl", compute='_compute')
    nbre_de_voie                             = fields.Integer("Nbre de voie")
    
    capacite_de_levage_vsb                   = fields.Boolean("Capacite de Levage (kg) vsb", compute='_compute')
    capacite_de_levage_obl                   = fields.Boolean("Capacite de Levage (kg) obl", compute='_compute')
    capacite_de_levage                       = fields.Integer("Capacite de Levage (kg)")
    
    dimension_bande_vsb                      = fields.Boolean("Dimension bande (mm) vsb", compute='_compute')
    dimension_bande_obl                      = fields.Boolean("Dimension bande (mm) obl", compute='_compute')
    dimension_bande                          = fields.Integer("Dimension bande (mm)")
    
    dimension_cage_vsb                       = fields.Boolean("Dimension cage (mm) vsb", compute='_compute')
    dimension_cage_obl                       = fields.Boolean("Dimension cage (mm) obl", compute='_compute')
    dimension_cage                           = fields.Integer("Dimension cage (mm)")
    
    poids_kg_vsb                             = fields.Boolean("Poids (kg) vsb", compute='_compute')
    poids_kg_obl                             = fields.Boolean("Poids (kg) obl", compute='_compute')
    poids_kg                                 = fields.Integer("Poids (kg)")
    
    affectation_sur_le_site_vsb              = fields.Boolean("Affectation sur le site vsb", compute='_compute')
    affectation_sur_le_site_obl              = fields.Boolean("Affectation sur le site obl", compute='_compute')
    affectation_sur_le_site                  = fields.Char("Affectation sur le site")
    
    is_mold_ids_vsb                          = fields.Boolean(u"Moules affectés vsb", compute='_compute')
    is_mold_ids_obl                          = fields.Boolean(u"Moules affectés obl", compute='_compute')
    is_mold_ids                              = fields.Many2many("is.mold", "equipement_mold_rel", "equipement_id", "mold_id", u"Moules affectés")
    
    is_dossierf_ids_vsb                      = fields.Boolean("Dossier F vsb", compute='_compute')
    is_dossierf_ids_obl                      = fields.Boolean("Dossier F obl", compute='_compute')
    is_dossierf_ids                          = fields.Many2many("is.dossierf", "equipement_dossierf_rel", "equipement_id", "dossierf_id", "Dossier F")
    
    type_de_fluide_vsb                       = fields.Boolean("Type de fluide vsb", compute='_compute')
    type_de_fluide_obl                       = fields.Boolean("Type de fluide obl", compute='_compute')
    type_de_fluide                           = fields.Selection([
            ("eau", "eau"),
            ("huile", "huile"),
        ], "Type de fluide")
    
    temperature_maximum_vsb                  = fields.Boolean(u"Température maximum (°C) vsb", compute='_compute')
    temperature_maximum_obl                  = fields.Boolean(u"Température maximum (°C) obl", compute='_compute')
    temperature_maximum                      = fields.Integer(u"Température maximum (°C)")
    
    puissance_de_refroidissement_vsb         = fields.Boolean("Puissance de refroidissement (kw) vsb", compute='_compute')
    puissance_de_refroidissement_obl         = fields.Boolean("Puissance de refroidissement (kw) obl", compute='_compute')
    puissance_de_refroidissement             = fields.Float("Puissance de refroidissement (kw)", digits=(14, 2))
    
    debit_maximum_vsb                        = fields.Boolean(u"Débit maximum (L/min) (m3/h) vsb", compute='_compute')
    debit_maximum_obl                        = fields.Boolean(u"Débit maximum (L/min) (m3/h) obl", compute='_compute')
    debit_maximum                            = fields.Float(u"Débit maximum (L/min) (m3/h)", digits=(14, 2))
    
    volume_l_vsb                             = fields.Boolean("Volume (L) vsb", compute='_compute')
    volume_l_obl                             = fields.Boolean("Volume (L) obl", compute='_compute')
    volume_l                                 = fields.Integer("Volume (L)")
    
    option_depresssion_vsb                   = fields.Boolean(u"Option déprésssion vsb", compute='_compute')
    option_depresssion_obl                   = fields.Boolean(u"Option déprésssion obl", compute='_compute')
    option_depresssion                       = fields.Selection([
            ("oui", "oui"),
            ("non", "non"),
        ], u"Option déprésssion")
    
    mesure_debit_vsb                         = fields.Boolean(u"Mesure débit (L/mn) vsb", compute='_compute')
    mesure_debit_obl                         = fields.Boolean(u"Mesure débit (L/mn) obl", compute='_compute')
    mesure_debit                             = fields.Selection([
            ("oui", "oui"),
            ("non", "non"),
        ], u"Mesure débit (L/mn)")
    
    base_capacitaire_vsb                     = fields.Boolean("Base Capacitaire vsb", compute='_compute')
    base_capacitaire_obl                     = fields.Boolean("Base Capacitaire obl", compute='_compute')
    base_capacitaire                         = fields.Char("Base Capacitaire")
    
    emplacement_affectation_pe_vsb           = fields.Boolean("Emplacement / affectation PE vsb", compute='_compute')
    emplacement_affectation_pe_obl           = fields.Boolean("Emplacement / affectation PE obl", compute='_compute')
    emplacement_affectation_pe               = fields.Char("Emplacement / affectation PE")

    adresse_ip_mac_vsb = fields.Boolean("Adresse IP / MAC vsb", compute='_compute')
    adresse_ip_mac_obl = fields.Boolean("Adresse IP / MAC obl", compute='_compute')
    adresse_ip_mac     = fields.Char("Adresse IP / MAC")


    # Integration de THEIA
    ordre_vsb                   = fields.Boolean("ordre_vsb", compute='_compute')
    ordre_obl                   = fields.Boolean("ordre_obl", compute='_compute')
    ordre                       = fields.Integer('Ordre')

    ilot_id_vsb                 = fields.Boolean("ilot_id_vsb", compute='_compute')
    ilot_id_obl                 = fields.Boolean("ilot_id_obl", compute='_compute')
    ilot_id                     = fields.Many2one('is.ilot', u"Ilot")

    raspberry_id_vsb            = fields.Boolean("raspberry_id_vsb", compute='_compute')
    raspberry_id_obl            = fields.Boolean("raspberry_id_obl", compute='_compute')
    raspberry_id                = fields.Many2one('is.raspberry', u"Raspberry")

    etat_presse_id_vsb          = fields.Boolean("etat_presse_id_vsb", compute='_compute')
    etat_presse_id_obl          = fields.Boolean("etat_presse_id_obl", compute='_compute')
    etat_presse_id              = fields.Many2one('is.etat.presse', u"État Presse")

    couleur_vsb                 = fields.Boolean("couleur_vsb", compute='_compute')
    couleur_obl                 = fields.Boolean("couleur_obl", compute='_compute')
    couleur                     = fields.Char('Couleur'            , compute='_couleur')

    prioritaire_vsb             = fields.Boolean("prioritaire_vsb", compute='_compute')
    prioritaire_obl             = fields.Boolean("prioritaire_obl", compute='_compute')
    prioritaire                 = fields.Boolean('Presse prioritaire')

    zone_id_vsb                 = fields.Boolean("zone_id_vsb", compute='_compute')
    zone_id_obl                 = fields.Boolean("zone_id_obl", compute='_compute')
    zone_id                     = fields.Many2one("is.preventif.equipement.zone", "Zone préventif")

