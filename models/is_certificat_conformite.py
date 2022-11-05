# -*- coding: utf-8 -*-
from odoo import models,fields,api
from datetime import datetime
#import os
#from pyPdf import PdfFileWriter, PdfFileReader
#import tempfile
#from contextlib import closing


class is_bon_transfert(models.Model):
    _inherit='is.bon.transfert'

    def _compute_is_certificat_conformite_msg(self):
        for obj in self:
            msg = False
            if obj.partner_id.is_certificat_matiere:
                nb=0
                for line in obj.line_ids:
                    certificat = self.env['is.certificat.conformite'].GetCertificat(obj.partner_id, line.product_id.id)
                    if not certificat:
                        nb+=1
                msg=u"Ne pas oublier de fournir les certificats matières."
                if nb:
                    msg+=u"\nATTENTION : Il manque "+str(nb)+u" certificats !"
            obj.is_certificat_conformite_msg = msg

    is_certificat_conformite_msg = fields.Text('Certificat de conformité', compute='_compute_is_certificat_conformite_msg', store=False, readonly=True)


    def imprimer_certificat_action(self):
        for obj in self:
            cr , uid, context = self.env.args
            db = self._cr.dbname
            path="/tmp/certificats-" + db + '-'+str(uid)
            cde="rm -Rf " + path
            os.popen(cde).readlines()
            if not os.path.exists(path):
                os.makedirs(path)
            paths=[]
            for line in obj.line_ids:
                certificat = self.env['is.certificat.conformite'].GetCertificat(obj.partner_id, line.product_id.id)
                if certificat:
                    vals={
                        'client_order_ref': False,
                        'order_id'        : False,
                        'picking_id'      : False,
                        'bon_transfert_id': obj.id,
                        'qt_liv'          : line.quantite,
                        'rsp_livraison'   : self._uid,
                        'num_lot'         : False,
                        'date_fabrication': False,
                    }
                    certificat.write(vals)
                    #** Recherche des lots scannés ************************************
                    lots={}
                    for um in obj.galia_um_ids:
                        if um.product_id == line.product_id:
                            for uc in um.uc_ids:
                                if uc.production not in lots:
                                    lots[uc.production] = {}
                                    lots[uc.production]["qt"]=0
                                lots[uc.production]["qt"]+=uc.qt_pieces
                                date_fabrication = uc.date_creation[:10]
                                lots[uc.production]["date_fabrication"]=date_fabrication   
                    if lots=={}:
                        lots[' ']={}
                        lots[' ']["date_fabrication"]=False
                        lots[' ']["qt"]=False
                    x=0
                    for lot in lots:
                        x+=1
                        certificat.num_lot          = lot
                        certificat.date_fabrication = lots[lot]["date_fabrication"]
                        certificat.qt_liv           = lots[lot]["qt"]
                        result = self.env['report'].get_pdf(certificat, 'is_pg_2019.is_certificat_conformite_report')
                        file_name = path + '/'+str(line.id) + '-' + str(x) + '.pdf'
                        fd = os.open(file_name,os.O_RDWR|os.O_CREAT)
                        try:
                            os.write(fd, result)
                        finally:
                            os.close(fd)
                        paths.append(file_name)

            # ** Merge des PDF *****************************************************
            path_merged=self.env['stock.picking']._merge_pdf(paths)
            pdfs = open(path_merged,'rb').read().encode('base64')
            # **********************************************************************

            # ** Recherche si une pièce jointe est déja associèe *******************
            attachment_obj = self.env['ir.attachment']
            name = 'certificats.pdf'
            attachments = attachment_obj.search([('name','=',name)],limit=1)
            # **********************************************************************

            # ** Creation ou modification de la pièce jointe ***********************
            vals = {
                'name':        name,
                'datas_fname': name,
                'type':        'binary',
                'datas':       pdfs,
            }
            if attachments:
                for attachment in attachments:
                    attachment.write(vals)
                    attachment_id=attachment.id
            else:
                attachment = attachment_obj.create(vals)
                attachment_id=attachment.id
            #***********************************************************************

            #** Envoi du PDF mergé dans le navigateur ******************************
            if attachment_id:
                return {
                    'type' : 'ir.actions.act_url',
                    'url': '/web/binary/saveas?model=ir.attachment&field=datas&id='+str(attachment_id)+'&filename_field=name',
                    'target': 'new',
                }
            #***********************************************************************







