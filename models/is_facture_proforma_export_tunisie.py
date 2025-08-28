# -*- coding: utf-8 -*-
from odoo import models, fields


class IsFactureProformaExportTunisie(models.Model):
	_name = 'is.facture.proforma.export.tunisie'
	_description = 'Facture Proforma Export Tunisie'
	_order = 'chrono desc'

	chrono             = fields.Integer('Chrono', index=True)
	client_id          = fields.Many2one('res.partner', 'Client')
	adresse            = fields.Text('Adresse de facturation')
	date_creation      = fields.Date("Date de création", default=lambda self: fields.Datetime.now(), readonly=True)
	type_exportation   = fields.Selection([
		('10', 'Exportation définitive'),
		('20', 'Exportation temporaire'),
		('30', 'Retour pour perfectionnement actif réparation'),
		('40', "Exportation définitive suite mise en conformité"),
		('50', 'Réexportation après réparation'),
	], "Type d'exportation")
	mode_transport     = fields.Selection([
		('10', 'Routier'),
		('20', 'Maritime'),
		('30', 'Aérien'),
	], 'Mode de transport')
	commentaire        = fields.Text('Commentaire')

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
