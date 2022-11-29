from odoo import fields, models,api


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    summary_request_id = fields.Many2one('summary.request')
    attachment = fields.Binary(related='summary_request_id.attachment', string='Attachment')
    file_name = fields.Char(related='summary_request_id.file_name')