class is_bon_transfert_line(models.Model):
    _inherit='is.bon.transfert.line'

    def _compute_is_certificat_conformite_vsb(self):
        for obj in self:
            vsb = False
            if obj.bon_transfert_id.partner_id.is_certificat_matiere:
                certificat = self.env['is.certificat.conformite'].GetCertificat(obj.bon_transfert_id.partner_id, obj.product_id.id)
                if certificat:
                    vsb = 1
                else:
                    vsb = 2
            obj.is_certificat_conformite_vsb = vsb

    is_certificat_conformite_vsb = fields.Integer('Certificat de conformité', compute='_compute_is_certificat_conformite_vsb', store=False, readonly=True)


    def pas_de_certifcat_action(self):
        for obj in self:
            print(obj)


    def imprimer_certificat_action(self):
        dummy, view_id = self.env['ir.model.data'].get_object_reference('is_pg_2019', 'is_certificat_conformite_form_view')
        for obj in self:
            certificat = self.env['is.certificat.conformite'].GetCertificat(obj.bon_transfert_id.partner_id, obj.product_id.id)
            if certificat:
                return {
                    'name': "Certificat de conformité",
                    'view_mode': 'form',
                    'view_id': view_id,
                    'view_type': 'form',
                    'res_model': 'is.certificat.conformite',
                    'type': 'ir.actions.act_window',
                    'res_id': certificat.id,
                    'domain': '[]',
                }









