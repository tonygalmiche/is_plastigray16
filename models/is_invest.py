# -*- coding: utf-8 -*-

from odoo import models,fields,api
import time
#import psycopg2
#import psycopg2.extras


class IsInvestGlobal(models.Model):
    _name = 'is.invest.global'
    _description = u"Investissement global"
    _order='name'

    @api.depends('name')
    def _compute_montant(self):
        for obj in self:
            montant_odoo  = 0.0
            montant_cegid = 0.0
            reste_odoo    = 0.0
            reste_cegid   = 0.0
            for line in obj.detail_ids:
                montant_odoo  += line.montant_odoo
                montant_cegid += line.montant_cegid
            obj.montant_odoo  = montant_odoo
            obj.montant_cegid = montant_cegid
            obj.reste_odoo    = obj.montant - montant_odoo
            obj.reste_cegid   = obj.montant - montant_cegid


    name          = fields.Char(u'N°Invest Global', index=True, readonly=True)
    date_creation = fields.Date(u"Date de création", copy=False, default=fields.Date.context_today, readonly=True)
    annee         = fields.Char(u'Année', index=True, required=True, default=lambda *a:time.strftime('%Y'))
    site_id       = fields.Many2one("is.database", "Site", index=True,required=True)
    intitule      = fields.Char(u'Intitulé', required=True)
    montant       = fields.Integer('Montant Budget (€)')
    detail_ids    = fields.One2many('is.invest.detail', 'global_id', u"Investissements Détail", readonly=True)
    montant_odoo  = fields.Float(u"Montant Odoo" , digits=(12, 0), compute="_compute_montant", store=False, readonly=True)
    montant_cegid = fields.Float(u"Montant Cegid", digits=(12, 0), compute="_compute_montant", store=False, readonly=True)
    reste_odoo    = fields.Float(u"Reste Odoo"   , digits=(12, 0), compute="_compute_montant", store=False, readonly=True)
    reste_cegid   = fields.Float(u"Reste Cegid"  , digits=(12, 0), compute="_compute_montant", store=False, readonly=True)


    def create(self, vals):
        try:
            annee = int(vals['annee'])
        except ValueError:
            annee=0
        if annee<2019 or annee>2099:
            raise Warning(u"L'année doit-être comprise entre 2019 et 2099 !")
        data_obj = self.env['ir.model.data']
        sequence_ids = data_obj.search([('name','=','is_invest_global_seq')])
        if sequence_ids:
            sequence_id = data_obj.browse(sequence_ids[0].id).res_id
            vals['name'] = self.env['ir.sequence'].get_id(sequence_id, 'id')
        obj = super(IsInvestGlobal, self).create(vals)
        return obj


    def creer_detail_action(self):
        """Création investissement détail"""
        for obj in self:
            vals = {
                'type': 'ir.actions.act_window',
                'name': u'Création investissement détail',
                'target': 'current', #use 'current' for not opening in a dialog
                'res_model': 'is.invest.detail',
                'view_type': 'form',
                'views': [[False,'form']],
                'context':{
                    'default_global_id': obj.id,
                }
            };
            return vals


