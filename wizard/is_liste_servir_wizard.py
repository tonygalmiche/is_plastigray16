# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import date, timedelta
import time

class is_liste_servir_wizard(models.TransientModel):
    _name = "is.liste.servir.wizard"
    _description = "Listes a servir des clients"  
    
    date_debut = fields.Date(u"Date de début d'expédition", required=False)
    date_fin   = fields.Date(u"Date de fin d'expédition", required=True, default=lambda self: self._date_fin())
    livrable   = fields.Boolean("Livrable (avec stock)", default=False)


    def _date_fin(self):
        now = date.today()                 # Date du jour
        date_fin = now + timedelta(days=1) # J+1
        return date_fin


    def generer_liste_servir_client(self):
        cr = self._cr
        for obj in self:
            print(obj)
            SQL="delete from is_liste_servir_client"
            cr.execute(SQL)
            SQL="""
                select  so.partner_id, 
                        rp.zip, 
                        rp.city, 
                        rp.is_delai_transport, 
                        sum(sol.product_uom_qty)
                from sale_order so inner join sale_order_line   sol on so.id=sol.order_id
                                   inner join res_partner       rp  on so.partner_id=rp.id
                                   inner join product_product   pp  on sol.product_id=pp.id
                                   inner join  product_template pt  on pp.product_tmpl_id=pt.id
                where sol.is_date_expedition<='"""+str(obj.date_fin)+"""' 
                      and so.state='draft' 
                      and sol.is_type_commande='ferme' 
                      and so.is_type_commande!='ls'
            """
            if obj.livrable:
                SQL=SQL+"""
                      and (
                        select sum(sq.quantity) 
                        from stock_quant sq inner join stock_location sl on sq.location_id=sl.id
                        where sq.product_id=pp.id and sl.usage='internal' and sl.active='t'
                      )>=sol.product_uom_qty
                """
            if obj.date_debut:
                SQL=SQL+" and sol.is_date_expedition>='"+str(obj.date_debut)+"' "
            SQL=SQL+"group by so.partner_id, rp.zip, rp.city, rp.is_delai_transport"
            cr.execute(SQL)
            result = cr.fetchall()
            for row in result:
                SQL="""
                    select id 
                    from is_liste_servir 
                    where state!='traite' and partner_id="""+str(row[0])+" limit 1"
                cr.execute(SQL)
                result2 = cr.fetchall()
                liste_servir_id=False
                for row2 in result2:
                    liste_servir_id=row2[0]



                vals={
                    'name'            : row[0],
                    'liste_servir_id' : liste_servir_id,
                    'zip'             : row[1],
                    'city'            : row[2],
                    'delai_transport' : row[3],
                    'date_debut'      : obj.date_debut,
                    'date_fin'        : obj.date_fin,
                    'livrable'        : obj.livrable,
                }
                new_id=self.env['is.liste.servir.client'].create(vals)
            return {
                'name': "Clients à livrer",
                'type': 'ir.actions.act_window',
                'view_mode': 'tree',
                'res_model': 'is.liste.servir.client',
                'target': 'current',
            }
        view_id = self.env.ref('is_plastigray16.is_product_template_only_form_view').id
        for obj in self:
            return {
                'name': "Article",
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'product.template',
                'type': 'ir.actions.act_window',
                'res_id': obj.product_id.product_tmpl_id.id,
                'domain': '[]',
            }







