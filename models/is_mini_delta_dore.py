# -*- coding: utf-8 -*-
from odoo import models,fields,api
from odoo.exceptions import ValidationError
import base64
import csv
#import csv, cStringIO
from datetime import date,datetime,timedelta
#import unicodedata
import math


_MOIS=['Janvier', 'Février','Mars','Avril','Mai', 'Juin','Juillet','Aout','Septembre','Octobre','Novembre','Décembre']

class is_mini_delta_dore(models.Model):
    _name = "is.mini.delta.dore"
    _description="Mini delta dore"
    _order='name desc'

    name            = fields.Char('N° traitement', readonly=True)
    partner_id      = fields.Many2one('res.partner', 'Client', required=True, domain=[('customer','=',True),('is_company','=',True)])
    file_ids        = fields.Many2many('ir.attachment', 'is_mini_delta_dore_file_rel', 'doc_id', 'file_id', 'Fichier à traiter')
    nb_jours        = fields.Integer('Nombre de jours dans le fichier'   , default=5)
    nb_semaines     = fields.Integer('Nombre de semaines dans le fichier', default=4)
    nb_mois         = fields.Integer('Nombre de mois dans le fichier'    , default=8)
    edi_id          = fields.Many2one('is.edi.cde.cli', 'EDI généré', readonly=True, copy=False)
    line_ids        = fields.One2many('is.mini.delta.dore.line'  , 'mini_delta_dore_id', u"Lignes")
    besoin_ids      = fields.One2many('is.mini.delta.dore.besoin', 'mini_delta_dore_id', u"Besoins")


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('is.mini.delta.dore')
        return super().create(vals_list)


    def calcul_action(self):
        for obj in self:
            if obj.edi_id:
                raise ValidationError('Un EDI a déjà été généré. Il faut le traiter ou le supprimer pour pouvoir lancer un nouveau calcul')
            obj.line_ids.unlink()
            obj.besoin_ids.unlink()
            for attachment in obj.file_ids:
                res=self.traitement(attachment)
            self.creation_edi()


    def creation_edi(self):
        cr=self._cr
        cr.commit()
        for obj in self:
            SQL="""
                select
                    l.reference_client,
                    b.date_livraison,
                    b.type_commande,
                    sum(b.commande)
                from is_mini_delta_dore_besoin b inner join is_mini_delta_dore_line l on b.line_id=l.id 
                where b.mini_delta_dore_id="""+str(obj.id)+""" and b.commande!=0
                group by l.reference_client, b.date_livraison, b.type_commande
            """
            cr.execute(SQL)
            result = cr.fetchall()
            datas=''
            for row in result:
                lig=str(row[0])+'\t'+str(row[1])+'\t'+str(row[2])+'\t'+str(row[3])+'\n'
                datas+=lig

            #** Ajout en pièce jointe ******************************************
            name='edi-mini-delta-dore.csv'
            attachment_obj = self.env['ir.attachment']
            model='is.edi.cde.cli'
            vals = {
                'name':        name,
                #'datas_fname': name,
                'type':        'binary',
                #'file_type':   'text/csv',
                'res_model':   model,
                #'datas':       datas.encode('base64'),
                #'datas': base64.b64encode(datas),
                'datas'      : base64.b64encode(bytes(datas, 'utf-8')) # bytes,
            }
            attachment=attachment_obj.create(vals)
            vals = {
                'partner_id': obj.partner_id.id,
                'file_ids' : [(6,0,[attachment.id])],
            }
            edi=self.env['is.edi.cde.cli'].create(vals)
            obj.edi_id=edi.id
            #*******************************************************************

    def traitement(self, attachment):
        cr=self._cr
        res = []
        for obj in self:
            #** Recherche du prochain jour livrable de ce client ***************
            closing_days = obj.partner_id.num_closing_days(obj.partner_id)
            d = datetime.now()        # Date de jour
            d = d + timedelta(days=1) # Ne pas livrer le jour même => Ajouter 1 jour
            while (int(d.strftime('%w')) in closing_days):
                d = d + timedelta(days=1)
            date_prochaine_livraison=d
            #*******************************************************************

            nb_jours    = obj.nb_jours
            nb_semaines = obj.nb_semaines
            nb_mois     = obj.nb_mois

            # Décodage du fichier avec détection automatique de l'encodage (UTF-8 ou ISO-8859-1)
            raw_data = base64.decodebytes(attachment.datas)
            try:
                attachment = raw_data.decode('utf-8')
            except UnicodeDecodeError:
                attachment = raw_data.decode('iso-8859-1')




            #attachment=attachment.decode('iso-8859-1').encode('utf8')
            csvfile = attachment.split("\n")
            csvfile = csv.reader(csvfile, delimiter=';')
            tsemaines={}
            tmois={}
            tdates=[]
            for lig, row in enumerate(csvfile):
                if lig==2:
                    annee=date.today().year
                    ct=1
                    for cel in row:
                        if ct==10:
                            #** Recherche du lundi de chaque semaine ***********
                            d=datetime.strptime(cel, '%d/%m/%y')
                            for i in range(0,365):
                                semaine='S'+d.strftime('%W/%Y')
                                #Test si lundi
                                if d.isoweekday()==1:
                                    tsemaines[semaine]=d
                                d = d + timedelta(days=+1)   # Date +1 jour
                            #***************************************************

                            #** Recherche du premier jour de chaque mois *******
                            d=datetime.strptime(cel, '%d/%m/%y')
                            for i in range(0,12):
                                d = d.replace(day=1)      # Fixe le jour à 1
                                d = self.premier_lundi(d) # Recherche le premier lundi suivant
                                mois=d.strftime('%m/%Y')
                                tmois[mois]=d
                                d = d + timedelta(days=32) # Ajoute 32 jours => mois suivant
                            #***************************************************

                            #** Date premier lundi *****************************
                            d=datetime.strptime(cel, '%d/%m/%y')
                            weekday = d.weekday()                    # Jour dans la semaine
                            date_lundi = d - timedelta(days=weekday) # Date du lundi précédent
                            #***************************************************

                        #** Dates en jours => Lundi précédent ******************
                        if ct>=10 and ct<(10+nb_jours):
                            tdates.append([cel,date_lundi])
                            annee=d.year

                        #* Dates en semaines => Lundi de la semaine ************
                        if ct>=(10+nb_jours) and ct<(10+nb_jours+nb_semaines):
                            cel=cel.strip()
                            if cel[0:1]=="S" and len(cel)==2:
                                cel="S0%s"%cel[1:2]
                            semaine=cel+'/'+str(annee)
                            d=tsemaines[semaine]
                            tdates.append([cel,d])
                            # Mémoriser l'année et le mois de la dernière semaine traitée
                            annee_derniere_semaine=d.year
                            mois_derniere_semaine=d.month
                            d = d + timedelta(days=7) # Ajoute 7 jours => semaine suivant
                            annee=d.year # Année de la semaine suivante

                        #* Dates en mois => 1er lundi du mois ******************
                        if ct>=(10+nb_jours+nb_semaines) and ct<(10+nb_jours+nb_semaines+nb_mois):
                            mois=cel.strip()
                            num_mois_int=_MOIS.index(mois)+1
                            num_mois=str(num_mois_int).zfill(2)
                            # Initialisation de l'année des mois à partir de la dernière semaine traitée
                            if ct==(10+nb_jours+nb_semaines):
                                annee_mois=annee_derniere_semaine
                                # Si le premier mois est avant le mois de la dernière semaine, c'est l'année suivante
                                if num_mois_int < mois_derniere_semaine:
                                    annee_mois+=1
                                num_mois_precedent=num_mois_int
                            # Détection du passage à l'année suivante (ex: Décembre -> Janvier)
                            elif num_mois_int < num_mois_precedent:
                                annee_mois+=1
                            num_mois_precedent=num_mois_int
                            mois_annee=num_mois+'/'+str(annee_mois)
                            date_mois=tmois[mois_annee]
                            tdates.append([mois,date_mois])
                        ct+=1

                if lig>2:
                    ct=1
                    reference_client=''
                    product={}
                    line={}
                    anomalie   = []
                    stock      = 0
                    stock_mini = 0
                    stock_maxi = 0
                    stock_date = 0
                    for cel in row:
                        if ct==1:
                            reference_client=cel.strip()
                            product = self.env['product.product'].search([
                                ('is_ref_client', '=', reference_client),
                                ('is_client_id' , '=', obj.partner_id.id),
                            ],limit=1,order='id desc')
                            order = self.env['sale.order'].search([
                                ('partner_id.is_code', '=', obj.partner_id.is_code),
                                ('is_ref_client'     , '=', reference_client),
                                ('is_type_commande'  , '=', 'ouverte'),
                            ],limit=1)
                            if order:
                                product=order.is_article_commande_id
                        if ct==2:
                            designation_client=cel.strip()
                        if ct==3:
                            indice_client=cel.strip()
                        if ct==5:
                            multiple=self.txt2integer(cel)
                        if ct==6:
                            stock=self.txt2integer(cel)
                        if ct==7:
                            stock_mini=self.txt2integer(cel)
                        if ct==8:
                            stock_maxi=self.txt2integer(cel)
                        if ct==10:
                            #Recherche multiple de livraison *******************
                            multiple_livraison=0
                            for l in product.is_client_ids:
                                if l.client_id.id==obj.partner_id.id:
                                    multiple_livraison=l.multiple_livraison

                            #***************************************************
                            if indice_client!=product.is_ind_plan:
                                anomalie.append(u'Indice différent')
                            if stock<stock_mini:
                                anomalie.append(u'Stock<Mini')
                            if stock>stock_maxi:
                                anomalie.append(u'Stock>Maxi')
                            if multiple_livraison==0:
                                anomalie.append(u'Multiple Plastigray=0')
                            else:
                                if round(multiple/multiple_livraison,2)!=round(multiple/multiple_livraison):
                                    anomalie.append(u'Multiple Client incohérent avec multiple Plastigray')
                            vals={
                                'mini_delta_dore_id': obj.id,
                                'reference_client'  : reference_client,
                                'designation_client': designation_client,
                                'indice_client'     : indice_client,
                                'multiple'          : multiple,
                                'stock'             : stock,
                                'stock_mini'        : stock_mini,
                                'stock_maxi'        : stock_maxi,
                                'product_id'        : product.id,
                                'indice'            : product.is_ind_plan,
                                'multiple_livraison': multiple_livraison,
                                'order_id'          : order.id,
                                'anomalie'          : ', '.join(anomalie),
                            }
                            line=self.env['is.mini.delta.dore.line'].create(vals)
                            stock_date=stock-stock_mini

                        if ct>=10 and ct<(10+nb_jours+nb_semaines+nb_mois):

                            #** Pour les mois, il faut éclater en 4 lignes *****
                            eclate=1
                            if ct>=(10+nb_jours+nb_semaines) and ct<(10+nb_jours+nb_semaines+nb_mois):
                                eclate=4
                            #***************************************************

                            for i in range(0,eclate):
                                besoin         = self.txt2integer(cel)
                                date_origine   = tdates[ct-10][0]
                                d              = tdates[ct-10][1]
                                date_calculee  = d + timedelta(days=i*7) # Ajoute 7 jours => semaine suivant
                                besoin_calcule = besoin/eclate
                                vals={
                                    'mini_delta_dore_id': obj.id,
                                    'line_id'           : line.id,
                                    'product_id'        : product.id,
                                    'multiple'          : multiple,
                                    'stock'             : stock,
                                    'stock_mini'        : stock_mini,
                                    'stock_maxi'        : stock_maxi,
                                    'product_id'        : product.id,
                                    'besoin'            : besoin,
                                    'date_origine'      : date_origine,
                                    'date_calculee'     : date_calculee,
                                    'besoin_calcule'    : besoin_calcule,
                                }
                                self.env['is.mini.delta.dore.besoin'].create(vals)
                        ct+=1


            #** Calcul du stock à date et des livraisons ***********************
            for line in obj.line_ids:
                SQL="""
                    select
                        id,
                        line_id,
                        product_id,
                        multiple,
                        stock,
                        stock_mini,
                        stock_maxi,
                        date_calculee,
                        besoin_calcule
                    from is_mini_delta_dore_besoin 
                    where line_id="""+str(line.id)+""" 
                    order by date_calculee, id
                """
                cr.execute(SQL)
                result = cr.fetchall()
                lig=0
                for row in result:
                    b=self.env['is.mini.delta.dore.besoin'].browse(row[0])
                    if b:
                        lig=lig+1
                        multiple       = row[3]
                        stock          = row[4]
                        stock_mini     = row[5]
                        stock_maxi     = row[6]
                        date_calculee  = row[7]
                        besoin_calcule = row[8]
                        #date_calculee=datetime.strptime(date_calculee, '%Y-%m-%d')
                        if lig==1:
                            stock_date=stock-stock_mini
                        stock_date     = stock_date - besoin_calcule
                        commande       = 0
                        date_livraison = False
                        type_commande  = False
                        if stock_date<0:
                            type_commande  = 'previsionnel'
                            commande=-stock_date
                            x=float(commande)/float(multiple)
                            x=math.ceil(x)
                            commande=multiple*x
                            date_livraison=date_calculee
                            if date_calculee<=date_prochaine_livraison.date():
                                type_commande  = 'ferme'
                                date_livraison=date_prochaine_livraison
                                commande=commande+multiple # Ajoute 1 multiple si commande ferme
                            stock_date=stock_date+commande
                        anomalie = []
                        if stock_date<0:
                            anomalie.append(u'Stock<Mini')
                        if (stock_date+stock_mini)>stock_maxi:
                            anomalie.append(u'Stock>Maxi')
                        vals={
                            'stock_date'        : stock_date+stock_mini,
                            'stock_date_mini'   : stock_date,
                            'type_commande'     : type_commande,
                            'commande'          : commande,
                            'date_livraison'    : date_livraison,
                            'anomalie'          : ', '.join(anomalie),
                        }
                        b.write(vals)
            #*******************************************************************
        return res


    def txt2integer(self,txt):
        txt=str(txt).strip()
        #txt = unicode(txt,'utf-8')
        #txt = unicodedata.normalize('NFD', txt).encode('ascii', 'ignore')
        txt=txt.replace(u' ', '')
        try:
            x = int(txt)
        except ValueError:
            x=0
        return x


    def premier_lundi(self,d):
        while (d.isoweekday()!=1):
            d = d + timedelta(days=1)
        return d


    def besoins_action(self):
        for obj in self:
            return {
                'name': u'Besoins mini Delta Dore',
                'view_mode': 'tree,form',
                'res_model': 'is.mini.delta.dore.besoin',
                'domain': [
                    ('mini_delta_dore_id'  ,'=', obj.id),
                ],
                'type': 'ir.actions.act_window',
                'limit': 1000,
            }



