# -*- coding: utf-8 -*-
from odoo import models,fields,api
from odoo.exceptions import ValidationError
import time
import datetime
import pytz
#import cProfile

import logging
_logger = logging.getLogger(__name__)


#TODO : Permet d'indiquer l'id du produit à analyser (product.product)
product_id_test=False
#product_id_test=10604


def duree(debut):
    dt = datetime.datetime.now() - debut
    ms = (dt.days * 24 * 60 * 60 + dt.seconds) * 1000 + dt.microseconds / 1000.0
    ms=int(ms)
    return ms


def _now(debut):
    return datetime.datetime.now(pytz.timezone('Europe/Paris')).strftime('%H:%M:%S') + ' : '+ str(int(duree(debut)/1000))+"s "


class mrp_generate_previsions(models.TransientModel):
    _name = "mrp.previsions.generate"
    _description = "Generate previsions"

    max_date     = fields.Date('Date limite'               , required=True, default=lambda self: self._max_date())
    company_id   = fields.Many2one('res.company', 'Société', required=True, default=lambda self: self.env.user.company_id)
    regroupement = fields.Selection([('jour','Jour'),('semaine','Semaine')], string='Regroupement', default="jour")


    @api.constrains('max_date')
    def _check_date_max(self):
        now = datetime.date.today() # Date du jour
        for obj in self:
            if obj.max_date < now:
                raise ValidationError(
                    "La date limite (%s) doit-être supérieure à la date de jour (%s)"%(obj.max_date,now)
                )


    def _max_date(self):
        now = datetime.date.today()                # Date du jour
        date = now + datetime.timedelta(days=30)   # Date + 30 jours
        return date.strftime('%Y-%m-%d')           # Formatage


    #** Liste des dates à traiter **********************************************
    def _dates(self, date_max, nb_jours):
        now     = datetime.datetime.now()               # Date de jour
        if nb_jours==7:
            weekday = now.weekday()                         # Jour dans la semaine
            date = now - datetime.timedelta(days=weekday) # Date du lundi précédent
        else:
            date = now
        dates = []
        while(date.date()<=date_max):
            dates.append(date.strftime('%Y-%m-%d'))
            date = date + datetime.timedelta(days=nb_jours)
        return dates


    #** Ajouter 7 jours à la date indiquée *************************************
    def _date_fin(self, date, nb_jours):
        date_fin = datetime.datetime.strptime(date, '%Y-%m-%d')
        date_fin = date_fin + datetime.timedelta(days=nb_jours)
        date_fin = date_fin.strftime('%Y-%m-%d')
        return date_fin


    #** Enlever 7 jours à la date indiquée *************************************
    def _date_debut(self, date, nb_jours):
        date_debut = datetime.datetime.strptime(date, '%Y-%m-%d')
        date_debut = date_debut - datetime.timedelta(days=nb_jours)
        date_debut = date_debut.strftime('%Y-%m-%d')
        return date_debut


    def _articles(self):
        articles=[]
        filtre=[]
        #filtre=[('is_code','like','262282')]
        #filtre=[('is_code','in',['261928A','262996','602468','502905','502521'])]

        for product in self.env['product.product'].search(filtre):
            articles.append(product)
        articles.sort()
        return articles


    def _stocks(self,articles):
        cr=self._cr
        res={}
        # TODO : Modif stock du 21/01/2018 => Avant, c'était : where sl.name in ('01','05','MA') 
        sql="""
            select sq.product_id, sum(sq.quantity) 
            from stock_quant sq inner join stock_location sl on sq.location_id=sl.id
            where sl.usage='internal' and sl.active='t' and sl.control_quality='f'
            group by sq.product_id"""
        cr.execute(sql)
        for row in cr.fetchall():
            res[row[0]]=row[1]
        return res


    def _cde_cli(self, date_debut, date_fin):
        cr=self._cr
        now=datetime.datetime.now().strftime('%Y-%m-%d')
        if date_debut<=now:
            date_debut="2000-01-01"
        sql="""
            select sol.product_id, sum(sol.product_uom_qty)
            from sale_order so inner join sale_order_line sol on so.id=sol.order_id  
            where sol.state in ('draft','sent') 
                  and sol.is_date_expedition>='"""+str(date_debut)+"""'
                  and sol.is_date_expedition<'"""+str(date_fin)+"""'
            group by sol.product_id 
        """
        res={}
        cr.execute(sql)
        for row in cr.fetchall():
            res[row[0]]=row[1]
            #if row[0]==product_id_test:
            #    print("_cde_cli : ",row[0], row[1], date_debut, date_fin)
        return res


    def _cde_fou(self, date_debut, date_fin):
        cr=self._cr
        now=datetime.datetime.now().strftime('%Y-%m-%d')
        if date_debut<=now:
            date_debut="2000-01-01"
        sql="""
            select product_id, sum(product_qty)
            from stock_move 
            where state not in ('done','cancel','none') and picking_id is not null
                  and date>='"""+str(date_debut)+""" 02:00:00'
                  and date<'"""+str(date_fin)+""" 02:00:00'
            group by product_id
        """
        res={}
        cr.execute(sql)
        for row in cr.fetchall():
            res[row[0]]=row[1]
            #if row[0]==product_id_test:
            #    print "_cde_fou : ",row[0], row[1], date_debut, date_fin
        return res


    def _fl(self, date_debut, date_fin):
        cr=self._cr
        now=datetime.datetime.now().strftime('%Y-%m-%d')
        if date_debut<=now:
            date_debut="2000-01-01"
        date_debut = date_debut + ' 23:59:59'
        date_fin   = date_fin   + ' 23:59:59'
        sql="""
            select mp.product_id, sum(mp.is_qt_reste_uom)
            from mrp_production mp
            where 
                mp.state='draft' and
                mp.date_planned_start>='"""+date_debut+"""' and
                mp.date_planned_start<'"""+date_fin+"""'
            group by mp.product_id
        """
        res={}
        cr.execute(sql)
        for row in cr.fetchall():
            res[row[0]]=row[1]
        return res


    def _fm(self, date_debut, date_fin):
        cr=self._cr
        now=datetime.datetime.now().strftime('%Y-%m-%d')
        if date_debut<=now:
            date_debut="2000-01-01"

        date_debut = date_debut + ' 23:59:59'
        date_fin   = date_fin   + ' 23:59:59'
        sql="""
            select bom.product_id, sum(bom.product_qty*mp.is_qt_reste_uom)
            from is_mrp_production_bom bom inner join mrp_production mp on bom.production_id=mp.id 
            where 
                mp.date_planned_start>='"""+date_debut+"""' and 
                mp.date_planned_start<'"""+date_fin+"""' and
                mp.state not in ('done','cancel') and
                bom.is_cbn='t'
            group by bom.product_id
        """
        res={}
        cr.execute(sql)
        for row in cr.fetchall():
            res[row[0]]=row[1] or 0
        return res


    def _suggestions(self, date_debut, date_fin, type):
        cr=self._cr
        now=datetime.datetime.now().strftime('%Y-%m-%d')
        if date_debut<=now:
            date_debut="2000-01-01"
        previsions = self.env['mrp.prevision'].search([
            ('type','=',type),
            ('start_date','>=',date_debut),
            ('start_date','<',date_fin),
        ])
        res={}
        for prevision in previsions:
            product_id = prevision.product_id.id
            if product_id not in res:
                res[product_id]=0
            res[product_id]+=prevision.quantity
        return res


    def _creer_suggestion(self, product, quantity, date, nb_jours):
        type="fs"
        if product.route_ids:
            Buy=Manufacture=False
            for route in product.route_ids:
                if route.name=="Manufacture":
                    Manufacture=True
                if route.name=="Buy":
                    Buy=True
            if Manufacture:
                type="fs"
            if Buy:
                type="sa"

        if type=='fs':
            obj = self.env['mrp.prevision']
            end_date   = date
            start_date = self._date_debut(date, nb_jours)
            now=datetime.datetime.now().strftime('%Y-%m-%d')
            if start_date<=now:
                start_date="2000-01-01"
            rows = obj.search(['&','&','&',('type','=',type),('product_id','=',product.id),('start_date','>',start_date),('start_date','<=',end_date)])
            for row in rows:
                quantity=row.quantity+quantity
                obj.browse([row.id]).write({'quantity': quantity})
                if product.id==product_id_test:
                   print("creer_mrp_prevision : write : ", row.quantity, row.start_date, row.end_date)
                return quantity
        vals = {
            'type': type,
            'product_id': product.id,
            'quantity': quantity,
            'quantity_origine': quantity,
            'start_date': date,
            'end_date': date,
        }
        obj = self.env['mrp.prevision']
        id = obj.create(vals)
        if product.id==product_id_test:
           print("creer_mrp_prevision : create : ", vals["quantity"], vals["start_date"], vals["end_date"])
        return vals["quantity"]




    def generate_previsions(self):
        cr=self._cr
        debut=datetime.datetime.now()
        _logger.info(_now(debut) + "## DEBUT")

        regroupement = False
        states=["cbb"]
        for obj in self:
            nb_jours=1
            if obj.regroupement=='semaine':
                nb_jours=7

            prevision_obj = self.env['mrp.prevision']
            bom_line_obj  = self.env['mrp.bom.line']
            company_obj   = self.env['res.company']
            partner_obj   = self.env['res.partner']
            company       = obj.company_id
            dates         = self._dates(obj.max_date,nb_jours)

            #** supprimer les previsions existantes ****************************
            _logger.info(_now(debut) + '## Début delete from mrp_prevision')
            sql="""
                ALTER TABLE mrp_prevision DISABLE TRIGGER ALL; 
                DELETE FROM mrp_prevision;
                ALTER TABLE mrp_prevision ENABLE TRIGGER ALL; 
            """
            cr.execute(sql)
            _logger.info(_now(debut) + '## Fin delete from mrp_prevision')
            #*******************************************************************

            _logger.info(_now(debut) + '## Regroupement = ' + str(obj.regroupement))
            articles = self._articles()
            stocks   = self._stocks(articles)
            num_od=1
            compteur=1
            stock_theorique={}
            niveau=0
            state=states[niveau]
            while True:
                nb=0
                _logger.info(_now(debut) + "## Début Boucle state="+str(state)+" : "+str(compteur)+" : nb="+str(nb))
                for date in dates:
                    _logger.info(_now(debut) + '- ' + str(date))
                    date_debut  = date
                    date_fin    = self._date_fin(date,nb_jours)
                    cde_cli     = self._cde_cli(date_debut, date_fin)
                    cde_fou     = self._cde_fou(date_debut, date_fin)
                    fs          = self._suggestions(date_debut, date_fin, 'fs')
                    sa          = self._suggestions(date_debut, date_fin, 'sa')
                    ft          = self._suggestions(date_debut, date_fin, 'ft')
                    fl          = self._fl(date_debut, date_fin)
                    fm          = self._fm(date_debut, date_fin)
                    for product in articles:
                        qt_stock      = stocks.get(product.id, 0)
                        qt_cde_cli    = cde_cli.get(product.id, 0)
                        qt_cde_fou    = cde_fou.get(product.id, 0)
                        qt_fs         = fs.get(product.id, 0)
                        qt_sa         = sa.get(product.id, 0)
                        qt_ft         = ft.get(product.id, 0)
                        qt_fl         = fl.get(product.id, 0)
                        qt_fm         = fm.get(product.id, 0)
                        if date==dates[0]:
                            stock_theorique[product.id] = qt_stock - product.is_stock_secu
                        
                        if product.id==product_id_test:
                           print("stock_theorique avant calcul=",stock_theorique[product.id])
                        stock_theorique[product.id] = stock_theorique[product.id] - qt_cde_cli + qt_cde_fou + qt_fl - qt_fm + qt_fs + qt_sa - qt_ft

                        #** Uniquement pour le debuggage à l'écran *****************
                        if product.id==product_id_test:
                            print(str(product.id)+"\t"+ \
                                str(date)+"\t"+ \
                                str(date_debut)+"\t"+ \
                                str(date_fin)+"\t"+ \
                                "cde_cli:"     +str(qt_cde_cli)+"\t"+ \
                                "cde_fou:"     +str(qt_cde_fou)+"\t"+ \
                                "fl:"          +str(qt_fl)+"\t"+ \
                                "fm:"          +str(qt_fm)+"\t"+ \
                                "fs:"          +str(qt_fs)+"\t"+ \
                                "sa:"          +str(qt_sa)+"\t"+ \
                                "ft:"          +str(qt_ft)+"\t"+ \
                                "theorique:"   +str(stock_theorique[product.id])
                            )
                        #***********************************************************

                        #** Création des suggestions *******************************
                        if stock_theorique[product.id]<0:
                            qt=self._creer_suggestion(product, -stock_theorique[product.id], date, nb_jours)
                            stock_theorique[product.id]=stock_theorique[product.id]+qt
                            if product.id==product_id_test:
                               print("Création qt=",qt,stock_theorique[product.id])
                            num_od=num_od+1
                            nb=nb+1
                        if product.id==product_id_test:
                           print("stock_theorique=",stock_theorique[product.id])
                        #***********************************************************

                _logger.info(_now(debut)+"## Fin Boucle state="+str(state)+" : "+str(compteur)+" : nb="+str(nb))
                if nb==0:
                    niveau=niveau+1
                    if niveau>=len(states):
                        break
                    else:
                        compteur=0
                        state=states[niveau]
                compteur=compteur+1
                if compteur>12:
                    break
            _logger.info(_now(debut) + "## Fin du CBN")


            ##** Regroupement des FS et SA par semaine *************************
            _logger.info(_now(debut) + "## Debut du regroupement des SA et FS par semaine")
            dates = self._dates(obj.max_date, 7)
            for date in dates:
                _logger.info(_now(debut) + '- ' + str(date))
                date_debut  = date
                date_fin    = self._date_fin(date,nb_jours)
                now=datetime.datetime.now().strftime('%Y-%m-%d')
                if date_debut<=now:
                    date_debut="2000-01-01"
                sql="""
                    select product_id, type, count(*), sum(quantity)
                    from mrp_prevision 
                    where   start_date>='"""+date_debut+"""' 
                        and start_date<'"""+date_fin+"""'
                        and type in ('fs', 'sa')
                    group by product_id, type
                    having count(*)>1
                """
                cr.execute(sql)
                for row in cr.fetchall():
                    previsions = prevision_obj.search([
                        ('product_id','=',row[0]),
                        ('type','=',row[1]),
                        ('start_date','>=',date_debut),
                        ('start_date','<',date_fin),
                    ])
                    ct=0
                    for prevision in previsions:
                        if ct==0:
                            prevision.quantity=row[3]
                        else:
                            prevision.unlink()
                        ct=ct+1
            _logger.info(_now(debut) + "## Fin du regroupement des SA et FS par semaine")
            #*******************************************************************

        _logger.info(_now(debut) + "## FIN")


        #** Action pour retourner à la liste des prévisions ********************
        action =  {
            'name': "Previsions",
            'view_mode': 'tree,form',
            'res_model': 'mrp.prevision',
            'type': 'ir.actions.act_window',
            'domain': '[]',
        }
        return action