class stock_picking(models.Model):
    _inherit = "stock.picking"
    
    def _compute_is_certificat_conformite_msg(self):
        for obj in self:
            msg = False
            if obj.partner_id.is_certificat_matiere:
                nb=0
                for line in obj.move_lines:
                    certificat = self.env['is.certificat.conformite'].GetCertificat(obj.partner_id, line.product_id.id)
                    if not certificat:
                        nb+=1
                msg=u"Ne pas oublier de fournir les certificats matières."
                if nb:
                    msg+=u"\nATTENTION : Il manque "+str(nb)+u" certificats !"
            obj.is_certificat_conformite_msg = msg

    is_certificat_conformite_msg = fields.Text('Certificat de conformité', compute='_compute_is_certificat_conformite_msg', store=False, readonly=True)


    def _merge_pdf(self, documents):
        """Merge PDF files into one.
        :param documents: list of path of pdf files
        :returns: path of the merged pdf
        """
        writer = PdfFileWriter()
        streams = []  # We have to close the streams *after* PdfFilWriter's call to write()
        for document in documents:
            pdfreport = file(document, 'rb')
            streams.append(pdfreport)
            reader = PdfFileReader(pdfreport)
            for page in range(0, reader.getNumPages()):
                writer.addPage(reader.getPage(page))
        merged_file_fd, merged_file_path = tempfile.mkstemp(suffix='.pdf', prefix='report.merged.tmp.')
        with closing(os.fdopen(merged_file_fd, 'w')) as merged_file:
            writer.write(merged_file)
        for stream in streams:
            stream.close()
        return merged_file_path


    def imprimer_certificat_action(self):
        for obj in self:
            if obj.is_sale_order_id.is_liste_servir_id:
                obj.is_sale_order_id.is_liste_servir_id.affecter_uc_aux_lignes_ls_action()
            cr , uid, context = self.env.args
            db = self._cr.dbname
            path="/tmp/certificats-" + db + '-'+str(uid)
            cde="rm -Rf " + path
            os.popen(cde).readlines()
            if not os.path.exists(path):
                os.makedirs(path)
            paths=[]
            for move in obj.move_lines:
                certificat = self.env['is.certificat.conformite'].GetCertificat(obj.partner_id, move.product_id.id)
                if certificat:
                    self.env['is.certificat.conformite'].WriteCertificat(certificat,move)

                    #** Recherche des lots scannés ************************************
                    lots={}
                    if move.picking_id.is_sale_order_id:
                        if  move.picking_id.is_sale_order_id.is_liste_servir_id:
                            if move.picking_id.is_sale_order_id.is_liste_servir_id.galia_um_ids:
                                for um in move.picking_id.is_sale_order_id.is_liste_servir_id.galia_um_ids:
                                    if um.product_id == move.product_id:
                                        for uc in um.uc_ids:
                                            if uc.production not in lots:
                                                lots[uc.production] = {}
                                                lots[uc.production]["qt"]=0
                                            lots[uc.production]["qt"]+=uc.qt_pieces
                                            date_fabrication = uc.date_creation[:10]
                                            lots[uc.production]["date_fabrication"]=date_fabrication   
                    if lots=={}:
                        lots[' ']={}
                        lots[' ']["date_fabrication"]=False
                        lots[' ']["qt"]=False
                    x=0

                    for lot in lots:
                        #** Recherche qt livrée par lot et par commande client **********
                        qt_liv=0
                        if move.picking_id.is_sale_order_id:
                            if  move.picking_id.is_sale_order_id.is_liste_servir_id:
                                if move.picking_id.is_sale_order_id.is_liste_servir_id.galia_um_ids:
                                    for um in move.picking_id.is_sale_order_id.is_liste_servir_id.galia_um_ids:
                                        if um.product_id == move.product_id:
                                            for uc in um.uc_ids:
                                                if uc.production==lot:
                                                    if uc.ls_line_id and uc.ls_line_id.client_order_ref==move.is_sale_line_id.is_client_order_ref:
                                                        qt_liv+=uc.qt_pieces
                        certificat.qt_liv  = qt_liv
                        #certificat.qt_liv = lots[lot]["qt"]
                        #****************************************************************

                        certificat.client_order_ref = move.is_sale_line_id.is_client_order_ref
                        certificat.num_lot          = lot
                        certificat.date_fabrication = lots[lot]["date_fabrication"]
                        x+=1
                        result = self.env['report'].get_pdf(certificat, 'is_pg_2019.is_certificat_conformite_report')
                        file_name = path + '/'+str(move.id) + '-' + str(x) + '.pdf'
                        fd = os.open(file_name,os.O_RDWR|os.O_CREAT)
                        try:
                            os.write(fd, result)
                        finally:
                            os.close(fd)
                        paths.append(file_name)

            # ** Merge des PDF *****************************************************
            path_merged=self._merge_pdf(paths)
            pdfs = open(path_merged,'rb').read().encode('base64')
            # **********************************************************************

            # ** Recherche si une pièce jointe est déja associèe *******************
            attachment_obj = self.env['ir.attachment']
            name = 'certificats.pdf'
            attachments = attachment_obj.search([('name','=',name)],limit=1)
            # **********************************************************************

            # ** Creation ou modification de la pièce jointe ***********************
            vals = {
                'name':        name,
                'datas_fname': name,
                'type':        'binary',
                'datas':       pdfs,
            }
            if attachments:
                for attachment in attachments:
                    attachment.write(vals)
                    attachment_id=attachment.id
            else:
                attachment = attachment_obj.create(vals)
                attachment_id=attachment.id
            #***********************************************************************

            #** Envoi du PDF mergé dans le navigateur ******************************
            if attachment_id:
                return {
                    'type' : 'ir.actions.act_url',
                    'url': '/web/binary/saveas?model=ir.attachment&field=datas&id='+str(attachment_id)+'&filename_field=name',
                    'target': 'new',
                }
            #***********************************************************************


