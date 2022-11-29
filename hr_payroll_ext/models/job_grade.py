from odoo import fields, models


class JobGrade(models.Model):
    _inherit = 'job.grade'

    analytic_tag_id = fields.Many2one('account.analytic.tag', string='Analytic Tag', required=True)