class is_mini_delta_dore_line(models.Model):
    _name='is.mini.delta.dore.line'
    _description="Mini delta dore lignes"
    _order='id'

    mini_delta_dore_id = fields.Many2one('is.mini.delta.dore', 'Mini Delta Dore', required=True, ondelete='cascade', readonly=True)
    reference_client   = fields.Char('Référence client')
    designation_client = fields.Char('Désignation client')
    indice_client      = fields.Char('Indice Client')
    multiple           = fields.Integer('Multiple Client')
    stock              = fields.Integer('Stock Client')
    stock_mini         = fields.Integer('Stock mini')
    stock_maxi         = fields.Integer('Stock maxi')
    product_id         = fields.Many2one('product.product', 'Article')
    indice             = fields.Char('Indice Plastigray')
    multiple_livraison = fields.Integer('Multiple Plastigray')
    order_id           = fields.Many2one('sale.order', 'Commande ouverte')
    anomalie           = fields.Char('Anomalie')
    besoin_ids         = fields.One2many('is.mini.delta.dore.besoin', 'line_id', u"Besoins")


    def besoins_action(self):
        for obj in self:
            return {
                'name': u'Besoins mini Delta Dore '+obj.product_id.is_code,
                'view_mode': 'tree,form',
                'res_model': 'is.mini.delta.dore.besoin',
                'domain': [
                    ('line_id','=', obj.id),
                ],
                'type': 'ir.actions.act_window',
                'limit': 1000,
            }


