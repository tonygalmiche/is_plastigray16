# -*- coding: utf-8 -*-
from odoo import models,fields,api
import datetime
import pytz


class is_pdc(models.Model):
    _name='is.pdc'
    _description="is_pdc"
    _order='name desc'

    name                  = fields.Date("Date du calcul", default=fields.Datetime.now)
    date_debut            = fields.Date("Date de début de période", required=True)
    date_fin              = fields.Date("Date de fin de période"  , required=True)
    nb_heures_total       = fields.Float("Nombres d'heures issues du calcul de charge dans la période", readonly=True)
    tps_brut              = fields.Float("Temps brut au rendement de 80%", readonly=True)
    nb_jours_ouvrables    = fields.Float("Nombre de jours ouvrables")
    nb_inscrits           = fields.Float("Nombre de personnes inscrites à l'effectif")
    nb_absents            = fields.Float("Absents sur la totalité de la période")
    effectif_operationnel = fields.Float("Effectif opérationnel", readonly=True, store=True, compute='_effectif_operationnel')
    decision_prise        = fields.Char("Décision prise")
    nb_presses            = fields.Integer("Nombre de presses")
    temps_ouverture       = fields.Integer("Temps d'ouverture")
    nb_heures_periode     = fields.Integer("Nombre d'heures total dans la période")

    total_presse_heure    = fields.Float('Total heures presses'          , readonly=True, store=True, compute='_compute')
    presse_pourcent       = fields.Integer('% Presse'                    , readonly=True, store=True, compute='_compute')
    presse_pourcent85     = fields.Integer('% presse au rendement de 85%', readonly=True, store=True, compute='_compute')


    mold_ids              = fields.One2many('is.pdc.mold'      , 'pdc_id', u'Moules')
    workcenter_ids        = fields.One2many('is.pdc.workcenter', 'pdc_id', u'Postes de charge')
    mod_ids               = fields.One2many('is.pdc.mod'       , 'pdc_id', u"Nombres d'heures par semaine")
    mold_nb               = fields.Integer('Nb moule', store=True, compute='_mold_nb')
    state                 = fields.Selection([
            ('creation', u'Création'),
            ('analyse', u'Analyse')
        ], u"État", readonly=True, index=True, default="creation")


    @api.depends('nb_heures_periode','nb_presses','temps_ouverture','workcenter_ids')
    def _compute(self):
        for obj in self:
            total_presse_heure=0
            for row in obj.workcenter_ids:
                total_presse_heure=total_presse_heure+row.presse_heure
            presse_pourcent=0
            presse_pourcent85=0
            if (obj.nb_presses*obj.temps_ouverture)!=0:
                presse_pourcent   = 100*total_presse_heure/(obj.nb_presses*obj.temps_ouverture)
                presse_pourcent85 = 100*total_presse_heure/(obj.nb_presses*obj.temps_ouverture)/0.85

            obj.total_presse_heure = total_presse_heure
            obj.presse_pourcent    = presse_pourcent
            obj.presse_pourcent85  = presse_pourcent85


    @api.depends('nb_inscrits','nb_absents')
    def _effectif_operationnel(self):
        for obj in self:
            obj.effectif_operationnel=obj.nb_inscrits-obj.nb_absents


    @api.depends('mold_ids')
    def _mold_nb(self):
        for obj in self:
            obj.mold_nb=len(obj.mold_ids)


    def action_importer_cbn(self):
        cr      = self._cr
        for obj in self:
            obj.mold_ids.unlink()
            #for row in obj.mold_ids:
            #    row.unlink()

            #** Importation des FS *********************************************
            cr.execute("""
                select  mrw.workcenter_id                        as workcenter_id,
                        pt.is_mold_dossierf                      as mold_dossierf,
                        pt.is_couleur                            as matiere,
                        sum(mp.quantity)                         as quantite,
                        sum(mp.quantity*mrw.is_nb_secondes)      as temps_total
                from mrp_prevision mp inner join product_product  pp on mp.product_id=pp.id
                                      inner join product_template pt on pp.product_tmpl_id=pt.id
                                      inner join mrp_bom          mb on pt.id=mb.product_tmpl_id and mb.sequence=0
                                      inner join mrp_routing_workcenter mrw on mb.routing_id=mrw.routing_id
                where   mp.type='fs' 
                        and mp.start_date>='"""+str(obj.date_debut)+"""'
                        and mp.start_date<='"""+str(obj.date_fin)+"""'
                group by mrw.workcenter_id, pt.is_mold_dossierf, pt.is_couleur
                order by mrw.workcenter_id;
            """)
            result = cr.fetchall()
            res={}
            for row in result:
                key=str(row[0])+"/"+str(row[1])+"/"+str(row[2])
                temps_u=temps_h=0
                if row[3]!=0:
                    temps_u=row[4]/row[3]
                    temps_h=row[4]/3600
                vals={
                    'workcenter_id': row[0],
                    'mold_dossierf': row[1],
                    'matiere'      : row[2],
                    'quantite'     : row[3],
                    'temps_u'      : temps_u,
                    'temps_h'      : temps_h,
                }
                res[key]=vals
            #*******************************************************************


            #** Importation des FL *********************************************
            filtre=[
                ('state','=',"draft"),
                ('date_planned_start','>=',obj.date_debut),
                ('date_planned_start','<=',obj.date_fin),
            ]
            productions = self.env['mrp.production'].search(filtre)
            for production in productions:
                for line in production.bom_id.routing_id.workcenter_lines:
                    qt_reste = production.is_qt_reste_uom
                    if qt_reste>0:
                        key="%s/%s/%s"%(line.workcenter_id.id,production.product_id.is_mold_dossierf,production.product_id.is_couleur)
                        temps_u=line.is_nb_secondes
                        temps_h=qt_reste*line.is_nb_secondes/3600
                        vals={
                            'workcenter_id': line.workcenter_id.id,
                            'mold_dossierf': production.product_id.is_mold_dossierf,
                            'matiere'      : production.product_id.is_couleur,
                            'quantite'     : qt_reste,
                            'temps_u'      : temps_u,
                            'temps_h'      : temps_h,
                        }
                        if not key in res:
                            res[key]=vals
                        else:
                            res[key]['quantite'] = res[key]['quantite']+qt_reste
                            res[key]['temps_h']  = res[key]['temps_h']+temps_h
            #*******************************************************************


            # #** Importation des FL *********************************************
            # cr.execute("""
            #     select  mrw.workcenter_id                        as workcenter_id,
            #             pt.is_mold_dossierf                      as mold_dossierf,
            #             pt.is_couleur                            as matiere,
            #             sum(sm.product_uom_qty)                         as quantite,
            #             sum(sm.product_uom_qty*mrw.is_nb_secondes) as temps_total
            #     from stock_move sm    inner join product_product  pp on sm.product_id=pp.id
            #                           inner join product_template pt on pp.product_tmpl_id=pt.id
            #                           inner join mrp_bom          mb on pt.id=mb.product_tmpl_id and mb.sequence=0
            #                           inner join mrp_routing_workcenter mrw on mb.routing_id=mrw.routing_id
            #     where sm.state in('confirmed','assigned') 
            #             and sm.date>='"""+str(obj.date_debut)+"""'
            #             and sm.date<='"""+str(obj.date_fin)+"""'
            #             and sm.production_id is not null
            #     group by mrw.workcenter_id, pt.is_mold_dossierf, pt.is_couleur
            #     order by mrw.workcenter_id;
            # """)
            # result = cr.fetchall()
            # for row in result:
            #     print(row[1])
            #     key=str(row[0])+"/"+str(row[1])+"/"+str(row[2])
            #     temps_u=temps_h=0
            #     if row[3]!=0:
            #         temps_u=row[4]/row[3]
            #         temps_h=row[4]/3600
            #     vals={
            #         'workcenter_id': row[0],
            #         'mold_dossierf': row[1],
            #         'matiere'      : row[2],
            #         'quantite'     : row[3],
            #         'temps_u'      : temps_u,
            #         'temps_h'      : temps_h,
            #     }
            #     if not key in res:
            #         res[key]=vals
            #     else:
            #         res[key]['quantite'] = res[key]['quantite']+row[3]
            #         res[key]['temps_h']  = res[key]['temps_h']+row[4]
            # #*******************************************************************

            pdc_mold_obj = self.env['is.pdc.mold']
            for key in res:
                vals={
                    'pdc_id'       : obj.id,
                    'workcenter_id': res[key]['workcenter_id'],
                    'mold_dossierf': res[key]['mold_dossierf'],
                    'matiere'      : res[key]['matiere'],
                    'quantite'     : res[key]['quantite'],
                    'temps_u'      : res[key]['temps_u'],
                    'capacite'     : obj.temps_ouverture,
                }
                pdc_mold_obj.create(vals)
            obj.state="analyse"
            self.action_recalculer()


    def action_detail_par_moule(self):
        for obj in self:

            print(obj)

            return {
                'name': obj.name,
                'view_mode': 'tree,form',
                'res_model': 'is.pdc.mold',
                'domain': [
                    ('pdc_id' ,'=',obj.id),
                ],
                'type': 'ir.actions.act_window',
                'limit': 1000,
            }


    def action_recalculer(self):
        cr      = self._cr
        for obj in self:
            obj.mod_ids.unlink()
            obj.workcenter_ids.unlink()
            cr.execute("""select sum(temps_h) from is_pdc_mold where resource_type='user' and pdc_id="""+str(obj.id))
            nb_heures_total = cr.fetchone()[0]
            if not nb_heures_total:
                return
            
            obj.nb_heures_total=nb_heures_total
            obj.tps_brut=nb_heures_total/0.8
            mod_obj = self.env['is.pdc.mod']
            if obj.nb_jours_ouvrables>0 and obj.nb_inscrits>0 and nb_heures_total:
                def _heures_par_jour(heures_par_semaine):
                    return heures_par_semaine/5.0

                vals={
                    'pdc_id': obj.id,
                    'intitule': "Nombre d'heures par jour travaillée",
                    'semaine_35': str(_heures_par_jour(35))+"H",
                    'semaine_37': str(_heures_par_jour(37.5))+"H",
                    'semaine_40': str(_heures_par_jour(40))+"H",
                    'semaine_48': str(_heures_par_jour(48))+"H",
                }
                mod_obj.create(vals)

                def _effectif_theorique(obj, heures_par_semaine):
                    return obj.tps_brut/obj.nb_jours_ouvrables/(heures_par_semaine/5)

                vals={
                    'pdc_id': obj.id,
                    'intitule': "Effectif théorique nécessaire sur la période",
                    'semaine_35': round(_effectif_theorique(obj, 35.0),1),
                    'semaine_37': round(_effectif_theorique(obj, 37.5),1),
                    'semaine_40': round(_effectif_theorique(obj, 40.0),1),
                    'semaine_48': round(_effectif_theorique(obj, 48.0),1),
                }
                mod_obj.create(vals)

                def _taux_charge(obj, heures_par_semaine):
                    taux_charge=100*_effectif_theorique(obj, heures_par_semaine)/obj.effectif_operationnel
                    return taux_charge

                vals={
                    'pdc_id': obj.id,
                    'intitule': "Taux de charge par opérateur sur la période",
                    'semaine_35': str(int(_taux_charge(obj, 35.0)))+"%",
                    'semaine_37': str(int(_taux_charge(obj, 37.5)))+"%",
                    'semaine_40': str(int(_taux_charge(obj, 40.0)))+"%",
                    'semaine_48': str(int(_taux_charge(obj, 48.0)))+"%",
                }
                mod_obj.create(vals)

                def _nb_interim(obj, heures_par_semaine):
                    nb_interim=_effectif_theorique(obj, heures_par_semaine)-obj.effectif_operationnel
                    if nb_interim<0:
                        nb_interim=0
                    return round(nb_interim,1)

                vals={
                    'pdc_id': obj.id,
                    'intitule': "Nombre d'interim necessaire (charge > au besoin)",
                    'semaine_35': _nb_interim(obj, 35.0),
                    'semaine_37': _nb_interim(obj, 37.5),
                    'semaine_40': _nb_interim(obj, 40.0),
                    'semaine_48': _nb_interim(obj, 48.0),
                }
                mod_obj.create(vals)

                def _nb_jours_chomage(obj, heures_par_semaine):
                    nb_interim=_effectif_theorique(obj, heures_par_semaine)-obj.effectif_operationnel
                    if nb_interim<0:
                        heures_par_jour=_heures_par_jour(heures_par_semaine)
                        nb_jours_chomage=(((obj.nb_jours_ouvrables*obj.effectif_operationnel*heures_par_jour)-obj.tps_brut)/obj.effectif_operationnel)/heures_par_jour
                        return round(nb_jours_chomage,1)
                    return ""

                vals={
                    'pdc_id': obj.id,
                    'intitule': "Nombre de jours de chômage (charge < au besoin)",
                    'semaine_35': _nb_jours_chomage(obj, 35.0),
                    'semaine_37': _nb_jours_chomage(obj, 37.5),
                    'semaine_40': _nb_jours_chomage(obj, 40.0),
                    'semaine_48': _nb_jours_chomage(obj, 48.0),
                }
                mod_obj.create(vals)

            for row in obj.workcenter_ids:
                row.unlink()
            cr.execute("""
                select rr.resource_type, ipm.workcenter_id, sum(temps_h) 
                from is_pdc_mold ipm inner join mrp_workcenter mw on ipm.workcenter_id=mw.id 
                                     inner join resource_resource rr on mw.resource_id=rr.id   
                where pdc_id="""+str(obj.id)+"""
                      and rr.resource_type='material' 
                group by rr.resource_type, ipm.workcenter_id
            """)
            result=cr.fetchall()
            obj.nb_presses=len(result)
            obj.nb_heures_periode=obj.nb_presses*obj.temps_ouverture
            workcenter_obj = self.env['is.pdc.workcenter']
            total_presse_heure = 0
            for r in result:
                presse_pourcent=0
                presse_pourcent85=0

                if r[0]=='material':
                    if obj.temps_ouverture!=0:
                        presse_pourcent   = 100*r[2]/obj.temps_ouverture
                        presse_pourcent85 = 100*r[2]/0.85/obj.temps_ouverture
                    total_presse_heure=total_presse_heure+r[2]

                vals={
                    'pdc_id': obj.id,
                    'resource_type'    : r[0],
                    'workcenter_id'    : r[1],
                    'presse_heure'     : int(r[2]),
                    'presse_pourcent'  : int(presse_pourcent),
                    'presse_heure85'   : int(r[2]/0.85),
                    'presse_pourcent85': int(presse_pourcent85),
                }
                workcenter_obj.create(vals)
            


