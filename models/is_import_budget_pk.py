# -*- coding: utf-8 -*-

from odoo import models,fields,api
#import psycopg2
#from psycopg2.extras import RealDictCursor
from odoo.exceptions import ValidationError


class is_import_budget_pk(models.Model):
    _name = 'is.import.budget.pk'
    _description = u"Import budget Gray (PIC/PDP) dans PK"
    _order='id desc'

    product_id     = fields.Many2one('product.product', u"Article")
    annee          = fields.Char(u'Année (AAAA)')
    mois           = fields.Char(u'Mois (AAAA-MM')
    anomalies      = fields.Text(u'Anomalies (articles non trouvés)', readonly=True)
    nb_lignes      = fields.Integer(u'Nb lignes importées)'         , readonly=True)


    def voir_les_lignes(self):
        for obj in self:
            domain=[
                ('type_donnee' ,'=','pic'),
            ]
            if obj.product_id:
                domain.append(('product_id','=',obj.product_id.id))
            if obj.annee:
                domain.append(('annee','=',obj.annee))
            if obj.mois:
                domain.append(('mois','=',obj.mois))

            return {
                'name'     : obj.id,
                'view_mode': 'tree,form',
                'res_model': 'is.pic.3ans',
                'domain'   : domain,
                'type'     : 'ir.actions.act_window',
                'limit'    : 1000,
            }


    def import_budget_pk(self):
        uid=self._uid
        for obj in self:
            if not obj.annee and not obj.mois:
                raise ValidationError(u"Il est obligatoire de saisir l'année ou le mois")
            company = self.env.user.company_id
            base1="odoo1"
            base3="odoo3"
            if company.is_postgres_host=='localhost':
                base1="pg-odoo1"
                base3="pg-odoo3"
            cnx1=False
            cnx3=False
            try:
                cnx1 = psycopg2.connect("dbname='"+base1+"' user='"+company.is_postgres_user+"' host='"+company.is_postgres_host+"' password='"+company.is_postgres_pwd+"'")
                cnx3 = psycopg2.connect("dbname='"+base3+"' user='"+company.is_postgres_user+"' host='"+company.is_postgres_host+"' password='"+company.is_postgres_pwd+"'")
            except:
                raise ValidationError("Impossible de se connecter à odoo1 ou odoo3")
            cr1 = cnx1.cursor(cursor_factory=RealDictCursor)
            cr3 = cnx3.cursor(cursor_factory=RealDictCursor)

            #** Purge des données *********************************************
            SQL="DELETE FROM is_pic_3ans WHERE id>0"
            if obj.product_id:
                SQL+=" and product_id="+str(obj.product_id.id)
            if obj.annee:
                SQL+=" and annee='"+obj.annee+"' "
            if obj.mois:
                SQL+=" and mois='"+obj.mois+"' "
            cr3.execute(SQL)
            cnx3.commit()
            #******************************************************************

            SQL="""
                select pic.annee, pic.mois, pt.is_code codepg, pic.type_donnee, pic.quantite, rp.is_code, rp.is_adr_code, pic.mold_dossierf, pic.description
                from is_pic_3ans pic join res_partner rp on pic.fournisseur_id=rp.id
                                     join product_product pp on pic.product_id=pp.id
                                     join product_template pt on pp.product_tmpl_id=pt.id
                where rp.is_code='7504'
            """
            if obj.product_id:
                SQL+=" and pt.is_code='"+obj.product_id.is_code+"' "
            if obj.annee:
                SQL+=" and pic.annee='"+obj.annee+"' "
            if obj.mois:
                SQL+=" and pic.mois='"+obj.mois+"' "
            SQL+="""
                order by pt.is_code, pic.mois, pic.type_donnee
            """
            cr1.execute(SQL)
            rows1 = cr1.fetchall()
            anomalies=[]
            nb=0
            for row1 in rows1:
                #** Recherche Fournisseur de destination **********************
                SQL="""
                    select id
                    from res_partner
                    where is_code=%s and is_adr_code=%s
                """
                cr3.execute(SQL,[row1["is_code"],row1["is_adr_code"]])
                rows3 = cr3.fetchone()
                fournisseur_id=False
                if rows3:
                    fournisseur_id = rows3["id"]
                else:
                    raise ValidationError("Fournisseur %s %s non trouvé"%(row1["is_code"],row1["is_adr_code"]))
                #**************************************************************

                #** Recherche article *****************************************
                codepg = row1["codepg"]
                SQL="""
                    select pp.id, pt.is_client_id, pt.is_fournisseur_id
                    from product_product pp join product_template pt on pp.product_tmpl_id=pt.id
                    where pt.is_code=%s
                """
                cr3.execute(SQL,[codepg])
                row3 = cr3.fetchone()
                #**************************************************************

                if row3:
                    nb+=1
                    product_id     = row3["id"]
                    client_id      = row3["is_client_id"]
                    fournisseur_id = row3["is_fournisseur_id"]
                    SQL="""
                        INSERT INTO is_pic_3ans(
                            type_donnee, annee, mois, product_id, quantite, mold_dossierf, description, client_id, fournisseur_id,
                            create_uid, write_uid, create_date,write_date)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now() AT TIME ZONE 'UTC', now() AT TIME ZONE 'UTC')
                    """
                    cr3.execute(SQL,[
                        'pic',
                        row1["annee"],
                        row1["mois"],
                        product_id,
                        row1["quantite"],
                        row1["mold_dossierf"],
                        row1["description"],
                        client_id,
                        fournisseur_id,
                        uid,
                        uid,
                    ])
                else:
                    if codepg not in anomalies:
                        anomalies.append(codepg)
            cnx3.commit()
            obj.anomalies = (anomalies and "\n".join(anomalies)) or False
            obj.nb_lignes = nb
            cnx1.close()
            cnx3.close()



