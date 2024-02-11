# -*- coding: utf-8 -*-

from odoo import models,fields,api
from odoo.exceptions import ValidationError
import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import sys


dessication_list=[('N', u'N'),('DS', u'DS')]


class is_etuve(models.Model):
    _name='is.etuve'
    _description="Etuve"
    _order='name'
    _sql_constraints = [('name_uniq','UNIQUE(name)', u'Cette étuve existe déjà')]

    name            = fields.Char("N°étuve",size=10, index=True                     , required=True)
    dessication     = fields.Selection(dessication_list, "Dessication"              , required=True, default="N")
    type_etuve      = fields.Selection([('0', u'0'),('MAT', u'MAT')], "Type étuve"  , required=True, default="0")
    capacite        = fields.Integer("Capacité"                                     , required=True, default=0)

    matiere_id        = fields.Many2one('product.product', 'Matière', readonly=True)
    num_ordre_matiere = fields.Char("N°ordre matière"               , readonly=True)
    of                = fields.Char("OF"                            , readonly=True)
    moule             = fields.Char("Moule"                         , readonly=True)
    taux_utilisation  = fields.Float("Taux d'utilisation étuve (%)" , readonly=True)
    progressbar       = fields.Float("Taux d'utilisation étuve"     , readonly=False)
    test_taux         = fields.Boolean("Test Taux"                  , readonly=True)
    message           = fields.Char("Message"                       , readonly=True)
    rsp_etuve_id      = fields.Many2one('is.etuve.rsp', 'Rsp étuve' , readonly=True)
    commentaire       = fields.Char("Commentaire optionnel"          , readonly=True)


    def action_saisie_etuve(self):
        for obj in self:
            saisie_obj = self.env['is.etuve.saisie']
            saisies  = saisie_obj.search([('etuve_id','=',obj.id)],limit=1)
            context={}
            for saisie in saisies:
                context={
                    'default_etuve_id'    : saisie.etuve_id.id,
                    'default_matiere_id'  : saisie.matiere_id.id,
                    'default_rsp_etuve_id': saisie.rsp_etuve_id.id,
                }
                ids=[]
                for of in saisie.of_ids:
                    vals={
                        'of_id': of.of_id.id
                    }
                    ids.append(vals)
                if len(ids)>0:
                    context.update({'default_of_ids': ids})
            return {
                'name'     : 'Saisie étuve',
                'view_mode': 'form',
                'res_model': 'is.etuve.saisie',
                'type'     : 'ir.actions.act_window',
                'context'  : context,
             }






class is_etuve_rsp(models.Model):
    _name='is.etuve.rsp'
    _description="Responsable Etuve"
    _order='name'
    _sql_constraints = [('name_uniq','UNIQUE(name)', u'Ce responsable existe déjà')]

    name         = fields.Char("Responsable étuve", required=True, index=True)
    mot_de_passe = fields.Char("Mot de passe"     , required=True)


class is_etuve_commentaire(models.Model):
    _name='is.etuve.commentaire'
    _description="Commentaire Etuve"
    _order='name'
    _sql_constraints = [('name_uniq','UNIQUE(name)', u'Ce commentaire existe déjà')]

    name         = fields.Char("Commentaire étuve", required=True, index=True)


