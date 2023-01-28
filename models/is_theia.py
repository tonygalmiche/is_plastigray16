# -*- coding: utf-8 -*-
from odoo import models,fields,api,tools
import time
import datetime
import os
#import subprocess
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


couleurs=[
    ('blanc','Blanc'),
    ('bleu','Bleu'),
    ('orange','Orange'),
    ('rouge','Rouge'),
    ('vert','Vert')
]

colors=[
    ("blanc"  , "white"),
    ("bleu"   , "#5BC0DE"),
    ("orange" , "#F0AD4E"),
    ("rouge"  , "#D9534F"),
    ("vert"   , "#5CB85C"),
]

states=[
    ("attente-controleur", "Attente contrôleur"),
    ("attente-tuteur"    , "Attente tuteur"),
    ("poste"             , "Opérateur habilité"),
    ("qualification"     , "Qualification"),
    ("dequalification"   , "Déqualification"),
]

etats_sorties=[
    ("released", "Ouverte"),
    ("pressed" , "Fermée"),
]


class is_etat_presse_regroupement(models.Model):
    _name = 'is.etat.presse.regroupement'
    _description = u"Regroupement État Presse"
    _order='ordre,name'

    name             = fields.Char('Intitulé' , required=True)
    couleur          = fields.Selection(couleurs, 'Couleur', required=False, help="Couleur affichée dans l'interface à la presse")
    ordre            = fields.Integer('Ordre', required=False, default=0)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', u"L'intulé doit être unique !"),
    ]


class is_etat_presse(models.Model):
    _name = 'is.etat.presse'
    _description = u"État Presse"
    _order='name5x5'    #Ordre de tri par defaut des listes
    _rec_name = 'name5x5'

    name             = fields.Char(u'Intitulé (4x4)'  , required=False)
    ligne            = fields.Integer(u'Ligne (4x4)'  , required=False)
    colonne          = fields.Integer(u'Colonne (4x4)', required=False)
    name5x5          = fields.Char(u'Intitulé'  , required=False)
    ligne5x5         = fields.Integer(u'Ligne'  , required=False)
    colonne5x5       = fields.Integer(u'Colonne', required=False)
    regroupement_id  = fields.Many2one('is.etat.presse.regroupement', u"Regroupement État Presse")
    couleur          = fields.Selection(couleurs, 'Couleur', required=False, help="Couleur affichée dans l'interface à la presse")
    production_serie = fields.Boolean('Production série',help='Cocher cette case si cet état correspond à la production série')
    action_id        = fields.Many2one('is.theia.validation.action', u"Action de validation")

    _sql_constraints = [
        ('name_uniq', 'unique(name)', u"L'intulé doit être unique !"),
    ]


class is_raspberry_entree_sortie(models.Model):
    _name = 'is.raspberry.entree.sortie'
    _description = u"Gestion des Entrées / Sorties du Raspberry"
    _order='entree_sortie,numero'
    
    @api.depends('etat')
    def _couleur(self):
        for obj in self:
            couleur=""
            if obj.etat=="pressed":
                couleur="#5CB85C"
            if obj.etat=="released":
                couleur="#D9534F"
            obj.couleur=couleur




    raspberry_id  = fields.Many2one('is.raspberry', 'Raspberry', required=True, ondelete='cascade', readonly=True)
    numero        = fields.Char(u'Numéro', required=True, index=True)
    entree_sortie = fields.Char(u'Entrée / Sortie', required=True, index=True)
    etat          = fields.Selection(etats_sorties, u'État', required=True, index=True)
    couleur       = fields.Char(u'Couleur', compute='_couleur')



    def changer_etat_action(self):
        for obj in self:
            if obj.etat=='pressed':
                etat="released"
            else:
                etat="pressed"
            obj.etat=etat
            IP=obj.raspberry_id.name
            _logger.info("is_raspberry_entree_sortie : changer_etat_action : %s : %s : %s : %s"%(etat, IP, obj.entree_sortie, obj.numero))
            cmd="ssh -o ConnectTimeout=2 -o StrictHostKeyChecking=no root@"+IP+' "service theia restart"'
            obj.raspberry_id.rafraichir_sorties()
            return True



class is_raspberry_zebra(models.Model):
    _name = 'is.raspberry.zebra'
    _description = u"is_raspberry_zebra"
    _order='name'
    
    name = fields.Char(u'Imprimante Zebra' , required=True)


