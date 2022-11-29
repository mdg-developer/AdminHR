from odoo import fields, models,api


class TravelType(models.Model):
    _name = 'hr.travel.type'
    _description = 'Travel Type'

    name = fields.Char('Name', required=True)
    job_grade_id = fields.Many2one('job.grade', string='Job Grade')
    allowance_ids = fields.One2many('hr.travel.allowance', 'type_id', 'Allowances')


class TravelAllowance(models.Model):
    _name = 'hr.travel.allowance'
    _description = 'Travel Allowance'

    name = fields.Char('Name', required=True)
    type_id = fields.Many2one('hr.travel.type', string='Travel Type', index=True, required=True, ondelete='cascade')
    standard_amount = fields.Float('Standard Amount', required=True)
    remark = fields.Char('Remark')
