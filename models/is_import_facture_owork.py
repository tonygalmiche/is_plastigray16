# -*- coding: utf-8 -*-
from odoo import models, fields, api # type: ignore
from datetime import datetime
import csv
import base64


# Problèmes recontrés:
# - Ajouter l'id de la facture dans O'work car le numero de facture fournissur n'est pas frocement unique
# - Lien vers la facture dans O'work
# - Est-il possible de télécharger la facture PDF de O'work dans Odoo
# - Manque code article, description et code établissement pour les lignes ajoutées
# - Le code TVA facturé n'est pas bon sur les nouvelles factures
# - Ne pas mettre dans le même fichier plisusrs établissement et indiquer dans le nom du fichier en préfix le codeetab

#TODO : 
# - Ajouter le nombre de lignes importé, le nombre d'anomalies et le nombre de factures sur l'entête
# - Afficher uniquement les lignes avec des anomalies par défaut
# - Création des factures


class is_import_facture_owork(models.Model):
    _name = "is.import.facture.owork"
    _description = "Importation factures O'Work"
    _order='name desc'

    name           = fields.Char("N°", readonly=True)
    attachment_ids = fields.Many2many('ir.attachment', 'is_import_facture_owork_attachment_rel', 'import_id', 'attachment_id', 'Fichiers à importer')
    nb_lignes      = fields.Integer("Nombre de lignes"  , readonly=True)
    nb_factures    = fields.Integer("Nombre de factures", readonly=True)
    nb_anomalies   = fields.Integer("Nombre d'anomalies", readonly=True)
    line_ids       = fields.One2many('is.import.facture.owork.line', 'import_id', "Lignes")
    invoice_ids    = fields.One2many('account.move', 'is_owork_id', "Factures")
    state          = fields.Selection([('analyse', 'Analyse'),('traite', 'Traité')], "État", index=True, default="analyse")


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('is.import.facture.owork')
        return super().create(vals_list)


    def import_facture_owork(self):

        owork_obj = self.env['is.import.facture.owork.line']


        for obj in self:
            obj.line_ids.unlink()
            for attachment in obj.attachment_ids:
                csvfile = base64.decodebytes(attachment.datas).decode('cp1252')
                csvfile = csvfile.replace('\r\n','\n').split("\n")
                csvfile = csv.DictReader(csvfile, delimiter=';')
                for ct, lig in enumerate(csvfile):
                    nb=len(lig)
                    vals={
                        'import_id': obj.id,
                        'fichier'  : attachment.name,
                    }
                    anomalies=[]
                    for key in lig:
                        if key.strip()!='':
                            val = lig[key]
                            field_obj = owork_obj._fields[key]
                            if isinstance(field_obj,  fields.Date):
                                try:
                                    val=datetime.strptime(lig[key], '%Y-%m-%d')
                                except ValueError:
                                    val=False
                                if not val:
                                    try:
                                        val=datetime.strptime(lig[key], '%d/%m/%Y')
                                    except ValueError:
                                        val=False
                            if isinstance(field_obj,  fields.Float):
                                try:
                                    val=float(val)
                                except ValueError:
                                    val=False
                            if isinstance(field_obj,  fields.Integer):
                                try:
                                    val=int(val)
                                except ValueError:
                                    val=False
                            if val=='null':
                                val=False
                            vals[key] = val

                            #** Recherche reception ***************************
                            if key=='numrecept' and val:
                                pickings = self.env['stock.picking'].search([('name','=',val)])
                                picking_id=False
                                for picking in pickings:
                                    picking_id=picking.id
                                if picking_id:
                                    vals['picking_id'] = picking_id
                                else:
                                    anomalies.append('Réception %s non trouvée'%val)
                            #**************************************************

                            #** Recherche ligne de réception ******************
                            if key=='numidodoo' and val:
                                moves = self.env['stock.move'].search([('id','=',val)])
                                stock_move_id=False
                                for move in moves:
                                    stock_move_id=move.id
                                if stock_move_id:
                                    vals['stock_move_id'] = stock_move_id
                                else:
                                    anomalies.append('Id ligne de réception %s non trouvée'%val)
                            #**************************************************

                            #** Recherche article ***************************
                            if key=='article':
                                products = self.env['product.product'].search([('is_code','=',val)])
                                product_id=False
                                for product in products:
                                    product_id=product.id
                                if product_id:
                                    vals['product_id'] = product_id
                                else:
                                    anomalies.append("Article '%s' non trouvée"%(val or ''))
                            #**************************************************

                           #** Recherche descriparticle ***************************
                            if key=='descriparticle':
                                if not val or val=='':
                                    anomalies.append("Description manquante")
                            #**************************************************

                            #** Recherche fournissur **************************
                            if key=='codefour':
                                partners = self.env['res.partner'].search([('is_code','=',val)])
                                partner_id=False
                                for partner in partners:
                                    partner_id=partner.id
                                if partner_id:
                                    vals['partner_id'] = partner_id
                                else:
                                    anomalies.append("Fournisseur '%s' non trouvée"%(val or ''))
                            #**************************************************

                            #** Recherche TVA **************************
                            if key=='codetvafact' and val:
                                taxs = self.env['account.tax'].search([('description','=',val)])
                                tax_id=False
                                for tax in taxs:
                                    tax_id=tax.id
                                if tax_id:
                                    vals['tax_id'] = tax_id
                                else:
                                    anomalies.append("TVA '%s' non trouvée"%(val or ''))
                            #**************************************************

                    #** Comparatif prix d'origine et prix facturé *************
                    prixorigine = vals.get('prixorigine') or 0
                    prixfact    = vals.get('prixfact') or 0
                    if prixorigine>0 and prixfact>0 and prixorigine!=prixfact:
                        anomalies.append("Le prix d'origine '%s' est différent du prix facturé %s"%(prixorigine,prixfact))

                    #** Vérification total ligne facturé **********************
                    prixfact      = round(vals.get('prixfact')     or 0, 2)
                    qtefact       = round(vals.get('qtefact')      or 0, 2)
                    totalfacture  = round(vals.get('totalfacture') or 0, 2)
                    total_calcule = round(prixfact*qtefact,2)
                    if total_calcule != totalfacture:
                        anomalies.append("Le total facturé %s est différent de %s x %s (%s)"%(totalfacture,prixfact,qtefact,total_calcule))

                    if len(anomalies)>0:
                        vals['anomalies'] = '\n'.join(anomalies)
                    
                    line = self.env['is.import.facture.owork.line'].create(vals)


            #** Vérfication que total facturé correspond au total des lignes **
            factures={}
            nb_anomalies = 0
            for line in obj.line_ids:
                if line.anomalies:
                    nb_anomalies+=1
                numfac = line.numfac
                if numfac not in factures:
                    factures[numfac] = 0
                factures[numfac] += line.totalfacture
            for line in obj.line_ids:
                numfac = line.numfac
                total_calcule = round(factures[numfac],2)
                if line.montantht != total_calcule:
                    anomalie = "Le total des lignes %s est différent du total de la facture %s"%(total_calcule,line.montantht)
                    if line.anomalies:
                        line.anomalies="%s\n%s"%(line.anomalies,anomalie)
                    else:
                        line.anomalies=anomalie
            #******************************************************************
            
            obj.nb_lignes    = len(obj.line_ids)
            obj.nb_factures  = len(factures)
            obj.nb_anomalies = nb_anomalies


    def voir_les_lignes(self):
        for obj in self:
            return {
                'name'     : obj.name,
                'view_mode': 'tree,form',
                'res_model': 'is.import.facture.owork.line',
                'domain'   : [('import_id' ,'=',obj.id)],
                'type'     : 'ir.actions.act_window',
                'limit'    : 1000,
            }



    def creation_factures(self):
        for obj in self:

            #** Liste des factures à créer ************************************
            factures={}
            for line in obj.line_ids:
                numfac = line.numfac
                if numfac not in factures:
                    if line.partner_id and line.datefact and line.numfac:
                        vals = {
                            'partner_id'      : line.partner_id.id,
                            'journal_id'      : 2,
                            'move_type'       : 'in_invoice',
                            'invoice_date'    : line.datefact,
                            'date'            : line.datefact,
                            'invoice_date_due': line.datefact,
                            'is_bon_a_payer'  : True,
                            'supplier_invoice_number': line.numfac,
                            'is_owork_id'     : obj.id,
                        }
                        factures[numfac]=vals
            #******************************************************************

            for facture in factures:
                lines = []
                invoice_line_tax_id=[]
                for line in obj.line_ids:
                    if line.numfac==facture:
                        product_id      = line.product_id.id
                        if product_id and line.stock_move_id.id:
                            description     = line.descriparticle
                            quantite        = line.qtefact
                            invoice_line_tax_id=[]
                            # for taxe_id in line.taxe_ids:
                            #     invoice_line_tax_id.append(taxe_id.id)
                            # if len(invoice_line_tax_id)==0:
                            #     invoice_line_tax_id=False
                            #is_document=line.move_id.purchase_line_id.is_num_chantier
                            #if is_document==False:
                            #    is_document=line.move_id.purchase_line_id.order_id.is_document
                            v = {
                                'product_id'      : product_id,
                                'name'            : description,
                                'quantity'        : line.qtefact,
                                'product_uom_id'  : line.stock_move_id.product_uom.id,
                                'price_unit'      : line.prixfact,
                                'tax_ids'         : [(6,0,invoice_line_tax_id)],
                                #'is_document'     : is_document,
                                'is_move_id'      : line.stock_move_id.id,
                                'purchase_line_id': line.stock_move_id.purchase_line_id.id,
                                'is_section_analytique_id': line.product_id.is_section_analytique_ha_id.id,
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
            obj.state='traite'


            
    def voir_les_factures(self):
        for obj in self:
            ids=[]
            for invoice in obj.invoice_ids:
                ids.append(invoice.id)
            print(ids)

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


class is_import_facture_owork_line(models.Model):
    _name = "is.import.facture.owork.line"
    _description = "Lignes importation factures O'Work"

    import_id      = fields.Many2one('is.import.facture.owork', "Import O'Work", required=True, ondelete='cascade')


    codeetab       = fields.Char("Code etab")
    codefour       = fields.Char("Code Four fact")
    codefourrcp    = fields.Char("Code Four Rcp")
    codeadrfour    = fields.Char("Code adr four")
    numbl          = fields.Char("Num BL")
    numrecept      = fields.Char("Num rcp")
    daterecpt      = fields.Date("Date rcp")
    numcde         = fields.Char("Num Cde")

    article        = fields.Char("Code Article")
    descriparticle = fields.Char("Description article")
    qterestefac    = fields.Float("Qt reste fac")
    prixorigine    = fields.Float("Prix Origine")
    total          = fields.Float("Total")
    codetvaorigine = fields.Char("Code TVA Origine")
    codetvafact    = fields.Char("Code TVA Fac")
    prixfact       = fields.Float("Prix Fac")
    qtefact        = fields.Float("Qt fac")
    datefact       = fields.Date("Date Fac")
    numfac         = fields.Char("Num Fac")
    montantht      = fields.Float("Montant HT")
    montanttva     = fields.Float("Montant TVA")
    montanttc      = fields.Float("Montant TTC")
    numidodoo      = fields.Integer("Id Odoo")

    totalfacture   = fields.Float("Total Facture")

    picking_id     = fields.Many2one('stock.picking', "Réception")
    stock_move_id  = fields.Many2one('stock.move', "Ligne de réception")
    partner_id     = fields.Many2one('res.partner', "Fournisseur")
    product_id     = fields.Many2one('product.product', "Article")
    tax_id         = fields.Many2one('account.tax', "TVA")
    invoice_id     = fields.Many2one('account.move', "Facture")

    fichier        = fields.Char("Fichier")
    anomalies      = fields.Text("Anomalies")
    
