# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.http import request


class ir_actions_act_url(models.Model):
    _inherit = 'ir.actions.act_url'




    # def read(self):
    #     res=super().read()

    #     print(self,res)

    #     return res



    # def get_company(self, cr, uid):
    #     user = self.pool['res.users'].browse(cr, uid, [uid])[0]
    #     company  = user.company_id
    #     return company


    # def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
    #     if not context: context = {}
    #     results = super(ir_actions_act_url, self).read(cr, uid, ids, fields=fields, context=context, load=load)
    #     if load=='_classic_read' and len(ids) == 1:

    #             if results[0]['name']==u'is_url_parc_presses_action':
    #                 user = self.pool['res.users'].browse(cr, uid, [uid], context=context)[0]
    #                 soc  = user.company_id.is_code_societe
    #                 ip   = request.httprequest.environ['REMOTE_ADDR'] 
    #                 url='http://raspberry-theia/atelier.php?atelier=inj&soc='+str(soc)+'&uid='+str(uid)
    #                 results[0].update({'url': url})


    #             if results[0]['name']==u'is_url_parc_presses_new_action':
    #                 user = self.pool['res.users'].browse(cr, uid, [uid], context=context)[0]
    #                 soc  = user.company_id.is_code_societe
    #                 ip   = request.httprequest.environ['REMOTE_ADDR'] 
    #                 url='http://raspberry-theia4/atelier.php?atelier=inj&soc='+str(soc)+'&uid='+str(uid)
    #                 results[0].update({'url': url})


    #             if results[0]['name']==u'is_url_parc_assemblage_action':
    #                 user = self.pool['res.users'].browse(cr, uid, [uid], context=context)[0]
    #                 soc  = user.company_id.is_code_societe
    #                 ip   = request.httprequest.environ['REMOTE_ADDR'] 
    #                 url='http://raspberry-theia4/atelier.php?atelier=ass&soc='+str(soc)+'&uid='+str(uid)
    #                 results[0].update({'url': url})

    #             if results[0]['name']==u'is_url_indicateur_rebuts_action':
    #                 user = self.pool['res.users'].browse(cr, uid, [uid], context=context)[0]
    #                 soc  = user.company_id.is_code_societe
    #                 ip   = request.httprequest.environ['REMOTE_ADDR'] 
    #                 url='http://odoo/odoo-theia/rebuts.php?soc='+str(soc)+'&uid='+str(uid)
    #                 results[0].update({'url': url})

    #             if results[0]['name']==u'is_url_indicateur_trs_action':
    #                 user = self.pool['res.users'].browse(cr, uid, [uid], context=context)[0]
    #                 soc  = user.company_id.is_code_societe
    #                 ip   = request.httprequest.environ['REMOTE_ADDR'] 
    #                 url='http://odoo/odoo-theia/trs.php?soc='+str(soc)+'&uid='+str(uid)
    #                 results[0].update({'url': url})


    #             if results[0]['name']==u'is_url_planning_action':
    #                 ip = request.httprequest.environ['REMOTE_ADDR'] 
    #                 company=self.get_company(cr,uid)
    #                 soc=company.partner_id.is_code
    #                 url=company.is_url_intranet_odoo or ''
    #                 url=url+'/odoo-erp/planning/?soc='+str(soc)+'&uid='+str(uid)
    #                 results[0].update({'url': url})

    #             if results[0]['name']==u'is_url_analyse_cbn_action':
    #                 ip = request.httprequest.environ['REMOTE_ADDR'] 
    #                 company=self.get_company(cr,uid)
    #                 soc=company.partner_id.is_code
    #                 url=company.is_url_intranet_odoo or ''
    #                 url=url+'/odoo-erp/cbn/Sugestion_CBN.php?Soc='+str(soc)+'&product_id=&uid='+str(uid)
    #                 results[0].update({'url': url})

    #             if results[0]['name']==u'is_url_pic_3_ans_action':
    #                 ip   = request.httprequest.environ['REMOTE_ADDR'] 
    #                 company=self.get_company(cr,uid)
    #                 soc=company.partner_id.is_code
    #                 url=company.is_url_intranet_odoo or ''
    #                 url=url+'/odoo-erp/analyses/pic-3-ans.php?Soc='+str(soc)+'&uid='+str(uid)
    #                 results[0].update({'url': url})

    #             if results[0]['name']==u'is_url_pic_3_mois':
    #                 ip   = request.httprequest.environ['REMOTE_ADDR'] 
    #                 company=self.get_company(cr,uid)
    #                 soc=company.partner_id.is_code
    #                 url=company.is_url_intranet_odoo or ''
    #                 url=url+'/odoo-erp/analyses/pic-3-mois.php?Soc='+str(soc)+'&uid='+str(uid)
    #                 results[0].update({'url': url})

    #             if results[0]['name']==u'is_url_theia':
    #                 company=self.get_company(cr,uid)
    #                 soc=company.partner_id.is_code
    #                 url=company.is_url_odoo_theia or ''
    #                 results[0].update({'url': url})

    #             if results[0]['name']==u'is_url_theia_suivi_prod':
    #                 company=self.get_company(cr,uid)
    #                 soc=company.partner_id.is_code
    #                 url=company.is_url_intranet_theia or ''
    #                 url=url+'/atelier.php?soc='+soc
    #                 results[0].update({'url': url})

    #     return results