class IsInvestDetail(models.Model):
    _name = 'is.invest.detail'
    _description = u"Investissement détail"
    _order='name'

    @api.depends('global_id')
    def _compute_montant_odoo(self):
        for obj in self:
            montant = 0.0
            for line in obj.cde_ids:
                montant += line.montant
            obj.montant_odoo = montant


    @api.depends('global_id')
    def _compute_montant_cegid(self):
        for obj in self:
            montant = 0.0
            for line in obj.compta_ids:
                montant += line.montant
            obj.montant_cegid = montant


    global_id     = fields.Many2one("is.invest.global", "Invest Global", readonly=True, index=True)
    ordre         = fields.Integer(u'Ordre', index=True, readonly=True)
    name          = fields.Char(u'N°Invest Détail', index=True, readonly=True)
    date_creation = fields.Date(u"Date de création", copy=False, default=fields.Date.context_today, readonly=True)
    annee         = fields.Char(u'Année', index=True, required=True, default=lambda *a:time.strftime('%Y'))
    site_id       = fields.Many2one("is.database", "Site", index=True,readonly=True)
    intitule      = fields.Char(u'Intitulé', required=True)
    imputation    = fields.Char(u'Imputation', required=True, index=True)
    section       = fields.Char(u'Section', required=True, index=True)
    cde_ids       = fields.One2many('is.invest.cde', 'detail_id', u"Commandes", readonly=True)
    compta_ids    = fields.One2many('is.invest.compta', 'detail_id', u"Compta", readonly=True)
    montant_odoo  = fields.Float(u"Montant Odoo",  digits=(12, 0), compute="_compute_montant_odoo" , store=False, readonly=True)
    montant_cegid = fields.Float(u"Montant Cegid", digits=(12, 0), compute="_compute_montant_cegid", store=False, readonly=True)


    def create(self, vals):
        cr , uid, context = self.env.args
        try:
            annee = int(vals['annee'])
        except ValueError:
            annee=0
        if annee<2019 or annee>2099:
            raise Warning(u"L'année doit-être comprise entre 2019 et 2099 !")
        global_id = context.get('default_global_id')
        if global_id:
            g = self.env['is.invest.global'].browse(global_id)
            res = self.env['is.invest.detail'].search([('global_id','=',global_id)],order='ordre desc',limit=1)
            ordre = 1
            for line in res:
                ordre = line.ordre+1
            name = g.name + ('00'+str(ordre))[-2:]
            vals['global_id'] = global_id
            vals['ordre'] = ordre
            vals['name']  = name
            vals['site_id']  = g.site_id.id
        else:
            raise Warning(u"Investissement global non défini !")
        obj = super(IsInvestDetail, self).create(vals)
        return obj


    def actualiser_commandes(self):
        """Actualiser les commandes"""
        cr , uid, context = self.env.args
        for obj in self:
            obj.cde_ids.unlink()
            company = self.env.user.company_id
            dbname='pg-odoo1'
            dbnames=['odoo1','odoo4']
            if company.is_postgres_host=='localhost':
                dbnames=['pg-odoo1','pg-odoo4']
            for dbname in dbnames:
                cnx = psycopg2.connect("dbname='"+dbname+"' user='"+company.is_postgres_user+"' host='"+company.is_postgres_host+"' password='"+company.is_postgres_pwd+"'")
                if cnx:
                    cur = cnx.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                    SQL= """
                        select 
                            po.name,
                            po.date_order,
                            po.is_document,
                            pol.date_planned,
                            pt.is_code,
                            pol.product_qty,
                            pol.price_unit,
                            po.id order_id,
                            pol.is_num_chantier
                        from purchase_order po inner join purchase_order_line pol on po.id=pol.order_id
                                               inner join product_product      pp on pol.product_id=pp.id
                                               inner join product_template     pt on pp.product_tmpl_id=pt.id
                        where 
                            pol.is_num_chantier like 'M____/"""+obj.name+"""'  and 
                            pol.date_planned>='"""+obj.annee+"""-01-01' and
                            pol.date_planned<='"""+obj.annee+"""-12-31'
                    """
                    cur.execute(SQL)
                    rows = cur.fetchall()
                    for row in rows:
                        vals={
                            'detail_id': obj.id,
                            'order'    : row['name'],
                            'order_id' : row['order_id'],
                            'code_pg'  : row['is_code'],
                            'date_liv' : row['date_planned'],
                            'qt_cde'   : row['product_qty'],
                            'prix'     : row['price_unit'],
                            'montant'  : row['product_qty']*row['price_unit'],
                            'base'     : dbname,
                        }
                        doc = self.env['is.invest.cde'].create(vals)
        return []


class IsInvestCde(models.Model):
    _name = 'is.invest.cde'
    _description = u"Investissement commandes"
    _order='detail_id,order'

    detail_id     = fields.Many2one("is.invest.detail", "Invest Détail", index=True)
    order         = fields.Char(u'N°Cde', index=True)
    order_id      = fields.Integer(u'N°Cde Id')
    code_pg       = fields.Char(u'Code PG', index=True)
    date_liv      = fields.Date(u'Date liv')
    qt_cde        = fields.Float(u'Qt Cde')
    prix          = fields.Float(u'Prix unitaire')
    montant       = fields.Float(u'Montant total')
    base          = fields.Char(u'Base', index=True)

    def acces_commande_action(self):
        """Accès à la commande"""
        for obj in self:
            url = u'https://'+obj.base+'/web#id='+str(obj.order_id)+'&view_type=form&model=purchase.order'
            vals = {
                'type'  : 'ir.actions.act_url',
                'name'  : u'Accès à la commande',
                'target': 'new', #use 'current' for not opening in a dialog
                'url'   : url, 
            };
            return vals


class IsInvestCompta(models.Model):
    _name = 'is.invest.compta'
    _description = u"Investissement compta"
    _order='detail_id,piece'

    detail_id     = fields.Many2one("is.invest.detail", "Invest Détail", index=True)
    date_facture  = fields.Date(u'Date', index=True)
    piece         = fields.Char(u'Pièce')
    intitule      = fields.Char(u'Intitulé')
    affaire       = fields.Char(u'Affaire')
    compte        = fields.Char(u'Compte')
    section       = fields.Char(u'Section')
    montant       = fields.Float(u'Montant')






