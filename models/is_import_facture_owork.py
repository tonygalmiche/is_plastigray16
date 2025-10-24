# -*- coding: utf-8 -*-
from odoo import models, fields, api         # type: ignore
from odoo.exceptions import ValidationError  # type: ignore
from datetime import datetime
from urllib import request
from urllib.error import HTTPError, URLError
from socket import timeout
from subprocess import PIPE, Popen
import pytz
import csv
import base64
import sys
import logging
_logger = logging.getLogger(__name__)



class is_import_facture_owork(models.Model):
    _name = "is.import.facture.owork"
    _description = "Importation factures O'Work"
    _order='name desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    active                = fields.Boolean("Actif", default=True, tracking=True)
    name                  = fields.Char("N°", readonly=True, tracking=True)
    attachment_ids        = fields.Many2many('ir.attachment', 'is_import_facture_owork_attachment_rel', 'import_id', 'attachment_id', 'Fichiers à importer')
    nb_lignes             = fields.Integer("Nombre de lignes"  , readonly=True, tracking=True)
    nb_factures_a_traiter = fields.Integer("Nombre de factures à traiter", readonly=True, tracking=True)
    nb_factures           = fields.Integer("Nombre de factures générées", readonly=True, tracking=True, compute='_compute_nb_factures', store=True)
    nb_anomalies          = fields.Integer("Nombre d'anomalies", readonly=True, tracking=True, compute='_compute_nb_anomalies', store=True)
    line_ids              = fields.One2many('is.import.facture.owork.line', 'import_id', "Lignes", copy=True)
    invoice_ids           = fields.One2many('account.move', 'is_owork_id', "Factures Odoo")
    state                 = fields.Selection([('analyse', 'Analyse'),('traite', 'Traité')], "État", index=True, default="analyse", tracking=True)
    factures              = fields.Text("Factures", readonly=True, tracking=True)


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('is.import.facture.owork')
        return super().create(vals_list)


    @api.depends('invoice_ids')
    def _compute_nb_factures(self):
        for obj in self:
            obj.nb_factures = len(obj.invoice_ids)


    @api.depends('line_ids','line_ids.anomalies')
    def _compute_nb_anomalies(self):
        for obj in self:
            nb_anomalies = 0
            for line in obj.line_ids:
                if line.anomalies:
                    nb_anomalies+=1
            obj.nb_anomalies = nb_anomalies


    def actualiser_lignes(self):
        for obj in self:
            obj.line_ids.actualiser_ligne()

            #** Statistiques **************************************************
            obj.nb_lignes = len(obj.line_ids)
            factures=[]
            for line in obj.line_ids:
                if line.numfac not in factures:
                    factures.append(line.numfac)
            obj.nb_factures_a_traiter = len(factures)
            if len(factures)>0:
                factures = '\n'.join(factures)
            else:
                factures=False
            obj.factures = factures
            #******************************************************************
        return []

    # def actualiser_lignes(self):
    #     """Action pour actualiser les lignes depuis l'interface utilisateur"""
    #     self._actualiser_lignes_compute()
    #     return []
    #     # return {
    #     #     'type': 'ir.actions.client',
    #     #     'tag': 'display_notification',
    #     #     'params': {
    #     #         'title': "Actualisation terminée",
    #     #         'message': f"Lignes actualisées avec succès. {self.nb_lignes} lignes traitées, {self.nb_anomalies} anomalies détectées.",
    #     #         'type': 'success',
    #     #         'sticky': False,
    #     #     }
    #     # }



    # def import_site_owork(self):
    #     for obj in self:
    #         company = self.env.company
    #         url = company.is_url_facture_owork
    #         if url : 
    #             try:
    #                 res = request.urlopen(request.Request(url), timeout=3)
    #                 filename = res.info().get_filename()
    #                 data = res.read()
    #             except:
    #                 raise ValidationError("Pas de fichier à récupérer ou problème de connexion !")
    #             datas = base64.b64encode(data)
    #             vals = {
    #                 'name':        filename,
    #                 'type':        'binary',
    #                 'res_id':      obj.id,
    #                 'datas':       datas,
    #             }
    #             attachment = self.env['ir.attachment'].create(vals)
    #             obj.attachment_ids = [attachment.id]
    #             obj.import_facture_owork()


    # def import_facture_owork(self):
    #     owork_obj = self.env['is.import.facture.owork.line']
    #     for obj in self:
    #         obj.line_ids.unlink()
    #         for attachment in obj.attachment_ids:
    #             csvfile = base64.decodebytes(attachment.datas).decode('cp1252')
    #             csvfile = csvfile.replace('\r\n','\n').split("\n")
    #             csvfile = csv.DictReader(csvfile, delimiter=';')
    #             for ct, lig in enumerate(csvfile):
    #                 nb=len(lig)
    #                 vals={
    #                     'import_id': obj.id,
    #                     'fichier'  : attachment.name,
    #                 }
    #                 anomalies=[]
    #                 for key in lig:
    #                     if key:
    #                         if key.strip()!='':
    #                             val = lig[key]
    #                             field_obj = owork_obj._fields[key]
    #                             if isinstance(field_obj,  fields.Date):
    #                                 try:
    #                                     val=datetime.strptime(lig[key], '%Y-%m-%d')
    #                                 except ValueError:
    #                                     val=False
    #                                 if not val:
    #                                     try:
    #                                         val=datetime.strptime(lig[key], '%d/%m/%Y')
    #                                     except ValueError:
    #                                         val=False
    #                             if isinstance(field_obj,  fields.Float):
    #                                 try:
    #                                     val=float(val)
    #                                 except ValueError:
    #                                     val=False
    #                             if isinstance(field_obj,  fields.Integer):
    #                                 try:
    #                                     val=int(val)
    #                                 except ValueError:
    #                                     val=False
    #                             if val=='null':
    #                                 val=False
    #                             vals[key] = val

    #                             #** Recherche reception ***************************
    #                             if key=='numrecept' and val:
    #                                 pickings = self.env['stock.picking'].search([('name','=',val)])
    #                                 picking_id=False
    #                                 for picking in pickings:
    #                                     picking_id=picking.id
    #                                 if picking_id:
    #                                     vals['picking_id'] = picking_id
    #                                 else:
    #                                     anomalies.append('Réception %s non trouvée'%val)
    #                             #**************************************************

    #                             #** Recherche ligne de réception ******************
    #                             if key=='numidodoo' and val:
    #                                 moves = self.env['stock.move'].search([('id','=',val)])
    #                                 stock_move_id=False
    #                                 for move in moves:
    #                                     stock_move_id=move.id
    #                                 if stock_move_id:
    #                                     vals['stock_move_id'] = stock_move_id
    #                                 else:
    #                                     anomalies.append('Id ligne de réception %s non trouvée'%val)
    #                             #**************************************************

    #                             #** Recherche article ***************************
    #                             if key=='article':
    #                                 product_id=False
    #                                 if val:
    #                                     products = self.env['product.product'].search([('is_code','=',val)])
    #                                     for product in products:
    #                                         product_id=product.id
    #                                 else:
    #                                     if lig['numidodoo']:
    #                                         moves = self.env['stock.move'].search([('id','=', lig['numidodoo'])])
    #                                         for move in moves:
    #                                             product_id=move.product_id.id
    #                                             vals['article'] = move.product_id.is_code
    #                                 if product_id:
    #                                     vals['product_id'] = product_id
    #                                 else:
    #                                     anomalies.append("Article '%s' non trouvée"%(val or ''))
                                    


    #                             #**************************************************

    #                             # #** Recherche descriparticle **********************
    #                             # if key=='descriparticle':
    #                             #     if not val or val=='':
    #                             #         anomalies.append("Description manquante")
    #                             # #**************************************************

    #                             #** Recherche fournissur **************************
    #                             if key=='codefour':
    #                                 partner_id=False
    #                                 if val:
    #                                     partners = self.env['res.partner'].search([('is_code','=',val)])
    #                                     partner_id=False
    #                                     for partner in partners:
    #                                         partner_id=partner.id
    #                                 else:


    #                                     if lig['numidodoo'] and lig['numidodoo']!='null':


    #                                         moves = self.env['stock.move'].search([('id','=', lig['numidodoo'])])
    #                                         for move in moves:
    #                                             partner_id=move.picking_id.partner_id.id
    #                                             vals['codefour'] = move.picking_id.partner_id.is_code
    #                                 if partner_id:
    #                                     vals['partner_id'] = partner_id
    #                                 else:
    #                                     anomalies.append("Fournisseur '%s' non trouvée"%(val or ''))
    #                             #**************************************************

    #                             #** Recherche TVA **************************
    #                             if key=='codetvafact' and val:
    #                                 taxs = self.env['account.tax'].search([('description','=',val)])
    #                                 tax_id=False
    #                                 for tax in taxs:
    #                                     tax_id=tax.id
    #                                 if tax_id:
    #                                     vals['tax_id'] = tax_id
    #                                 else:
    #                                     anomalies.append("TVA '%s' non trouvée"%(val or ''))
    #                             #**************************************************

    #                 #** Comparatif prix d'origine et prix facturé *************
    #                 prixorigine = vals.get('prixorigine') or 0
    #                 prixfact    = vals.get('prixfact') or 0
    #                 if prixorigine>0 and prixfact>0 and round(prixorigine,2)!=round(prixfact,2):
    #                     anomalies.append("Le prix d'origine '%s' est différent du prix facturé %s"%(round(prixorigine,2),round(prixfact,2)))

    #                 #** Vérification total ligne facturé **********************
    #                 prixfact      = vals.get('prixfact')     or 0
    #                 qtefact       = vals.get('qtefact')      or 0
    #                 totalfacture  = vals.get('totalfacture') or 0
    #                 total_calcule = round(prixfact*qtefact,2)
    #                 if total_calcule != totalfacture:
    #                     anomalies.append("Le total facturé %s est différent de %s x %s (%s)"%(totalfacture,prixfact,qtefact,total_calcule))

    #                 if len(anomalies)>0:
    #                     vals['anomalies'] = '\n'.join(anomalies)
                    
    #                 line = self.env['is.import.facture.owork.line'].create(vals)


    #         #** Vérfication que total facturé correspond au total des lignes **
    #         factures={}
    #         nb_anomalies = 0
    #         for line in obj.line_ids:
    #             if line.anomalies:
    #                 nb_anomalies+=1
    #             numfac = line.numfac
    #             if numfac not in factures:
    #                 factures[numfac] = 0
    #             factures[numfac] += line.totalfacture
    #         for line in obj.line_ids:
    #             numfac = line.numfac
    #             total_calcule = round(factures[numfac],2)
    #             if line.montantht != total_calcule:
    #                 anomalie = "Le total des lignes %s est différent du total de la facture %s"%(total_calcule,line.montantht)
    #                 if line.anomalies:
    #                     line.anomalies="%s\n%s"%(line.anomalies,anomalie)
    #                 else:
    #                     line.anomalies=anomalie
    #         #******************************************************************
            
    #         obj.nb_lignes    = len(obj.line_ids)
    #         obj.nb_factures  = len(factures)
    #         obj.nb_anomalies = nb_anomalies


    def voir_les_lignes(self):
        for obj in self:
            ctx={
                'default_import_id': obj.id,
            }
            return {
                'name'     : obj.name,
                'view_mode': 'tree,form',
                'res_model': 'is.import.facture.owork.line',
                'domain'   : [('import_id' ,'=',obj.id)],
                'type'     : 'ir.actions.act_window',
                'context'  : ctx,
                'limit'    : 1000,
            }



    def creation_factures(self):
        for obj in self:

            #** Liste des factures à créer ************************************
            factures={}
            for line in obj.line_ids:
                numfac = line.numfac
                if numfac not in factures:
                    bon_a_payer = True
                    if line.litige=='L':
                        bon_a_payer = False
                    if line.partner_id and line.datefact and line.numfac:
                        vals = {
                            'partner_id'      : line.partner_id.id,
                            'journal_id'      : 2,
                            'move_type'       : 'in_invoice',
                            'invoice_date'    : line.datefact,
                            'date'            : line.datefact,
                            'invoice_date_due': line.datefact,
                            'is_bon_a_payer'  : bon_a_payer,
                            'supplier_invoice_number': line.numfac,
                            'is_owork_id'     : obj.id,
                            'is_id_owork'     : line.id_owork,
                        }
                        factures[numfac]=vals
            #******************************************************************

            for facture in factures:
                lines = []
                invoice_line_tax_id=[]
                for line in obj.line_ids:
                    if line.numfac==facture:
                        product_id = line.product_id.id
                        if product_id:
                            #and line.stock_move_id.id:
                            description     = line.descriparticle
                            quantite        = line.qtefact
                            invoice_line_tax_id=[]
                            if line.tax_id:
                                invoice_line_tax_id.append(line.tax_id.id)
                                #** Ajout tax déductible pour Intracom ********
                                if line.tax_id.description=='ACH_UE_due-20.0':
                                    taxs = self.env['account.tax'].search([('description','=',"ACH_UE_ded.-20.0")])
                                    for tax in taxs:
                                        invoice_line_tax_id.append(tax.id)
                                #**********************************************
                            if len(invoice_line_tax_id)==0:
                                invoice_line_tax_id=False
                            #is_document=line.move_id.purchase_line_id.is_num_chantier
                            #if is_document==False:
                            #    is_document=line.move_id.purchase_line_id.order_id.is_document


                            product_uom_id = line.product_id.uom_po_id.id
                            if line.stock_move_id.id:
                                product_uom_id = line.stock_move_id.purchase_line_id.product_uom.id

                            v = {
                                'product_id'      : product_id,
                                'name'            : description or product_id.name,
                                'quantity'        : line.qtefact,
                                #'product_uom_id' : line.stock_move_id.product_uom.id,
                                'product_uom_id'  : product_uom_id,
                                'price_unit'      : line.prixfact,
                                'tax_ids'         : [(6,0,invoice_line_tax_id)],
                                #'is_document'    : is_document,
                                'is_move_id'      : line.stock_move_id.id,
                                'purchase_line_id': line.stock_move_id.purchase_line_id.id,
                                'is_section_analytique_id': line.product_id.is_section_analytique_ha_id.id,
                                'is_document'     : line.num_chantier_fact or line.num_chantier_rcp or False,
                            }
                            lines.append([0,False,v]) 


                vals=factures[facture]
                vals.update({
                    'invoice_line_ids': lines,
                })
                invoice=self.env['account.move'].create(vals)
                for line in obj.line_ids:
                    if line.numfac==facture:
                        line.invoice_id = invoice.id
                for line in invoice.invoice_line_ids:
                    if line.is_move_id:
                        line.is_move_id.invoice_state='invoiced'
                        line.is_move_id.picking_id._compute_invoice_state()

                for line in obj.line_ids:
                    invoice = line.invoice_id
                    anomalies=[]
                    if round(invoice.amount_untaxed,2)!=round(line.montantht,2):
                        anomalies.append("Le montant HT de la facture O'Work (%s) est différent de cette facture Odoo (%s)"%(round(line.montantht,2),round(invoice.amount_untaxed,2)))
                    if round(invoice.amount_tax,2)!=round(line.montanttva,2):
                        anomalies.append("Le montant de la TVA de la facture O'Work (%s) est différent de cette facture Odoo (%s)"%(round(line.montanttva,2),round(invoice.amount_tax,2)))
                    if round(invoice.amount_total,2)!=round(line.montanttc,2):
                        anomalies.append("Le montant TTC de la facture O'Work (%s) est différent de cette facture Odoo (%s)"%(round(line.montanttc,2),round(invoice.amount_total,2)))
                    if len(anomalies)>0:
                        anomalies = '\n'.join(anomalies)
                    else:
                        anomalies=False
                    invoice.is_anomalies_owork = anomalies
            obj.state='traite'

   
    def voir_les_factures(self):
        for obj in self:
            ids=[]
            for invoice in obj.invoice_ids:
                ids.append(invoice.id)
            tree_view_id=self.env.ref('is_plastigray16.is_view_invoice_tree')
            res= {
                'name': obj.name,
                'view_mode': 'tree,form',
                'res_model': 'account.move',
                'views': [[tree_view_id.id, "list"], [False, "form"]],
                'type': 'ir.actions.act_window',
                'context': {'default_move_type':'in_invoice', 'move_type':'in_invoice'},
                'domain': [('move_type','=','in_invoice'),('id','in',ids)],
            }
            return res


    def exporter_receptions_owork_action(self):
        name = "exporter-receptions-owork"
        cdes = self.env['is.commande.externe'].search([('name','=',name)])
        if len(cdes)==0:
            raise ValidationError("Commande externe '%s' non trouvée !"%name)
        for cde in cdes:
            p = Popen(cde.commande, shell=True, stdout=PIPE, stderr=PIPE)
            stdout, stderr = p.communicate()
            _logger.info("%s => %s"%(cde.commande,stdout))
            if stderr:
                raise ValidationError("Erreur dans commande externe '%s' => %s"%(cde.commande,stderr))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': "Exportation vers O'Work éffectutée",
                #'message': "Exportation vers O'Work éffectutée",
                'type': 'success',
                'sticky': False,
            }
        }


