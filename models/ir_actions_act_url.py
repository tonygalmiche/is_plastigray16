# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.http import request
import base64



class ir_actions_report(models.Model):
    "Utilisé pour obtenir le PDF du bilan de fin d'OF en XML-RCP"
    _inherit = "ir.actions.report"

    def render_qweb_pdf_xmlrpc(self, report_ref, res_ids=None, data=None):
        print("TEST")
        pdf_content = self._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)
        print("pdf_content=",pdf_content)

        pdf_content_encoded = base64.b64encode(pdf_content[0]) # needs to be encoded to be able to access with xmlrpc
        print("pdf_content_encoded=",pdf_content_encoded)

        return pdf_content_encoded


class ir_actions_act_url(models.Model):
    _inherit = 'ir.actions.act_url'

    def get_soc_uid(self):
        uid     = self._uid
        user    = self.env['res.users'].browse(uid)
        soc     = user.company_id.is_code_societe
        return soc,uid


    def is_parc_presses_url_action(self):
        soc,uid=self.get_soc_uid()
        url = "http://raspberry-theia4-16/atelier.php?atelier=inj&soc=%s&uid=%s"%(soc,uid)
        return {
            'type'  : 'ir.actions.act_url',
            'target': 'new',
            'url'   : url,
        }

    def is_parc_assemblage_url_action(self):
        soc,uid=self.get_soc_uid()
        url = "http://raspberry-theia4-16/atelier.php?atelier=ass&soc=%s&uid=%s"%(soc,uid)
        return {
            'type'  : 'ir.actions.act_url',
            'target': 'new',
            'url'   : url,
        }

    def is_indicateur_rebut_url_action(self):
        soc,uid=self.get_soc_uid()
        url = "http://odoo16/odoo-theia/rebuts.php?soc=%s&uid=%s"%(soc,uid)
        return {
            'type'  : 'ir.actions.act_url',
            'target': 'new',
            'url'   : url,
        }

    def is_indicateur_trs_url_action(self):
        soc,uid=self.get_soc_uid()
        url = "http://odoo16/odoo-theia/trs.php?soc=%s&uid=%s"%(soc,uid)
        return {
            'type'  : 'ir.actions.act_url',
            'target': 'new',
            'url'   : url,
        }

    def is_planning_url_action(self):
        soc,uid=self.get_soc_uid()
        url = "http://odoo16/odoo-erp/planning/?soc=%s&uid=%s"%(soc,uid)
        return {
            'type'  : 'ir.actions.act_url',
            'target': 'new',
            'url'   : url,
        }

    def is_pic_3ans_url_action(self):
        soc,uid=self.get_soc_uid()
        url = "http://odoo16/odoo-erp/analyses/pic-3-ans.php?soc=%s&uid=%s"%(soc,uid)
        return {
            'type'  : 'ir.actions.act_url',
            'target': 'new',
            'url'   : url,
        }

    def is_pic_3mois_url_action(self):
        soc,uid=self.get_soc_uid()
        url = "http://odoo16/odoo-erp/analyses/pic-3-mois.php?soc=%s&uid=%s"%(soc,uid)
        return {
            'type'  : 'ir.actions.act_url',
            'target': 'new',
            'url'   : url,
        }
