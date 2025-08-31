# -*- coding: utf-8 -*-
from odoo import models, fields, api



class IsFactureProformaExportTunisie(models.Model):
	_name = 'is.facture.proforma.export.tunisie'
	_description = 'Facture Proforma Export Tunisie'
	_order = 'chrono desc'
	_rec_name = 'chrono'
	_inherit = ['mail.thread', 'mail.activity.mixin']

	chrono             = fields.Integer('Chrono', index=True, tracking=True, readonly=True, copy=False)
	client_id          = fields.Many2one('res.partner', 'Client', tracking=True, domain=[("is_company","=",True), ("customer","=",True)])
	adresse            = fields.Text('Adresse de facturation', tracking=True)
	date_creation      = fields.Date("Date de création", default=lambda self: fields.Datetime.now(), tracking=True)
	type_exportation   = fields.Selection([
		('10', 'Exportation définitive'),
		('20', 'Exportation temporaire'),
		('30', 'Retour pour perfectionnement actif réparation'),
		('40', "Exportation définitive suite mise en conformité"),
		('50', 'Réexportation après réparation'),
	], "Type d'exportation", tracking=True)
	mode_transport     = fields.Selection([
		('10', 'Routier'),
		('20', 'Maritime'),
		('30', 'Aérien'),
	], 'Mode de transport', tracking=True)
	commentaire        = fields.Text('Commentaire', tracking=True)
	active             = fields.Boolean('Actif', default=True, tracking=True)
	dynacase_id        = fields.Integer(string='Id Dynacase', index=True, copy=False, tracking=True)
	piece_jointe_ids   = fields.Many2many("ir.attachment", "is_facture_proforma_export_tunisie_piece_jointe_rel", "piece_jointe", "att_id", string="Pièce jointe")

	# Totaux calculés
	nb_colis          = fields.Integer('Nombre de colis'            , compute='_compute_totaux', store=False, readonly=True)
	poids_net_total   = fields.Integer('Poids net total (Kg)'       , compute='_compute_totaux', store=False, readonly=True)
	poids_brut_total  = fields.Integer('Poids brut total (Kg)'      , compute='_compute_totaux', store=False, readonly=True)
	montant_total     = fields.Float('Montant total', digits=(14, 2), compute='_compute_totaux', store=False, readonly=True)


	# Lignes de colisage
	colisage_ids       = fields.One2many(
		'is.facture.proforma.export.tunisie.colisage',
		'proforma_id',
		'Colisages'
	)

	# Lignes de facture
	ligne_ids          = fields.One2many(
		'is.facture.proforma.export.tunisie.ligne',
		'proforma_id',
		'Lignes de facture'
	)

	@api.depends(
		'colisage_ids',
		'colisage_ids.poids_net',
		'colisage_ids.poids_brut',
		'ligne_ids',
		'ligne_ids.prix_total'
	)
	def _compute_totaux(self):
		for rec in self:
			rec.nb_colis = len(rec.colisage_ids)
			rec.poids_net_total = sum((l.poids_net or 0.0) for l in rec.colisage_ids)
			rec.poids_brut_total = sum((l.poids_brut or 0.0) for l in rec.colisage_ids)
			rec.montant_total = sum((l.prix_total or 0.0) for l in rec.ligne_ids)

	def lien_vers_dynacase_action(self):
		"""Ouvre la fiche Dynacase liée si un identifiant est renseigné."""
		self.ensure_one()
		if not self.dynacase_id:
			return False
		url = f"https://dynacase-rp/?sole=Y&app=FDL&action=FDL_CARD&id={int(self.dynacase_id)}"
		return {
			'type'  : 'ir.actions.act_url',
			'target': 'new',
			'url'   : url,
		}


	@api.model_create_multi
	def create(self, vals_list):
		for vals in vals_list:
			if "chrono" not in vals:
				last_codif = self.env["is.facture.proforma.export.tunisie"].search([('chrono', '!=', None)], order="chrono desc", limit=1)
				if last_codif:
					chrono = last_codif.chrono
				else:
					chrono = 0
				vals["chrono"] = chrono + 1


		print(vals_list)

		records = super().create(vals_list)
		# Après création, renuméroter les colis 1..x pour chaque proforma
		for rec in records:
			rec._renumeroter_colis()
			rec._renumeroter_lignes()
		return records

	def write(self, vals):
		res = super().write(vals)
		# Renuméroter les colis après toute modification, en particulier si colisage_ids change
		for rec in self:
			rec._renumeroter_colis()
			rec._renumeroter_lignes()
		return res

	def _renumeroter_colis(self):
		"""Attribue num_colis = '1'..'x' sur les lignes de colisage dans l'ordre d'insertion (id asc)."""
		self.ensure_one()
		i = 1
		for colis in self.colisage_ids.sorted('id'):
			# Éviter des writes inutiles si déjà correctement numéroté
			num_str = str(i)
			if (colis.num_colis or '') != num_str:
				colis.write({'num_colis': num_str})
			i += 1

	def _renumeroter_lignes(self):
		"""Attribue num = 1..x sur les lignes de facture dans l'ordre d'insertion (id asc)."""
		self.ensure_one()
		i = 1
		for ligne in self.ligne_ids.sorted('id'):
			if (ligne.num or 0) != i:
				ligne.write({'num': i})
			i += 1




