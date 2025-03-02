# -*- coding: utf-8 -*-
from odoo import models, fields, api # type: ignore
import csv
import base64


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
        for obj in self:
            obj.line_ids.unlink()
            for attachment in obj.attachment_ids:
                csvfile = base64.decodebytes(attachment.datas).decode('cp1252')
                csvfile = csvfile.split("\r\n")
                csvfile = csv.DictReader(csvfile, delimiter=';')
                for ct, lig in enumerate(csvfile):
                    nb=len(lig)

                    vals={
                        'import_id': obj.id
                    }
                    for key in lig:
                        vals[key] = lig[key]
                    line = self.env['is.import.facture.owork.line'].create(vals)
                    print(ct,nb,lig,line)


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
    montantht      = fields.Char("Montant HT")
    daterecpt      = fields.Char("Date rcp")
    numrecept      = fields.Char("Num rcp")
    montanttva     = fields.Char("Montant TVA")
    numcde         = fields.Char("Num Cde")
    total          = fields.Char("Total")
    numbl          = fields.Char("Num BL")
    codefour       = fields.Char("Code Four")
    prixfact       = fields.Char("Prix Fac")
    numfac         = fields.Char("Num Fac")
    numidodoo      = fields.Char("Id Odoo")
    prixorigine    = fields.Char("Prix Origine")
    datefact       = fields.Char("Date Fac")
    codefourrcp    = fields.Char("Code Four Rcp")
    codeadrfour    = fields.Char("Code adr four")
    descriparticle = fields.Char("Description article")
    codetvaorigine = fields.Char("Code TVA Origine")
    codetvafact    = fields.Char("Code TVA Fac")
    codeetab       = fields.Char("Code etab")
    qterestefac    = fields.Char("Qt reste fac")
    qtefact        = fields.Char("Qt fac")
    totalfacture   = fields.Char("Total Facture")
    article        = fields.Char("Article")
    montanttc      = fields.Char("Montant TTC")
