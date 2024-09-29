# -*- coding: utf-8 -*-

from odoo import models,fields,api
from odoo.exceptions import AccessError, ValidationError, UserError
import time
from datetime import date, datetime
import base64
import os
#from pyPdf import PdfFileWriter, PdfFileReader
from PyPDF2 import PdfFileWriter, PdfFileReader, PdfFileMerger
import tempfile


#from ftplib import FTP
#from contextlib import closing
import logging
_logger = logging.getLogger(__name__)


modele_mail=u"""
<html>
    <head>
        <meta content="text/html; charset=UTF-8" http-equiv="Content-Type">
    </head>
    <body>
        <font>Bonjour, </font>
        <br><br>
        <font> Veuillez trouver ci-joint notre facture.</font>
        <br><br>
        Cordialement <br><br>
        [from]<br>
    </body>
</html>
"""


class is_account_folio(models.Model):
    _name  = 'is.account.folio'
    _description="Folio"
    _order = 'name desc'

    name          = fields.Char('N° de Folio'              , readonly=True)
    date_creation = fields.Date("Date de création"         , readonly=True, default=lambda *a: fields.datetime.now())
    createur_id   = fields.Many2one('res.users', 'Créé par', readonly=True, default=lambda self: self.env.user)
    invoice_ids   = fields.One2many('account.move', 'is_folio_id', 'Factures', readonly=True)

    def create(self, vals):
        data_obj = self.env['ir.model.data']
        sequence_ids = data_obj.search([('name','=','seq_is_account_folio')])
        if len(sequence_ids)>0:
            sequence_id = sequence_ids[0].res_id
            vals['name'] = self.env['ir.sequence'].get_id(sequence_id, 'id')
        res = super(is_account_folio, self).create(vals)
        return res