class IsFactureProformaExportTunisieColisage(models.Model):
	_name = 'is.facture.proforma.export.tunisie.colisage'
	_description = 'Ligne de colisage (Proforma Export Tunisie)'
	_order = 'id asc'
	_rec_name = 'num_colis'

	proforma_id = fields.Many2one('is.facture.proforma.export.tunisie', 'Proforma', required=True, ondelete='cascade')
	num_colis   = fields.Char('Numéro du colis', index=True)
	dimensions  = fields.Char('Dimensions')
	poids_net   = fields.Float('Poids net (Kg)', digits=(14, 3))
	poids_brut  = fields.Float('Poids brut (Kg)', digits=(14, 3))



	def name_get(self):
		result = []
		for rec in self:
			parts = []
			if rec.num_colis:
				parts.append(rec.num_colis)
			if rec.dimensions:
				parts.append(rec.dimensions)
			name = '-'.join(parts) if parts else str(rec.id)
			result.append((rec.id, name))
		return result

	@api.model
	def name_search(self, name='', args=None, operator='ilike', limit=100):
		args = args or []
		domain = []
		if name:
			domain = ['|', ('num_colis', operator, name), ('dimensions', operator, name)]
		recs = self.search(domain + args, limit=limit)
		return recs.name_get()


class IsFactureProformaExportTunisieLigne(models.Model):
	_name = 'is.facture.proforma.export.tunisie.ligne'
	_description = 'Ligne de facture (Proforma Export Tunisie)'
	_order = 'num asc, id asc'

	proforma_id   = fields.Many2one('is.facture.proforma.export.tunisie', 'Proforma', required=True, ondelete='cascade')
	num           = fields.Integer('N°')
	categorie     = fields.Selection([
		('T1', 'Consommable'),
		('T2', 'Matière première'),
		('T3', 'Matière premier hors CE'),
		('T4', 'Moyen de production'),
		('T5', 'Moyen de production hors CE'),
	], 'Catégorie')
	product_id    = fields.Many2one('product.product', 'Article')
	code_pg       = fields.Char('Code PG')
	designation   = fields.Text('Désignation')
	code_douanier = fields.Char('Code douanier')
	lot           = fields.Char('Lot')
	num_colis_id  = fields.Many2one('is.facture.proforma.export.tunisie.colisage', 'Colis', domain="[('proforma_id','=',proforma_id)]")
	num_colis     = fields.Char('N° du colis')
	quantite      = fields.Float('Quantité', digits=(14, 3))
	pu            = fields.Float('PU', digits=(14, 2))
	prix_total    = fields.Float('Prix total', digits=(14, 2), compute='_compute_prix_total', store=True, readonly=True)

	@api.depends('quantite', 'pu')
	def _compute_prix_total(self):
		for record in self:
			record.prix_total = (record.quantite or 0) * (record.pu or 0)



	@api.onchange('product_id')
	def onchange_product_id(self):
		cr=self._cr
		code_pg = designation = code_douanier = pu = False
		if self.product_id:
			SQL="""
				SELECT 
					pt.is_code, 
					pt.name->>'fr_FR' designation, 
					pt.is_nomenclature_douaniere,
					(select cout_act_total from is_cout where name=pp.id limit 1) cout
				FROM product_template pt join product_product pp on pp.product_tmpl_id=pt.id
				WHERE pp.id=%s
			"""%self.product_id.id
			cr.execute(SQL)
			rows = cr.dictfetchall()
			for row in rows:
				code_pg       = row['is_code']
				designation   = row['designation']
				code_douanier = row['is_nomenclature_douaniere']
				pu            = row['cout']
		self.code_pg       = code_pg
		self.designation   = designation
		self.code_douanier = code_douanier
		self.pu            = pu



	@api.onchange('num_colis_id')
	def onchange_num_colis_id(self):
		num_colis = False
		if self.num_colis_id:
			num_colis = self.num_colis_id.num_colis
		self.num_colis = num_colis