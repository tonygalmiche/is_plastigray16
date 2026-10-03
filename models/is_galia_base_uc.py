# -*- coding: utf-8 -*-
from odoo import models, fields, api # type: ignore
from odoo.exceptions import ValidationError  # type: ignore
from xmlrpc import client as xmlrpclib
from datetime import datetime
from markupsafe import Markup
import logging
_logger = logging.getLogger(__name__)


class is_galia_base_uc(models.Model):
    _name='is.galia.base.uc'
    _description="Etiquettes Galia UC"
    _order='num_eti desc'
    _rec_name='num_eti'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _sql_constraints = [('num_eti_uniq','UNIQUE(num_eti,um_id)', u'Cette étiquette existe déjà dans cette UM')]

    um_id         = fields.Many2one('is.galia.base.um', 'UM', required=True, ondelete='cascade', tracking=True)
    um_mixte      = fields.Selection(related="um_id.mixte")
    um_active     = fields.Boolean(related="um_id.active", string="UM active", store=True, tracking=True)
    location_id   = fields.Many2one('stock.location', 'Emplacement UM', related='um_id.location_id', store=True, index=True)
    num_eti       = fields.Integer("N°Étiquette UC", required=True, index=True, tracking=True)
    type_eti      = fields.Char("Type étiquette", required=True   , index=True, tracking=True)
    num_carton    = fields.Integer("N°Carton", required=True      , index=True, tracking=True)
    qt_pieces     = fields.Integer("Qt Pièces", required=True, tracking=True)
    date_creation = fields.Datetime("Date de création", required=True, tracking=True)
    production_id = fields.Many2one('mrp.production', 'Ordre de fabrication', tracking=True)
    lot_id        = fields.Many2one('stock.lot', 'Lot', tracking=True)
    production    = fields.Char('Fabrication', tracking=True, index=True)
    product_id    = fields.Many2one('product.product', 'Article', required=True , index=True, tracking=True)
    is_category_id     = fields.Many2one('is.category', 'Catégorie', related='product_id.is_category_id', store=True)
    is_gestionnaire_id = fields.Many2one('is.gestionnaire', 'Gestionnaire', related='product_id.is_gestionnaire_id', store=True)
    segment_id         = fields.Many2one('is.product.segment', 'Segment', related='product_id.segment_id', store=True)
    qty_available = fields.Float('Stock article', related='product_id.qty_available')
    employee_id   = fields.Many2one("hr.employee", "Employé", tracking=True)
    liste_servir_id   = fields.Many2one('is.liste.servir' , 'Liste à servir'  , related='um_id.liste_servir_id')
    bon_transfert_id  = fields.Many2one('is.bon.transfert', 'Bon de transfert', related='um_id.bon_transfert_id')
    ls_line_id        = fields.Many2one('is.liste.servir.line' , 'Ligne liste à servir', tracking=True)
    bt_line_id        = fields.Many2one('is.bon.transfert.line', 'Ligne bon de transfert', tracking=True)
    stock_move_id     = fields.Many2one('stock.move', 'Ligne livraison', tracking=True)
    stock_move_rcp_id = fields.Many2one('stock.move', 'Ligne réception', tracking=True)
    reception_inter_site_id = fields.Many2one('is.reception.inter.site', 'Réception inter-site', tracking=True)
    reimprime               = fields.Boolean("UC à ré-imprimer", default=False, tracking=True, help="Il faut ré-imprimer cette UC car le point de déchargement, le code routage ou le point de destination a changé")
    etiquette_remplacee_le  = fields.Datetime("Etiquette remplacée le", tracking=True, help="Date et heure de mise en place de l'étiquette ré-imprimée")
    active                  = fields.Boolean("Actif", default=True, tracking=True, index=True)
    information             = fields.Text("Information", readonly=True, compute='_compute_anomalie', store=False)
    anomalie                = fields.Text("Anomalie", readonly=True, compute='_compute_anomalie', store=False)
    doublon                = fields.Boolean("Doublon", readonly=True, compute='_compute_doublon', store=True, tracking=True)
    emplacement_ci          = fields.Boolean("Emplacement CI", compute='_compute_emplacement_ci', store=False)
    lot_ids                 = fields.One2many('is.galia.base.uc.lot', 'uc_id', "Lots", help="Pour les colis incomplets (CI) contenant plusieurs lots")


    @api.constrains('qt_pieces', 'lot_ids')
    def _check_qt_lots(self):
        for obj in self:
            if obj.lot_ids:
                qt_lots = sum(obj.lot_ids.mapped('qt_pieces'))
                if qt_lots!=obj.qt_pieces:
                    raise ValidationError("UC %s : la somme des quantités des lots (%s) doit être égale à Qt Pièces (%s)"%(obj.num_eti,qt_lots,obj.qt_pieces))


    @api.depends('location_id')
    def _compute_emplacement_ci(self):
        for obj in self:
            obj.emplacement_ci = obj.location_id.name=='CI' and obj.location_id.usage=='internal'


    def reintegrer_ci_production_action(self):
        # Archive l'UC et son UM et remet le stock de l'UC de CI vers ATELIER
        for obj in self:
            um = obj.um_id
            if not obj.emplacement_ci:
                raise ValidationError("L'UC %s n'est pas dans l'emplacement CI"%obj.num_eti)
            if len(um.uc_ids)>1:
                raise ValidationError("Réintégration impossible car l'UM %s contient %s UC"%(um.name,len(um.uc_ids)))
            atelier_id = um._get_location_id()
            if not atelier_id:
                raise ValidationError("Emplacement ATELIER non trouvé")
            product = obj.product_id
            qty     = obj.qt_pieces
            lots = self.env['stock.lot'].search([('product_id','=',product.id),('name','=',obj.production)], limit=1)
            if not lots:
                raise ValidationError("Lot %s non trouvé pour l'article %s"%(obj.production,product.is_code))
            quants = self.env['stock.quant'].search([
                ('product_id' ,'=',product.id),
                ('location_id','=',obj.location_id.id),
                ('lot_id'     ,'=',lots.id),
            ])
            stock = sum(quants.mapped('quantity'))
            if stock<qty:
                raise ValidationError("Réintégration impossible car stock insuffisant en CI pour le lot %s : Stock=%s < Qt UC=%s"%(obj.production,stock,qty))
            name="UC %s"%obj.num_eti
            vals={
                "product_id": product.id,
                "product_uom": product.uom_id.id,
                "location_id": obj.location_id.id,
                "location_dest_id": atelier_id,
                "origin": name,
                "name": name,
                "reference": name,
                "procure_method": "make_to_stock",
                "product_uom_qty": qty,
                "scrapped": False,
                "propagate_cancel": True,
                "is_inventory": True,
                "additional": False,
            }
            move=self.env['stock.move'].create(vals)
            vals={
                "move_id": move.id,
                "product_id": product.id,
                "product_uom_id": product.uom_id.id,
                "location_id": obj.location_id.id,
                "location_dest_id": atelier_id,
                "lot_id": lots.id,
                "qty_done": qty,
                "reference": name,
            }
            self.env['stock.move.line'].create(vals)
            move._action_done()
            msg=Markup('Réintégration de CI en production : %s pièces du lot %s déplacées vers ATELIER (mouvement <a href="#" data-oe-model="stock.move" data-oe-id="%s">%s</a>)')%(qty,obj.production,move.id,move.id)
            obj.message_post(body=msg)
            um.message_post(body=msg)
            obj.active = False
            um.active  = False
        return True


    @api.depends('num_eti', 'active', 'um_id', 'location_id', 'product_id', 'qt_pieces', 'production', 'lot_id', 'lot_ids', 'lot_ids.lot_id', 'lot_ids.qt_pieces')
    def _compute_anomalie(self):
        for obj in self:
            information = []
            anomalie = []
            if obj.num_eti and obj.active and obj.um_id.active:
                domain = [('num_eti','=',obj.num_eti),('id','!=',obj._origin.id),('um_id.active','=',True)]
                doublons = self.search(domain)
                if doublons:
                    ums = (obj.um_id | doublons.um_id).mapped('name')
                    msg = "Etiquette dans plusieurs UM (%s)"%', '.join(ums)
                    anomalie.append(msg)

            #** Comparaison des quantités par lot avec le stock de l'emplacement (comme sur l'UM)
            if obj.product_id and obj.location_id.usage=='internal':
                for vals in obj.get_qt_par_lot():
                    msg="%s : %s : Qt UC=%s : Stock=%s"%(
                        (obj.product_id.is_code or '').ljust(8),
                        (vals['lot'].name or 'Lot non trouvé').ljust(8),
                        str(int(vals['qt_pieces'])).ljust(4),
                        int(vals['stock'])
                    )
                    if vals['lot'] and vals['qt_pieces']<=vals['stock']:
                        information.append(msg)
                    else:
                        anomalie.append(msg)
            obj.information = (len(information) and '\n'.join(information)) or False
            obj.anomalie    = (len(anomalie)    and '\n'.join(anomalie)) or False


    def get_qt_par_lot(self):
        "Quantités par lot de l'UC (tableau des lots, sinon champ Lot, sinon lot de la Fabrication) et stock du lot dans l'emplacement de l'UC"
        self.ensure_one()
        res=[]
        if self.lot_ids:
            lignes = [(line.lot_id, line.qt_pieces) for line in self.lot_ids]
        else:
            lot = self.lot_id
            if not lot and self.production:
                lot = self.env['stock.lot'].search([('product_id','=',self.product_id.id),('name','=',self.production)], limit=1)
            lignes = [(lot, self.qt_pieces)]
        for lot,qt_pieces in lignes:
            stock=0
            if lot:
                domain=[
                    ('product_id' ,'=',self.product_id.id),
                    ('location_id','=',self.location_id.id),
                    ('lot_id'     ,'=',lot.id),
                ]
                stock = sum(self.env['stock.quant'].search(domain).mapped('quantity'))
            res.append({
                'lot'      : lot,
                'qt_pieces': qt_pieces,
                'stock'    : stock,
            })
        return res


    @api.depends('num_eti', 'active', 'location_id', 'location_id.usage')
    def _compute_doublon(self):
        for obj in self:
            doublon = False
            if obj.num_eti and obj.active and obj.location_id.usage=='internal':
                domain = [
                    ('num_eti','=',obj.num_eti),
                    ('id','!=',obj._origin.id),
                    ('active','=',True),
                    ('location_id.usage','=','internal'),
                ]
                doublon = bool(self.search_count(domain))
            obj.doublon = doublon


    def _recompute_doublon_num_eti(self, num_etis):
        # Recalcule le champ 'doublon' de toutes les UC partageant l'un de ces num_eti.
        # Nécessaire car le calcul dépend d'autres enregistrements (recherche de
        # doublons), ce qu'Odoo ne peut pas suivre automatiquement via @api.depends.
        num_etis = [n for n in num_etis if n]
        if not num_etis:
            return
        records = self.with_context(active_test=False).search([('num_eti','in', num_etis)])
        if records:
            records._compute_doublon()


    @api.onchange('lot_ids')
    def onchange_lot_ids(self):
        if self.lot_ids:
            self.lot_id = False


    def _effacer_lot_si_tableau(self):
        # Le champ 'lot_id' est réservé au cas d'un seul lot : il est effacé si le tableau des lots est renseigné
        ucs = self.filtered(lambda uc: uc.lot_ids and uc.lot_id)
        if ucs:
            ucs.write({'lot_id': False})


    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._recompute_doublon_num_eti(records.mapped('num_eti'))
        records._effacer_lot_si_tableau()
        return records


    def write(self, vals):
        need_recompute = 'active' in vals or 'um_id' in vals or 'num_eti' in vals
        num_etis = self.mapped('num_eti') if need_recompute else []
        res = super().write(vals)
        if need_recompute:
            self._recompute_doublon_num_eti(num_etis + self.mapped('num_eti'))
        if 'lot_id' in vals or 'lot_ids' in vals:
            self._effacer_lot_si_tableau()
        return res


    def unlink(self):
        num_etis = self.mapped('num_eti')
        res = super().unlink()
        self._recompute_doublon_num_eti(num_etis)
        return res


    def recalculer_doublon_action(self):
        self._recompute_doublon_num_eti(self.mapped('num_eti'))


    def retrouver_lot_action(self):
        "Retrouve le lot à partir du champ Fabrication"
        nb = len(self)
        for ct, obj in enumerate(self, 1):
            _logger.info("retrouver_lot_action : %s/%s - UC N°%s"%(ct, nb, obj.num_eti))
            if not obj.production or obj.lot_id or obj.lot_ids:
                continue
            productions = self.env['mrp.production'].search([('name','=',obj.production)], limit=1)
            if not productions and obj.product_id.is_fournisseur_id:
                #** Article acheté : recherche par le lot fournisseur, en priorité le lot ayant du stock dans l'emplacement de l'UC, sinon le plus récent
                lots = self.env['stock.lot'].search([('is_lot_fournisseur','=',obj.production),('product_id','=',obj.product_id.id)], order='id desc')
                if len(lots)>1 and obj.location_id:
                    quants = self.env['stock.quant'].search([('lot_id','in',lots.ids),('location_id','=',obj.location_id.id),('quantity','>',0)])
                    if quants:
                        lots = quants.lot_id.sorted('id', reverse=True)
                lots = lots[:1]
            else:
                lots = self.env['stock.lot'].search([('name','=',obj.production),('product_id','=',obj.product_id.id)], limit=1)
            if lots:
                obj.lot_id = lots.id


    def etiquette_remplacee_action(self):
        for obj in self:
            obj.etiquette_remplacee_le = datetime.now()
        return []


    def acceder_uc_action(self):
        for obj in self:
            return {
                'name': "Etiquettes UC",
                'view_mode': 'form',
                'res_model': 'is.galia.base.uc',
                'type': 'ir.actions.act_window',
                'res_id': obj.id,
                'domain': '[]',
            }


    def mettre_um_client_action(self):
        self.um_id.actualiser_emplacement_um_client_sans_restriction_action()


    def picking_um_action(self):
        # Action du menu : met les UC sélectionnées dans une nouvelle UM
        if not self:
            return True
        um_dest_id = self.picking_um()
        return {
            'name'     : "Etiquettes UM",
            'view_mode': 'form',
            'res_model': 'is.galia.base.um',
            'type'     : 'ir.actions.act_window',
            'res_id'   : um_dest_id,
        }


    def picking_um(self, um_dest_id=False, liste_servir_id=False):
        # Retire les UC de leurs UM et les met toutes dans l'UM de destination
        # (créée si um_dest_id n'est pas fourni, et associée à la liste à servir
        # liste_servir_id si fournie). Retourne l'id de l'UM de destination.
        # Appelée aussi depuis scan-exp (picking-um.php) en XML-RPC.
        if not self:
            raise ValidationError("Aucune UC à déplacer")
        ums = self.um_id
        um_dest     = self.env['is.galia.base.um'].browse(um_dest_id) if um_dest_id else False
        liste_servir = self.env['is.liste.servir'].browse(liste_servir_id) if liste_servir_id else (um_dest and um_dest.liste_servir_id)
        if um_dest and um_dest in ums:
            raise ValidationError("Les UC sont déjà dans l'UM %s"%um_dest.name)
        for um in ums:
            if not um.active:
                raise ValidationError("Picking impossible car l'UM %s est archivée"%um.name)
            if um.location_id.usage!='internal':
                raise ValidationError("Picking impossible car l'UM %s n'est pas dans un emplacement interne (%s)"%(um.name, um.location_id.name or 'aucun emplacement'))
            if um.liste_servir_id:
                raise ValidationError("Picking impossible car l'UM %s est associée à la liste à servir %s"%(um.name, um.liste_servir_id.name))
            if um.bon_transfert_id:
                raise ValidationError("Picking impossible car l'UM %s est associée au bon de transfert %s"%(um.name, um.bon_transfert_id.name))
        if um_dest and not um_dest.active:
            raise ValidationError("Picking impossible car l'UM de destination %s est archivée"%um_dest.name)
        locations = ums.location_id | (um_dest.location_id if um_dest else self.env['stock.location'])
        if len(locations)>1:
            raise ValidationError("Picking impossible car les UM ne sont pas toutes dans le même emplacement (%s)"%', '.join(locations.mapped('name')))
        products_um_uc = self.product_id.filtered(lambda p: p.is_um_egale_uc)
        if products_um_uc:
            raise ValidationError("Picking impossible car ces articles sont de type UM=UC : %s"%', '.join(products_um_uc.mapped('is_code')))
        if liste_servir:
            products_hors_ls = self.product_id - liste_servir.line_ids.product_id
            if products_hors_ls:
                raise ValidationError("Picking impossible car ces articles ne sont pas sur la liste à servir %s : %s"%(liste_servir.name, ', '.join(products_hors_ls.mapped('is_code'))))
        creation = not um_dest
        if creation:
            um_dest = self.env['is.galia.base.um'].create({
                'mixte'          : 'non',
                'location_id'    : ums.location_id.id,
                'production_id'  : ums.production_id.id if len(ums.production_id)==1 else False,
                'liste_servir_id': liste_servir.id if liste_servir else False,
            })
        lien_um     = Markup('<a href="#" data-oe-model="is.galia.base.um" data-oe-id="%s">%s</a>')
        lien_um_new = lien_um%(um_dest.id, um_dest.name)
        lignes = []
        for um in ums:
            ucs         = self.filtered(lambda uc: uc.um_id==um)
            num_etis    = ', '.join(str(uc.num_eti) for uc in ucs.sorted('num_eti'))
            lien_um_old = lien_um%(um.id, um.name)
            ucs.write({'um_id': um_dest.id})
            um.message_post(body=Markup("Picking : %s UC retirées (%s) et mises dans l'UM %s")%(len(ucs), num_etis, lien_um_new))
            if not self.search_count([('um_id','=',um.id)]):
                um.message_post(body="Picking : UM archivée car elle ne contient plus d'UC")
                um.active = False
            for uc in ucs:
                uc.message_post(body=Markup("Picking : UC déplacée de l'UM %s vers l'UM %s")%(lien_um_old, lien_um_new))
            lignes.append(Markup("<li>%s UC (%s) retirées de l'UM %s</li>")%(len(ucs), num_etis, lien_um_old))
        if len(um_dest.uc_ids.product_id)>1 and um_dest.mixte!='oui':
            um_dest.mixte = 'oui'
        titre = "Picking : UM créée avec %s UC :" if creation else "Picking : ajout de %s UC :"
        um_dest.message_post(body=Markup(titre+"<ul>%s</ul>")%(len(self), Markup('').join(lignes)))
        return um_dest.id


    # def archiver_sur_stock_action(self):
    #     date_limite = datetime.now() - relativedelta(months=1)
    #     total = len(self)
    #     for i, obj in enumerate(self, start=1):
    #         if obj.date_creation > date_limite:
    #             continue
    #         if obj.product_id.qty_available == 0:
    #             msg = "%s/%s : UC %s archivée automatiquement car le stock de l'article %s est à 0."%(i, total, obj.num_eti, obj.product_id.is_code)
    #             obj.message_post(body=msg)
    #             _logger.info(msg)
    #             obj.active = False


    def imprimer_etiquette_uc_action(self):
        user = self.env['res.users'].browse(self._uid)
        company = self.env.company
        DB        = company.is_nom_base_odoo0
        USERID    = 2
        DBLOGIN   = company.is_login_admin
        USERPASS  = company.is_mdp_admin
        URL       = company.is_url_odoo0 
        sock = xmlrpclib.ServerProxy('%s/xmlrpc/2/object'%URL)
        for obj in self:
            #** Retrouver la société de l'étiquette ***************************
            Soc=False
            domain=[('num_eti','=',obj.num_eti)]
            try:
                lines=sock.execute_kw(DB, USERID, USERPASS, 'is.galia.base', 'search_read', [domain], {'fields': ['num_eti', 'soc'], 'limit': 3, 'order': 'id desc'})
            except:
                msg="Problème de connexion sur %s ou sur la base %s"%(URL,DB)
                raise ValidationError(msg)
            for line in lines:
                Soc=line.get('soc')
            if not Soc:
                msg="Etiquette %s non trouvée dans Odoo 0"%obj.num_eti
                raise ValidationError(msg)
            #******************************************************************
            vals={
                'ACTION'      : 'OK', 
                'Soc'         : Soc, 
                'Etiquette'   : obj.type_eti, 
                'Imprimante'  : 'ZPL', 
                'zzCode'      : obj.production, 
                'zzDebut'     : obj.num_carton, 
                'zzFin'       : obj.num_carton, 
                'zzNbPieces'  : obj.qt_pieces, 
                'zzMDP1'      : company.is_mdp_quantite,
                'zzMDP2'      : company.is_mdp_reimprimer, 
                'zzValidation': 'OK', 
                'zzAction'    : 'Imprimer', 
                'user_name'   : user.name,
            }
            
            # Écrire dans le chatter le contenu de vals
            message = "Impression étiquette UC avec les paramètres suivants :<br/>"
            for key, value in vals.items():
                # Ne pas afficher les mots de passe
                if 'MDP' not in key:
                    message += f"<b>{key}</b> : {value}<br/>"


            #message += "uc_id=%s<br/>"%obj.id
            message += "UC=%s<br/>"%obj.num_eti
            message += "UM=%s<br/>"%obj.um_id.name
            message += "Liste à servir=%s<br/>"%obj.um_id.liste_servir_id.name

            obj.message_post(body=message)
            
            try:
                res = sock.execute_kw(DB, USERID, USERPASS, 'is.galia.base', 'creer_etiquette', [[0], vals])
            except:
                msg="Problème de connexion sur %s ou sur la base %s"%(URL,DB)
                raise ValidationError(msg)
            if 'Msg' in res:
                if res['Msg']!='':
                    raise ValidationError(res['Msg'])
            ZPL = res.get('ZPL')
            self.env['is.galia.base'].imprimer_zpl(ZPL)
            return True


class is_galia_base_uc_lot(models.Model):
    _name='is.galia.base.uc.lot'
    _description="Lots des étiquettes Galia UC"
    _order='uc_id,id'

    uc_id     = fields.Many2one('is.galia.base.uc', 'UC', required=True, ondelete='cascade', index=True)
    lot_id    = fields.Many2one('stock.lot', 'Lot', required=True)
    qt_pieces = fields.Integer("Quantité", required=True)


    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.uc_id._effacer_lot_si_tableau()
        return records
