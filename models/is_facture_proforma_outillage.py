# -*- coding: utf-8 -*-
from odoo import models,fields,api
from odoo.exceptions import ValidationError
from datetime import date, datetime


modele_mail=u"""
<html>
    <head>
        <meta content="text/html; charset=UTF-8" http-equiv="Content-Type">
    </head>
    <body>
        <font>Bonjour, </font>
        <br><br>
        <font> Veuillez trouver ci-joint notre facture proforma outillage.</font>
        <br><br>
        Cordialement <br><br>
        [from]<br>
    </body>
</html>
"""


class is_facture_proforma_outillage(models.Model):
    _name='is.facture.proforma.outillage'
    _description="is_facture_proforma_outillage"
    _inherit=['mail.thread']
    _order='name desc'

    @api.depends('line_ids')
    def _compute(self):
        for obj in self:
            total = 0
            for line in obj.line_ids:
                total += line.total
            obj.total = total


    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.term_id = self.partner_id.property_payment_term.id


    @api.onchange('term_id','date_facture')
    def onchange_payment_term_date_invoice(self):
        date_due = self.date_facture
        if self.term_id and self.date_facture:
            pterm = self.env['account.payment.term'].browse(self.term_id.id)
            pterm_list = pterm.compute(value=1, date_ref=self.date_facture)[0]
            if pterm_list:
                date_due = max(line[0] for line in pterm_list)
        self.date_due = date_due


    name            = fields.Char(u"Facture proforma outillage", readonly=True)
    date_facture    = fields.Date(u"Date facture"             , required=True, default=lambda *a: fields.datetime.now())
    date_envoi_mail = fields.Datetime("Mail envoyé le", readonly=True, copy=False)
    date_due       = fields.Date(u"Date d'échéance")
    partner_id     = fields.Many2one('res.partner', 'Adresse de facturation', required=True, domain=[('is_code','=like','50%'),('customer','=',True)])
    cofor          = fields.Char("N° fournisseur (COFOR)" , related="partner_id.is_cofor", readonly=True)
    vat            = fields.Char("N° fiscal" , related="partner_id.vat", readonly=True)
    term_id        = fields.Many2one('account.payment.term', 'Conditions de paiement')
    type_reglement = fields.Many2one('account.journal', 'Type règlement', related="partner_id.is_type_reglement", readonly=True)
    rib_id         = fields.Many2one('res.partner.bank', 'RIB', related="partner_id.is_rib_id", readonly=True)
    num_cde          = fields.Char("N° de commande")
    bl_manuel_id     = fields.Many2one('is.bl.manuel', 'BL manuel')
    picking_id       = fields.Many2one('stock.picking', 'Livraison', domain=[('picking_type_id','=', 2)])
    mold_id          = fields.Many2one('is.mold', 'Moule', required=True)
    mold_designation = fields.Char('Désignation', related="mold_id.designation", readonly=True)
    total        = fields.Float("Total (€)", digits=(14,2), compute='_compute', readonly=True, store=True)
    commentaire  = fields.Text(u'Commentaire')
    line_ids     = fields.One2many('is.facture.proforma.outillage.line', 'proforma_id', u"Lignes", copy=True)

    
    def create(self, vals):
        data_obj = self.env['ir.model.data']
        sequence_ids = data_obj.search([('name','=','is_facture_proforma_outillage_seq')])
        if sequence_ids:
            sequence_id = data_obj.browse(sequence_ids[0].id).res_id
            vals['name'] = self.env['ir.sequence'].get_id(sequence_id, 'id')
        obj = super(is_facture_proforma_outillage, self).create(vals)
        return obj


    def envoyer_par_mail_action(self):
        cr , uid, context = self.env.args
        user = self.env['res.users'].browse(uid)
        if user.email==False:
            raise Warning(u"Votre mail n'est pas renseigné !")
        if not self.pool['res.users'].has_group(cr, uid, 'is_plastigray16.is_comptable_group'):
            raise Warning(u"Accès non autorisé !")
        partners={}
        for obj in self:
            if not obj.date_envoi_mail:
                partner = obj.partner_id
                if not partner in partners:
                    partners[partner]=[]
                partners[partner].append(obj)
        for partner in partners:
            attachment_ids=[]
            for obj in partners[partner]:

                # ** Recherche si une pièce jointe est déja associèe **************
                model='is.facture.proforma.outillage'
                name="Facture-Proforma-"+obj.name+".pdf"
                attachment_obj = self.env['ir.attachment']
                attachments = attachment_obj.search([('res_model','=',model),('res_id','=',obj.id),('name','=',name)])
                # *****************************************************************

                # ** Creation ou modification de la pièce jointe *******************
                pdf = self.env['report'].get_pdf(obj, 'is_plastigray16.report_is_facture_proforma_outillage')

                vals = {
                    'name':        name,
                    'datas_fname': name,
                    'type':        'binary',
                    'res_model':   model,
                    'res_id':      obj.id,
                    'datas':       pdf.encode('base64'),
                }
                attachment_id=False
                if attachments:
                    for attachment in attachments:
                        attachment.write(vals)
                        attachment_id=attachment.id
                else:
                    attachment = attachment_obj.create(vals)
                    attachment_id=attachment.id
                if attachment_id:
                    attachment_ids.append(attachment_id)
                # ******************************************************************

            #** Recherche du contact Facturation *******************************
            SQL="""
                select rp.name, rp.email
                from res_partner rp inner join is_type_contact itc on rp.is_type_contact=itc.id
                where 
                    rp.parent_id=%s and 
                    itc.name='Facturation' and
                    rp.active='t'
            """
            cr.execute(SQL, [partner.id])
            result = cr.fetchall()
            emails_to=[]
            for row in result:
                email_to = row[1]
                if email_to:
                    emails_to.append(row[0]+u' <'+email_to+u'>')
            if len(emails_to)==0:
                raise Warning(u"Aucun contact de type 'Facturation' trouvé pour le client "+partner.name)
            #*******************************************************************

            email_cc   = user.name+u' <'+user.email+u'>'
            email_to   = u','.join(emails_to)
            email_from = email_cc
            subject    = u'Facture Proforma Outillage pour '+partner.name
            email_vals = {}
            body_html=modele_mail.replace('[from]', user.name)
            email_vals.update({
                'subject'       : subject,
                'email_to'      : email_to,
                'email_cc'      : email_cc,
                'email_from'    : email_from, 
                'body_html'     : body_html.encode('utf-8'), 
                'attachment_ids': [(6, 0, [attachment_ids])] 
            })

            email_id=self.env['mail.mail'].create(email_vals)
            if email_id:
                self.env['mail.mail'].send(email_id)

            email_to   = u','.join(emails_to)

            for obj in partners[partner]:
                obj.message_post(body=subject+u' envoyée par mail à '+u','.join(emails_to))
                obj.date_envoi_mail=datetime.now()


class is_facture_proforma_outillage_line(models.Model):
    _name='is.facture.proforma.outillage.line'
    _description="is_facture_proforma_outillage_line"
    _order='proforma_id,sequence'


    @api.depends('pourcentage','prix')
    def _compute(self):
        for obj in self:
            obj.total=obj.pourcentage*obj.prix/100

    proforma_id = fields.Many2one('is.facture.proforma.outillage', "Facture proforma outillage", required=True, ondelete='cascade', readonly=True)
    sequence    = fields.Integer('Ordre')
    designation = fields.Text(u'Désignation'      , required=True)
    pourcentage = fields.Float("Pourcentage (%)"  , digits=(14,0), required=True)
    prix        = fields.Float("Prix unitaire (€)", digits=(14,2), required=True)
    total       = fields.Float("Total (€)"        , digits=(14,2), compute='_compute', readonly=True, store=True)



