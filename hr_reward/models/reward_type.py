from odoo import fields, models


class RewardType(models.Model):
    _name = 'reward.type'
    _description = 'Reward Type'

    name = fields.Char('Name')
    mark = fields.Float('Mark')
    manager_mark = fields.Float('Manager Mark')
    approval_mark = fields.Float('Approval Manager Mark')
    dotted_line_mark = fields.Float('Dotted line Manager Mark')
    reward_title_ids = fields.One2many('reward.title', 'type_id', 'Reward Titles')
    carry_reward = fields.Boolean(string='Carried Forward', default=False)
    
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Name must be unique!')
    ]


class RewardTitle(models.Model):
    _name = 'reward.title'
    _description = 'Reward Title'

    name = fields.Char('Name', required=True)
    type_id = fields.Many2one('reward.type', string='Reward Type', required=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name, type_id)', 'Name must be unique!')]