class is_raspberry(models.Model):
    _name = 'is.raspberry'
    _description = u"raspberry"
    _order='name'
    

    @api.depends('name')
    def _compute_presse_id(self):
        for obj in self:
            presses = self.env['is.equipement'].search([('raspberry_id','=',obj.id)])
            presse_id=False
            for presse in presses:
                presse_id = presse.id
            obj.last_presse_id = presse_id


    name               = fields.Char(u'Adresse IP' , required=True)
    adresse_mac        = fields.Char(u'Adresse MAC', index=True)
    last_presse_id     = fields.Many2one('is.equipement', u"Equipement", compute='_compute_presse_id', required=False, readonly=True)
    onglet_indicateurs = fields.Boolean(u'Afficher onglet "Indicateurs"' , default=False)
    onglet_es          = fields.Boolean(u'Afficher onglet "Entrées / Sorties"', default=False)
    onglet_actif       = fields.Char(u'Onglet actif', readonly=True, help=u"Ce champ est utilsé pour détecter si une mise à jour de l'onglet Indicateurs est necessaire")
    declaration_odoo   = fields.Boolean(u'Activer la déclaration de production dans Odoo', default=False)
    zebra_id           = fields.Many2one('is.raspberry.zebra', u"Imprimante Zebra")
    entree_ids         = fields.One2many('is.raspberry.entree.sortie', 'raspberry_id', u"Entrées du Raspberry",  domain=[('entree_sortie','=','entree')])
    sortie_ids         = fields.One2many('is.raspberry.entree.sortie', 'raspberry_id', u"Sorties du Raspberry",  domain=[('entree_sortie','=','sortie')])


    def rafraichir_raspberry(self):
        for obj in self:
            IP=obj.name
            cmd="ssh -o ConnectTimeout=2 -o StrictHostKeyChecking=no root@"+IP+' "export XAUTHORITY=/home/pi/.Xauthority; export DISPLAY=:0; xdotool search --class chromium | tail -1"'
            WID=subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell = True).strip()
            cmd="ssh -o ConnectTimeout=2 -o StrictHostKeyChecking=no root@"+IP+' "export XAUTHORITY=/home/pi/.Xauthority; export DISPLAY=:0 && xdotool windowfocus '+WID+' && xdotool key --window '+WID+' F5"'
            res=subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell = True).strip()


    def rafraichir_sorties(self):
        for obj in self:
            IP=obj.name
            sorties=list("00000000")
            for line in obj.sortie_ids:
                if line.etat=="pressed" and line.numero:
                    n = int(line.numero)
                    sorties[n-1]="1"
            sorties = "".join(sorties)
            path="/tmp/sorties-rasberry-"+IP+".txt"
            f = open(path, "w")
            f.write(sorties)
            f.close()
            cmd="scp -o ConnectTimeout=2 -o StrictHostKeyChecking=no "+path+" root@"+IP+":/opt/theia/sorties/sorties.txt"
            res=subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell = True).strip()

            _logger.info("is_raspberry : rafraichir_sorties : %s : %s : %s"%(obj.name, sorties, res))


            #TODO : Le rafraissement ne fonctionne pas toujours (1 fois sur 2)
            #cmd="ssh -o ConnectTimeout=2 -o StrictHostKeyChecking=no root@"+IP+' "export XAUTHORITY=/home/pi/.Xauthority; export DISPLAY=:0; xdotool search --class chromium | tail -1"'
            #WID=subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell = True).strip()
            #print WID,type(WID)
            #cmd="ssh -o ConnectTimeout=2 -o StrictHostKeyChecking=no root@"+IP+' "export XAUTHORITY=/home/pi/.Xauthority; export DISPLAY=:0 && xdotool windowfocus '+WID+' && xdotool key --window '+WID+' Shift_L+F1"'  #Shift_L+F2
            #res=subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell = True).strip()
            #print res,type(res)

            #cmd="export XAUTHORITY=/home/pi/.Xauthority; export DISPLAY=:0 && xdotool windowfocus "+WID+" && xdotool key --window "+WID+" Shift_L+F2"


            #Envoi d'une série de touche au clavier (ex : Badge RFID) (pour test)
            #cmd="ssh -o ConnectTimeout=2 root@"+IP+' "export XAUTHORITY=/home/pi/.Xauthority; export DISPLAY=:0; xdotool search --class chromium | tail -1"'
            #WID=subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell = True).strip()
            #cmd="ssh -o ConnectTimeout=2 root@"+IP+' "export XAUTHORITY=/home/pi/.Xauthority; export DISPLAY=:0 && xdotool windowfocus '+WID+' && xdotool type --window '+WID+' 3742554362 && xdotool key --window '+WID+' KP_Enter"'
            #res=subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell = True).strip()