class is_pdc_mold(models.Model):
    _name='is.pdc.mold'
    _description="is_pdc_mold"
    _order='pdc_id desc, workcenter_id, mold_dossierf'


    def _get_default_pdc_id(self):
        context=self._context
        return context.get('pdc_id') or False


    pdc_id         = fields.Many2one('is.pdc', 'PDC', required=True, ondelete='cascade', default=lambda self: self._get_default_pdc_id())
    workcenter_id  = fields.Many2one('mrp.workcenter', 'Poste de charge')
    resource_type  = fields.Selection([('material', u'Machine'),('user', u'MO')], u"Type", readonly=True, index=True, store=True, compute='_resource_type')
    mold_id        = fields.Many2one('is.mold', 'Moule')
    mold_dossierf  = fields.Char('Moule/DossierF')
    matiere        = fields.Char('Matière')
    quantite       = fields.Integer('Quantité')
    temps_u        = fields.Float('Temps unitaire (s)', digits=(14, 4))
    temps_h        = fields.Float('Temps (H)'       , store=True,  compute='_compute', readonly=1)
    capacite       = fields.Float('Capacité'        , store=True,  compute='_compute', readonly=1)
    temps_pourcent = fields.Float('Temps (%)'       , store=True,  compute='_compute', readonly=1)

    cumul_pourcent = fields.Float('Temps Cumulé (%)', store=False, compute='_cumul', readonly=1)
    cumul_h        = fields.Float('Cumul (H)'       , store=False, compute='_cumul', readonly=1)
    cumul_j        = fields.Float('Cumul (J)'       , store=False, compute='_cumul', readonly=1)


    @api.depends('workcenter_id')
    def _resource_type(self):
        for obj in self:
            obj.resource_type = obj.workcenter_id.resource_type


    @api.depends('quantite','temps_u','pdc_id.temps_ouverture')
    def _cumul(self):
        debut=datetime.datetime.now()
        for obj in self:
            context = self._context
            cr      = self._cr
            cumul_pourcent=0
            cumul_h=0
            if obj.mold_dossierf and obj.workcenter_id.id and obj.pdc_id.id:
                sql="""
                    select sum(temps_pourcent), sum(temps_h)
                    from is_pdc_mold
                    where mold_dossierf<='"""+str(obj.mold_dossierf)+"""'
                          and workcenter_id="""+str(obj.workcenter_id.id)+"""
                          and pdc_id="""+str(obj.pdc_id.id)+"""
                """
                cr.execute(sql)
                for row in cr.fetchall():
                    if row[0]:
                        cumul_pourcent = row[0]
                        cumul_h        = row[1]

            obj.cumul_pourcent = cumul_pourcent
            obj.cumul_h        = cumul_h   
            obj.cumul_j        = cumul_h/24



    @api.depends('quantite','temps_u','pdc_id.temps_ouverture')
    def _compute(self):
        debut=datetime.datetime.now()
        for obj in self:
            temps_h=obj.temps_u*obj.quantite/3600
            capacite=obj.pdc_id.temps_ouverture
            temps_pourcent=0
            if capacite!=0:
                temps_pourcent=100*temps_h/capacite
            obj.temps_h=temps_h
            obj.capacite=capacite
            obj.temps_pourcent=temps_pourcent


