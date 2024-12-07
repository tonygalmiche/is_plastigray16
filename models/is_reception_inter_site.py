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
                    sm.id move_id,
                    sol.is_date_livraison
                FROM stock_picking sp join stock_move       sm on sm.picking_id=sp.id
                                      join product_product  pp on sm.product_id=pp.id 
                                      join product_template pt on pp.product_tmpl_id=pt.id
                                      join sale_order_line sol on sm.sale_line_id=sol.id 
                WHERE 
                    sp.name='%s' and 
                    sp.state='done' and sm.state='done' and sp.picking_type_id=2


                ORDER BY sol.is_date_livraison,pt.is_code
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
                        sm.location_dest_id,
                        sp.scheduled_date,
                        pol.date_planned
                    FROM stock_picking sp join stock_move         sm on sm.picking_id=sp.id
                                        join product_product      pp on sm.product_id=pp.id 
                                        join product_template     pt on pp.product_tmpl_id=pt.id
                                        join purchase_order_line pol on sm.purchase_line_id=pol.id
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
                        ORDER BY pol.date_planned
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
                        ORDER BY pol.date_planned
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

                        #** Recherche location_id dans stock.move *************
                        move = self.env['stock.move'].browse(move_rcp_id)
                        if move.is_location_dest_prevu_id.id:
                            location_id = move.is_location_dest_prevu_id.id

                        #** Recherche des UC/UM *******************************
                        SQL="""
                            SELECT 
                                uc.num_eti,uc.qt_pieces,um.name, uc.num_carton, uc.qt_pieces, 
                                uc.product_id, uc.type_eti, uc.date_creation,uc.production,pt.is_code,
                                um.mixte,um.active
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
                                    VALUES (%s, %s, %s, %s, now() AT TIME ZONE 'UTC', now() AT TIME ZONE 'UTC', %s, %s)
                                    RETURNING id
                                """
                                cr.execute(SQL,[
                                    name,
                                    uid,
                                    uid,
                                    location_id,
                                    line['mixte'],
                                    line['active'],
                                ])
                                rows2 = cr.dictfetchall()
                                for row2 in rows2:
                                    um_id=row2['id']
                                    #info.append('Création UM %s'%name)
                            if not um_id:
                                alerte.append("Impossible de trouver ou créer l'UM %s"%name)
                            else:
                                #** Mise à jour location_id de l'UM ***********
                                um = self.env['is.galia.base.um'].browse(um_id)
                                if um.id:
                                    um.location_id = location_id

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

                        msg = "%s : %s au %s Liv (%s) : %s au %s Rcp (%s) : %s Scan : %s Qt pièces UC"%(
                            is_code.ljust(9), 
                            str(qt_liv).rjust(8), 
                            row_liv['is_date_livraison'],
                            row_liv['name'],
                            str(qt_rcp).rjust(8),
                            str(row['date_planned'])[0:10],  
                            num_rcp,
                            str(qt_scan).rjust(8),
                            str(qt_uc).rjust(8)
                        )
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



    def voir_articles_action(self):
        for obj in self:
            ids=[]
            lines = self.env['is.galia.base.uc'].search([('reception_inter_site_id','=',obj.id)])
            for line in lines:
                product_id = line.product_id.product_tmpl_id.id
                if product_id not in ids:
                    ids.append(product_id)
            res= {
                'name': obj.name,
                'view_mode': 'tree,form',
                'res_model': 'product.template',
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
                    picking.mise_a_jour_colisage_action()
            obj.state='controle'


    def get_um_reception_action(self):
        for obj in self:
            obj.get_um_reception(bl=obj.num_bl)


    def get_ums(self):
        for obj in self:
            lines = self.env['is.galia.base.uc'].search([('reception_inter_site_id','=',obj.id)])
            ids=[]
            for line in lines:
                um_id = line.um_id.id
                if um_id not in ids:
                    ids.append(um_id)
            ums = self.env['is.galia.base.um'].search([('id','in',ids)])
            return ums 


    def get_stock_par_emplacement_et_par_article(self):
        for obj in self:
            ums=obj.get_ums()
            res={}
            for um in ums:
                for uc in um.uc_ids:
                    code        = uc.product_id.is_code
                    location    = uc.um_id.location_id.name
                    key = "%s-%s"%(location,code)
                    if key not in res:
                        vals={
                            'qt_pieces'       : 0,
                            'code_pg'         : uc.product_id.is_code,
                            'product_id'      : uc.product_id.id,
                            'location_id'     : uc.um_id.location_id.id,
                            'location_dest_id': obj.location_id.id,
                            'location'        : uc.um_id.location_id.name,
                            'um_ids'          : [],
                        }
                        res[key] = vals
                    res[key]['qt_pieces']+=uc.qt_pieces
                    if um.id not in res[key]['um_ids']:
                        res[key]['um_ids'].append(um.id)



            stock_sorted = dict(sorted(res.items())) 
            for key in stock_sorted:
                product_id     = stock_sorted[key]['product_id']
                location_id = stock_sorted[key]['location_id']
                ##** Recherche du stock pour l'article et l'emplacement
                quants=self.env['stock.quant'].search([('product_id','=',product_id),('location_id','=',location_id)])
                stock=0
                for quant in quants:
                    stock+=quant.quantity
                stock_sorted[key]['stock'] = stock
                btn="btn-success"
                if stock_sorted[key]['location_id']==stock_sorted[key]['location_dest_id']:
                    btn="btn-warning 1"
                if stock_sorted[key]['qt_pieces']>res[key]['stock']:
                    btn="btn-warning 2"
                if stock_sorted[key]['location'][0:1]=='Q':
                    btn="btn-warning 3"
                stock_sorted[key]['btn']=btn
            stock_sorted = list(stock_sorted.values())
            return stock_sorted


    def get_um_reception(self,bl=False):
        err=False
        domain=[
            ('num_bl','=',bl),
            ('state','=','controle'),
        ]
        receptions = self.env['is.reception.inter.site'].search(domain)
        data={}
        reception_id = False
        emplacement  = '01'
        stock_sorted=False
        for reception in receptions:
            reception_id = reception.id
            emplacement  = reception.location_id.name
            ums=reception.get_ums()
            #** Recherche des Qt par code PG pour chaque UM (UM xmixte) *******
            for um in ums:
                res={}
                for uc in um.uc_ids:
                    code = uc.product_id.is_code
                    if code not in res:
                        res[code] = 0
                    res[code]+=uc.qt_pieces
                codes=[]
                for code in res:
                    val="%s : %s"%(code,res[code])
                    codes.append(val)
                codes='<br>'.join(codes)
                vals={
                    'id'           : um.id,
                    'name'         : um.name,
                    'location_id'  : um.location_id.id,
                    'location'     : um.location_id.name,
                    'qt_pieces'    : um.qt_pieces,
                    'date_ctrl_rcp': um.date_ctrl_rcp,
                    'codes'        : codes,
                }
                key=um.name
                data[key]=vals
            #******************************************************************
            stock_sorted = reception.get_stock_par_emplacement_et_par_article()
        data_sorted = dict(sorted(data.items())) 
        res={
            'data'        : list(data_sorted.values()),
            'stock'       : stock_sorted,
            'reception_id': reception_id,
            'emplacement' : emplacement,
            'err'         : err,
        }
        return res
    

    def move_stock(self):
        for obj in self:
            stock_sorted = obj.get_stock_par_emplacement_et_par_article()
            for line in stock_sorted:
                if line['btn']=='btn-success':
                    product = self.env['product.product'].browse(line['product_id'])
                    if product:
                        # line_vals={
                        #     "location_id"     : line['location_id'],
                        #     "location_dest_id": line['location_dest_id'],
                        #     #"lot_id"          : line['btn'],
                        #     "qty_done"        : line['qt_pieces'],
                        #     "product_id"      : line['product_id'],
                        # }
                        move_vals={
                            "location_id"     : line['location_id'],
                            "location_dest_id": line['location_dest_id'],
                            "product_uom_qty" : line['qt_pieces'],
                            "product_id"      : line['product_id'],
                            "name"            : product.name,
                        }
                        filtre=[('code', '=', 'internal')]
                        picking_type_id = self.env['stock.picking.type'].search(filtre)[0]
                        picking_vals={
                            "picking_type_id" : picking_type_id.id,
                            "location_id"     : line['location_id'],
                            "location_dest_id": line['location_dest_id'],
                            #'move_line_ids'   : [[0,False,line_vals]],
                            'move_ids'        : [[0,False,move_vals]],
                        }
                        picking=self.env['stock.picking'].create(picking_vals)
                        for move in picking.move_ids_without_package:
                            move.product_uom_qty = line['qt_pieces']
                            move.quantity_done   = line['qt_pieces']
                        picking.action_confirm()
                        picking._action_done()

                        #** Déplacement des UM ********************************
                        for um_id in  line['um_ids']:
                            um = self.env['is.galia.base.um'].browse(um_id)
                            if um:
                                um.location_id = line['location_dest_id']
                        # #******************************************************
            obj.state='termine'
            res={
                'data': [],
                'test': 'TEST',
                'err' : "",
            }
            return res