class stock_move(models.Model):
    _inherit = "stock.move"
    
    def _compute_is_certificat_conformite_vsb(self):
        for obj in self:
            vsb = False
            if obj.picking_id.partner_id.is_certificat_matiere:
                certificat = self.env['is.certificat.conformite'].GetCertificat(obj.picking_id.partner_id, obj.product_id.id)
                if certificat:
                    vsb = 1
                else:
                    vsb = 2
            obj.is_certificat_conformite_vsb = vsb

    is_certificat_conformite_vsb = fields.Integer('Certificat de conformité', compute='_compute_is_certificat_conformite_vsb', store=False, readonly=True)


    def pas_de_certifcat_action(self):
        for obj in self:
            print(obj)


    def imprimer_certificat_action(self):
        dummy, view_id = self.env['ir.model.data'].get_object_reference('is_pg_2019', 'is_certificat_conformite_form_view')
        for obj in self:
            certificat = self.env['is.certificat.conformite'].GetCertificat(obj.picking_id.partner_id, obj.product_id.id)
            if certificat:
                self.env['is.certificat.conformite'].WriteCertificat(certificat,obj)
                return {
                    'name': "Certificat de conformité",
                    'view_mode': 'form',
                    'view_id': view_id,
                    'view_type': 'form',
                    'res_model': 'is.certificat.conformite',
                    'type': 'ir.actions.act_window',
                    'res_id': certificat.id,
                    'domain': '[]',
                }


class is_certificat_conformite(models.Model):
    _name='is.certificat.conformite'
    _description="is_certificat_conformite"
    _order='product_id,client_id'
    _sql_constraints = [('product_id_client_id_uniq','UNIQUE(product_id,client_id)', u'Un certificat existe déjà pour ce client et pour cet article !')] 
    _rec_name = 'product_id'


    @api.depends('rsp_livraison')
    def _compute_job_id(self):
        for obj in self:
            job_id=False
            if obj.rsp_livraison:
                employes = self.env['hr.employee'].search([("user_id","=",obj.rsp_livraison.id)])
                for employe in employes:
                    job_id=employe.job_id.id
            obj.job_id=job_id


    @api.depends('rsp_livraison')
    def _compute_date_bl(self):
        for obj in self:
            date_bl = False
            if obj.picking_id:
                date_bl = obj.picking_id.is_date_expedition
            if obj.bon_transfert_id:
                date_bl = obj.bon_transfert_id.date_creation
            obj.date_bl = date_bl


    product_id       = fields.Many2one('product.product', u"Article", domain=[('sale_ok','=',True)], required=True, index=True)
    client_id        = fields.Many2one('res.partner', u'Client', domain=[('is_company','=',True),('customer','=',True)], required=True, index=True)
    ref_client       = fields.Char(u"Référence client", related='product_id.is_ref_client', readonly=True)
    ref_plan         = fields.Char(u"Référence plan"  , related='product_id.is_ref_plan'  , readonly=True)
    ind_plan         = fields.Char(u"Indice plan"     , related='product_id.is_ind_plan'  , readonly=True)
    client_order_ref = fields.Char(u'N° commande client')
    order_id         = fields.Many2one('sale.order'   , u'N° de commande')
    picking_id       = fields.Many2one('stock.picking', u'N°BL', domain=[('picking_type_id','=',2)])
    bon_transfert_id = fields.Many2one('is.bon.transfert', u'Bon de transfert')
    date_bl          = fields.Date(u"Date d'expédition", compute='_compute_date_bl', store=False, readonly=True)





    qt_liv           = fields.Float(u"Quantité livrée")
    num_lot          = fields.Char(u"N° de lot")
    date_fabrication = fields.Date(u"Date de fabrication")
    rsp_qualite      = fields.Many2one('res.users', u'Responsable qualité')
    rsp_livraison    = fields.Many2one('res.users', u'Responsable livraison')
    job_id           = fields.Many2one('hr.job', u'Fonction', compute='_compute_job_id', store=False, readonly=True)
    pourcentage_maxi = fields.Char(u"Pourcentage maxi de broyé", default="0%")
    reference_ids    = fields.One2many('is.certificat.conformite.reference', 'certificat_id', u"Références", copy=True)
    autre_ids        = fields.One2many('is.certificat.conformite.autre'    , 'certificat_id', u"Autre"     , copy=True)
    autre2_ids       = fields.One2many('is.certificat.conformite.autre2'   , 'certificat_id', u"Autre 2"   , copy=True)
    fabricant_ids    = fields.One2many('is.certificat.conformite.fabricant', 'certificat_id', u"Fabricants", copy=True)
    state            = fields.Selection([
            ('creation', u'Création'),
            ('valide'  , u"Validé"),
        ], "Etat", readonly=True, default="creation")


    def GetCertificat(self,partner_id,product_id):
        filtre = [
            ('client_id.is_code' , '=', partner_id.is_code),
            ('product_id', '=', product_id),
            ('state'     , '=', 'valide'),
        ]
        certificats = self.env['is.certificat.conformite'].search(filtre)
        certificat = certificats and certificats[0] or False
        return certificat


    def WriteCertificat(self,certificat,move):
        if move and move.is_sale_line_id and move.picking_id:
            if certificat.picking_id != move.picking_id:
                certificat.num_lot          = False
                certificat.date_fabrication = False
            orders=[]
            for line in move.picking_id.move_lines:
                if line.product_id==move.product_id:
                    order = line.is_sale_line_id.is_client_order_ref
                    if order not in orders:
                        orders.append(order)
            vals={
                'client_order_ref': u", ".join(orders),
                'order_id'        : move.is_sale_line_id.order_id.id,
                'picking_id'      : move.picking_id.id,
                'bon_transfert_id': False,
                'date_bl'         : move.picking_id.is_date_expedition,
                'qt_liv'          : move.product_uom_qty,
                'rsp_livraison'   : self._uid,
                'num_lot'         : False,
                'date_fabrication': False,
            }
            certificat.write(vals)


    def vers_valide(self):
        for obj in self:
            obj.state='valide'


    def vers_creation(self):
        for obj in self:
            obj.state='creation'