class is_of(models.Model):
    _name = 'is.of'
    _description = u"Ordre de fabrication"
    _rec_name = "name"
    _order='name desc'

    name              = fields.Char('N°OF' , required=True)
    moule             = fields.Char('Moule' , required=False)
    nb_empreintes     = fields.Integer("Nombre d'empreintes", required=False)
    coef_cpi          = fields.Float("Coefficient Theia", required=False, digits=(14,2))
    code_article      = fields.Char('Code article' , required=True)
    categorie         = fields.Char('Catégorie')
    designation       = fields.Char('Désignation' , required=False)
    uc                = fields.Integer('Qt par UC', required=False)
    cout              = fields.Float('Coût article', digits=(12,4), required=False)
    presse_id         = fields.Many2one('is.equipement', u"Equipement",  domain=[('type_id.code','=','PE')], required=False, index=False)
    affecte           = fields.Boolean(u"OF affecté à l'équipement", index=True,help=u"Cocher cette case si l'OF est affecté à l'équipement")
    ordre             = fields.Integer('Ordre', index=True, required=False)
    qt                = fields.Integer('Qt à produire', required=False)
    nb_cycles         = fields.Integer('Nombre de cycles')
    qt_theorique      = fields.Integer('Qt réalisée théorique', required=False)
    qt_declaree       = fields.Integer('Qt déclarée', required=False)
    qt_restante       = fields.Integer('Qt restante', required=False)
    qt_rebut          = fields.Integer('Qt rebuts')
    qt_rebut_theo     = fields.Integer('Qt rebuts théorique')
    taux_rebut        = fields.Float('Taux rebuts (%)'          , digits=(12,2))
    taux_rebut_theo   = fields.Float('Taux rebuts théorique (%)', digits=(12,2))
    cycle_gamme       = fields.Float('Cycle gamme', digits=(12,1), required=False)
    cycle_moyen       = fields.Float('Cycle moyen (10 derniers cycles)', digits=(12,1), required=False)
    cycle_moyen_serie = fields.Float('Cycle moyen', help=u'Temps de production série / nombre de cycles', digits=(12,1), required=False)
    tps_restant       = fields.Float('Temps de production restant', required=False)
    heure_debut       = fields.Datetime('Heure de début de production', index=True, required=False)
    heure_fin         = fields.Datetime('Heure de fin de production', required=False, index=True)
    employee_id       = fields.Many2one("hr.employee", "Employé")
    heure_fin_planning= fields.Datetime('Heure de fin du planning')
    tps_ids           = fields.One2many('is.of.tps'  , 'of_id', u"Répartition des temps d'arrêt")
    rebut_ids         = fields.One2many('is.of.rebut', 'of_id', u"Répartition des rebuts")
    impression_bilan  = fields.Boolean('Bilan imprimé et envoyé par mail', index=True)
    impression_bilan_equipe = fields.Boolean(u"Bilan des OFs de l'équipe imprimé et envoyé par mail", index=True, default=False)
    prioritaire       = fields.Boolean('Ordre de fabrication prioritaire')
    
    _sql_constraints = [
        ('name_uniq', 'unique(name)', u"Le numéro d'OF doit être unique !"),
    ]


    def get_id_production_serie(self):
        cr = self._cr
        SQL="""
            select id from is_etat_presse where name='Production série'
        """
        cr.execute(SQL)
        result = cr.fetchall()
        id_etat_presse=0
        for row in result:
            id_etat_presse=row[0]
        return id_etat_presse


    def get_cycle_moyen_serie(self):
        cr = self._cr
        id_production_serie=self.get_id_production_serie()
        nb=len(self)
        ct=0
        for obj in self:
            if obj.qt_theorique!=0:
                ct=ct+1
                SQL="""
                    select
                        ipa.type_arret_id,
                        sum(ipa.tps_arret)
                    from is_presse_arret ipa inner join is_presse_arret_of_rel ipaof on ipa.id=ipaof.is_of_id
                                             inner join is_of                     io on ipaof.is_presse_arret_id=io.id
                    where 
                        ipaof.is_presse_arret_id="""+str(obj.id)+""" and 
                        io.presse_id=ipa.presse_id and 
                        ipa.type_arret_id="""+str(id_production_serie)+"""
                    group by ipa.type_arret_id
                """
                cr.execute(SQL)
                result = cr.fetchall()
                tps_prod_serie=0
                for row in result:
                    tps_prod_serie=row[1]
                cycle_moyen=tps_prod_serie*3600/obj.qt_theorique
                obj.cycle_moyen_serie=cycle_moyen
                _logger.info(str(ct)+u"/"+str(nb)+u" - Calcul cycle moyen "+obj.name+u' ('+str(cycle_moyen)+u')')


    def get_qt_rebut(self):
        cr = self._cr
        nb=len(self)
        ct=0
        for obj in self:
            ct=ct+1
            SQL="""
                select sum(iod.qt_rebut) 
                from is_of_declaration iod
                where iod.of_id="""+str(obj.id)+"""
            """
            cr.execute(SQL)
            result = cr.fetchall()
            qt_rebut=0
            for row in result:
                qt_rebut=row[0]
            obj.qt_rebut=qt_rebut
            _logger.info(str(ct)+u"/"+str(nb)+u" - Recalcul Qt Rebut "+obj.name+u' ('+str(qt_rebut)+u')')


    def bilan_fin_of(self):
        cr = self._cr

        id_etat_presse=self.get_id_production_serie()

        nb=len(self)
        ct=0
        for obj in self:
            ct=ct+1
            _logger.info(str(ct)+u"/"+str(nb)+u" - "+obj.name)

            #** Répartition des temps d'arrêt **********************************
            SQL="""
                select
                    ipa.type_arret_id,
                    sum(ipa.tps_arret)
                from is_presse_arret ipa inner join is_presse_arret_of_rel ipaof on ipa.id=ipaof.is_of_id
                                         inner join is_of                     io on ipaof.is_presse_arret_id=io.id
                where ipaof.is_presse_arret_id="""+str(obj.id)+""" and io.presse_id=ipa.presse_id
                group by ipa.type_arret_id
            """
            cr.execute(SQL)
            result = cr.fetchall()
            obj.tps_ids.unlink()
            tps_prod_serie=0
            for row in result:
                vals={
                    'of_id'         : obj.id,
                    'etat_presse_id': row[0],
                    'tps_arret'     : row[1],
                }
                if id_etat_presse==row[0]:
                    tps_prod_serie=row[1]
                self.env['is.of.tps'].create(vals)
            #*******************************************************************

            #** Temps de cycle moyen série *************************************
            if obj.qt_theorique!=0:
                obj.cycle_moyen_serie=tps_prod_serie*3600/obj.qt_theorique
            #*******************************************************************


            #** Répartition des rebuts *****************************************
            SQL="""
                select defaut_id,sum(qt_rebut)::int
                from is_of_declaration 
                where of_id="""+str(obj.id)+""" and qt_rebut is not null and defaut_id is not null
                group by defaut_id;
            """
            cr.execute(SQL)
            result = cr.fetchall()
            obj.rebut_ids.unlink()
            for row in result:
                vals={
                    'of_id'    : obj.id,
                    'defaut_id': row[0],
                    'qt_rebut' : row[1],
                }
                id=self.env['is.of.rebut'].create(vals)
            #*******************************************************************

            #** Quantité déclarée bonne ****************************************
            SQL="""
                select sum(qt_bonne)::int
                from is_of_declaration 
                where of_id="""+str(obj.id)+""" and qt_bonne is not null
            """
            cr.execute(SQL)
            result = cr.fetchall()
            for row in result:
                obj.qt_declaree=row[0]
            #*******************************************************************


            #** Nombre de cycles ***********************************************
            SQL="""
                SELECT count(*) as nb
                FROM is_presse_cycle a inner join is_presse_cycle_of_rel b on id=b.is_of_id
                WHERE is_presse_cycle_id="""+str(obj.id)+"""
                GROUP BY b.is_presse_cycle_id
            """
            cr.execute(SQL)
            result = cr.fetchall()
            for row in result:
                obj.nb_cycles=row[0]
            #*******************************************************************


            #** Taux de rebuts *************************************************
            self.get_qt_rebut()
            qt_bonne = obj.qt_declaree or 0
            qt_rebut = obj.qt_rebut or 0
            taux_rebut=0
            if (qt_bonne+qt_rebut)!=0:
                taux_rebut=100.0*qt_rebut/(qt_bonne+qt_rebut)
            obj.taux_rebut=taux_rebut

            qt_theorique   = obj.qt_theorique or 0
            qt_rebut_theo  = qt_theorique-qt_bonne
            if qt_rebut_theo<0:
                qt_rebut_theo=0
            taux_rebut_theo=0
            if qt_theorique!=0:
                taux_rebut_theo=100.0*qt_rebut_theo/qt_theorique
            obj.qt_rebut_theo   = qt_rebut_theo
            obj.taux_rebut_theo = taux_rebut_theo
            #*******************************************************************
        return []



