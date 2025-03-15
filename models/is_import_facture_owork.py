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
    line_ids       = fields.One2many('is.import.facture.owork.line', 'import_id', "Lignes")


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


            #** Vérfication que total facture correspond au total des lignes **
            factures={}
            for line in obj.line_ids:
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
    partner_id     = fields.Many2one('res.partner', "Fournisseur")
    product_id     = fields.Many2one('product.product', "Article")
    tax_id         = fields.Many2one('account.tax', "TVA")

    fichier        = fields.Char("Fichier")
    anomalies      = fields.Text("Anomalies")
    
