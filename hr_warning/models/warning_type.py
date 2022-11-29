from odoo import fields, models


class WarningType(models.Model):    
    _name = 'warning.type'    
    _description = 'Warning Type'

    name = fields.Char('Name')
    mark = fields.Float('Mark')
    manager_mark = fields.Float('Manager Mark')
    approval_mark = fields.Float('Approval Manager Mark')
    dotted_line_mark = fields.Float('Dotted line Manager Mark')
    warning_title_ids = fields.One2many('warning.title', 'type_id', 'Warning Titles')
    carry_warning = fields.Boolean(string='Carried Forward', default=False)
    
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Name must be unique!')
    ]


class WarningTitle(models.Model):
    _name = 'warning.title'
    _description = 'Warning Title'

    name = fields.Char('Name', required=True)
    type_id = fields.Many2one('warning.type', string='Warning Type', required=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name, type_id)', 'Name must be unique!')]