class account_invoice(models.Model):
    _inherit = 'account.move'
    _order   = 'id desc'

    amount_untaxed_signed = fields.Monetary(string='Montant HT')
  
    invoice_date       = fields.Date(default=fields.Datetime.now)
    is_document        = fields.Char('Document'     , help="Ce champ est utilisé dans les factures diverses pour saisir le moule ou le n° d'investissement")
    is_num_cde_client  = fields.Char('N° Cde Client', help="Ce champ est utilisé dans les factures diverses sans commande client dans Odoo")
    supplier_invoice_number  = fields.Char('N° facture fournisseur')
    is_num_bl_manuel   = fields.Char('N° BL manuel' , help="Ce champ est utilisé dans les factures diverses sans bon de livraison dans Odoo")
    is_escompte        = fields.Float("Escompte", compute='_compute')
    is_tva             = fields.Float("TVA"     , compute='_compute', help="Taxes sans l'escompte")
    is_folio_id        = fields.Many2one('is.account.folio', 'Folio'      , copy=False)
    is_export_cegid_id = fields.Many2one('is.export.cegid' , 'Folio Cegid', copy=False)
    is_bon_a_payer     = fields.Boolean("Bon à payer", default=True)
    is_type_facture    = fields.Selection([
            ('standard'  , u'Standard'),
            ('diverse'   , u'Diverse'),
            ('avoir-qt'  , u'Avoir quantité'),
            ('avoir-prix', u'Avoir prix'),
        ], u"Type de facture", default='standard', index=True)
    is_origine_id     = fields.Many2one('account.move', "Facture d'origine")
    is_mode_envoi_facture = fields.Selection([
        ('courrier'        , 'Envoi par courrier'),
        ('courrier2'       , 'Envoi par courrier en double exemplaire'),
        ('mail'            , 'Envoi par mail (1 mail par facture)'),
        ('mail2'           , 'Envoi par mail (1 mail par facture en double exemplaire)'),
        ('mail_client'     , 'Envoi par mail (1 mail par client)'),
        ('mail_client_bl'  , 'Envoi par mail avec BL (1 mail par client)'),
        ('mail_regroupe_bl', 'Regroupement des BL sur une même facture et envoi par mail'),
    ], "Mode d'envoi de la facture")
    is_date_envoi_mail = fields.Datetime("Mail envoyé le", readonly=False, copy=False)
    is_masse_nette     = fields.Float("Masse nette (Kg)")
    is_facture_pdf_ids       = fields.One2many('is.account.move.pdf', 'move_id', 'Facture PDF')
    state = fields.Selection([
        ('draft' , 'Brouillon'),
        ('posted', 'Validée'),
        ('cancel', 'Annulée'),
    ], "État")


    def _compute_name(self):
        res=super()._compute_name()
        for obj in self:
            if obj.move_type in ['out_invoice','out_refund']:
                for line in obj.invoice_line_ids:
                    state="2binvoiced"
                    if obj.state in ["posted","draft"]:
                        state="invoiced"
                    line.is_move_id.invoice_state = state
                    line.is_move_id.picking_id._compute_invoice_state()
        return res


    @api.onchange('partner_id')
    def pg_onchange_partner_id(self):
        self.is_mode_envoi_facture = self.partner_id.is_mode_envoi_facture


    # invoice_state = fields.Selection([
    #     ('2binvoiced', u'à Facturer'),
    #     ('none'      , u'Annulé'),
    #     ('invoiced'  , u'Facturé'),




    # @api.depends('state')
    # def pg_onchange_state(self):
    #     for obj in self:
    #         for line in obj.invoice_line_ids:



    def _compute(self):
        for obj in self:
            escompte = tva = 0
            #for tax in obj.tax_ids:
                # if tax.account_id.code=='665000':
                #     escompte=escompte+tax.amount
                # else:
                #     tva=tva+tax.amount
            for line in obj.line_ids:
                if line.account_id.code=='665000':
                    escompte=escompte+line.amount_currency
            #    else:
            #        tva=tva+line.amount_currency
            obj.is_escompte = escompte
            obj.is_tva      = tva


    def voir_facture_client_action(self):
        for obj in self:
            #view_id=self.env.ref('is_plastigray16.is_invoice_form')
            view_id=self.env.ref('is_plastigray16.is_account_view_move_form')
            res= {
                'name': 'Facture Client',
                'view_mode': 'form',
                'res_model': 'account.move',
                'res_id': obj.id,
                'view_id': view_id.id,
                'type': 'ir.actions.act_window',
                'context': {'default_move_type':'out_invoice', 'move_type':'out_invoice', 'journal_type': 'sale'},
                'domain': [('move_type','=','out_invoice'),('journal_type','=','sale')],
            }
            return res


    def voir_facture_fournisseur_action(self):
        for obj in self:
            #view_id=self.env.ref('is_plastigray16.is_invoice_supplier_form')
            view_id=self.env.ref('is_plastigray16.is_account_view_move_form')
            res= {
                'name': 'Facture Client',
                'view_mode': 'form',
                'res_model': 'account.move',
                'res_id': obj.id,
                'view_id': view_id.id,
                'type': 'ir.actions.act_window',
                'context': {'default_move_type':'in_invoice', 'move_type':'in_invoice'},
                'domain': [('move_type','=','in_invoice')],
            }
            return res


    def valider_facture_brouillon_action(self):
        """Valider les factures brouillon"""
        domain = [('id', 'in', self._context.get('active_ids', [])), ('state', '=', 'draft')]
        moves = self.env['account.move'].search(domain).filtered('line_ids')
        if not moves:
            raise UserError('There are no journal items in the draft state to post.')
        moves._post()


    def invoice_print(self):
        assert len(self) == 1, 'This option should only be used for a single id at a time.'
        self.sent = True
        res = self.env.ref('is_plastigray16.is_report_invoice').report_action(self)
        return res


    def _merge_pdf(self, documents):
        merged_file_fd, merged_file_path = tempfile.mkstemp(suffix='.pdf', prefix='report.merged.tmp.')
        merger = PdfFileMerger()
        for document in documents:
            merger.append(document)
        merger.write(merged_file_path)
        merger.close()
        return merged_file_path


    def imprimer_simple_double(self):
        """Imprimer en simple ou double exemplaire"""
        uid=self._uid
        db = self._cr.dbname
        path="/tmp/factures-" + db + '-'+str(uid)
        cde="rm -Rf " + path
        os.popen(cde).readlines()
        if not os.path.exists(path):
            os.makedirs(path)

        nb=len(self)
        ct=1
        paths=[]
        for obj in self:
            msg = '%s/%s - Imprimer en simple ou double exemplaire : %s'%(ct,nb,obj.name)
            _logger.info(msg)
            ct+=1

            #TODO : Modif du 28/09/24 => Suppression piece jointe avant création et ajout dans le tableau
            obj.attachment_ids.unlink()
            result = self.env['ir.actions.report']._render_qweb_pdf('account.account_invoices',[obj.id])[0]
            obj.sauvegarde_pdf(result)
            #******************************************************************

            r = range(1, 2)
            if obj.is_mode_envoi_facture=='courrier2':
                r = range(1, 3)
            for x in r:
                file_name = path + '/'+str(obj.name) + '-' + str(x) + '.pdf'
                fd = os.open(file_name,os.O_RDWR|os.O_CREAT)
                try:
                    os.write(fd, result)
                finally:
                    os.close(fd)
                paths.append(file_name)


        # ** Merge des PDF *****************************************************
        path_merged=self._merge_pdf(paths)
        pdfs = open(path_merged,'rb').read()
        # **********************************************************************


        # ** Recherche si une pièce jointe est déja associèe *******************
        attachment_obj = self.env['ir.attachment']
        name = 'factures-' + db + '-' + str(uid) + '.pdf'
        attachments = attachment_obj.search([('name','=',name)],limit=1)
        # **********************************************************************


        # ** Creation ou modification de la pièce jointe ***********************
        vals = {
            'name':        name,
            'type':        'binary',
            'datas':       base64.b64encode(pdfs),
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
                'url': '/web/content/%s?download=true'%(attachment_id),
            }
        #***********************************************************************

    def sauvegarde_pdf(self, datas):
        for obj in self:
            # #TODO : La comparaison des md5 ne fonctionne pas, car à chaque PDF généré, le md5 est différent
            # def get_md5(path,datas):
            #     f = open(path,'wb')
            #     f.write(base64.b64decode(datas))
            #     f.close()
            #     f = open(path,'r')
            #     cde="sha1sum %s"%path
            #     f = os.popen(cde)
            #     md5 = f.read().split(' ')[0]
            #     f.close()
            #     return md5

            # uid=self._uid
            # db = self._cr.dbname
            # path="/tmp/facture-pdf-%s-%s-%s.pdf"%(obj.name,db,uid)
            # md5 = get_md5(path,datas)
            # lines = self.env['is.account.move.pdf'].search([('move_id','=',obj.id)],order='id desc', limit=1)
            # last_path="%s.last"%path
            # last_md5=False
            # for line in lines:
            #     for pdf in line.facture_pdf_ids:
            #         last_md5 = get_md5(last_path,pdf.datas)
            vals = {
                    'move_id': obj.id,
            }
            line = self.env['is.account.move.pdf'].create(vals)
            attachment_obj = self.env['ir.attachment']
            vals = {
                'name':        obj.name + '.pdf',
                'type':        'binary',
                'res_model':   'is.account.move.pdf',
                'res_id':      line.id,
                'datas':       base64.b64encode(datas),
            }
            attachment = attachment_obj.create(vals)
            line.facture_pdf_ids = [attachment.id]


    def envoi_par_mail(self):
        """Envoi du mail directement sans passer par le wizard"""
        uid=self._uid
        cr=self._cr
        if not self.env['res.users'].has_group('is_plastigray16.is_comptable_group'):
            raise ValidationError(u"Accès non autorisé !")
        ids=[]
        for obj in self:
            ids.append(str(obj.id))
        if len(ids)>0:
            SQL="""
                select ai.is_mode_envoi_facture, ai.partner_id, ai.name, ai.id
                from account_move ai
                where 
                    ai.id in("""+','.join(ids)+""")  and 
                    ai.is_date_envoi_mail is null and 
                    ai.is_mode_envoi_facture like 'mail%'
                order by ai.is_mode_envoi_facture, ai.partner_id, ai.name
            """
            cr.execute(SQL)
            result = cr.fetchall()

            # ** Un mail par client*********************************************
            partners={}
            for row in result:
                if row[0]=='mail_client':
                    partner_id = row[1]
                    id         = row[3]
                    if not partner_id in partners:
                        partners[partner_id]=[]
                    partners[partner_id].append(id)
            #*******************************************************************


            # ** Un mail+BL par client******************************************
            for row in result:
                if row[0]=='mail_client_bl':
                    partner_id = row[1]
                    id         = row[3]
                    if not partner_id in partners:
                        partners[partner_id]=[]
                    partners[partner_id].append(id)
            #*******************************************************************


            #** Envoi des mails par partner ************************************
            for partner_id in partners:
                ids=partners[partner_id]
                self._envoi_par_mail(partner_id, ids)
            #*******************************************************************


            # ** Un mail par facture *******************************************
            for row in result:
                if row[0] in ['mail', 'mail_regroupe_bl']:
                    partner_id = row[1]
                    id         = row[3]
                    self._envoi_par_mail(partner_id, [id])
            #*******************************************************************


            # ** Un mail par facture en double exemplaire **********************
            for row in result:
                if row[0]=='mail2':
                    partner_id = row[1]
                    id         = row[3]
                    self._envoi_par_mail(partner_id, [id])
            #*******************************************************************




    def _envoi_par_mail(self, partner_id, ids):
        uid=self._uid
        cr=self._cr
        user = self.env['res.users'].browse(self._uid)
        if user.email==False:
            raise ValidationError(u"Votre mail n'est pas renseigné !")
        attachment_ids=[]
        for id in ids:
            invoice = self.env['account.move'].browse(id)
            attachments = self.env['ir.attachment'].search([
                ('res_model','=','account.move'),
                ('res_id'   ,'=',id),
            ], order='id desc', limit=1)
            if len(attachments)==0:
                raise ValidationError(u"Facture %s non générée (non imprimée) !"%invoice.name)

            for attachment in attachments:
                if invoice.is_mode_envoi_facture=='mail2':
                    # ** Duplication de la facture + fusion ********************
                    db = self._cr.dbname
                    path="/tmp/factures-" + db + '-'+str(uid)
                    cde="rm -Rf " + path
                    os.popen(cde).readlines()
                    if not os.path.exists(path):
                        os.makedirs(path)
                    paths=[]
                    for x in range(1, 3):
                        file_name = path + '/'+str(invoice.name) + '-' + str(x) + '.pdf'
                        #fd = os.open(file_name,os.O_RDWR|os.O_CREAT)
                        #fd = open(file_name,'wb')
                        with open(file_name,'wb') as f:
                            f.write(base64.decodebytes(attachment.datas))

                        # try:
                        #     #os.write(fd, attachment.datas.decode('base64'))
                        #     os.write(fd, base64.decodebytes(attachment.datas))
                        # finally:
                        #     close(fd)
                        paths.append(file_name)

                    # ** Merge des PDF *****************************************
                    path_merged=self._merge_pdf(paths)
                    pdfs = open(path_merged,'rb').read()
                    # **********************************************************

                    # ** Création d'une piece jointe fusionnée *****************
                    name = 'facture-' + str(invoice.name) + '-' + str(uid) + '.pdf'
                    vals = {
                        'name':        name,
                        #'datas_fname': name,
                        'type':        'binary',
                        #'datas':       pdfs,
                        'datas':        base64.b64encode(pdfs),
                    }
                    new = self.env['ir.attachment'].create(vals)
                    attachment_id=new.id
                    #***********************************************************
                else:
                    attachment_id=attachment.id

                attachment_ids.append(attachment_id)


        partner = self.env['res.partner'].browse(partner_id)
        if partner.is_mode_envoi_facture=='mail_client_bl':
            attachment_obj = self.env['ir.attachment']
            for id in ids:
                invoice = self.env['account.move'].browse(id)
                for line in invoice.invoice_line_ids:
                    picking=line.is_move_id.picking_id
                    if picking:

                        # ** Recherche si une pièce jointe est déja associèe au bl *
                        model='stock.picking'
                        name='BL-'+picking.name+u'.pdf'
                        attachments = attachment_obj.search([('res_model','=',model),('res_id','=',picking.id),('name','=',name)])
                        # **********************************************************

                        # ** Creation ou modification de la pièce jointe *******************
                        #pdf = self.env['report'].get_pdf(picking, 'stock.report_picking')
                        pdf = self.env['ir.actions.report']._render_qweb_pdf('stock.report_picking',[picking.id])[0]
                        vals = {
                            'name':        name,
                            #'datas_fname': name,
                            'type':        'binary',
                            'res_model':   model,
                            'res_id':      picking.id,
                            #'datas':       pdf.encode('base64'),
                            'datas':       base64.b64encode(pdf), #.encode('base64'),
                        }
                        if attachments:
                            for attachment in attachments:
                                attachment.write(vals)
                                attachment_id=attachment.id
                        else:
                            attachment = attachment_obj.create(vals)
                            attachment_id=attachment.id
                        # ******************************************************************

                        if attachment_id not in attachment_ids:
                            attachment_ids.append(attachment_id)


        #** Recherche du contact Facturation *******************************
        SQL="""
            select rp.name, rp.email, rp.active
            from res_partner rp inner join is_type_contact itc on rp.is_type_contact=itc.id
            where 
                rp.parent_id="""+str(partner_id)+""" and 
                itc.name='Facturation' and
                rp.active='t'
        """
        cr.execute(SQL)
        result = cr.fetchall()
        emails_to=[]
        for row in result:
            email_to = str(row[1])
            if email_to=='None':
                raise ValidationError(u"Mail du contact de facturation non renseigné pour le client "+partner.is_code+u'/'+partner.is_adr_code+" !")
            emails_to.append(row[0]+u' <'+email_to+u'>')
        if len(emails_to)==0:
            raise ValidationError(u"Aucun contact de type 'Facturation' trouvé pour le client "+partner.is_code+u'/'+partner.is_adr_code+" !")
        #*******************************************************************

        email_cc   = user.name+u' <'+user.email+u'>'
        email_to   = u','.join(emails_to)
        #email_to   = email_cc
        email_from = email_cc
        subject    = u'Facture Plastigray pour '+partner.name
        #subject    = u'Facture Plastigray pour '+partner.name+u' ('+u','.join(emails_to)+u')'
        email_vals = {}
        body_html=modele_mail.replace('[from]', user.name)
        email_vals.update({
            'subject'       : subject,
            'email_to'      : email_to,
            'email_cc'      : email_cc,
            'email_from'    : email_from, 
            'body_html'     : body_html.encode('utf-8'), 
            'attachment_ids': [(6, 0, attachment_ids)] 
        })
        email_id=self.env['mail.mail'].create(email_vals)
        if email_id:
            self.env['mail.mail'].send(email_id)
        email_to   = u','.join(emails_to)
        for id in ids:
            invoice = self.env['account.move'].browse(id)
            invoice.message_post(body=subject+u' envoyée par mail à '+u','.join(emails_to))
            invoice.is_date_envoi_mail=datetime.now()


    def action_move_create(self):
        for obj in self:
            if obj.is_mode_envoi_facture==False:
                obj.is_mode_envoi_facture=obj.partner_id.is_mode_envoi_facture
        super(account_invoice, self).action_move_create()
        self.escompte()


    def button_cancel(self):
        super(account_invoice, self).button_cancel()
        for obj in self:
            if obj.move_type=='in_invoice':
                for line in obj.invoice_line_ids:
                    if line.is_move_id:
                        line.is_move_id.invoice_state='2binvoiced'
                        line.is_move_id.picking_id._compute_invoice_state()


    def action_post(self):
        res=super(account_invoice, self).action_post()
        for obj in self:
            if obj.move_type=='in_invoice':
                for line in obj.invoice_line_ids:
                    if line.is_move_id:
                        line.is_move_id.invoice_state='invoiced'
                        line.is_move_id.picking_id._compute_invoice_state()
        return res



    # def action_cancel(self):
    #     for obj in self:
    #         if obj.type=='in_invoice':
    #             for line in obj.invoice_line:
    #                 if line.is_move_id:
    #                     line.is_move_id.invoice_state='none'
    #                     line.is_move_id.picking_id._compute_invoice_state()
    #                 line.is_move_id=False
    #     super(account_invoice, self).action_cancel()


    def button_reset_taxes(self):
        res=super(account_invoice, self).button_reset_taxes()
        self.escompte()
        return res


    def escompte(self):
        for obj in self:
            #Suppression des lignes d'escomptes
            for l in obj.tax_line:
                if l.name=='Escompte' or l.name=='TVA sur escompte':
                    l.unlink()
            if obj.partner_id.is_escompte:
                #Recherche du total HT
                ht=0.0
                tax_id=False
                for l in obj.invoice_line:
                    ht=ht+l.price_subtotal
                    if l.invoice_line_tax_id:
                        tax_id=l.invoice_line_tax_id[0]
                #Escompte
                tax_obj = self.env['account.move.tax']
                taux=obj.partner_id.is_escompte.taux/100
                tax_vals={
                    'invoice_id': obj.id,
                    'name': 'Escompte',
                    'account_id': obj.partner_id.is_escompte.compte.id,
                    'base': ht,
                    'amount': -ht*taux
                }
                tax_obj.create(tax_vals)
                #TVA sur Escompte
                if tax_id:
                    tax_vals={
                        'invoice_id': obj.id,
                        'name': 'TVA sur escompte',
                        'account_id': tax_id.account_collected_id.id,
                        'base': ht*taux,
                        'amount': -ht*taux*tax_id.amount
                    }
                    tax_obj.create(tax_vals)


    def line_get_convert(self, line, part, date):
        '''
        Permet d'ajouter dans la table account_move_line le lien vers la ligne de facture,
        pour récupérer en particulier la section analytique
        '''
        res=super(account_invoice, self).line_get_convert(line, part, date)
        res['is_account_invoice_line_id']=line.get('invl_id', False)
        return res


    def _prepare_refund(self, invoice, date=None, period_id=None, description=None, journal_id=None):
        """
        Permet d'ajouter les champs personnalisés de la facture sur l'avoir
        """
        res=super(account_invoice, self)._prepare_refund(invoice, date, period_id, description, journal_id)
        res['is_document']=invoice.is_document
        res['is_num_cde_client']=invoice.is_num_cde_client
        res['is_num_bl_manuel']=invoice.is_num_bl_manuel
        res['supplier_invoice_number']=invoice.supplier_invoice_number
        return res


    def compute_amortissement_moule_action(self):
        for obj in self:
            obj.invoice_line_ids._compute_amortissement_moule()