class is_of_tps(models.Model):
    _name='is.of.tps'
    _description="is_of_tps"
    _order='of_id,tps_arret desc,etat_presse_id'

    @api.depends('etat_presse_id')
    def _couleur(self):
        for obj in self:
            couleur=""
            for color in colors:
                if obj.etat_presse_id.couleur==color[0]:
                    couleur=color[1]
            obj.couleur=couleur

    of_id          = fields.Many2one('is.of', 'N°OF', required=True, ondelete='cascade', readonly=True)
    etat_presse_id = fields.Many2one('is.etat.presse', u"État Presse", required=True)
    couleur        = fields.Char('Couleur', compute='_couleur')
    tps_arret      = fields.Float('Durée dans cet état (H)', digits=(12,4))


class is_of_rebut(models.Model):
    _name='is.of.rebut'
    _description="is_of_rebut"
    _order='of_id,qt_rebut desc,defaut_id'

    of_id      = fields.Many2one('is.of', 'N°OF', required=True, ondelete='cascade', readonly=True)
    defaut_id  = fields.Many2one('is.type.defaut', u"Type de défaut", required=True)
    qt_rebut   = fields.Integer('Qt rebut')


class is_of_declaration(models.Model):
    _name = 'is.of.declaration'
    _description = u"Déclaration des fabrications et des rebuts sur les OF"
    _rec_name = "name"
    _order='name desc'

    name        = fields.Datetime("Date Heure",required=True)
    of_id       = fields.Many2one('is.of', u"OF", required=True)
    num_carton  = fields.Integer('N°Carton', required=False)
    qt_bonne    = fields.Integer('Qt bonne', required=False)
    qt_rebut    = fields.Integer('Qt rebut', required=False)
    defaut_id   = fields.Many2one('is.type.defaut', u"Type de défaut", required=False)
    employee_id = fields.Many2one("hr.employee", "Employé")


