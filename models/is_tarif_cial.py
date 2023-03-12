# -*- coding: utf-8 -*-
from odoo import models,fields,api
from odoo.exceptions import ValidationError
import datetime


class is_tarif_cial(models.Model):
    _name='is.tarif.cial'
    _description="Tarif commercial"
    _order='product_id, partner_id, indice_prix desc'
    _sql_constraints = [('is_indice_prix_uniq','UNIQUE(partner_id, product_id,indice_prix)', 'Cet indice de prix existe déja pour ce client et cet article')]


    display_name        = fields.Char(string='Name', compute='_compute_display_name')
    partner_id          = fields.Many2one('res.partner', 'Client'      , required=True, index=True)
    product_id          = fields.Many2one('product.template', 'Article', required=True, index=True)
    is_ref_client       = fields.Char("Référence client", related='product_id.is_ref_client', readonly=True)
    is_mold_dossierf    = fields.Char('Moule', related='product_id.is_mold_dossierf', readonly=True)
    is_gestionnaire_id  = fields.Many2one('is.gestionnaire', 'Gestionnaire', related='product_id.is_gestionnaire_id', readonly=True)
    indice_prix         = fields.Integer("Indice Prix", required=True, index=True, default=999)
    date_debut          = fields.Date("Date de début")
    date_fin            = fields.Date("Date de fin")
    type_evolution      = fields.Char("Type évolution")
    part_matiere        = fields.Float("Part Matière"       , digits=(12, 4))
    part_composant      = fields.Float("Part Composant"     , digits=(12, 4))
    part_emballage      = fields.Float("Part Emballage"     , digits=(12, 4))
    va_injection        = fields.Float("VA Injection"       , digits=(12, 4))
    va_assemblage       = fields.Float("VA Assemblage"      , digits=(12, 4))
    frais_port          = fields.Float("Frais de Port"      , digits=(12, 4))
    logistique          = fields.Float("Logistique"         , digits=(12, 4))
    amortissement_moule = fields.Float("Amt client négocié" , digits=(12, 4))
    amt_interne         = fields.Float("Amt interne"        , digits=(12, 4))
    cagnotage           = fields.Float("Cagnotage"          , digits=(12, 4))
    surcout_pre_serie   = fields.Float("Surcôut pré-série"  , digits=(12, 4))
    prix_vente          = fields.Float("Prix de Vente"      , digits=(12, 4))
    ecart               = fields.Float("Ecart prix de vente", digits=(12, 4), compute='_ecart')
    numero_dossier      = fields.Char("Numéro de dossier")
    active              = fields.Boolean('Actif', default=True)


    @api.depends(
            'part_matiere', 
            'part_composant', 
            'part_emballage', 
            'va_injection', 
            'va_assemblage', 
            'frais_port', 
            'logistique', 
            'amortissement_moule', 
            'amt_interne', 
            'cagnotage', 
            'surcout_pre_serie', 
            'prix_vente'
        )
    def _ecart(self):
        for obj in self:
            obj.ecart = obj.prix_vente-( \
                obj.part_matiere+ \
                obj.part_composant+ \
                obj.part_emballage+ \
                obj.va_injection+ \
                obj.va_assemblage+ \
                obj.frais_port+ \
                obj.logistique+ \
                obj.amortissement_moule+ \
                obj.amt_interne+ \
                obj.cagnotage+ \
                obj.surcout_pre_serie \
            )

    @api.depends('product_id', 'indice_prix')
    def _compute_display_name(self):
        for obj in self:
            self.display_name = obj.product_id.is_code + " ("+str(obj.indice_prix)+")"


    def create(self, vals):
        res=super(is_tarif_cial, self).create(vals)
        if res.ecart!=0:
            raise ValidationError(u"Ecart prix de vente différent de 0 !")
        return res


    def write(self, vals):
        res=super(is_tarif_cial, self).write(vals)
        for obj in self:
            if obj.ecart!=0:
                raise ValidationError(u"Ecart prix de vente différent de 0 !")
        return res


    def evolution_indice_prix(self):
        if len(self)>1:
            raise ValidationError(u"Impossible de faire évoluer plusieurs tarifs en même temps !")
        for obj in self:
            if obj.indice_prix!=999:
                raise ValidationError(u"Cette fonction n'est possible que depuis l'indice 999 !")
            new_obj=obj.copy({})
            res=self.env['is.tarif.cial'].search([
                ['partner_id', '=', obj.partner_id.id], 
                ['product_id', '=', obj.product_id.id],
                ['indice_prix', '!=', 999],
            ], order="indice_prix desc", limit=1)
            indice_prix=1
            for line in res:
                indice_prix=line.indice_prix+1
            new_obj.indice_prix=indice_prix

            if obj.indice_prix==999:
                obj.numero_dossier=""
                obj.type_evolution=""


    def copy(self,vals):
        for obj in self:
            vals['indice_prix']=0
            res=super(is_tarif_cial, self).copy(vals)
            return res


    def name_get(self):
        res = []
        for obj in self:
            name=obj.product_id.is_code
            res.append((obj.id,name))
        return res


    def init(self):
        cr = self._cr
        cr.execute("""
            CREATE OR REPLACE FUNCTION get_amortissement_moule(code_client char, pt_id  integer) RETURNS float AS $$
            BEGIN
                RETURN (
                    COALESCE(
                        (
                            select itc.amortissement_moule 
                            from is_tarif_cial itc inner join res_partner rp on itc.partner_id=rp.id
                            where itc.product_id=pt_id and rp.is_code=code_client and itc.indice_prix=999
                            order by itc.amortissement_moule desc limit 1
                        )
                    ,0)
                );
            END;
            $$ LANGUAGE plpgsql;

            
            CREATE OR REPLACE FUNCTION get_amortissement_moule_a_date(code_client char, pt_id  integer, date_tarif date) RETURNS float AS $$
            BEGIN
                RETURN (
                    COALESCE(
                        (
                            select itc.amortissement_moule 
                            from is_tarif_cial itc inner join res_partner rp on itc.partner_id=rp.id
                            where 
                                itc.product_id=pt_id and rp.is_code=code_client and 
                                (itc.date_fin   is null or itc.date_fin   >= date_tarif) and
                                (itc.date_debut is null or itc.date_debut <= date_tarif) 
                            order by itc.indice_prix desc limit 1
                        )
                    ,0)
                );
            END;
            $$ LANGUAGE plpgsql;  


            CREATE OR REPLACE FUNCTION get_amt_interne_a_date(code_client char, pt_id  integer, date_tarif date) RETURNS float AS $$
            BEGIN
                RETURN (
                    COALESCE(
                        (
                            select itc.amt_interne 
                            from is_tarif_cial itc inner join res_partner rp on itc.partner_id=rp.id
                            where 
                                itc.product_id=pt_id and rp.is_code=code_client and 
                                (itc.date_fin   is null or itc.date_fin   >= date_tarif) and
                                (itc.date_debut is null or itc.date_debut <= date_tarif) 
                            order by itc.indice_prix desc limit 1
                        )
                    ,0)
                );
            END;
            $$ LANGUAGE plpgsql;


            CREATE OR REPLACE FUNCTION get_cagnotage_a_date(code_client char, pt_id  integer, date_tarif date) RETURNS float AS $$
            BEGIN
                RETURN (
                    COALESCE(
                        (
                            select itc.cagnotage 
                            from is_tarif_cial itc inner join res_partner rp on itc.partner_id=rp.id
                            where 
                                itc.product_id=pt_id and rp.is_code=code_client and 
                                (itc.date_fin   is null or itc.date_fin   >= date_tarif) and
                                (itc.date_debut is null or itc.date_debut <= date_tarif) 
                            order by itc.indice_prix desc limit 1
                        )
                    ,0)
                );
            END;
            $$ LANGUAGE plpgsql;
        """)