class is_certificat_conformite_reference(models.Model):
    _name='is.certificat.conformite.reference'
    _description="is_certificat_conformite_reference"
    _order='certificat_id,reference'

    certificat_id = fields.Many2one('is.certificat.conformite', "Certificat de conformité", required=True, ondelete='cascade', readonly=True)
    reference     = fields.Char(u"Référence", required=True)
    fabricant     = fields.Char(u"Fabricant de la matière de base", required=True)
    ref_precise   = fields.Char(u"Référence précise de la matière de base")
    epaisseur     = fields.Char(u"Epaisseur minimale mesurable sur la pièce")
    classe        = fields.Char(u"Classe d'inflammabilité de la matière dans l'épaisseur mini")


class is_certificat_conformite_autre(models.Model):
    _name='is.certificat.conformite.autre'
    _description="is_certificat_conformite_autre"
    _order='certificat_id,autre_conformite'

    certificat_id         = fields.Many2one('is.certificat.conformite', "Certificat de conformité", required=True, ondelete='cascade', readonly=True)
    autre_conformite      = fields.Char(u"Autres conformités", required=True)
    epaisseur_mini        = fields.Char(u"Epaisseur mini mesurable sur la pièce")
    classe_inflammabilite = fields.Char(u"Classe d'inflammabilité de la matière dans l'épaisseur mini")


class is_certificat_conformite_autre2(models.Model):
    _name='is.certificat.conformite.autre2'
    _description="is_certificat_conformite_autre2"
    _order='certificat_id'

    certificat_id = fields.Many2one('is.certificat.conformite', "Certificat de conformité", required=True, ondelete='cascade', readonly=True)
    autre         = fields.Char(u"Autre", required=True)


class is_certificat_conformite_fabricant(models.Model):
    _name='is.certificat.conformite.fabricant'
    _description="is_certificat_conformite_fabricant"
    _order='certificat_id,fabricant'

    certificat_id = fields.Many2one('is.certificat.conformite', "Certificat de conformité", required=True, ondelete='cascade', readonly=True)
    fabricant   = fields.Char(u"Fabricant de la matière pigmentée", required=True)
    pourcentage = fields.Char(u"% de la matière pigmentée", required=True)