class is_pdc_workcenter(models.Model):
    _name='is.pdc.workcenter'
    _description="is_pdc_workcenter"
    _order='resource_type, workcenter_id'

    pdc_id            = fields.Many2one('is.pdc', 'PDC', required=True, ondelete='cascade')
    resource_type     = fields.Selection([('material', u'Machine'),('user', u'MO')], u"Type de ressource", index=True)
    workcenter_id     = fields.Many2one('mrp.workcenter', 'Poste de charge')
    presse_heure      = fields.Float('H Presse')
    presse_pourcent   = fields.Float('% Presse')
    presse_heure85    = fields.Float('H presse au rendement de 85%')
    presse_pourcent85 = fields.Float('% presse au rendement de 85%')

    def action_acces_moules(self):
        for obj in self:
            return {
                'name': u'Moules de la section '+obj.workcenter_id.name,
                'view_mode': 'tree,form',
                'res_model': 'is.pdc.mold',
                'domain': [
                    ('pdc_id','=',obj.pdc_id.id),
                    ('workcenter_id','=',obj.workcenter_id.id)
                ],
                'context':{
                    'default_pdc_id'        : obj.pdc_id.id,
                    'default_workcenter_id' : obj.workcenter_id.id,
                },
                'type': 'ir.actions.act_window',
            }





class is_pdc_mod(models.Model):
    _name='is.pdc.mod'
    _description="is_pdc_mod"
    _order='id'

    pdc_id            = fields.Many2one('is.pdc', 'PDC', required=True, ondelete='cascade')
    intitule          = fields.Char('Intitulé')
    semaine_35        = fields.Char('35H')
    semaine_37        = fields.Char('37,5H')
    semaine_40        = fields.Char('40H')
    semaine_48        = fields.Char('48H')


