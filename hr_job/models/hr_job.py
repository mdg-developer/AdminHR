from odoo import fields, models, api, _

class HrJobBenefit(models.Model):    
    _name = 'hr.job.benefit'    
    _description = 'Job Position Benefit'    
    
    name = fields.Char('Name')
    job_id  = fields.Many2one('hr.job', string='Job Position')
    benefit_line = fields.One2many('job.benefit.line', 'job_id', string='Benefit')
    company_id = fields.Many2one('res.company', string='Company')
    branch_id = fields.Many2one('res.branch', string='Branch')
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Name must be unique!')
    ]
    
    @api.onchange('job_id')
    def onchange_job_id(self):
        line = self.env['job.line'].search([('job_id', '=', self.job_id.id)])
        if self.job_id:
            self.company_id = line.company_id.id
            self.branch_id = line.branch_id.id
            
class JobBenefitLine(models.Model):    
    _name = 'job.benefit.line'    
    
    job_id = fields.Many2one('hr.job.benefit', string='Job Benefit',required=True, index=True, ondelete='cascade')
    benefit_id  = fields.Many2one('hr.job.benefit.config', 'Benefit')
    description  = fields.Char('Description')
    qty = fields.Integer(string="Quantity")
    state = fields.Selection([('pending', 'Pending'),  ('on_hand', 'On Hand'),('paid', 'Paid'), ('hand_over', 'Hand Over')],
                              string="Status", default='pending', required=True, readonly=False, copy=False)
    