class account_invoice_line(models.Model):
    _inherit = "account.move.line"

    is_section_analytique_id   = fields.Many2one('is.section.analytique', 'Section analytique')
    is_move_id                 = fields.Many2one('stock.move', 'Mouvement de stock', index=True)
    is_document                = fields.Char("N° du chantier")


    is_account_invoice_line_id = fields.Integer('Lien entre account_invoice_line et account_move_line pour la migration', index=True)
    #is_account_invoice_line_id = fields.Many2one('account.move.line', 'Ligne de facture')


    #TODO : Le champ is_account_invoice_line_id existait avant la migration pour recuperr la section analytique avec cette fonction
    # @api.model
    # def line_get_convert(self, line, part, date):
    #     '''
    #     Permet d'ajouter dans la table account_move_line le lien vers la ligne de facture,
    #     pour récupérer en particulier la section analytique
    #     '''
    #     res=super(account_invoice, self).line_get_convert(line, part, date)
    #     res['is_account_invoice_line_id']=line.get('invl_id', False)
    #     return res


    @api.depends('move_id.state')
    def _compute_amortissement_moule(self):
        cr = self._cr
        for obj in self:
            amortissement_moule = 0
            amt_interne = 0
            cagnotage = 0
            montant_amt_moule = 0
            montant_amt_interne = 0
            montant_cagnotage = 0
            montant_matiere = 0
            if obj.product_id and obj.quantity and obj.move_id and obj.move_id.partner_id and obj.move_id.invoice_date:
                SQL="""
                    SELECT
                        get_amortissement_moule_a_date(rp.is_code, pt.id, ai.invoice_date) as amortissement_moule,
                        get_amt_interne_a_date(rp.is_code, pt.id, ai.invoice_date) as amt_interne,
                        get_cagnotage_a_date(rp.is_code, pt.id, ai.invoice_date) as cagnotage,
                        fsens(ai.move_type)*get_amortissement_moule_a_date(rp.is_code, pt.id, ai.invoice_date)*ail.quantity as montant_amt_moule,
                        fsens(ai.move_type)*get_amt_interne_a_date(rp.is_code, pt.id, ai.invoice_date)*ail.quantity as montant_amt_interne,
                        fsens(ai.move_type)*get_cagnotage_a_date(rp.is_code, pt.id, ai.invoice_date)*ail.quantity as montant_cagnotage,
                        fsens(ai.move_type)*get_cout_act_matiere_st(pp.id)*ail.quantity as montant_matiere,
                        ai.invoice_date,
                        ai.state
                    from account_move ai inner join account_move_line    ail on ai.id=ail.move_id
                                         inner join product_product       pp on ail.product_id=pp.id
                                         inner join product_template      pt on pp.product_tmpl_id=pt.id
                                         inner join res_partner           rp on ai.partner_id=rp.id
                    where ail.id=%s
                """
                cr.execute(SQL,[obj.id])
                res_ids = cr.fetchall()
                for res in res_ids:
                    amortissement_moule = res[0]
                    amt_interne         = res[1]
                    cagnotage           = res[2]
                    montant_amt_moule   = res[3]
                    montant_amt_interne = res[4]
                    montant_cagnotage   = res[5]
                    montant_matiere     = res[6]
            obj.is_amortissement_moule = amortissement_moule
            obj.is_amt_interne         = amt_interne
            obj.is_cagnotage           = cagnotage
            obj.is_montant_amt_moule   = montant_amt_moule
            obj.is_montant_amt_interne = montant_amt_interne
            obj.is_montant_cagnotage   = montant_cagnotage
            obj.is_montant_matiere     = montant_matiere


    is_amortissement_moule = fields.Float('Amt client négocié'        , digits=(14,4), store=True, compute='_compute_amortissement_moule')
    is_amt_interne         = fields.Float('Amt interne'               , digits=(14,4), store=True, compute='_compute_amortissement_moule')
    is_cagnotage           = fields.Float('Cagnotage'                 , digits=(14,4), store=True, compute='_compute_amortissement_moule')
    is_montant_amt_moule   = fields.Float('Montant amt client négocié', digits=(14,2), store=True, compute='_compute_amortissement_moule')
    is_montant_amt_interne = fields.Float('Montant amt interne'       , digits=(14,2), store=True, compute='_compute_amortissement_moule')
    is_montant_cagnotage   = fields.Float('Montant cagnotage'         , digits=(14,2), store=True, compute='_compute_amortissement_moule')
    is_montant_matiere     = fields.Float('Montant matière livrée'    , digits=(14,2), store=True, compute='_compute_amortissement_moule')



    @api.onchange('product_id','quantity')
    def pg_onchange_product_id(self):
        self.is_section_analytique_id = self.product_id.is_section_analytique_id.id
        if self.move_id.is_type_facture=='diverse':
            price = 0
            pricelist = self.move_id.partner_id.property_product_pricelist
            if pricelist:
                price, justifcation = pricelist.price_get(
                    product = self.product_id,
                    qty     = self.quantity, 
                    date    = self.move_id.invoice_date
                )
            self.price_unit = price



    # def product_id_change(self, product_id, uom_id, qty=0, name='', type='out_invoice',
    #         partner_id=False, fposition_id=False, price_unit=False, currency_id=False,
    #         company_id=None):

    #     #** Recherche lot pour retrouver le prix *******************************
    #     partner = self.env['res.partner'].browse(partner_id)
    #     lot_livraison=0
    #     is_section_analytique_id=False
    #     if product_id:
    #         product = self.env['product.product'].browse(product_id)
    #         lot_livraison=self.env['product.template'].get_lot_livraison(product.product_tmpl_id,partner)
    #         is_section_analytique_id=product.is_section_analytique_id.id
    #         if type=='in_invoice':
    #             is_section_analytique_id=product.is_section_analytique_ha_id.id
    #     #***********************************************************************

    #     res=super(account_invoice_line, self).product_id_change(product_id, uom_id, lot_livraison, name, type,
    #         partner_id, fposition_id, price_unit, currency_id,company_id)
    #     res['value']['is_section_analytique_id']=is_section_analytique_id

    #     #** Recherche prix dans liste de prix pour la date et qt ***************
    #     pricelist = partner.property_product_pricelist.id
    #     if product_id:
    #         date = time.strftime('%Y-%m-%d',time.gmtime()) # Date du jour
    #         if pricelist:
    #             ctx = dict(
    #                 self._context,
    #                 uom=uom_id,
    #                 date=date,
    #             )
    #             price_unit = self.env.get('product.pricelist').price_get(self._cr, self._uid, [pricelist],
    #                     product_id, lot_livraison or 1.0, partner_id, ctx)[pricelist]
    #         res['value']['price_unit']=price_unit
    #     #***********************************************************************

    #     #** Ajout du code_pg dans la description *******************************
    #     if product_id:
    #         product = self.env['product.product'].browse(product_id)
    #         res['value']['name']=product.is_code+u' '+product.name

    #     return res


class is_account_move_pdf(models.Model):
    _name = 'is.account.move.pdf'
    _description = u'Facture'
    
    move_id                = fields.Many2one('account.move', 'Facture', required=True, ondelete="cascade")
    facture_pdf_ids        = fields.Many2many('ir.attachment', 'is_account_move_pdf_rel', 'pdf_id', 'attachment_id', 'Facture PDF')
