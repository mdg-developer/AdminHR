from odoo import fields, models

class SalaryTable(models.Model):    
    _name = 'fleet.trip'    
    _description = 'Trip Type'

    name = fields.Char(string='Name')
    expense_id = fields.One2many('route.expense','route_plan_id')
    allowance_id = fields.One2many('route.allowance','route_plan_id')
    
    
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Name must be unique!')
    ]
       
    
class RouteExpense(models.Model):    
    _name = 'route.expense'
    _description = 'Route Expense'  
     
    name = fields.Char(string='Expense')
    amount = fields.Float(string='Standard Amount')
    remark = fields.Char(string='Remark')
    route_plan_id = fields.Many2one('route.plan', string='Route Plan')
     
class RouteAllowance(models.Model):    
    _name = 'route.allowance'   
     
    name = fields.Char(string='Allowance')
    amount = fields.Float(string='Standard Amount')
    remark = fields.Char(string='Remark')
    route_plan_id = fields.Many2one('route.plan', string='Route Plan')