class is_mini_delta_dore_besoin(models.Model):
    _name='is.mini.delta.dore.besoin'
    _description="Mini delta dore besoin"
    _order='product_id,date_calculee,id'

    mini_delta_dore_id = fields.Many2one('is.mini.delta.dore'     , 'Mini Delta Dore'     , required=True, ondelete='cascade', readonly=True)
    line_id            = fields.Many2one('is.mini.delta.dore.line', 'Mini Delta Dore Line', required=True, ondelete='cascade', readonly=True)
    product_id         = fields.Many2one('product.product', 'Article')
    multiple           = fields.Integer('Multiple Client')
    stock              = fields.Integer('Stock Client')
    stock_mini         = fields.Integer('Stock mini')
    stock_maxi         = fields.Integer('Stock maxi')
    multiple_livraison = fields.Integer('Multiple Plastigray')
    besoin             = fields.Integer('Besoin')
    date_origine       = fields.Char('Date origine')
    date_calculee      = fields.Date('Date calculée')
    besoin_calcule     = fields.Integer('Besoin calculé')
    stock_date         = fields.Integer('Stock à date')
    stock_date_mini    = fields.Integer('Stock à date - Mini')
    type_commande      = fields.Selection([('ferme', 'Ferme'),('previsionnel', 'Prév.')], "Type")
    commande           = fields.Integer('Quantité à livrer')
    date_livraison     = fields.Date('Date de livraison')
    anomalie           = fields.Char('Anomalie')