class is_etuve_saisie(models.Model):
    _name='is.etuve.saisie'
    _description="Saisie Etuve"
    _order='name desc'


    def _string2float(self,val):
        val=str(val)
        res=0
        if val!='None':
            res=float(val.replace(',','.'))
        return res


    @api.depends('matiere_id','of_ids')
    def _compute(self):
        uid=self._uid
        cr=self._cr
        company = self.env.user.company_id
        for obj in self:
            base0="odoo16-0"
            if company.is_postgres_host=='localhost':
                base0="pg-odoo16-0"
            try:
                #url = "dbname='"+base0+"' user='"+company.is_postgres_user+"' host='"+company.is_postgres_host+"' password='"+company.is_postgres_pwd+"'"
                url = "dbname='%s' user='%s' host='%s' password='%s'"%(base0,company.is_postgres_user,company.is_postgres_host,company.is_postgres_pwd)
                cnx0 = psycopg2.connect(url)
                cr0 = cnx0.cursor(cursor_factory=RealDictCursor)
            except:
                raise ValidationError("Impossible de se connecter à %s"%(base0))

            #** Recherche fiche technique Matière dans odoo0 ******************
            tmp_etuvage=tps_etuvage=densite=dessication_matiere=False
            CodeMatiere=obj.matiere_id.is_code
            if CodeMatiere:
                SQL="""
                    SELECT densite, temps_etuvage, temperature_etuvage, dessiccateur
                    FROM is_dossier_article
                    WHERE code_pg=%s
                """
                cr0.execute(SQL, [CodeMatiere])
                result = cr0.fetchall()
                for row in result:
                    tmp_etuvage         = row["temperature_etuvage"]
                    tps_etuvage         = row["temps_etuvage"]
                    densite             = row["densite"]
                    dessication_matiere = row["dessiccateur"]
            #******************************************************************

            obj.tmp_etuvage   = tmp_etuvage
            obj.tps_etuvage   = tps_etuvage
            obj.densite       = densite
            obj.dessication_matiere = dessication_matiere
            obj.capacite_maxi = str(len(obj.of_ids))
            EtuveCapacite=obj.etuve_id.capacite
            CoefSecurite=0.95
            CoefFoisonnement=0.6
            capacite_maxi=False
            if densite:
                capacite_maxi=round(CoefSecurite*CoefFoisonnement*EtuveCapacite*densite,0)
            obj.capacite_maxi = capacite_maxi
            conso_horaire=0.0
            for row in obj.of_ids:
                conso_horaire=conso_horaire+round(row.debit)
            obj.conso_horaire = conso_horaire
            taux_utilisation=False
            if capacite_maxi: 
                taux_utilisation=round(100*tps_etuvage*conso_horaire/capacite_maxi,2)
            obj.taux_utilisation=taux_utilisation
            test_taux=message=False
            if taux_utilisation>105:
                test_taux=True
                message=u"Attention : Le taux d'utilisation de l'étuve est de "+str(int(taux_utilisation))+u'%'
            obj.test_taux=test_taux
            obj.message=message


    name                 = fields.Char("Saisie", index=True , readonly=True)
    etuve_id             = fields.Many2one('is.etuve', 'Etuve', required=True)
    capacite             = fields.Integer('Capacité' , related='etuve_id.capacite'   , readonly=True)
    dessication          = fields.Selection(string="Dessication", related='etuve_id.dessication', readonly=True)
    num_ordre_matiere    = fields.Char("N°ordre matière")                # required=True
    rsp_etuve_id         = fields.Many2one('is.etuve.rsp', 'Rsp étuve')  # required=True

    fake_mot_de_passe    = fields.Char("Fake mot de passe", store=False) # Astuce pour ne pas afficher la liste des mots de passe dans le champ au dessus de mot_de_passe
    mot_de_passe         = fields.Char("Mot de passe")                   # required=True

    commentaire_id       = fields.Many2one('is.etuve.commentaire', 'Commentaire') # required=True
    commentaire_optionel = fields.Char("Commentaire optionnel")

    matiere_id           = fields.Many2one('product.product', 'Matière', required=True, domain=[('family_id.name','=','MATIERE')] )
    tmp_etuvage          = fields.Float("Température d'étuvage"    , readonly=True, compute='_compute', store=True)
    tps_etuvage          = fields.Float("Temps d'étuvage matière"  , readonly=True, compute='_compute', store=True)
    densite              = fields.Float("Densité"                  , readonly=True, compute='_compute', store=True)
    dessication_matiere  = fields.Char("Dessication Matière"       , readonly=True, compute='_compute', store=True)
    capacite_maxi        = fields.Float("Capacité maxi étuve (Kg)"  , readonly=True, compute='_compute', store=True)
    conso_horaire        = fields.Float("Consommation horaire (Kg/H)", readonly=True, compute='_compute', store=True)
    taux_utilisation     = fields.Float("Taux utilisation étuve (%)", readonly=True, compute='_compute', store=True)
    test_taux            = fields.Boolean("Test Taux"               , readonly=True, compute='_compute', store=True)
    message              = fields.Char("Message"                    , readonly=True, compute='_compute', store=True)
    of_ids               = fields.One2many('is.etuve.of', 'etuve_id', u"OFs")
    
    state = fields.Selection(
        [("brouillon", "Brouillon"), ("valide", "Validé")],
        required=True,
        default="brouillon",
    )
    active = fields.Boolean("Active", default=False)


    def validation_action(self):
        for obj in self:
            if not obj.num_ordre_matiere or not obj.rsp_etuve_id or not obj.commentaire_id:
                raise ValidationError("Les champs 'N°ordre matière', 'Rsp étuve' et 'Commentaire' sont obligatoires !")
            if obj.rsp_etuve_id.mot_de_passe!=obj.mot_de_passe:
                raise ValidationError("Mot de passe incorecte !")
            
            #** Mise à jour des données de l'étuve *********************************
            etuve=obj.etuve_id.sudo()
            etuve.matiere_id        = obj.matiere_id.id
            etuve.num_ordre_matiere = obj.num_ordre_matiere
            etuve.taux_utilisation  = obj.taux_utilisation
            etuve.progressbar       = obj.taux_utilisation
            etuve.test_taux         = obj.test_taux
            etuve.message           = obj.message
            etuve.rsp_etuve_id      = obj.rsp_etuve_id.id
            of=[]
            moule=[]
            for row in obj.of_ids:
                of.append(row.of_id.name)
                moule.append(row.moule)
            etuve.of=', '.join(of)
            etuve.moule=', '.join(moule)
            commentaire = obj.commentaire_id.name
            if obj.commentaire_optionel:
                commentaire=commentaire+u', '+obj.commentaire_optionel
            etuve.commentaire = commentaire
            #***********************************************************************

            obj.active=True
            obj.state='valide'


    @api.model_create_multi
    def create(self, vals_list):
        vals=vals_list[0]

        vals['name'] = self.env['ir.sequence'].next_by_code('is.etuve.saisie')
        obj = super().create(vals_list)

        #** Vérfication des matières *******************************************
        for row in obj.of_ids:
            if not row.matiere:
                raise ValidationError("Les matières des OF ne correspondent pas à la matière de l'étuve !")
        #***********************************************************************

        return obj



    def copy(self, default=None):
        raise ValidationError(u"Duplication interdite !")


