# -*- coding: utf-8 -*-
from odoo import models,fields,api,tools,SUPERUSER_ID
from odoo.exceptions import ValidationError
import string
import time
from datetime import datetime, date, timedelta
from subprocess import PIPE, Popen
import logging
_logger = logging.getLogger(__name__)


class stock_location(models.Model):
    _inherit = 'stock.location'

    control_quality = fields.Boolean(u'Contrôle qualité', default=False)

    def name_get(self):
        res = []
        for obj in self:
            name = obj.name
            res.append((obj.id,name))
        return res


class is_commentaire_mouvement_stock(models.Model):
    _name = 'is.commentaire.mouvement.stock'
    _description = 'Comentaires sur les mouvements'

    name = fields.Char('Description', required=True)


class stock_lot(models.Model):
    _inherit = "stock.lot"
    _order="id desc"

    is_date_peremption = fields.Date("Date de péremption")
    is_lot_fournisseur = fields.Char("Lot fournisseur")
    company_id = fields.Many2one('res.company', 'Company', required=True, store=True, index=True, default=1) #J'ai ajouté default=1, sinon, impossible de créer des lots


    def _domain_product_id(self):
        "Modification de la fonction par défaut pour autoriser tous les articles dans un lot"
        domain = [
            #"('tracking', '!=', 'none')",
            "('type', '=', 'product')",
            "'|'",
                "('company_id', '=', False)",
                "('company_id', '=', company_id)"
        ]
        if self.env.context.get('default_product_tmpl_id'):
            domain.insert(0,
                ("('product_tmpl_id', '=', %s)" % self.env.context['default_product_tmpl_id'])
            )
        res='[' + ', '.join(domain) + ']'
        return res


class stock_picking_type(models.Model):
    _inherit = "stock.picking.type"


    def name_get(self):
        res = []
        for picking_type in self:
            name = picking_type.name
            res.append((picking_type.id, name))
        return res


class is_stock_picking_colisage(models.Model):
    _name='is.stock.picking.colisage'
    _description="UC du picking"
    _order='colis_id'

    picking_id = fields.Many2one('stock.picking', 'Picking', required=True, ondelete='cascade')
    colis_id   = fields.Many2one('is.product.ul', 'Colis')
    nb         = fields.Float('Nb')


