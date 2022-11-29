from odoo import fields, models

class SalaryTable(models.Model):    
    _name = 'hr.salary'    
    _description = 'Salary Table'

    job_grade_id  = fields.Many2one('job.grade', string='Job Grade')
    salary_level_id   = fields.Many2one('salary.level', string='Salary Level ')
    salary = fields.Float(string='Salary')
    
    _sql_constraints = [
        ('job_level_uniq', 'unique(job_grade_id,salary_level_id)', 'Job Grade and Salary Level must be unique!')        
    ]