class is_etuve_of(models.Model):
    _name='is.etuve.of'
    _description="OF Etuve"
    _order='etuve_id,id'

    @api.depends('of_id')
    def _compute(self):
        cr = self.env.cr
        for obj in self:
            if not obj.of_id or not obj.etuve_id.matiere_id:
                return
            of=obj.of_id
            obj.code_pg   = of.product_id.is_code
            obj.qt_prevue = of.product_qty
            obj.moule     = of.product_id.is_mold_id.name
 
            #** Recherche de la presse de l'OF *************************************
            presse=False
            for line in of.workorder_ids:
                if line.workcenter_id.resource_type=='material' and line.workcenter_id.code<'9000':
                    presse=line.workcenter_id.code
                    obj.presse=presse
            #***********************************************************************

            #** Recherche du temps de cycle de la gamme ****************************
            tps_cycle_matiere=False
            nb_empreintes = of.bom_id.routing_id.is_nb_empreintes
            theia         = of.bom_id.routing_id.is_coef_theia
            for line in of.bom_id.routing_id.workcenter_lines:
                if line.workcenter_id.resource_type=='material':
                    nb_secondes=line.is_nb_secondes
                    tps_cycle_matiere=nb_secondes*nb_empreintes*theia
                    obj.tps_cycle_matiere=tps_cycle_matiere
            if nb_empreintes==0:
                nb_empreintes=1
            #***********************************************************************

            #** Recherche de la matière utilisée dans l'OF *************************
            matiere = obj.etuve_id.matiere_id.is_code
            suffix  = matiere[-4:]
            broye   = '59'+suffix
            SQL="""
                select pt.is_code, sum(bom.product_qty*mp.product_qty) 
                from mrp_production mp join is_mrp_production_bom bom on mp.id=bom.production_id 
                                       join product_product pp on bom.product_id=pp.id 
                                       join product_template pt on pp.product_tmpl_id=pt.id 
                where bom.production_id="""+str(obj.of_id.id)+""" and (pt.is_code='"""+str(matiere)+"""' or pt.is_code='"""+str(broye)+"""')
                group by pt.is_code 
            """
            #    order by max(bom.id) """
            matiere=poids_moulee=False
            cr.execute(SQL)
            result = cr.fetchall()
            besoin_total_of=qty=0.0
            for row in result:
                matiere = row[0]
                qty     = row[1] or 0
                #Si le code est du broyé, il faut multiplier la quantité par deux pour doubler le temps d'étuvage
                if matiere[0:2]=='59':
                    qty=qty*2
                besoin_total_of=besoin_total_of+qty
            obj.matiere         = matiere
            obj.besoin_total_of = besoin_total_of
            #***********************************************************************

            #** Calcul poids de la moulée et du débit ******************************
            poids_moulee=debit=0
            if of.product_qty!=0.0:
                poids_moulee=nb_empreintes*1000*besoin_total_of/of.product_qty
            obj.poids_moulee=poids_moulee
            if tps_cycle_matiere:
                debit=poids_moulee*3.6/tps_cycle_matiere
            obj.debit=debit
            #***********************************************************************


    etuve_id          = fields.Many2one('is.etuve.saisie', 'Étuve', required=True, ondelete='cascade')
    of_id             = fields.Many2one('mrp.production', 'Ordre de fabrication', required=True, domain=[('state','in',['draft'])])
    matiere           = fields.Char("Matière"              , readonly=True, compute='_compute', store=True, required=False)
    code_pg           = fields.Char("Code PG"              , readonly=True, compute='_compute', store=True)
    qt_prevue         = fields.Integer("Qt prévue"         , readonly=True, compute='_compute', store=True)
    moule             = fields.Char("Moule"                , readonly=True, compute='_compute', store=True)
    presse            = fields.Char("Presse"               , readonly=True, compute='_compute', store=True)
    tps_arret_matiere = fields.Float("Tps arrêt matière"   , readonly=True, compute='_compute', store=True)
    tps_cycle_matiere = fields.Float("Tps cycle matière"   , readonly=True, compute='_compute', store=True)
    besoin_total_of   = fields.Float("Besoin total of (Kg)", readonly=True, compute='_compute', store=True)
    poids_moulee      = fields.Float("Poids moulée (g)"    , readonly=True, compute='_compute', store=True)
    debit             = fields.Float("Débit (Kg/H)"        , readonly=True, compute='_compute', store=True)