class is_presse_cycle(models.Model):
    _name = 'is.presse.cycle'
    _description = u"Cycles des presses"
    _rec_name = "date_heure"
    _order='date_heure desc'

    @api.depends('etat')
    def _couleur(self):
        for obj in self:
            couleur=""
            if obj.etat=="pressed":
                couleur="#5CB85C"
            if obj.etat=="released":
                couleur="#D9534F"
            obj.couleur=couleur

    date_heure = fields.Datetime("Date Heure",required=True, index=True)
    presse_id  = fields.Many2one('is.equipement', u"Equipement",  domain=[('type_id.code','=','PE')], required=False, index=True)
    entree     = fields.Char("Entrée", index=True)
    etat       = fields.Char("État"  , index=True)
    couleur    = fields.Char('Couleur', compute='_couleur')
    of_ids     = fields.Many2many('is.of', 'is_presse_cycle_of_rel', 'is_of_id', 'is_presse_cycle_id', 'OF', readonly=False, required=False)
    

class is_presse_arret(models.Model):
    _name = 'is.presse.arret'
    _description = u"Arrêts des presses"
    _rec_name = "date_heure"
    _order='date_heure desc'

    @api.depends('date_heure')
    def _couleur(self):
        for obj in self:
            couleur=""
            for color in colors:
                if obj.type_arret_id.couleur==color[0]:
                    couleur=color[1]
            obj.couleur=couleur

    date_heure    = fields.Datetime("Date Heure",required=True)
    presse_id     = fields.Many2one('is.equipement', u"Equipement",  domain=[('type_id.code','=','PE')], required=True, index=True)
    type_arret_id = fields.Many2one('is.etat.presse', u"État équipement", required=True)
    couleur       = fields.Char('Couleur'            , compute='_couleur')
    origine       = fields.Char("Origine du changement d'état")
    tps_arret     = fields.Float("Durée dans cet état", required=False)
    of_ids        = fields.Many2many('is.of', 'is_presse_arret_of_rel', 'is_of_id', 'is_presse_arret_id', 'OF', readonly=False, required=False)
    employee_id   = fields.Many2one("hr.employee", "Employé")


