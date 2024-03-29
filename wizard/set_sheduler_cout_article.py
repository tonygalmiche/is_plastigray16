# -*- coding: utf-8 -*-
from odoo import models,fields,api,tools
from odoo.exceptions import ValidationError
from datetime import datetime

# from openerp.exceptions import except_orm
# from openerp import models, fields, api, _
# from openerp.exceptions import Warning
import pytz
# from openerp import tools





class shedule_cout_article_report(models.TransientModel):
    _name="shedule.cout.article.report"
    _description="Sauvegarder les couts des articles"


    next_call = fields.Datetime("Heure d'exécution", required=True, default=lambda self: self._next_call())

    # _defaults = {
    #     'next_call': lambda *a: _next_call(),
    # }


    def _next_call(self):
        now=datetime.now()
        return now.strftime('%Y-%m-%d 20:00:00')


    def set_sheduler_cout_article(self):
        view_id = self.env.ref('is_plastigray16.cron_cout_article_report').id
        if view_id:
            sheduler_brw = self.env['ir.cron'].browse(view_id)
            if sheduler_brw.active:
                utc = sheduler_brw.nextcall
                datetime_format = tools.misc.DEFAULT_SERVER_DATETIME_FORMAT
                from_zone=pytz.utc
                to_zone = self.env.user.tz
                user_tz = self.env.user.tz or pytz.utc
                #local = pytz.timezone(user_tz)
                #display_date_result = datetime.strftime(pytz.utc.localize(datetime.strptime(utc, datetime_format)).astimezone(local),u"%d/%m/%Y à %H:%M") 
                raise ValidationError("Cette action est déjà plannifiée le %s"%sheduler_brw.nextcall)
            sheduler_brw.sudo().write({
                'active':True, 
                'nextcall':self.next_call, 'numbercall':1,
                'user_id': self._uid,
            })
        return True
    
    