class is_import_facture_owork_line(models.Model):
    _name = "is.import.facture.owork.line"
    _description = "Lignes importation factures O'Work"
    _rec_name = 'id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    active         = fields.Boolean("Actif", default=True, tracking=True)
    import_id      = fields.Many2one('is.import.facture.owork', "Import O'Work", required=True, ondelete='cascade', tracking=True)
    codeetab       = fields.Char("Code etab", tracking=True)
    codefour       = fields.Char("Code Four fact", tracking=True)
    codefourrcp    = fields.Char("Code Four Rcp", tracking=True)
    codeadrfour    = fields.Char("Code adr four", tracking=True)
    numbl          = fields.Char("Num BL", tracking=True)
    numrecept      = fields.Char("Num rcp", tracking=True)
    daterecpt      = fields.Date("Date rcp", tracking=True)
    numcde         = fields.Char("Num Cde", tracking=True)
    num_chantier_rcp  = fields.Char("N°Chantier Rcp", tracking=True)
    num_chantier_fact = fields.Char("N°Chantier Fact", tracking=True)
    sec_ana_origine = fields.Char("Section Rcp", tracking=True)
    sec_ana_fact    = fields.Char("Section Fact", tracking=True)
    cpte_origine    = fields.Char("Compte Rcp", tracking=True)
    cpte_fact       = fields.Char("Compte Fact", tracking=True)
    article        = fields.Char("Code Article", tracking=True)
    descriparticle = fields.Char("Description article", tracking=True)
    qterestefac    = fields.Float("Qt reste fac", digits=(12, 6), tracking=True)
    prixorigine    = fields.Float("Prix Origine", digits=(12, 6), tracking=True)
    total          = fields.Float("Total ligne HT", digits=(12, 4), tracking=True)
    codetvaorigine = fields.Char("Code TVA Origine", tracking=True)
    codetvafact    = fields.Char("Code TVA Fac", tracking=True)
    prixfact       = fields.Float("Prix Fac", digits=(12, 6), tracking=True)
    qtefact        = fields.Float("Qt fac"  , digits=(12, 6), tracking=True)
    datefact       = fields.Date("Date Fac", tracking=True)
    numfac         = fields.Char("Num Fac", tracking=True)
    montantht      = fields.Float("Montant HT Facture", tracking=True)
    montanttva     = fields.Float("Montant TVA Facture", tracking=True)
    montanttc      = fields.Float("Montant TTC Facture", tracking=True)
    numidodoo      = fields.Char("Id Odoo", tracking=True)
    id_owork       = fields.Integer("id O'Work", tracking=True)
    totalfacture   = fields.Float("Total ligne facture", tracking=True)
    litige         = fields.Char("Litige", tracking=True)
    picking_id     = fields.Many2one('stock.picking', "Réception", tracking=True, copy=False)
    stock_move_id  = fields.Many2one('stock.move', "Ligne de réception", tracking=True, copy=False, ondelete='set null')
    partner_id     = fields.Many2one('res.partner', "Fournisseur", tracking=True, copy=False)
    product_id     = fields.Many2one('product.product', "Article", tracking=True, copy=False)
    tax_id         = fields.Many2one('account.tax', "TVA", tracking=True, copy=False)
    invoice_id     = fields.Many2one('account.move', "Facture", tracking=True, copy=False)
    fichier        = fields.Char("Fichier", tracking=True)
    anomalies      = fields.Text("Anomalies", tracking=True, copy=False, compute='actualiser_ligne', store=True, readonly=True)
 

    @api.depends('codefour','codefourrcp','numidodoo','codetvafact','prixorigine','prixfact','qtefact','totalfacture','total','montantht','article')
    def actualiser_ligne(self):
        cr=self._cr
        for obj in self:
            anomalies=[]
            #** Recherche article *********************************************
            if obj.article:
                domain=[
                    ('is_code'    ,'=', obj.article),
                ]
                products = self.env['product.product'].search(domain)
                product_id = False
                for product in products:
                    product_id = product.id
                obj.product_id = product_id
                if not product_id:
                    anomalies.append("Code article '%s' non trouvé dans Odoo"%(obj.article))
            #******************************************************************

            #** Recherche fournisseur *****************************************
            partner_id = False
            codefour = obj.codefour or obj.codefourrcp
            if codefour:
                is_code = codefour.lstrip("0")
                domain=[
                    ('is_code'    ,'=', is_code),
                    ('is_adr_code','=', '0')
                ]
                partners = self.env['res.partner'].search(domain)
                for partner in partners:
                    partner_id = partner.id
            obj.partner_id = partner_id
            if not partner_id:
                anomalies.append("Fournisseur à facturer non trouvé (codefour=%s)"%(codefour))
            #******************************************************************

            numrecept = obj.numrecept or ''
            if numrecept!='':
                #** stock_move_id, product_id et picking_id ************************
                stock_move_id = product_id = picking_id = False
                t = (obj.numidodoo or '').split('-')
                stock_move_id = obj.numidodoo
                if len(t)==3:
                    stock_move_id = t[1]
                try:
                    stock_move_id = int(stock_move_id)
                except ValueError:
                    anomalies.append("stock_move_id non valide (numidodoo=%s et stock_move_id=%s)" % (obj.numidodoo, stock_move_id))
                    stock_move_id=0
                if not stock_move_id:
                    anomalies.append("stock_move_id non trouvé (numidodoo=%s) "%(obj.numidodoo))
                if stock_move_id:
                    SQL="""
                        select sm.id, sm.picking_id, sm.product_id, sp.partner_id
                        from stock_move sm join stock_picking sp on sm.picking_id=sp.id
                        where sm.id=%s
                    """
                    cr.execute(SQL,[stock_move_id])
                    rows = cr.dictfetchall()
                    stock_move_id = False
                    for row in rows:
                        stock_move_id = row['id']
                        picking_id = row['picking_id']
                        product_id = row['product_id']
                        if not partner_id:
                            partner_id = row['partner_id']
                    if not stock_move_id:
                        anomalies.append("stock_move_id non trouvé (stock_move_id=%s) "%(obj.numidodoo))
                    if not picking_id:
                        anomalies.append("picking_id non trouvé (stock_move_id=%s) "%(stock_move_id))
                    if not product_id:
                        anomalies.append("product_id non trouvé (stock_move_id=%s) "%(stock_move_id))
                    if not partner_id:
                        anomalies.append("partner_id non trouvé (stock_move_id=%s) "%(stock_move_id))
                obj.stock_move_id = stock_move_id
                obj.picking_id = picking_id
                obj.product_id = product_id
                obj.partner_id = partner_id
                #*******************************************************************

            #** Recherche TVA **************************************************
            if obj.codetvafact:
                tax_id = False
                SQL="""
                    select id
                    from account_tax
                    where description=%s
                """
                cr.execute(SQL,[obj.codetvafact])
                rows = cr.dictfetchall()
                for row in rows:
                    tax_id = row['id']
                if not tax_id:
                    anomalies.append("TVA '%s' non trouvée"%(obj.codetvafact))
                obj.tax_id = tax_id
            #******************************************************************

            # #** Comparatif prix d'origine et prix facturé *********************
            # prixorigine = round(obj.prixorigine,6)
            # prixfact    = round(obj.prixfact,6)
            # if prixorigine>0 and prixfact>0 and prixorigine!=prixfact:
            #     anomalies.append("Le prix d'origine '%s' est différent du prix facturé '%s'"%(prixorigine,prixfact))
            # #******************************************************************

            #** Vérification total ligne facturé ******************************
            prixfact      = obj.prixfact
            qtefact       = obj.qtefact
            totalfacture  = obj.totalfacture
            total_calcule = round(prixfact*qtefact,2)
            if total_calcule != totalfacture:
                anomalies.append("Le total facturé %s est différent de %s x %s (%s)"%(totalfacture,prixfact,qtefact,total_calcule))
            #******************************************************************

            #** Vérfication que total facturé correspond au total des lignes **
            total_calcule = 0
            for line in obj.import_id.line_ids:
                if line.numfac == obj.numfac:
                    if obj._origin.id == line.id:
                        total_calcule+=obj.totalfacture
                    else:
                        total_calcule+=line.totalfacture
            total_calcule = round(total_calcule,4)
            if total_calcule!=obj.montantht:
                anomalies.append("Le total des lignes %s est différent du total de la facture %s"%(total_calcule,obj.montantht))
            #******************************************************************

            #** Anomalies *****************************************************
            if len(anomalies)>0:
                anomalies = '\n'.join(anomalies)
            else:
                anomalies=False
            obj.anomalies = anomalies
            #******************************************************************
