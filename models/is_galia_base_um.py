# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools # type: ignore
from odoo.exceptions import ValidationError  # type: ignore
from markupsafe import Markup
import os
import logging
_logger = logging.getLogger(__name__)

_MIXTE=[
    ('oui', 'Oui'),
    ('non', 'Non'),
]


class is_galia_base_um(models.Model):
    _name='is.galia.base.um'
    _description="Etiquettes Galia UM"
    _order='name desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _sql_constraints = [('name_uniq','UNIQUE(name)', u'Cette étiquette UM existe déjà')]

    @api.depends('uc_ids')
    def _compute(self):
        for obj in self:
            qt_pieces  = 0
            product_id = False
            if obj.mixte=='non':
                for line in obj.uc_ids:
                    qt_pieces += line.qt_pieces
                    product_id = line.product_id
            obj.product_id = product_id
            obj.qt_pieces  = qt_pieces
            premiere_uc = obj.uc_ids[:1]
            obj.etiquette_um_a5 = bool(premiere_uc.product_id.product_tmpl_id.is_type_etiquette_um_id)
            obj.nb_uc = len(obj.uc_ids)

    name             = fields.Char("N°Étiquette UM", readonly=True             , index=True, tracking=True)
    mixte            = fields.Selection(_MIXTE, "UM mixte", default='non', required=True, tracking=True)
    liste_servir_id  = fields.Many2one('is.liste.servir', 'Liste à servir'     , index=True, tracking=True)
    bon_transfert_id = fields.Many2one('is.bon.transfert', 'Bon de transfert'  , index=True, tracking=True)
    production_id    = fields.Many2one('mrp.production', 'Ordre de fabrication', index=True, tracking=True)
    location_id      = fields.Many2one('stock.location', 'Emplacement actuel'  , index=True, domain=[("usage","=","internal")], default=lambda self: self._get_location_id(), tracking=True)
    location_dest_id = fields.Many2one('stock.location', 'Emplacement de destination'      , domain=[("usage","=","internal")], tracking=True)
    uc_ids           = fields.One2many('is.galia.base.uc'  , 'um_id', "UCs")
    product_id       = fields.Many2one('product.product', 'Article', readonly=True, compute='_compute', store=False)
    qt_pieces        = fields.Integer("Qt Pièces"                  , readonly=True, compute='_compute', store=False)
    etiquette_um_a5  = fields.Boolean("Étiquette UM A5", readonly=True, compute='_compute', store=False)
    nb_uc            = fields.Integer("Nb UC", readonly=True, compute='_compute', store=False)
    employee_id      = fields.Many2one("hr.employee", "Employé", tracking=True)
    date_fin         = fields.Datetime("Date fin UM", tracking=True, help="Renseignée par le bouton 'Fin UM' de la presse (THEIA), qui imprime l'étiquette UM. Tant qu'elle est vide, l'UM est l'UM en cours de l'OF et reçoit les UC scannées ; ensuite, une nouvelle UM est créée.")
    active           = fields.Boolean("Active", default=True, copy=False, index=True, tracking=True)
    date_ctrl_rcp    = fields.Datetime("Date contrôle réception", tracking=True)
    information      = fields.Text("Information", readonly=True, compute='_compute_information_anomalie', store=False)
    anomalie         = fields.Text("Anomalie"   , readonly=True, compute='_compute_information_anomalie', store=False)
    emplacement_pi   = fields.Boolean("Emplacement PI", compute='_compute_emplacement_pi', store=False)
    creer_um_homogenes_vsb = fields.Boolean("Créer les UM homogènes visible", compute='_compute_creer_um_homogenes_vsb', store=False)
    date_preparation_reintegration_pi = fields.Datetime("Date préparation ré-intégration PI", copy=False, index=True, tracking=True, help="Renseignée lors de la réintégration PI vers ATELIER. Tant que la date effective est vide, l'UM est reprise au premier scan d'UC du même article sur une presse, au lieu de créer une nouvelle UM.")
    date_effective_reintegration_pi   = fields.Datetime("Date effective ré-intégration PI"  , copy=False, index=True, tracking=True, help="Renseignée par la presse lors de la reprise de l'UM : elle est rattachée au nouvel OF et rouverte pour recevoir les UC suivantes.")


    @api.model
    def creer_um_theia(self, vals):
        "Création d'une UM depuis THEIA (XML-RPC) avec l'utilisateur Odoo de l'employé qui a scanné son badge. Retourne l'id de l'UM"
        model_uc, employee = self.env['is.galia.base.uc']._env_employe(vals.get('employee_id'))
        um = self.with_env(model_uc.env).create(vals)
        if employee:
            um.message_post(body="UM créée sur la presse par l'employé %s"%employee.name)
        return um.id


    @api.model
    def fin_um_theia(self, production_id, employee_id):
        "Bouton 'Fin UM' de THEIA (XML-RPC) : termine les UM en cours de l'OF avec l'utilisateur Odoo de l'employé. Retourne le nombre d'UM terminées"
        model_uc, employee = self.env['is.galia.base.uc']._env_employe(employee_id)
        ums = self.with_env(model_uc.env).with_context(active_test=False).search([('production_id','=',int(production_id)),('date_fin','=',False)])
        ums.write({'date_fin': fields.Datetime.now(), 'employee_id': employee.id or False})
        if employee:
            for um in ums:
                um.message_post(body="UM terminée sur la presse par l'employé %s"%employee.name)
        return len(ums)


    def _get_cle_lot(self, uc, lot):
        "Clé de regroupement article / lot (nom du lot, sinon Fabrication si le lot n'est pas trouvé)"
        return "%s-%s"%(uc.product_id.is_code, lot.name if lot else (uc.production or ''))


    def get_qt_par_lot(self):
        for obj in self:
            #** Recherche des quantités par article et par lot ****************
            #** (lots des UC : tableau des lots, champ Lot ou Fabrication)    **
            mydict={}
            for uc in obj.uc_ids:
                for lot,qt_pieces in uc.get_lots():
                    key=obj._get_cle_lot(uc, lot)
                    if key not in mydict:
                        mydict[key]={
                            'product'   : uc.product_id,
                            'production': lot.name if lot else uc.production,
                            'lot_id'    : lot.id or False,
                            'qt_pieces' : 0
                        }
                    mydict[key]['qt_pieces']+=qt_pieces
            sorted_dict = dict(sorted(mydict.items()))
            #******************************************************************

            for key in sorted_dict:
                vals=sorted_dict[key]
                lot_id=vals['lot_id']

                #** Recherche du stock ****************************************
                domain=[
                    ('product_id' ,'=',vals['product'].id),
                    ('location_id','=',obj.location_id.id),
                    ('lot_id'     ,'=',lot_id),
                ]
                quants=self.env['stock.quant'].search(domain)
                stock=0
                for quant in quants:
                    stock+=quant.quantity
                vals['stock'] = stock
                #**************************************************************
            return sorted_dict


    @api.depends('location_id','uc_ids')
    def _compute_information_anomalie(self):
        for obj in self:
            information=[]
            anomalie = []
            if obj.location_id.usage=='customer':
                obj.information = False
                obj.anomalie    = False
                continue
            sorted_dict = obj.get_qt_par_lot()
            for key in sorted_dict:
                vals=sorted_dict[key]
                msg="%s : %s : lot_id=%s : Qt UM=%s : Stock=%s"%(
                    vals['product'].is_code.ljust(8),
                    (vals['production'] or '').ljust(8),
                    str(vals['lot_id']).ljust(8),
                    str(int(vals['qt_pieces'])).ljust(4),
                    int(vals['stock'])
                )
                if vals['qt_pieces']<=vals['stock']:
                    information.append(msg)
                else:
                    anomalie.append(msg)
            obj.information = (len(information) and '\n'.join(information)) or False
            obj.anomalie    = (len(anomalie)    and '\n'.join(anomalie)) or False


    def deplacer_um_action(self):
        for obj in self:
            if obj.anomalie:
                raise ValidationError("Déplacement impossible car stock non disponible dans emplacement '%s':\n%s"%(obj.location_id.name,obj.anomalie))
            sorted_dict = obj.get_qt_par_lot()
            #** Vérification que les lots des UC sont disponibles en stock ****
            for key in sorted_dict:
                vals = sorted_dict[key]
                if not vals['lot_id']:
                    raise ValidationError("Déplacement impossible car le lot %s n'existe pas pour l'article %s"%(vals['production'] or '',vals['product'].is_code))
                if vals['stock']<vals['qt_pieces']:
                    raise ValidationError("Déplacement impossible car stock insuffisant dans l'emplacement '%s' pour l'article %s et le lot %s : Stock=%s < Qt UM=%s"%(obj.location_id.name,vals['product'].is_code,vals['production'],vals['stock'],vals['qt_pieces']))
            #******************************************************************
            location_src  = obj.location_id
            location_dest = obj.location_dest_id
            moves={}
            for key in sorted_dict:
                product = sorted_dict[key]['product']
                qty     = sorted_dict[key]['qt_pieces']
                lot_id  = sorted_dict[key]['lot_id']
                name="UM %s"%obj.name
                vals={
                    "product_id": product.id,
                    "product_uom": product.uom_id.id,
                    "location_id": obj.location_id.id,
                    "location_dest_id": obj.location_dest_id.id,
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
                    "location_dest_id": obj.location_dest_id.id,
                    "lot_id": lot_id,
                    "qty_done": qty,
                    "reference": name,
                }
                move_line=self.env['stock.move.line'].create(vals)
                move._action_done()
                moves[key]=move
            obj.location_id = obj.location_dest_id.id
            obj.location_dest_id = False

            #** Traçabilité dans le chatter de l'UM et des UC *****************
            def lien_move(move):
                return Markup('<a href="#" data-oe-model="stock.move" data-oe-id="%s">%s</a>')%(move.id,move.id)
            lignes=[]
            for key in sorted_dict:
                vals = sorted_dict[key]
                lignes.append(Markup('<li>%s : %s pièces du lot %s (mouvement %s)</li>')%(vals['product'].is_code,int(vals['qt_pieces']),vals['production'],lien_move(moves[key])))
            msg=Markup('Déplacement de l\'UM de %s vers %s :<ul>%s</ul>')%(location_src.name,location_dest.name,Markup('').join(lignes))
            obj.message_post(body=msg)
            for uc in obj.uc_ids:
                for lot,qt_pieces in uc.get_lots():
                    key=obj._get_cle_lot(uc, lot)
                    msg=Markup('Déplacement avec l\'UM %s de %s vers %s : %s pièces du lot %s (mouvement %s)')%(obj.name,location_src.name,location_dest.name,qt_pieces,sorted_dict[key]['production'],lien_move(moves[key]))
                    uc.message_post(body=msg)
            #******************************************************************
            return True


    # def archiver_sur_stock_action(self):
    #     date_limite = datetime.now() - relativedelta(months=1)
    #     filtre = [
    #         #('name' , '=', 'Inventaire'),
    #         ('usage', '=', 'inventory'),
    #     ]
    #     lines = self.env["stock.location"].search(filtre)
    #     location_inventaire_id = lines and lines[0].id or False
    #     total = len(self)
    #     for i, obj in enumerate(self, start=1):
    #         if obj.create_date > date_limite:
    #             continue
    #         if obj.location_id and obj.location_id.usage != 'internal':
    #             continue
    #         if not obj.uc_ids:
    #             msg = "%s/%s : UM %s archivée automatiquement car elle n'a plus d'UC active."%(i, total, obj.name)
    #             obj.location_id = location_inventaire_id
    #             obj.message_post(body=msg)
    #             _logger.info(msg)
    #             obj.active = False


    def _get_location_id(self):
        filtre = [
            ('name' , '=', 'ATELIER'),
            ('usage', '=', 'internal'),
        ]
        lines = self.env["stock.location"].search(filtre)
        location_id = lines and lines[0].id or False
        return location_id


    @api.depends('location_id')
    def _compute_emplacement_pi(self):
        for obj in self:
            obj.emplacement_pi = obj.location_id.name=='PI' and obj.location_id.usage=='internal'


    @api.depends('active','mixte','location_id','uc_ids')
    def _compute_creer_um_homogenes_vsb(self):
        for obj in self:
            obj.creer_um_homogenes_vsb = obj.active and obj.mixte=='oui' and obj.location_id.usage=='internal' and bool(obj.uc_ids)


    def creer_um_homogenes_action(self):
        # Répartit les UC de l'UM mixte dans une nouvelle UM par article (même emplacement, donc sans mouvement de stock),
        # puis archive l'UM mixte vidée et la met dans INV. Les autres contrôles (liste à servir, bon de transfert,
        # articles UM=UC...) sont ceux de picking_um
        lien_um = Markup('<a href="#" data-oe-model="is.galia.base.um" data-oe-id="%s">%s</a>')
        ums = self.env['is.galia.base.um']
        for obj in self:
            if not obj.creer_um_homogenes_vsb:
                raise ValidationError("L'UM %s doit être active, mixte, en stock et contenir des UC"%obj.name)
            ums_obj = self.env['is.galia.base.um']
            for product in obj.uc_ids.product_id.sorted('is_code'):
                ucs = obj.uc_ids.filtered(lambda uc: uc.product_id==product)
                um  = self.browse(ucs.picking_um())
                # Date de fin renseignée : sinon THEIA prendrait cette UM pour l'UM en cours de son OF
                um.date_fin = fields.Datetime.now()
                um.message_post(body=Markup("UM homogène créée à partir de l'UM mixte %s")%(lien_um%(obj.id, obj.name)))
                ums_obj |= um
            obj.message_post(body=Markup("UM mixte remplacée par les UM homogènes : %s")%Markup(', ').join(lien_um%(um.id, um.name) for um in ums_obj))
            obj.mettre_um_archivee_dans_inv_action()
            ums |= ums_obj
        return {
            'name'     : "UM homogènes",
            'view_mode': 'tree,form',
            'res_model': 'is.galia.base.um',
            'type'     : 'ir.actions.act_window',
            'domain'   : [('id','in',ums.ids)],
        }


    def reintegrer_pi_production_action(self):
        # Déplace l'UM et le stock de ses UC de PI vers ATELIER
        atelier_id = self._get_location_id()
        if not atelier_id:
            raise ValidationError("Emplacement ATELIER non trouvé")
        for obj in self:
            if not obj.active:
                raise ValidationError("Réintégration impossible car l'UM %s est archivée"%obj.name)
            if not obj.emplacement_pi:
                raise ValidationError("Réintégration impossible car l'UM %s n'est pas dans l'emplacement PI (emplacement actuel : %s)"%(obj.name,obj.location_id.name or 'aucun'))
            if obj.mixte!='non':
                raise ValidationError("Réintégration impossible car l'UM %s est mixte"%obj.name)
            if obj.liste_servir_id:
                raise ValidationError("Réintégration impossible car l'UM %s est dans la liste à servir %s"%(obj.name,obj.liste_servir_id.name))
            if obj.bon_transfert_id:
                raise ValidationError("Réintégration impossible car l'UM %s est dans le bon de transfert %s"%(obj.name,obj.bon_transfert_id.name))
            if not obj.uc_ids:
                raise ValidationError("Réintégration impossible car l'UM %s ne contient aucune UC"%obj.name)
            obj.location_dest_id = atelier_id
            obj.deplacer_um_action()
            # UM en attente d'être complétée par le premier scan d'UC sur une presse (THEIA), qui la rouvrira
            # (date effective vidée si l'UM avait déjà été réintégrée une première fois : l'historique reste dans le chatter)
            obj.write({
                'date_preparation_reintegration_pi': fields.Datetime.now(),
                'date_effective_reintegration_pi'  : False,
            })
        return True


    def actualiser_emplacement_um_action(self):
        # Bascule chaque UM vers l'emplacement Client dès que toutes ses UC sont livrées,
        # et archive les UC en doublon (même num_eti) trouvées sur d'autres UM.
        self._actualiser_emplacement_um(verifier_livraison=True)


    def actualiser_emplacement_um_sans_livraison_action(self):
        # Comme actualiser_emplacement_um_action, mais sans vérifier que les UC sont
        # livrées : il suffit que l'UM soit affectée à une liste à servir ou un bon
        # de transfert pour être basculée dans l'emplacement Client.
        self._actualiser_emplacement_um(verifier_livraison=False)


    def actualiser_emplacement_um_client_sans_restriction_action(self):
        # Force le basculement de l'UM dans l'emplacement Client, sans aucune
        # vérification (ni UC livrées, ni liste à servir/bon de transfert).
        self._actualiser_emplacement_um(verifier_livraison=False, sans_restriction=True)


    def mettre_um_archivee_dans_inv_action(self):
        # Sort du stock les UM archivées restées dans un emplacement interne (et leurs UC, dont l'emplacement suit
        # celui de l'UM) en les mettant dans l'emplacement d'inventaire INV. Les UM actives sont ignorées
        location_inv = self.env["stock.location"].search([('name','=','INV'),('usage','=','inventory')], limit=1)
        if not location_inv:
            raise ValidationError("Emplacement 'INV' de type 'Inventaire' non trouvé.")
        ums = self.filtered(lambda um: not um.active and um.location_id.usage=='internal')
        total = len(ums)
        for i, obj in enumerate(ums, start=1):
            msg = "UM archivée déplacée de l'emplacement %s vers %s pour la sortir du stock."%(obj.location_id.name, location_inv.name)
            _logger.info("%s/%s : UM %s : %s"%(i, total, obj.name, msg))
            obj.message_post(body=msg)
            obj.location_id = location_inv.id
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': "UM archivées dans 'INV'",
                'message': "%s UM déplacée(s) dans INV, %s ignorée(s) (actives ou pas dans un emplacement interne)"%(total, len(self)-total),
                'type': 'success' if total else 'warning',
                'sticky': False,
            },
        }


    def _actualiser_emplacement_um(self, verifier_livraison, sans_restriction=False):
        lines = self.env["stock.location"].search([('usage','=','customer')], limit=1)
        location_client_id = lines and lines[0].id or False
        if not location_client_id:
            raise ValidationError("Aucun emplacement de type 'Client' n'a été trouvé.")
        total = len(self)
        for i, obj in enumerate(self, start=1):
            if obj.location_id.id==location_client_id:
                continue
            if sans_restriction:
                raison = "l'emplacement a été forcé sans restriction"
            elif verifier_livraison:
                if not obj.uc_ids or not all(uc.stock_move_id and uc.stock_move_id.state=='done' for uc in obj.uc_ids):
                    continue
                raison = "toutes ses UC sont livrées"
            else:
                if not (obj.liste_servir_id or obj.bon_transfert_id):
                    continue
                raison = "elle est affectée à une liste à servir ou un bon de transfert"

            msg = "UM %s déplacée dans l'emplacement Client car %s."%(obj.name, raison)
            obj.message_post(body=msg)
            _logger.info("%s/%s : %s"%(i, total, msg))
            obj.location_id = location_client_id

            if obj.uc_ids:
                doublons = self.env['is.galia.base.uc'].search([
                    ('num_eti','in', obj.uc_ids.mapped('num_eti')),
                    ('um_id','!=', obj.id),
                ])
                if doublons:
                    details = ', '.join("UC %s (UM %s)"%(uc.num_eti, uc.um_id.name) for uc in doublons)
                    _logger.info("UM %s : archivage des UC en doublon : %s"%(obj.name, details))
                    for doublon in doublons:
                        doublon.message_post(body="UC archivée automatiquement : doublon avec l'UC %s de l'UM %s."%(doublon.num_eti, obj.name))
                    doublons.active = False


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Utiliser la séquence uniquement si le name n'est pas déjà fourni
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('is.galia.base.um')
        return super().create(vals_list)


    def write(self, vals):
        need_recompute = 'location_id' in vals
        num_etis = self.uc_ids.mapped('num_eti') if need_recompute else []
        res = super().write(vals)
        if need_recompute:
            self.env['is.galia.base.uc']._recompute_doublon_num_eti(num_etis)
        return res


    @api.onchange('liste_servir_id')
    def onchange_liste_servir_id(self):
        location_id = self.liste_servir_id.is_source_location_id.id
        if location_id:
            self.location_id = location_id


    @api.onchange('bon_transfert_id')
    def onchange_bon_transfert_id(self):
        location_id = self.bon_transfert_id.location_id.id
        if location_id:
            self.location_id = location_id


    @api.onchange('production_id')
    def onchange_production_id(self):
        location_id = self.production_id.location_dest_id.id
        if location_id:
            self.location_id = location_id


    def acceder_um_action(self):
        view_id = self.env.ref('is_plastigray16.is_galia_base_um_form_view').id
        for obj in self:
            return {
                'name': "Etiquettes UM",
                'view_mode': 'form',
                'view_id': view_id,
                'res_model': 'is.galia.base.um',
                'type': 'ir.actions.act_window',
                'res_id': obj.id,
                'domain': '[]',
            }


    def voir_uc_action(self):
        for obj in self:
            res= {
                'name': obj.name,
                'view_mode': 'tree,form',
                'res_model': 'is.galia.base.uc',
                'type': 'ir.actions.act_window',
                'domain': [('um_id','=',obj.id)],
            }
            return res


    def imprimer_etiquette_um_action(self):
        for obj in self : 
            cdes = self.env['is.commande.externe'].search([('name','=',"imprimer-etiquette-um")])
            for cde in cdes:
                model=self._name
                uid=self._uid
                user=self.env['res.users'].browse(uid)
                soc=user.company_id.partner_id.is_code
                x = cde.commande
                x = x.replace("#soc"  , soc)
                x = x.replace("#um_id", str(obj.id))
                x = x.replace("#uid"  , str(uid))
                
                # Écrire dans le chatter le contenu de la commande
                message = "Impression étiquette UM avec les paramètres suivants :<br/>"
                message += f"<b>Société</b> : {soc}<br/>"
                message += f"<b>UM ID</b> : {obj.id}<br/>"
                message += f"<b>Utilisateur ID</b> : {uid}<br/>"
                message += f"<b>Utilisateur</b> : {user.name}<br/>"
                message += f"<b>Commande</b> : {x}<br/>"
                obj.message_post(body=message)
                
                _logger.info(x)
                lines=os.popen(x).readlines()
                for line in lines:
                    _logger.info(line.strip())


    def imprimer_etiquette_um_a5(self, imprimante=False):
        # Balises ZPL utilisées :
        # ^XA : début du format d'étiquette
        # ^CI28 : encodage UTF-8, pour les caractères accentués
        # ^PW : largeur de l'étiquette (en dots)
        # ^LL : longueur/hauteur de l'étiquette (en dots)
        # ^FO : position (x,y) de l'élément qui suit, depuis le coin haut-gauche
        # ^GB : dessine un cadre/une ligne (largeur, hauteur, épaisseur du trait)
        # ^A0R : police utilisée pour le texte qui suit (hauteur, largeur des caractères), tournée à 90°
        # ^FD : donnée (texte) à afficher
        # ^FS : fin de l'élément
        # ~DG : télécharge un graphique (logo Sécu) en mémoire imprimante
        # ^XG : rappelle un graphique déjà téléchargé en mémoire (position, facteurs d'agrandissement x/y)
        # ^BY : épaisseur/ratio des modules du code-barre qui suit
        # ^B3 : dessine un code-barre Code 39 (orientation, checksum, hauteur, ligne de lecture...)
        # ^XZ : fin du format d'étiquette
        #
        # Comme pour l'étiquette UC (Uc2.zpl) et l'étiquette UM actuelle (qui recharge le même format 'UC'),
        # toute l'étiquette est dessinée tournée à 90° (^A0R) : le logo Secu.grf, qui n'est jamais tourné
        # lui-même, s'affiche alors dans le bon sens une fois l'étiquette physiquement tournée à la lecture.

        # Imprimante Zebra 300dpi => 300/25.4 dots par mm
        #DOTS_PAR_MM = 300/25.4
        DOTS_PAR_MM = 300/25 # Pour grossir un peu

        def mm(valeur_mm):
            return round(valeur_mm*DOTS_PAR_MM)

        # Toutes les dimensions ci-dessous sont exprimées en mm, dans le repère logique
        # non tourné (0,0)=haut-gauche, x vers la droite, y vers le bas, comme un plan classique.
        LARGEUR  = 210  # Largeur étiquette (A5 paysage)
        HAUTEUR  = 148  # Hauteur étiquette (A5 paysage)
        EPAISSEUR = 3   # Epaisseur des traits, en dots
        TAILLE_POLICE       = 3 # Hauteur/largeur des caractères des labels
        TAILLE_POLICE_5MM   = 5 # Hauteur/largeur des caractères des valeurs, en 5mm
        TAILLE_POLICE_7MM   = 7 # Hauteur/largeur des caractères des valeurs, en 7mm
        TAILLE_POLICE_13MM  = 13 # Hauteur/largeur des caractères des valeurs, en 13mm
        MARGE_TEXTE_GAUCHE  = 2 # Marge ajoutée devant les labels de la colonne de gauche
        DECALAGE_TEXTE      = 8 # Décalage des labels, en dots (1pt vers le bas et vers la droite)
        ESPACE_LABEL_VALEUR = 1 # Espace minimum entre le label et sa valeur, en mm

        # Rotation 90° de tout le plan logique (x,y) vers le repère physique de l'étiquette,
        # pour que le texte ^A0R se lise de haut en bas comme sur l'étiquette UC.
        # taille_police : pour le texte (^A0R), l'ancre déborde vers la cellule au-dessus si on
        # ne décale pas d'une hauteur de caractère ; laisser à 0 pour les lignes (^GB).
        def FO(x, y, taille_police=0):
            decalage = DECALAGE_TEXTE if taille_police else 0 # Uniquement pour le texte, pas pour les lignes (^GB)
            px = mm(HAUTEUR-y-taille_police)-decalage # -decalage : vers la gauche, pour ne pas coller à la ligne
            py = mm(x)+decalage                       # +decalage : vers le bas, pour ne pas coller à la ligne
            return "^FO%s,%s"%(px, py)

        # Logo Sécu (case vide entre les poids et le Produit, colonne de droite)
        # NB : avec FO(x,y), c'est y qui pilote la position horizontale à l'écran et x la position
        # verticale (le texte tourné ^A0R inverse les deux par rapport à une lecture non tournée).
        LOGO_SECU_MAGNIFICATION = 1 # ^XG n'accepte que des facteurs entiers (1,2,3...)
        LOGO_SECU_TAILLE = 22*LOGO_SECU_MAGNIFICATION # Taille du logo (256 dots ≈ 22mm à l'échelle 1), pour ne pas déborder dans la cellule au-dessus, comme le texte
        LOGO_SECU_Y = 46+((76-46)-LOGO_SECU_TAILLE)/2 # Centré horizontalement (à l'écran) dans la ligne 46-76
        LOGO_SECU_X = 210-LOGO_SECU_TAILLE-TAILLE_POLICE_7MM-2 # Proche du bas (à l'écran), en laissant la place aux lettres R/S juste après
        LOGO_SECU_LETTRE_X = LOGO_SECU_X+LOGO_SECU_TAILLE # Lettres R/S affichées juste après le logo (à l'écran)

        # Contenu du graphique Secu.grf (logo sécurité), envoyé une fois en mémoire imprimante
        addons_path = tools.config['addons_path'].split(',')[1]
        path = "%s/is_plastigray16/static/src/galia/"%addons_path
        SECU_GRF = open(path+'Secu.grf','rb').read().decode("utf-8")
        SECU_GRF = SECU_GRF.split('^XA')[0] # Le fichier contient un fragment parasite '^XA^LL0750' en fin de fichier, qui casse le format

        # Lignes horizontales (dans le repère logique) : (y, x_debut, x_fin)
        LIGNES_H = [
            (0    , 0  , 210),
            (20   , 0  , 210),
            (46   , 0  , 210),
            (76   , 0  , 210),
            (104  , 0  , 100),
            (125  , 0  , 210),
            (148  , 0  , 210),
            (33   , 100, 210),
            (86.5 , 100, 210),
            (114.5, 100, 210),
        ]

        # Lignes verticales (dans le repère logique) : (x, y_debut, y_fin)
        LIGNES_V = [
            (0  , 0    , 148),
            (210, 0    , 148),
            (100, 0    , 148),
            (136, 33   , 46),
            (173, 33   , 46),
            (140, 114.5, 125),
        ]

        # Labels (dans le repère logique) : (x, y, texte, colonne)
        LABELS = [
            (0  , 0    , "Destinataire"       , 'gauche'),
            (0  , 20   , "N°document"         , 'gauche'),
            (0  , 46   , "N°produit (P)"      , 'gauche'),
            (0  , 76   , "Quantité (Q)"       , 'gauche'),
            (0  , 104  , "Fournisseur (V)"    , 'gauche'),
            (0  , 125  , "N°étiquette"        , 'gauche'),

            (100, 0    , "Lieu de livraison"  , 'droite'),
            (100, 20   , "Adresse expéditeur" , 'droite'),
            (100, 33   , "Poids net (kg)"     , 'droite'),
            (136, 33   , "Poids brut (kg)"    , 'droite'),
            (173, 33   , "Nb boites"          , 'droite'),
            (100, 76   , "Produit"            , 'droite'),
            (100, 86.5 , "Ref Logistique"     , 'droite'),
            (100, 114.5, "Date"               , 'droite'),
            (140, 114.5, "Indice Modification", 'droite'),
            (100, 125  , "N°lot (H)"          , 'droite'),
        ]

        # Codes-barres : (x, y, hauteur, clé de la valeur, préfixe)
        # y = bas de la ligne du tableau - hauteur - ESPACE_CODE_BARRE (espace avant le trait du dessous)
        # x des codes-barres à droite = base de la colonne (100) + 2mm (décalage vers la droite)
        ESPACE_CODE_BARRE = 3 # mm - marge de sécurité (le rendu ne semble pas respecter exactement 1mm)
        CODES_BARRES = [
            (MARGE_TEXTE_GAUCHE, 76   -13-ESPACE_CODE_BARRE, 13, 'numero_produit', 'P'),
            (MARGE_TEXTE_GAUCHE, 104  -13-ESPACE_CODE_BARRE, 13, 'quantite_um'   , 'Q'),
            (MARGE_TEXTE_GAUCHE, 125  -13-ESPACE_CODE_BARRE, 13, 'fournisseur'   , 'V'),
            (MARGE_TEXTE_GAUCHE, 148  -13-ESPACE_CODE_BARRE, 13, 'num_etiquette' , ''),
            (100+2             , 114.5-13-ESPACE_CODE_BARRE, 13, 'ref_logistique', ''),
            (100+2             , 148  -13-ESPACE_CODE_BARRE, 13, 'num_lot'       , 'H'),
        ]

        for obj in self:
            # Destinataire : adresse du client par défaut de l'article de la première UC de cette UM, sur 3 lignes
            premiere_uc = obj.uc_ids[:1]
            client = premiere_uc.product_id.product_tmpl_id.is_client_ids.filtered(lambda c: c.client_defaut)[:1].client_id
            lignes_destinataire = [
                client.name or '',
                client.street or '',
                ' '.join(filter(None, [client.zip, client.city])),
            ] if client else []

            # Point de déchargement de la commande de la ligne de livraison de la première UC, juste après le label Destinataire
            point_dechargement = premiere_uc.stock_move_id.sale_line_id.order_id.is_point_dechargement or ''

            # Adresse expéditeur : champ 'Adresse expéditeur' du type étiquette UM de l'article, sur une ligne
            expediteur = premiere_uc.product_id.product_tmpl_id.is_type_etiquette_um_id.adresse_expediteur or ''

            # Fournisseur (V) : champ is_cofor du client de l'article
            fournisseur = client.is_cofor or ''

            # Poids net/brut : somme, pour chaque UC, du poids net/brut de l'article multiplié par sa quantité
            poids_net  = sum(uc.qt_pieces*uc.product_id.product_tmpl_id.weight_net for uc in obj.uc_ids)
            poids_brut = sum(uc.qt_pieces*uc.product_id.product_tmpl_id.weight     for uc in obj.uc_ids)

            # Nb boites : nombre d'UC de cette UM
            nb_boites = len(obj.uc_ids)

            # Lieu de livraison : point de destination de la ligne de commande de la ligne de livraison de la première UC
            lieu_livraison = premiere_uc.stock_move_id.sale_line_id.is_point_destination or ''

            # N°produit (P) : référence de l'article selon le type étiquette UM (ref PG/plan/client)
            article        = premiere_uc.product_id.product_tmpl_id
            type_eti_um    = article.is_type_etiquette_um_id
            REF_LOGISTIQUE = {
                'ref_pg'    : article.is_code,
                'ref_plan'  : article.is_ref_plan,
                'ref_client': article.is_ref_client,
            }
            numero_produit = REF_LOGISTIQUE.get(type_eti_um.ref_logistique) or ''

            # Logo Sécu : affiché si is_soumise_regl est renseigné, avec les lettres R et/ou S
            is_soumise_regl = article.is_soumise_regl or ''

            # Produit : désignation de l'article, précédée du code fabrication selon is_type_etiquette_um
            produit = article.name or ''
            if type_eti_um.produit=='avec_code_fabrication' and article.is_code_fabrication:
                produit = "%s-%s"%(article.is_code_fabrication, produit)

            # Quantité (Q) : quantité de l'UM
            quantite_um = obj.qt_pieces

            # Ref Logistique : référence plan de l'article
            ref_logistique = article.is_ref_plan or ''

            # Date : date de création de la première UC, au format Ymd
            date = premiere_uc.date_creation.strftime('%Y%m%d') if premiere_uc.date_creation else ''

            # N°lot (H) : champ 'Production' de la première UC
            num_lot = premiere_uc.production or ''

            # Indice Modification : indice plan de l'article
            indice_modification = article.is_ind_plan or ''

            # N°étiquette : nom de l'UM
            num_etiquette = obj.name or ''

            # Pour les UM mixtes, ces valeurs n'ont pas de sens (pas un seul article) et sont effacées, sans code-barre
            CODES_BARRES_SUPPRIMES = []
            if obj.mixte=='oui':
                is_soumise_regl   = ''
                numero_produit    = ''
                quantite_um       = ''
                produit           = ''
                ref_logistique    = ''
                indice_modification = ''
                date              = ''
                num_lot           = ''
                CODES_BARRES_SUPPRIMES = ['numero_produit', 'quantite_um', 'ref_logistique', 'num_lot']

            ZPL  = "^XA\n"
            ZPL += "^CI28\n" # Encodage UTF-8, pour les caractères accentués
            ZPL += "^PW%s\n"%(mm(HAUTEUR)+EPAISSEUR) # Largeur physique = hauteur logique (étiquette tournée à 90°)
            ZPL += "^LL%s\n"%(mm(LARGEUR)+EPAISSEUR) # Hauteur physique = largeur logique (étiquette tournée à 90°)
            if is_soumise_regl:
                ZPL += SECU_GRF # Envoi du graphique une seule fois, avant tout le reste (sinon l'étiquette est corrompue)
            for y, x_debut, x_fin in LIGNES_H:
                # Ligne horizontale logique => ligne verticale physique
                ZPL += "%s^GB%s,%s,%s^FS\n"%(FO(x_debut, y), EPAISSEUR, mm(x_fin-x_debut), EPAISSEUR)
            for x, y_debut, y_fin in LIGNES_V:
                # Ligne verticale logique => ligne horizontale physique
                ZPL += "%s^GB%s,%s,%s^FS\n"%(FO(x, y_fin), mm(y_fin-y_debut), EPAISSEUR, EPAISSEUR)
            for x, y, texte, colonne in LABELS:
                marge = MARGE_TEXTE_GAUCHE if colonne=='gauche' else 0
                if texte=="N°étiquette":
                    # Suffixe (G) UM mixte ou (M) UM homogène
                    texte = "%s (%s)"%(texte, 'G' if obj.mixte=='oui' else 'M')
                ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(x+marge, y, TAILLE_POLICE), mm(TAILLE_POLICE), mm(TAILLE_POLICE), texte)

            # Valeur du Point de déchargement, juste après le label Destinataire (sur la même ligne)
            x_point_dechargement = 25 # Largeur approximative du label 'Destinataire'
            ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(x_point_dechargement, 0, TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), point_dechargement)

            # Valeur du Destinataire, affichée ligne par ligne sous le label
            y_valeur = TAILLE_POLICE+ESPACE_LABEL_VALEUR # Juste sous le label, avec un minimum d'espace
            for num_ligne, ligne in enumerate(lignes_destinataire):
                y_ligne = y_valeur+num_ligne*TAILLE_POLICE_5MM
                ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(MARGE_TEXTE_GAUCHE, y_ligne, TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), ligne)

            # Valeur de l'Adresse expéditeur, sur une seule ligne sous le label
            y_expediteur = 20+TAILLE_POLICE+ESPACE_LABEL_VALEUR # Label 'Adresse expéditeur' positionné à y=20
            ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(100, y_expediteur, TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), expediteur)

            # Valeurs des poids net/brut et du nb boites, sous les labels positionnés à y=33
            y_poids = 33+TAILLE_POLICE+ESPACE_LABEL_VALEUR
            ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(100, y_poids, TAILLE_POLICE_7MM), mm(TAILLE_POLICE_7MM), mm(TAILLE_POLICE_7MM), '%.2f'%poids_net)
            ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(136, y_poids, TAILLE_POLICE_7MM), mm(TAILLE_POLICE_7MM), mm(TAILLE_POLICE_7MM), '%.2f'%poids_brut)
            ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(173, y_poids, TAILLE_POLICE_7MM), mm(TAILLE_POLICE_7MM), mm(TAILLE_POLICE_7MM), nb_boites)

            # Valeur du Lieu de livraison, sous le label positionné à y=0
            y_livraison = TAILLE_POLICE+ESPACE_LABEL_VALEUR
            ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(100, y_livraison, TAILLE_POLICE_13MM), mm(TAILLE_POLICE_13MM), mm(TAILLE_POLICE_13MM), lieu_livraison)

            # Valeur du N°produit (P), juste après le label (sur la même ligne) pour économiser de la hauteur
            x_produit = 20 # Largeur approximative du label 'N°produit (P)'
            ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(x_produit, 46, TAILLE_POLICE_13MM), mm(TAILLE_POLICE_13MM), mm(TAILLE_POLICE_13MM), numero_produit)

            # Valeur du Produit, sous le label positionné à y=76
            y_produit_designation = 76+TAILLE_POLICE+ESPACE_LABEL_VALEUR
            ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(100, y_produit_designation, TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), produit)

            # Valeur de la Quantité (Q), juste après le label (sur la même ligne)
            x_quantite = 20 # Largeur approximative du label 'Quantité (Q)'
            ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(x_quantite, 76, TAILLE_POLICE_13MM), mm(TAILLE_POLICE_13MM), mm(TAILLE_POLICE_13MM), quantite_um)

            # Valeur de Ref Logistique, juste après le label (sur la même ligne) pour gagner de la hauteur
            x_ref_logistique = 100+28 # Colonne de droite (base 100) + largeur approximative du label 'Ref Logistique'
            ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(x_ref_logistique, 86.5, TAILLE_POLICE_13MM), mm(TAILLE_POLICE_13MM), mm(TAILLE_POLICE_13MM), ref_logistique)

            # Valeurs de Date et Indice Modification, sous les labels positionnés à y=114.5
            y_date = 114.5+TAILLE_POLICE+ESPACE_LABEL_VALEUR
            ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(100, y_date, TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), date)
            ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(140, y_date, TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), indice_modification)

            # Valeur du N°lot (H), juste après le label (sur la même ligne) pour gagner de la hauteur
            x_num_lot = 100+14 # Colonne de droite (base 100) + largeur approximative du label 'N°lot (H)'
            ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(x_num_lot, 125, TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), num_lot)

            # Valeur du N°étiquette, juste après le label (sur la même ligne) pour gagner de la hauteur
            x_etiquette = 25 # Largeur approximative du label 'N°étiquette'
            ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(x_etiquette, 125, TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), num_etiquette)

            # Valeur du Fournisseur (V), juste après le label (sur la même ligne) pour gagner de la hauteur
            x_fournisseur = 25 # Largeur approximative du label 'Fournisseur (V)'
            ZPL += "%s^A0R,%s,%s^FD%s^FS\n"%(FO(x_fournisseur, 104, TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), mm(TAILLE_POLICE_5MM), fournisseur)

            # Codes-barres : N°produit (P), Quantité (Q), Fournisseur (V), N°étiquette, Ref Logistique
            VALEURS_CODE_BARRE = {
                'numero_produit' : numero_produit,
                'quantite_um'    : quantite_um,
                'fournisseur'    : fournisseur,
                # Préfixe G (UM mixte) ou M (UM homogène), uniquement pour le code-barre
                'num_etiquette'  : ('G' if obj.mixte=='oui' else 'M')+num_etiquette,
                'ref_logistique' : ref_logistique,
                'num_lot'        : num_lot,
            }
            for x, y, hauteur, cle, prefixe in CODES_BARRES:
                if cle in CODES_BARRES_SUPPRIMES:
                    continue
                valeur = "%s%s"%(prefixe, VALEURS_CODE_BARRE[cle])
                ZPL += "^BY4,2.0\n" # Module doublé (2 -> 4 dots) pour des codes-barres 2x plus larges
                ZPL += "%s^B3R,N,%s,N,N^FD%s^FS\n"%(FO(x, y, hauteur), mm(hauteur), valeur)

            # Logo Sécu : identique au code de creer_etiquette (^XGR:SECU2.grf,1,1^FS, sans ^FW),
            # correctement orienté car toute l'étiquette est tournée à 90° comme l'étiquette UC.
            if is_soumise_regl:
                ZPL += "%s^XGR:SECU2.grf,%s,%s^FS\n"%(FO(LOGO_SECU_X, LOGO_SECU_Y, LOGO_SECU_TAILLE), LOGO_SECU_MAGNIFICATION, LOGO_SECU_MAGNIFICATION)
                if 'R' in is_soumise_regl:
                    # R aligné sur le bord haut du logo (à l'écran)
                    ZPL += "%s^A0R,%s,%s^FDR^FS\n"%(FO(LOGO_SECU_LETTRE_X, LOGO_SECU_Y, TAILLE_POLICE_7MM), mm(TAILLE_POLICE_7MM), mm(TAILLE_POLICE_7MM))
                if 'S' in is_soumise_regl:
                    # S aligné sur le bord bas du logo (à l'écran)
                    ZPL += "%s^A0R,%s,%s^FDS^FS\n"%(FO(LOGO_SECU_LETTRE_X, LOGO_SECU_Y+LOGO_SECU_TAILLE-TAILLE_POLICE_7MM, TAILLE_POLICE_7MM), mm(TAILLE_POLICE_7MM), mm(TAILLE_POLICE_7MM))

            ZPL += "^MMT\n"   #Avance de l'éiquette
            ZPL += "^XZ\n"


            try:
                imprimante_utilisee = self.env['is.galia.base'].imprimer_zpl(ZPL, imprimante=imprimante)
            except Exception as e:
                # Nouveau curseur : le message doit survivre au rollback provoqué par l'exception
                with self.pool.cursor() as new_cr:
                    new_env = api.Environment(new_cr, self.env.uid, self.env.context)
                    new_env['is.galia.base.um'].browse(obj.id).message_post(
                        body="Échec de l'impression étiquette UM A5 (%s) : %s"%(obj.name, e)
                    )
                raise

            # Écrire dans le chatter à chaque impression
            message = "Impression étiquette UM A5 (%s) sur l'imprimante <b>%s</b>"%(obj.name, imprimante_utilisee)
            obj.message_post(body=message)

        return True


    def imprimer_etiquette_uc_action(self):
        user = self.env['res.users'].browse(self._uid)
        company = self.env.company
        for obj in self:
            domain = [('um_id','=',obj.id)]
            ucs = self.env['is.galia.base.uc'].search(domain)
            for uc in ucs:
                uc.imprimer_etiquette_uc_action()
