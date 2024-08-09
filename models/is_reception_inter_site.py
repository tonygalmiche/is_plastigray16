# -*- coding: utf-8 -*-
from odoo import models,fields,api,tools,SUPERUSER_ID
from odoo.exceptions import ValidationError
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, date, timedelta

class is_reception_inter_site(models.Model):
    _name = 'is.reception.inter.site'
    _description = 'Réception inter-site'
    _order = 'name desc'

    name                     = fields.Char('N° réception inter-site', readonly=True)
    site_livraison_id        = fields.Many2one('is.database', 'Site de livraison', required=True)
    fournisseur_reception_id = fields.Many2one('res.partner', 'Fournisseur de réception', required=True, domain=[('is_company','=',True),('supplier','=',True)])
    num_bl                   = fields.Char('N°BL fournisseur', copy=False)
    alerte                   = fields.Text('Alerte', readonly=1, copy=False)
    info                     = fields.Text('Info'  , readonly=1, copy=False)


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('is.reception.inter.site')
        return super().create(vals_list)


    def reception_inter_site_action(self):
        cr  = self._cr
        uid = self._uid
        alerte=[]
        info=[]
        for obj in self:
            company = self.env.user.company_id
            DBNAME   = obj.site_livraison_id.database
            USER     = company.is_postgres_user
            HOST     = company.is_postgres_host
            PASSWORD = company.is_postgres_pwd
            try:
                cnx_liv = psycopg2.connect("dbname='%s' user='%s' host='%s' password='%s'"%(DBNAME,USER,HOST,PASSWORD))
                cr_liv  = cnx_liv.cursor(cursor_factory=RealDictCursor)
            except Exception:
                raise ValidationError('Impossible de se connecter à la base %s du site %s'%(DBNAME,obj.site_livraison_id.name))

            SQL="""
                SELECT 
                    sp.name, 
                    pt.is_code,
                    sm.quantity_done,
                    sp.date_done,
                    sm.id move_id
                FROM stock_picking sp join stock_move       sm on sm.picking_id=sp.id
                                      join product_product  pp on sm.product_id=pp.id 
                                      join product_template pt on pp.product_tmpl_id=pt.id
                WHERE 
                    sp.name='%s' and 
                    sp.state='done' and sm.state='done' and sp.picking_type_id=2
            """%(obj.num_bl)
            cr_liv.execute(SQL)
            rows_liv = cr_liv.fetchall()
            nb_liv=nb_rcp=0
            UMs=[]
            for row_liv in rows_liv:
                nb_liv+=1
                is_code = row_liv['is_code']
                qt_liv  = row_liv['quantity_done']
                move_id = row_liv['move_id']

                date_debut = row_liv['date_done']
                date_fin   = date_debut + timedelta(days=7)

                

                #** Recherche de la réception *********************************
                SQL="""
                    SELECT 
                        sp.name, 
                        pt.is_code,
                        sm.product_uom_qty,
                        sm.id move_id
                    FROM stock_picking sp join stock_move       sm on sm.picking_id=sp.id
                                        join product_product  pp on sm.product_id=pp.id 
                                        join product_template pt on pp.product_tmpl_id=pt.id
                    WHERE 
                        pt.is_code='%s' and sp.partner_id=%s and
                        sp.state='done' and sm.state='done' and sp.picking_type_id=1 and
                        sp.is_date_reception>='%s' and sp.is_date_reception<='%s'
                    limit 1
                """%(is_code,obj.fournisseur_reception_id.id,date_debut,date_fin)


                cr.execute(SQL)
                rows = cr.dictfetchall()
                for row in rows:
                    nb_rcp+=1
                    qt_rcp  = row['product_uom_qty']

                    #** Recherche des UC/UM ***********************************
                    SQL="""
                        SELECT uc.num_eti,uc.qt_pieces,um.name
                        FROM is_galia_base_uc uc join is_galia_base_um um on uc.um_id=um.id
                        WHERE uc.stock_move_id=%s
                    """%move_id
                    cr_liv.execute(SQL)
                    lines = cr_liv.fetchall()
                    qt_scan=0
                    for line in lines:
                        num_eti = line['num_eti']
                        qt_scan+=line['qt_pieces']
                        if line['name'] not in UMs:
                            UMs.append(line['name'])
                    #**********************************************************

                    msg = "%s : %s Liv : %s Rcp : %s Scan"%(is_code.ljust(9), str(qt_liv).rjust(10),str(qt_rcp).rjust(10),str(qt_scan).rjust(10))
                    if qt_rcp==qt_liv and qt_liv==qt_scan:
                        info.append(msg)
                    else:
                        alerte.append(msg)



            #** Création des UMs **********************************************
            for UM in UMs:
                print(UM)
                SQL="""
                    INSERT INTO is_galia_base_um(name,create_uid,write_uid,create_date,write_date,mixte,active)
                    VALUES (%s, %s, %s, now() AT TIME ZONE 'UTC', now() AT TIME ZONE 'UTC', 'non', 't')
                """
                cr.execute(SQL,[UM,uid,uid])
            #******************************************************************


            info.append("%s lignes livrées"%nb_liv)
            info.append("%s réceptions trouvées"%nb_rcp)
            
            #** Alerte si nb_liv<>nb_rcp **************************************
            if nb_liv!=nb_rcp:
                alerte.append('Nombre de lignes de réception (%s) différent du nombre lignes livrées (%s)'%(nb_rcp,nb_liv))
            #******************************************************************

            if alerte==[]:
                alerte=False
            else:
                alerte='\n'.join(alerte)
            obj.alerte = alerte
            if info==[]:
                info=False
            else:
                info='\n'.join(info)
            obj.info = info