class is_type_defaut(models.Model):
    _name = 'is.type.defaut'
    _description = u"Type de défaut des rebuts"
    _order='name'

    name   = fields.Char('Type de défaut' , required=True)
    active = fields.Boolean(u'Actif', default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', u"Le type de défaut doit être unique !"),
    ]


class is_theia_trs(models.Model):
    _name = 'is.theia.trs'
    _description = u"Table calculée pour optimiser temps de réponse analyse TRS"
    _order='presse,date_heure desc,of'

    date_heure   = fields.Datetime(u'Heure début' , required=True, index=True)
    presse       = fields.Char(u'Presse'          , required=True, index=True)
    presse_id    = fields.Many2one('is.equipement', u"Equipement", required=True, index=True)
    ilot         = fields.Char(u'Ilot', index=True)
    etat         = fields.Char(u'État'            , required=True, index=True)
    etat_id      = fields.Many2one('is.etat.presse', u"État id", required=True, index=True)
    couleur      = fields.Char(u'Couleur Etat')
    of           = fields.Char(u'Code OF'              , required=True, index=True)
    of_id        = fields.Many2one('is.of', u"OF" , index=True)
    code_article = fields.Char('Code article', index=True)
    categorie    = fields.Char('Catégorie', index=True)
    moule        = fields.Char(u'Moule'           , required=True, index=True)
    coef_theia   = fields.Float("Coefficient Theia", digits=(14,2), default=1)
    duree_etat   = fields.Float("Durée dans cet état")
    duree_of     = fields.Float("Durée par OF")


class is_theia_validation_groupe(models.Model):
    _name = 'is.theia.validation.groupe'
    _description = u"Groupes de validation THEIA"
    _order='name'

    name         = fields.Char(u'Groupe de validation THEIA', required=True)
    employee_ids = fields.Many2many("hr.employee", "is_theia_validation_groupe_employee_rel", "groupe_id", "employee_id", "Employés")


class is_theia_validation_action(models.Model):
    _name = 'is.theia.validation.action'
    _description = u"Actions de validation THEIA"
    _order='name'

    name       = fields.Char(u'Action de validation THEIA', required=True)
    code       = fields.Char(u'Code', required=True)
    groupe_ids = fields.Many2many("is.theia.validation.groupe", "is_theia_validation_action_groupe_rel", "action_id", "groupe_id", "Groupes")


class is_theia_habilitation_operateur(models.Model):
    _name = 'is.theia.habilitation.operateur'
    _description = u"Habilitation des opérateurs sur les Moules avec THEIA"
    _rec_name = "heure_debut"
    _order='heure_debut desc'

    heure_debut  = fields.Datetime(u'Heure de début'          , required=True , index=True)
    heure_fin    = fields.Datetime(u'Heure de fin'            , required=False, index=True)
    presse_id    = fields.Many2one('is.equipement', u"Equipement" , required=True , index=True)
    moule        = fields.Char(u'Moule'                       , required=True , index=True)
    operateur_id = fields.Many2one("hr.employee", u"Opérateur", required=True , index=True)
    valideur_id  = fields.Many2one("hr.employee", u"Valideur" , required=False, index=True)
    state        = fields.Selection(states, 'État'            , required=True , index=True)


