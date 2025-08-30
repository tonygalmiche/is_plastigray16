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
	date_creation      = fields.Date("Date de création", default=lambda self: fields.Datetime.now(), readonly=True, tracking=True)
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

		return super().create(vals_list)




class IsFactureProformaExportTunisieColisage(models.Model):
	_name = 'is.facture.proforma.export.tunisie.colisage'
	_description = 'Ligne de colisage (Proforma Export Tunisie)'
	_order = 'id asc'

	proforma_id = fields.Many2one('is.facture.proforma.export.tunisie', 'Proforma', required=True, ondelete='cascade')
	num_colis   = fields.Char('Numéro du colis')
	dimensions  = fields.Char('Dimensions')
	poids_net   = fields.Float('Poids net (Kg)', digits=(14, 3))
	poids_brut  = fields.Float('Poids brut (Kg)', digits=(14, 3))


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
	code_pg       = fields.Char('Code PG')
	designation   = fields.Text('Désignation')
	code_douanier = fields.Char('Code douanier')
	lot           = fields.Char('Lot')
	num_colis     = fields.Char('Numéro du colis')
	quantite      = fields.Float('Quantité', digits=(14, 3))
	pu            = fields.Float('PU', digits=(14, 2))
	prix_total    = fields.Float('Prix total', digits=(14, 2))