class stock_picking(models.Model):
    _inherit = "stock.picking"
    _order   = "date desc, name desc"
    
    is_sale_order_id       = fields.Many2one('sale.order', 'Commande Client (champ obsolète dans Odoo 16 car remplacé par sale_id)')
    is_purchase_order_id   = fields.Many2one('purchase.order', 'Commande Fournisseur')
    is_transporteur_id     = fields.Many2one('res.partner', 'Transporteur', compute='_compute_transporteur_dates', store=True, readonly=False)
    is_date_expedition     = fields.Date("Date d'expédition"            , compute='_compute_transporteur_dates', store=True, readonly=False)
    is_date_livraison      = fields.Date("Date d'arrivée chez le client", compute='_compute_transporteur_dates', store=True, readonly=False)
    is_date_livraison_vsb  = fields.Boolean('Avertissement VSB', store=False, compute='_compute_is_date_livraison_vsb', readonly=True)
    is_date_livraison_msg  = fields.Char("Avertissement"       , store=False, compute='_compute_is_date_livraison_vsb', readonly=True)
    is_num_bl              = fields.Char("N° BL fournisseur", copy=False)
    is_date_reception      = fields.Date('Date de réception')
    is_facture_pk_id       = fields.Many2one('is.facture.pk', 'Facture PK')
    is_piece_jointe        = fields.Boolean(u"Pièce jointe", store=False, readonly=True, compute='_compute_is_piece_jointe')
    is_galia_um            = fields.Boolean(u"Test si étiquettes scannées sur Liste à servir", store=False, readonly=True, compute='_compute_is_galia_um')
    is_mode_envoi_facture  = fields.Selection(related="partner_id.is_mode_envoi_facture", string="Mode d'envoi des factures")
    is_traitement_edi      = fields.Selection(related='partner_id.is_traitement_edi', string='Traitement EDI', readonly=True)
    is_date_traitement_edi = fields.Datetime("Date traitement EDI")
    invoice_state = fields.Selection([
            ('none'      , 'Non applicable'),
            ('2binvoiced', "À facturer"),
            ('invoiced'  , "Facturé"),
        ], "Facturation", default="2binvoiced", compute="_compute_invoice_state", store=True)
    is_point_dechargement = fields.Char('Point de déchargement', compute='_compute_is_point_dechargement', store=False, readonly=True)
    is_colisage_ids       = fields.One2many('is.stock.picking.colisage', 'picking_id', "Colisage", readonly=1)
    is_nb_um              = fields.Integer('Nb UM', readonly=1)
    is_nb_uc              = fields.Integer('Nb UC', readonly=1)
    is_alerte             = fields.Text('Alerte', readonly=1)

    is_reception_inter_site_id = fields.Many2one('is.reception.inter.site', 'Réception inter-site', copy=False)
    is_qt_livree_inter_site    = fields.Float("Qt livrée inter-site", digits=(12, 6), copy=False)
    is_location_dest_prevu_id  = fields.Many2one('stock.location', 'Emplacement', help="Emplacement de destination du premier mouvement", compute='_compute_is_location_mouvement_id', store=False, readonly=True)

    is_plaque_immatriculation = fields.Char("Plaque d’immatriculation", copy=False)
    is_dossier_transport      = fields.Char("N° de dossier de transport ", copy=False)
    is_identifiant_transport  = fields.Char("N° identifiant transport", copy=False)
    is_votre_contact_id       = fields.Many2one('res.partner', 'Votre contact', readonly=True)


    @api.depends('move_ids_without_package')
    def _compute_is_location_mouvement_id(self):
        for obj in self:
            location_id = False
            for line in obj.move_ids_without_package:
                location_id=line.is_location_dest_prevu_id.id
                break
            obj.is_location_dest_prevu_id = location_id





    # is_site_livraison_id        = fields.Many2one('is.database', 'Site de livraison')
    # is_fournisseur_reception_id = fields.Many2one('res.partner', 'Fournisseur de réception', domain=[('is_company','=',True),('supplier','=',True)])
    # is_alerte_inter_sites       = fields.Text('Alerte inter-sites', readonly=1)
    # is_info_inter_sites         = fields.Text('Infos inter-sites', readonly=1)


    # def reception_inter_sites_action(self):
    #     for obj in self:
    #         database = obj.is_site_livraison_id


    #         company = self.env.user.company_id


    #         DBNAME   = database.database
    #         USER     = company.is_postgres_user
    #         HOST     = company.is_postgres_host
    #         PASSWORD = company.is_postgres_pwd
    #         cnx = psycopg2.connect("dbname='%s' user='%s' host='%s' password='%s'"%(DBNAME,USER,HOST,PASSWORD))
    #         cr  = cnx.cursor(cursor_factory=RealDictCursor)
    #         SQL="SELECT * FROM is_database" # WHERE database=%s"
    #         cr.execute(SQL) #, [DBNAME])
    #         rows = cr.fetchall()
    #         for row in rows:
    #             print(row)

            # try:
            #     #cnx = psycopg2.connect("dbname='"+self._cr.dbname+"' user='"+company.is_postgres_user+"' host='"+company.is_postgres_host+"' password='"+company.is_postgres_pwd+"'")

            #     DBNAME   = database.database
            #     USER     = company.is_postgres_user
            #     HOST     = company.is_postgres_host
            #     PASSWORD = company.is_postgres_pwd

            #     cnx = psycopg2.connect("dbname='%s' user='%s' host='%s' password='%s'"%(DBNAME,USER,HOST,PASSWORD))
            # except Exception:
            #     raise ValidationError('Postgresql 0 non disponible !')


            # DB        = database.database
            # USERID    = SUPERUSER_ID
            # DBLOGIN   = database.login
            # USERPASS  = database.password
            # DB_SERVER = database.ip_server
            # DB_PORT   = database.port_server

            # sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object' % (DB_SERVER, DB_PORT))
            # alerte=[]
            # info=[]
            # if not obj.is_site_livraison_id:
            #     alerte.append("Site de livraison obligatoire")
            # if not obj.is_fournisseur_reception_id:
            #     alerte.append("Fournisseur de réception obligatoire")

            # nb_rcp=nb_liv=0
            # nb_liv = len(obj.move_ids_without_package)
            # info.append("%s lignes livréees"%nb_liv)

            # #** Recherche dans les réceptions validées ************************
            # if not alerte:
            #     date_debut = obj.date_done
            #     date_fin   = obj.date_done + timedelta(days=7)
            #     domain=[
            #         ('is_num_bl','=',obj.name),
            #         ('picking_type_id','=',1),
            #         ('is_date_reception','>=',date_debut),
            #         ('is_date_reception','<=',date_fin),
            #         ('partner_id.is_code','=',obj.is_fournisseur_reception_id.is_code),
            #         ('partner_id.is_adr_code','=',obj.is_fournisseur_reception_id.is_adr_code),
            #         ('state','=','done'),
            #     ]

            #     lines = sock.execute_kw(DB, USERID, USERPASS, 'stock.picking', 'search_read', [domain], {'fields': ['name', 'id', 'is_date_reception'], 'limit': 100})
            #     nb_rcp = len(lines)
            #     info.append("%s réceptions trouvées"%nb_rcp)
            #     for line in lines:
            #         print(line['name'],line['is_date_reception'])
            # #******************************************************************

            # #** Alerte si nb_liv<>nb_rcp **************************************
            # if nb_liv!=nb_rcp:
            #     alerte.append('Nombre de lignes de réception (%s) différent du nombre lignes livrées (%s)'%(nb_rcp,nb_liv))



            # if alerte==[]:
            #     alerte=False
            # else:
            #     alerte='\n'.join(alerte)
            # obj.is_alerte_inter_sites = alerte
            # if info==[]:
            #     info=False
            # else:
            #     info='\n'.join(info)
            # obj.is_info_inter_sites = info



    def voir_picking_action(self):
        for obj in self:
            #view_id=self.env.ref('is_plastigray16.is_account_view_move_form')
            res= {
                'name': obj.name,
                'view_mode': 'form',
                'res_model': 'stock.picking',
                'res_id': obj.id,
                #'view_id': view_id.id,
                'type': 'ir.actions.act_window',
                #'context': {'default_move_type':'out_invoice', 'move_type':'out_invoice', 'journal_type': 'sale'},
                #'domain': [('move_type','=','out_invoice'),('journal_type','=','sale')],
            }
            return res


    def compute_is_identifiant_transport(self):
        "Recherche du champ sur les lignes de la commande pour le renseigner en entête de BL"
        for obj in self:
            if not obj.is_identifiant_transport:
                for move in obj.move_ids_without_package:
                    if move.sale_line_id.is_identifiant_transport:
                        obj.is_identifiant_transport = move.sale_line_id.is_identifiant_transport
                        break


    def compute_is_colisage_ids(self):
        for obj in self:
            obj.compute_is_identifiant_transport()
            colis={}
            lines=[]
            um_ids=[]
            nb_uc=0
            for move in obj.move_ids_without_package:
                for l in move.is_uc_ids:
                    nb_uc+=1
                    if l.um_id not in um_ids:
                        um_ids.append(l.um_id)
            for move in obj.move_ids_without_package:
                packaging=False
                for l in move.product_id.packaging_ids:
                    packaging = l.ul
                if packaging:
                    for l in move.is_uc_ids:
                        if packaging not in colis:
                            colis[packaging]=0
                        colis[packaging]+=1
            for line in colis:
                vals={
                    'picking_id': obj.id,
                    'colis_id'  : line.id,
                    'nb'        : colis[line],
                }
                lines.append([0,0,vals])
            obj.is_colisage_ids.unlink()
            obj.is_colisage_ids = lines
            obj.is_nb_um = len(um_ids)
            obj.is_nb_uc = nb_uc


    def compute_alerte(self):
        for obj in self:
            alerte=False
            is_qt_uc = quantity_done = 0
            for move in obj.move_ids_without_package:
                is_qt_uc+=move.is_qt_uc
                quantity_done+=move.quantity_done
            if is_qt_uc!=quantity_done and is_qt_uc>0:
                alerte="La quantité totale scannée (%s) ne correspond pas à la quantité livrée (%s) !"%(is_qt_uc,quantity_done)
            obj.is_alerte=alerte


    def is_alerte_action(self):
        print(self)


    @api.depends('move_ids_without_package')
    def _compute_is_point_dechargement(self):
        for obj in self:
            x = False
            for line in obj.move_ids_without_package:
                x=line.is_point_dechargement
                break
            obj.is_point_dechargement = x


    @api.depends('state', 'move_ids', 'move_ids.invoice_state')
    def _compute_invoice_state(self):
        for obj in self:
            if obj.state=="cancel":
                invoice_state="none"
            else:
                invoice_state="invoiced"
                for line in obj.move_ids_without_package:
                    if line.invoice_state!="invoiced":
                        invoice_state="2binvoiced"
                        break
            obj.invoice_state = invoice_state


    @api.depends('sale_id', 'partner_id')
    def _compute_transporteur_dates(self):
        date_expedition = time.strftime('%Y-%m-%d')
        #date_livraison  = self.env['stock.move']._get_date_livraison(date_expedition)
        date_livraison= self.env['res.partner'].get_date_livraison( self.company_id, self.partner_id, date_expedition)
        for obj in self:
            is_transporteur_id=False
            if obj.sale_id:
                is_transporteur_id = obj.sale_id.is_transporteur_id.id
            obj.is_transporteur_id = is_transporteur_id
            obj.is_date_expedition = date_expedition
            obj.is_date_livraison  = date_livraison
            if obj.sale_id.is_source_location_id:
                obj.location_id = obj.sale_id.is_source_location_id.id


    @api.onchange('is_date_expedition')
    def onchange_date_expedition(self):
        date_livraison = self.is_date_expedition
        if self.partner_id and self.company_id:
            date_livraison= self.env['res.partner'].get_date_livraison( self.company_id, self.partner_id, self.is_date_expedition)
        self.is_date_livraison = date_livraison


    def creer_factures_action(self):
        # ids=[]
        # for obj in self:
        #     id = obj.sale_id.id
        #     if id and id not in ids:
        #         ids.append(id)
        # self.env['sale.order'].search([('id','in',ids)])._create_invoices() #  def _create_invoices(self, grouped=False, final=False, date=None)

        for obj in self:
           self.env['sale.order'].search([('id','in',[obj.sale_id.id])])._create_invoices() #  def _create_invoices(self, grouped=False, final=False, date=None)


    def transfert_action(self):
        for obj in self:
            print(obj)


    def pj_action(self):
        for obj in self:
            print(obj)


    def _compute_is_piece_jointe(self):
        for obj in self:
            attachments = self.env['ir.attachment'].search([('res_model','=',self._name),('res_id','=',obj.id)])
            pj=False
            if attachments:
                pj=True
            obj.is_piece_jointe=pj


    @api.depends('is_date_livraison', 'partner_id', 'company_id')
    def _compute_is_date_livraison_vsb(self):
        for obj in self:
            vsb = self.check_date_livraison(obj.is_date_livraison, obj.partner_id.id)
            obj.is_date_livraison_vsb=vsb
            msg=''
            if not vsb:
                msg='La date de livraison tombe pendant la fermeture du client !'
            obj.is_date_livraison_msg=msg


    def _compute_is_galia_um(self):
        for obj in self:
            test=False
            if obj.sale_id.is_liste_servir_id.galia_um_ids:
                test=True
            obj.is_galia_um = test


    def get_is_code_rowspan(self,product_id):
        cr = self._cr
        for obj in self:
            liste_servir = obj.sale_id.is_liste_servir_id
            SQL="""
                select count(*)
                from is_galia_base_uc uc inner join is_galia_base_um um on uc.um_id=um.id
                                         inner join is_liste_servir ls on um.liste_servir_id=ls.id
                                         inner join product_product pp on uc.product_id=pp.id 
                where 
                    ls.id="""+str(liste_servir.id)+""" and 
                    uc.product_id="""+str(product_id)+""" 
            """
            cr.execute(SQL)
            result = cr.fetchall()
            nb=0
            for row in result:
                nb=row[0]
            return nb


    def get_um_rowspan(self,product_id,um_id):
        cr = self._cr
        for obj in self:
            liste_servir = obj.sale_id.is_liste_servir_id
            SQL="""
                select count(*)
                from is_galia_base_uc uc inner join is_galia_base_um um on uc.um_id=um.id
                                         inner join is_liste_servir ls on um.liste_servir_id=ls.id
                                         inner join product_product pp on uc.product_id=pp.id 
                where 
                    ls.id="""+str(liste_servir.id)+""" and 
                    uc.product_id="""+str(product_id)+""" and
                    um.id="""+str(um_id)+""" 
            """
            cr.execute(SQL)
            result = cr.fetchall()
            nb=0
            for row in result:
                nb=row[0]
            return nb


    def get_etiquettes(self):
        cr = self._cr
        res=[]
        for obj in self:
            #** Recherche des articles du BL **********************************
            product_ids=[]
            for line in obj.move_ids_without_package:
                if line.state=="done":
                    product_id = line.product_id.id
                    if product_id not in product_ids:
                        product_ids.append(str(product_id))
            product_ids = ",".join(product_ids)
            #******************************************************************

            liste_servir = obj.sale_id.is_liste_servir_id
            SQL="""
                select 
                    pt.is_code,
                    um.name,
                    uc.num_eti,
                    uc.qt_pieces,
                    pp.id,
                    um.id,
                    uc.production
                from is_galia_base_uc uc inner join is_galia_base_um um on uc.um_id=um.id
                                         inner join is_liste_servir ls on um.liste_servir_id=ls.id
                                         inner join product_product pp on uc.product_id=pp.id 
                                         inner join product_template pt on pp.product_tmpl_id=pt.id
                where 
                    ls.id="""+str(liste_servir.id)+""" and 
                    pp.id in ("""+product_ids+""") 
                order by pt.is_code, um.name, uc.num_eti
            """
            cr.execute(SQL)
            result = cr.fetchall()
            ct_code = 0
            ct_um   = 0
            is_code_rowspan = 0
            um_rowspan = 0
            mem_code = ''
            mem_um   = ''
            for row in result:
                is_code_rowspan=0
                um_rowspan=0
                if row[0]!=mem_code:
                    mem_code=row[0]
                    is_code_rowspan=self.get_is_code_rowspan(row[4])
                    ct_code=0

                is_code_um = (row[0]+row[1])
                if is_code_um!=mem_um:
                    mem_um=is_code_um
                    um_rowspan=self.get_um_rowspan(row[4],row[5])
                    ct_um=0

                ct_code+=1
                ct_um+=1

                vals={
                    'is_code'  : row[0],
                    'um'       : row[1],
                    'uc'       : row[2],
                    'qt_pieces': row[3],
                    'lot'      : row[6],
                    'is_code_rowspan': is_code_rowspan,
                    'um_rowspan': um_rowspan,
                }
                res.append(vals)
        return res


    def check_date_livraison(self, date_livraison,  partner_id, context=None):
        res_partner = self.env['res.partner']
        if partner_id and date_livraison:
            partner = self.env['res.partner'].browse(partner_id)
            # jours de fermeture de la société
            jours_fermes = res_partner.num_closing_days(partner)
            # Jours de congé de la société
            leave_dates = res_partner.get_leave_dates(partner,avec_jours_feries=True)
            # num de jour dans la semaine de la date de livraison
            if type(date_livraison) is str:
                date_livraison = datetime.strptime(date_livraison, '%Y-%m-%d')
            #num_day = time.strftime('%w', time.strptime(date_livraison, '%Y-%m-%d'))
            num_day = date_livraison.strftime('%Y%m%d')
            if int(num_day) in jours_fermes or date_livraison in leave_dates:
                return False
        return True


    def action_imprimer_etiquette_reception(self):
        for obj in self:
            uid=self._uid
            user=self.env['res.users'].browse(uid)
            soc=user.company_id.partner_id.is_code
            return {
                'type' : 'ir.actions.act_url',
                'url': 'http://odoo16/odoo-erp/reception/Impression_Etiquette_Reception.php?Soc='+str(soc)+'&&zzCode='+str(obj.name),
                'target': '_blank',
            }


    def action_annuler_reception(self):
        cr = self._cr
        for obj in self:
            if obj.state!='done':
                raise ValidationError("Cette réception n'est pas à l'état 'Fait' !")

            #** Copie du picking pour pourvoir refaire la réception ***********
            new_picking=obj.copy()
            new_picking.action_confirm()
            #******************************************************************

            #** Recherche si les lignes de cette réception son facturées ******
            for line in obj.move_ids_without_package:
                if line.invoice_state=='invoiced':
                    raise ValidationError('Annulation impossible car la réception est déjà facturée !')
                line.invoice_state="none"
            obj.invoice_state='none'
            #******************************************************************

            #** Création des mouvements inverses pour annuller la rcp *********
            for move in obj.move_ids_without_package:
                vals={
                    "product_id": move.product_id.id,
                    "product_uom": move.product_uom.id,
                    "location_id": move.location_dest_id.id,
                    "location_dest_id": move.location_id.id,
                    "origin": move.origin,
                    "name": move.name,
                    "reference": move.reference,
                    "procure_method": "make_to_stock",
                    "product_uom_qty": move.product_uom_qty,
                    "scrapped": False,
                    "propagate_cancel": True,
                    "additional": False,
                    "picking_id":move.picking_id.id,
                }
                move_retour=self.env['stock.move'].create(vals)
                for line in move.move_line_ids:
                    vals={
                        "move_id": move_retour.id,
                        "product_id": line.product_id.id,
                        "product_uom_id": line.product_uom_id.id,
                        "location_id": move.location_dest_id.id,
                        "location_dest_id": move.location_id.id,
                        "lot_id": line.lot_id.id,
                        "qty_done": line.qty_done,
                        "reference": line.reference,
                    }
                    move_line_retour=self.env['stock.move.line'].create(vals)
                move_retour._action_done()
            # #******************************************************************


            #** Annulation du picking d'origigne et des mouvements **************
            for move in obj.move_ids_without_package:
                move.state="cancel"
            obj.state="cancel"
            #for move in retour.move_ids_without_package:
            #    move.state="cancel"
            #******************************************************************

            return {
                'name': "Réception annullée",
                'view_mode': 'form',
                'res_model': 'stock.picking',
                'type': 'ir.actions.act_window',
                'res_id': new_picking.id,
                'domain': '[]',
            }


    def action_invoice_create(self, cr, uid, ids, journal_id, group=False, type='out_invoice', context=None):
        """
            Permet de fixer la date de la facture à la date de la livraison lors 
            de la création des factures à partir des livraisons
        """
        context = context or {}
        todo = {}
        for picking in self.browse(cr, uid, ids, context=context):
            partner = self._get_partner_to_invoice(cr, uid, picking, dict(context, type=type))
            if group:
                key = partner
            else:
                key = picking.id
            for move in picking.move_lines:
                if move.invoice_state == '2binvoiced':
                    if (move.state != 'cancel') and not move.scrapped:
                        todo.setdefault(key, [])
                        todo[key].append(move)
        invoices = []
        for moves in todo.values():
            date_inv=False
            for move in moves:
                date_inv=move.picking_id.is_date_expedition
            context['date_inv']=date_inv
            invoices += self._invoice_create_line(cr, uid, moves, journal_id, type, context=context)
        return invoices


    def affectation_uc_aux_lignes_des_livraisons(self):
        """Après avoir scanné les UC pour la liste à servir, il faut répartir 
        les UC sur les lignes des livraisons pour traiter les cas ou il y a 
        plusieurs lignes pour un même article"""

        cr = self._cr
        for obj in self:
            liste_servir_id = obj.sale_id.is_liste_servir_id.id
            if liste_servir_id:
                #** Reinitialisation du lien entre UC et ligne livraison ******
                SQL="update is_galia_base_uc set stock_move_id=NULL where um_id in (select id from is_galia_base_um where liste_servir_id=%s)"
                cr.execute(SQL,[liste_servir_id])
                cr.commit()

                #** Affectation des lignes de livraisons aux UC ***************
                for move in obj.move_ids_without_package:
                    quantite = move.product_uom_qty
                    filtre=[
                        ('liste_servir_id','=',liste_servir_id)
                    ]
                    if obj.state!='done':
                            raise ValidationError("Cette réception n'est pas à l'état 'Fait' !")
                    ums=self.env['is.galia.base.um'].search(filtre)
                    test=True
                    for  um in ums:
                        ct=1
                        for uc in um.uc_ids:
                             if uc.product_id==move.product_id and not uc.stock_move_id and test:
                                qt_pieces = uc.qt_pieces
                                uc.stock_move_id = move.id
                                quantite=quantite-qt_pieces
                                if quantite<=0:
                                    test=False
                                    #break
                                ct+=1
        cr.commit()


    def mise_a_jour_colisage_action(self):
        for obj in self:
            #** Recherche du contact de Plastigray ****************************
            company = self.env.user.company_id
            for contact in company.partner_id.child_ids:
                if contact.is_type_contact.name=='Logistique':
                    obj.is_votre_contact_id = contact.id
                    break
                    #print(contact, contact.is_type_contact.name)
            #******************************************************************

            obj.affectation_uc_aux_lignes_des_livraisons()
            liste_servir_id=obj.sale_id.is_liste_servir_id.id
            if liste_servir_id:
                obj.compute_is_colisage_ids()
            for move in obj.move_ids_without_package:
                move.compute_is_uc_galia()
                move._compute_lots()
            obj.compute_alerte()


    def desadv_action(self):
        for obj in self : 
            obj.affectation_uc_aux_lignes_des_livraisons()
            name='edi-tenor-desadv-odoo16'
            cdes = self.env['is.commande.externe'].search([('name','=',"edi-tenor-desadv-odoo16")])
            if (len(cdes)==0):
                raise ValidationError("Commande externe '%s' non trouvée"%name)
            for cde in cdes:
                model=self._name
                uid=self._uid
                user=self.env['res.users'].browse(uid)
                soc=user.company_id.partner_id.is_code
                x = cde.commande
                x = x.replace("#soc"   , soc)
                x = x.replace("#model" , model)
                x = x.replace("#res_id", str(obj.id))
                x = x.replace("#uid"   , str(uid))
                _logger.info(x)

                # lines=os.popen(x).readlines()
                # for line in lines:
                #     _logger.info(line.strip())

                p = Popen(x, shell=True, stdout=PIPE, stderr=PIPE)
                stdout, stderr = p.communicate()
                _logger.info("cde:%s, stdout:%s, stderr:%s"%(x,stdout.decode("utf-8"),stderr.decode("utf-8")))
                if stderr:
                    raise ValidationError("%s\n%s"%(x,stderr.decode("utf-8")))
                now = datetime.now()
                obj.is_date_traitement_edi = now
                lines = stdout.decode("utf-8").split('\n')
                body = u"<b>DESADV envoyé</b><br>"+"<br>".join(lines)
                vals={
                    'author_id': user.partner_id.id,
                    'subtype_id': self.env.ref('mail.mt_comment').id,
                    'body'     : body,
                    'model'    : model,
                    'res_id'   : obj.id
                }
                res=self.env['mail.message'].create(vals)


    def button_validate(self):
        self.action_assign()
        res=super().button_validate()
        return True


    def action_assign(self):
        for obj in self : 
            if obj.picking_type_id.code=='outgoing':
                for move in obj.move_ids_without_package:
                    move.move_line_ids.unlink()
                    move.quantity_done = move.product_uom_qty


    def test_action(self):
        for obj in self:
            for move in obj.move_ids_without_package:
                move.move_line_ids.unlink()
            obj.action_assign()


class stock_quant(models.Model):
    _inherit = "stock.quant"
    _order   = "product_id, location_id"

    is_mold_id          = fields.Many2one('is.mold'    , 'Moule'            , related='product_id.is_mold_id'         , readonly=True)


    @api.onchange('location_id', 'product_id', 'lot_id', 'package_id', 'owner_id')
    def _onchange_location_or_product_id(self):
        vals = {}

        # Once the new line is complete, fetch the new theoretical values.
        if self.product_id and self.location_id:
            # Sanity check if a lot has been set.
            #if self.lot_id:
            #    if self.tracking == 'none' or self.product_id != self.lot_id.product_id:
            #        vals['lot_id'] = None

            quant = self._gather(
                self.product_id, self.location_id, lot_id=self.lot_id,
                package_id=self.package_id, owner_id=self.owner_id, strict=True)
            if quant:
                self.quantity = quant.quantity

            # Special case: directly set the quantity to one for serial numbers,
            # it'll trigger `inventory_quantity` compute.
            if self.lot_id and self.tracking == 'serial':
                vals['inventory_quantity'] = 1
                vals['inventory_quantity_auto_apply'] = 1

        if vals:
            self.update(vals)