class is_theia_habilitation_operateur_etat(models.Model):
    _name = 'is.theia.habilitation.operateur.etat'
    _description="is_theia_habilitation_operateur_etat"
    _order = 'presse_id,moule,operateur_id'
    _auto = False

    presse_id    = fields.Many2one('is.equipement', u"Equipement" , required=True , index=True)
    moule        = fields.Char(u'Moule'                       , required=True , index=True)
    operateur_id = fields.Many2one("hr.employee", u"Opérateur", required=True , index=True)
    state        = fields.Selection(states, 'État'            , required=True , index=True)
    heure_debut  = fields.Datetime(u'Heure de début'          , required=True , index=True)

    def init(self):
        cr=self._cr
        tools.drop_view_if_exists(cr, 'is_theia_habilitation_operateur_etat')
        cr.execute("""
            CREATE OR REPLACE view is_theia_habilitation_operateur_etat AS (
                select 
                    a.presse_id,
                    a.moule,
                    a.operateur_id, 
                    max(a.id) id,
                    (   select b.state       
                        from is_theia_habilitation_operateur b 
                        where a.presse_id=b.presse_id and a.moule=b.moule and a.operateur_id=b.operateur_id 
                        order by b.id desc limit 1
                    ) state,
                    (   select c.heure_debut 
                        from is_theia_habilitation_operateur c 
                        where a.presse_id=c.presse_id and a.moule=c.moule and a.operateur_id=c.operateur_id 
                        order by c.id desc limit 1
                    ) heure_debut
                from is_theia_habilitation_operateur a 
                group by a.presse_id,a.moule,a.operateur_id
            )
        """)


class is_theia_lecture_ip(models.Model):
    _name = 'is.theia.lecture.ip'
    _description = u"Lecture des Instructions particulières des opérateurs sur les Moules dans THEIA"
    _rec_name = "date_heure"
    _order='date_heure desc'

    date_heure   = fields.Datetime(u'Heure de lecture'                                                    , required=True , index=True)
    presse_id    = fields.Many2one('is.equipement', u"Equipement"                                             , required=True , index=True)
    moule        = fields.Char(u'Moule'                                                                   , required=True , index=True)
    of_ids       = fields.Many2many('is.of', 'is_theia_lecture_ip_of_rel', 'lecture_ip_id', 'of_id', 'OFs', required=False)
    operateur_id = fields.Many2one("hr.employee", u"Opérateur"                                            , required=True , index=True)
    ip_id        = fields.Many2one("is.instruction.particuliere", u"Instruction Particulière"             , required=True , index=True)


class is_mold(models.Model):
    _inherit = 'is.mold'

    def dequalification_moule_action(self):
        cr = self._cr
        for obj in self:
            valideur_id = False
            employes = self.env['hr.employee'].search([('user_id','=',self._uid)])
            for employe in employes:
                valideur_id = employe.id
            SQL="""
                select distinct presse_id,operateur_id
                from is_theia_habilitation_operateur
                where moule=%s order by presse_id,operateur_id
            """
            cr.execute(SQL,[obj.name])
            result = cr.fetchall()
            for row in result:
                vals={
                    "heure_debut" : fields.datetime.now(),
                    "heure_fin"   : fields.datetime.now(),
                    "presse_id"   : row[0],
                    "moule"       : obj.name,
                    "operateur_id": row[1],
                    "valideur_id" : valideur_id,
                    "state"       : "dequalification",
                }
                id=self.env['is.theia.habilitation.operateur'].create(vals)


class is_theia_alerte_type(models.Model):
    _name = 'is.theia.alerte.type'
    _description = u"Type d'alerte dans THEIA"
    _order='name'

    name = fields.Char(u"Type d'alerte", required=True)
    code = fields.Char(u"Code"         , required=True)


class is_theia_alerte(models.Model):
    _name = 'is.theia.alerte'
    _description = u"Alerte dans THEIA"
    _order='equipement_id, type_alerte_id, heure_debut desc'

    equipement_id  = fields.Many2one("is.equipement"       , u"Process", required=True , index=True)
    type_alerte_id = fields.Many2one("is.theia.alerte.type", u"Type d'alerte"    , required=True , index=True)
    heure_debut    = fields.Datetime(u'Heure de début', required=True, index=True)
    heure_fin      = fields.Datetime(u'Heure de fin', index=True)
    active         = fields.Boolean(u'Active'       , index=True, default=True)


