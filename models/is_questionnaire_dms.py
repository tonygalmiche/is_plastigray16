# -*- coding: utf-8 -*-
from odoo import models,fields,api


TYPE_QUESTIONNAIRE=[
    ('technique' , "Technique"),
    ('logistique', "Logistique"),
    ('qualite'   , "Qualité"),
    ('operateur' , "Opérateur"),
]

_REPONSE=[
    ("OK" , "OK"),
    ("nOK", "nOK"),
]

class is_questionnaire_dms(models.Model):
    _name='is.questionnaire.dms'
    _description="Questionnaire DMS"
    _order='date_reponse desc'
    _rec_name = 'id'

    type_questionnaire = fields.Selection(TYPE_QUESTIONNAIRE, "Type de questionnaire", required=True)
    date_reponse       = fields.Datetime("Date réponse")
    questionnaire      = fields.Boolean("Questionnaite", help="Si cette case est cochée, ne pas afficher les réponses",default=False)
    of_id              = fields.Many2one('is.of', 'OF')
    habilitation_id    = fields.Many2one('is.theia.habilitation.operateur', 'Habilitation')
    employee_id        = fields.Many2one("hr.employee", "Employé")
    question_ids       = fields.One2many('is.questionnaire.dms.question'  , 'questionnaire_id', "Questions", copy=True)

    def acceder_questionnaire_action(self):
        for obj in self:
            res= {
                'name': 'Questionnaire',
                'view_mode': 'form',
                'res_model': 'is.questionnaire.dms',
                'res_id': obj.id,
                'type': 'ir.actions.act_window',
            }
            return res


class is_questionnaire_dms_question(models.Model):
    _name='is.questionnaire.dms.question'
    _description="Questions du questionnaire DMS"
    _order='sequence,id'

    questionnaire_id = fields.Many2one('is.questionnaire.dms', 'Questionnaire', required=True, ondelete='cascade', readonly=True)
    sequence         = fields.Integer("Ordre")
    question         = fields.Char("Question", required=True)
    reponse          = fields.Selection(_REPONSE, "Réponse (correction)")
    reponse_color    = fields.Selection(_REPONSE, "Réponse", compute='_compute_reponse_color')


    @api.depends('reponse')
    def _compute_reponse_color(self):
        for obj in self:
            obj.reponse_color = obj.reponse
