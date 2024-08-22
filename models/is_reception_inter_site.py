# -*- coding: utf-8 -*-
from odoo import models,fields,api,tools,SUPERUSER_ID
from odoo.exceptions import ValidationError
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, date, timedelta
import time

class is_reception_inter_site(models.Model):
    _name = 'is.reception.inter.site'
    _inherit=['mail.thread']
    _description = 'Réception inter-site'
    _order = 'name desc'

    name                     = fields.Char('N° réception inter-site', readonly=True, tracking=True)
    site_livraison_id        = fields.Many2one('is.database', 'Site de livraison', required=True, tracking=True)
    fournisseur_reception_id = fields.Many2one('res.partner', 'Fournisseur de réception', required=True, tracking=True, domain=[('is_company','=',True),('supplier','=',True)])
    num_bl                   = fields.Char('N°BL fournisseur', tracking=True, copy=False)
    location_id              = fields.Many2one('stock.location', 'Emplacement final', help="Emplacement après contrôle réception", index=True, domain=[("usage","=","internal")], default=lambda self: self._get_location_id())
    alerte                   = fields.Text('Alerte', readonly=1, copy=False)
    info                     = fields.Text('Info'  , readonly=1, copy=False)
    picking_ids              = fields.One2many('stock.picking', 'is_reception_inter_site_id', "Réceptions", readonly=True)
    etat_reception           = fields.Selection([
            ('pret', 'Prêt'),
            ('fait', 'Fait'),
        ], "Etat réception", default='pret', required=True, tracking=True)
    state = fields.Selection([
            ('analyse'  , 'Analyse'),
            ('reception', 'Réception'),
            ('controle' , 'Contrôle physique'),
            ('termine'  , 'Terminé'),
        ], "Etat", default='analyse', tracking=True)


    def _get_location_id(self):
        filtre = [
            ('name' , '=', '01'),
            ('usage', '=', 'internal'),
        ]
        lines = self.env["stock.location"].search(filtre)
        location_id = lines and lines[0].id or False
        return location_id
       

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('is.reception.inter.site')
        return super().create(vals_list)


    def analyse_action(self):
        "Analyse et création des UM/UC"
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

            SQL="UPDATE stock_picking set is_reception_inter_site_id=Null WHERE is_reception_inter_site_id=%s"%obj.id
            cr.execute(SQL)
            cr.commit()

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
                ORDER BY sm.sequence,sm.id
            """%(obj.num_bl)
            cr_liv.execute(SQL)
            rows_liv = cr_liv.fetchall()
            nb_liv=nb_rcp=0
            #UMs=[]
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
                        sp.id picking_id,
                        sp.name, 
                        pt.is_code,
                        sm.product_uom_qty,
                        sm.id move_id,
                        sm.location_dest_id
                    FROM stock_picking sp join stock_move       sm on sm.picking_id=sp.id
                                        join product_product  pp on sm.product_id=pp.id 
                                        join product_template pt on pp.product_tmpl_id=pt.id
                """
                if obj.etat_reception=='fait':
                    SQL="""%s
                        WHERE 
                            pt.is_code='%s' and sp.partner_id=%s and
                            sp.state='done' and sm.state='done' and sp.picking_type_id=1 and
                            sp.is_date_reception>='%s' and sp.is_date_reception<='%s'  and
                            sp.is_num_bl='%s' and
                            sp.is_reception_inter_site_id is Null 
                            -- and sm.product_uom_qty=%s
                        limit 1
                    """%(SQL,is_code,obj.fournisseur_reception_id.id,date_debut,date_fin,obj.num_bl,qt_liv)
                else:
                    SQL="""%s
                        WHERE 
                            pt.is_code='%s' and sp.partner_id=%s and
                            sp.state not in ('done','cancel','draft') and 
                            sm.state not in ('cancel','done') and sp.picking_type_id=1 and 
                            sp.is_reception_inter_site_id is Null 
                            -- and sm.product_uom_qty=%s
                        ORDER BY sp.scheduled_date
                        limit 1
                    """%(SQL, is_code, obj.fournisseur_reception_id.id,qt_liv)
                cr.execute(SQL)
                rows = cr.dictfetchall()
                if len(rows)==0:
                    msg="Réception non trouvée pour %s (Qt=%s)"%(is_code, qt_liv)
                    alerte.append(msg)
                else:
                    for row in rows:
                        nb_rcp+=1
                        num_rcp     = row['name']
                        picking_id  = row['picking_id']
                        qt_rcp      = row['product_uom_qty']
                        move_rcp_id = row['move_id']
                        location_id = row['location_dest_id']

                        #** Recherche des UC/UM ***********************************
                        SQL="""
                            SELECT uc.num_eti,uc.qt_pieces,um.name, uc.num_carton, uc.qt_pieces, uc.product_id, uc.type_eti, uc.date_creation,uc.production,pt.is_code
                            FROM is_galia_base_uc uc join is_galia_base_um um on uc.um_id=um.id
                                                    join product_product  pp on uc.product_id=pp.id 
                                                    join product_template pt on pp.product_tmpl_id=pt.id 
                            WHERE uc.stock_move_id=%s
                        """%move_id
                        cr_liv.execute(SQL)
                        lines = cr_liv.fetchall()
                        qt_scan = 0
                        qt_uc   = 0
                        for line in lines:
                            name    = line['name']
                            num_eti = line['num_eti']
                            code_pg = line['is_code']
                            qt_scan+=line['qt_pieces']

                            #** Recherche si UM existe déjà *******************
                            um_id=False
                            SQL="SELECT id from is_galia_base_um where name='%s'"%name
                            cr.execute(SQL)
                            rows2 = cr.dictfetchall()
                            if len(rows2)>0:
                                for row2 in rows2:
                                    um_id=row2['id']
                            else:
                                #** Création UM *******************************
                                SQL="""
                                    INSERT INTO is_galia_base_um(name,create_uid,write_uid,location_id,create_date,write_date,mixte,active)
                                    VALUES (%s, %s, %s, %s, now() AT TIME ZONE 'UTC', now() AT TIME ZONE 'UTC', 'non', 't')
                                    RETURNING id
                                """
                                cr.execute(SQL,[name,uid,uid,location_id])
                                rows2 = cr.dictfetchall()
                                for row2 in rows2:
                                    um_id=row2['id']
                                    #info.append('Création UM %s'%name)
                            if not um_id:
                                alerte.append("Impossible de trouver ou créer l'UM %s"%name)
                            else:
                                #** Recherche si UC existe déjà ***************
                                uc_id=False
                                SQL="SELECT id, qt_pieces from is_galia_base_uc where num_eti='%s' and um_id=%s"%(num_eti,um_id)
                                cr.execute(SQL)
                                rows2 = cr.dictfetchall()
                                if len(rows2)>0:
                                    for row2 in rows2:
                                        uc_id=row2['id']
                                        qt_uc+=row2['qt_pieces']
                                else:

                                    #** Cherche code PG dans base réception ***
                                    product_id = False
                                    SQL="""
                                        SELECT pp.id 
                                        FROM product_product pp join product_template pt on pp.product_tmpl_id=pt.id 
                                        WHERE pt.is_code=%s 
                                        limit 1
                                    """
                                    cr.execute(SQL,[code_pg])
                                    rows3 = cr.dictfetchall()
                                    for row3 in rows3:
                                        product_id=row3['id']
                                    if not product_id:
                                        alerte.append("Code PG '%s' non trouvé dans %s"%(code_pg,DBNAME))
                                    else:
                                        #** Création UC ***************************
                                        SQL="""
                                            INSERT INTO is_galia_base_uc(um_id,num_eti,num_carton,qt_pieces,product_id,type_eti,date_creation,create_uid,write_uid,create_date,write_date)
                                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now() AT TIME ZONE 'UTC', now() AT TIME ZONE 'UTC')
                                            RETURNING id
                                        """
                                        cr.execute(SQL,[
                                            um_id,
                                            num_eti,
                                            line['num_carton'],
                                            line['qt_pieces'],
                                            product_id,
                                            line['type_eti'],
                                            line['date_creation'],
                                            uid,
                                            uid,
                                        ])
                                        rows2 = cr.dictfetchall()
                                        for row2 in rows2:
                                            uc_id=row2['id']
                                            #info.append('Création UC %s'%num_eti)
                                            qt_uc+=line['qt_pieces']

                                #** Lien entre UC et stock.move réception *****
                                if uc_id:
                                    SQL="""
                                        UPDATE is_galia_base_uc 
                                        SET stock_move_rcp_id=%s, reception_inter_site_id=%s, production='%s'
                                        WHERE id=%s
                                    """%(move_rcp_id,obj.id,line['production'],uc_id)
                                    cr.execute(SQL)


                        #** Lien entre picking et is_reception_inter_site *********
                        picking = self.env['stock.picking'].browse(picking_id)
                        if picking.id:
                            picking.is_reception_inter_site_id = obj.id
                            picking.is_qt_livree_inter_site    = qt_scan # Quantitée scannée en livraison qu'il faudra réceptionner
                        #**********************************************************

                        msg = "%s : %s Liv : %s Rcp (%s) : %s Scan : %s Qt pièces UC"%(is_code.ljust(9), str(qt_liv).rjust(8),str(qt_rcp).rjust(8),num_rcp,str(qt_scan).rjust(8),str(qt_uc).rjust(8))
                        msg = msg.replace(' ', chr(160)) # Remplacer les espaces par des espaces insecables, sinon ils sont supprimés avec wkhtml2pdf
                        cr.commit()
                        if qt_rcp==qt_liv and qt_liv==qt_scan and qt_liv==qt_uc:
                            info.append(msg)
                        else:
                            alerte.append(msg)

            info.append("%s lignes livrées"%nb_liv)
            info.append("%s réceptions trouvées"%nb_rcp)
            
            #** Alerte si nb_liv<>nb_rcp **************************************
            if nb_liv!=nb_rcp:
                alerte.append('Nombre de lignes livrées (%s) différent du nombre lignes en réception (%s)'%(nb_liv,nb_rcp))
            if nb_liv==0:
                alerte.append('Nombre de lignes livrées à 0')
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

            if obj.etat_reception=='pret':
                obj.state='reception'
            else:
                obj.state='controle'


    def voir_receptions_action(self):
        for obj in self:
            view_id=self.env.ref('is_plastigray16.is_ligne_reception_tree_view')
            ids=[]
            lines = self.env['stock.picking'].search([('is_reception_inter_site_id','=',obj.id)])
            for line in lines:
                picking_id = line.id
                if picking_id not in ids:
                    ids.append(picking_id)
            res= {
                'name'     : obj.name,
                'view_mode': 'tree,form',
                'views'    : [[view_id.id, "list"], [False, "form"]],
                'res_model': 'is.ligne.reception',
                'type'     : 'ir.actions.act_window',
                'domain'   : [('picking_id','in',ids)],
            }
            return res

    def voir_uc_action(self):
        for obj in self:
            res= {
                'name': obj.name,
                'view_mode': 'tree,form',
                'res_model': 'is.galia.base.uc',
                'type': 'ir.actions.act_window',
                'domain': [('reception_inter_site_id','=',obj.id)],
            }
            return res


    def voir_um_action(self):
        for obj in self:
            ids=[]
            lines = self.env['is.galia.base.uc'].search([('reception_inter_site_id','=',obj.id)])
            for line in lines:
                um_id = line.um_id.id
                if um_id not in ids:
                    ids.append(um_id)
            res= {
                'name': obj.name,
                'view_mode': 'tree,form',
                'res_model': 'is.galia.base.um',
                'type': 'ir.actions.act_window',
                'domain': [('id','in',ids)],
            }
            return res


    def valider_receptions_action(self):
        for obj in self:
            for picking in obj.picking_ids:
                if picking.state!='done':
                    vals={
                        'is_num_bl': obj.num_bl
                    }
                    transfert = self.env['stock.transfer_details'].with_context(active_id=picking.id).create(vals)
                    for line in transfert.line_ids:
                        line.quantity = picking.is_qt_livree_inter_site
                    transfert.valider_action()
            obj.state='controle'


    def get_um_reception_action(self):
        for obj in self:
            obj.get_um_reception(bl=obj.num_bl)


    def get_um_reception(self,bl=False):
        err=False
        domain=[('num_bl','=',bl)]
        receptions = self.env['is.reception.inter.site'].search(domain)
        data=[]
        reception_id = False
        emplacement  = '01'
        for reception in receptions:
            reception_id = reception.id
            emplacement  = reception.location_id.name
            lines = self.env['is.galia.base.uc'].search([('reception_inter_site_id','=',reception.id)])
            ids=[]
            for line in lines:
                um_id = line.um_id.id
                if um_id not in ids:
                    ids.append(um_id)
            lines = self.env['is.galia.base.um'].search([('id','in',ids)])
            for line in lines:
                vals={
                    'id'           : line.id,
                    'name'         : line.name,
                    'location_id'  : line.location_id.id,
                    'location'     : line.location_id.name,
                    'qt_pieces'    : line.qt_pieces,
                    'date_ctrl_rcp': line.date_ctrl_rcp,
                }
                data.append(vals)
        res={
            'data'        : data,
            'reception_id': reception_id,
            'emplacement' : emplacement,
            'err'         : err,
        }
        print(emplacement)
        return res
    

    def move_stock(self):
        print(self)
        time.sleep(2)

        res={
            'data': [],
            'test': 'TEST',
            'err' : "",
        }
        return res


