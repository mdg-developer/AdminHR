from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from pytz import timezone, UTC

class HRReward(models.Model):
    _name = 'hr.reward'
    _description = 'Rewards'
    _order = 'id desc'
    
    utc_time = fields.Datetime.now()
    tz = timezone('Asia/Yangon')
    name = fields.Char(string='Name', copy=False, readonly=True)
    date = fields.Date('Warning Date',default= UTC.localize(utc_time, is_dst=None).astimezone(tz).date())
    employee_id = fields.Many2one('hr.employee', string='Employee')
    company_id = fields.Many2one('res.company', string='Company')
    branch_id = fields.Many2one('res.branch', string='Branch')
    department_id = fields.Many2one('hr.department', string='Department')
    description = fields.Char('Description')
    reward_type_id = fields.Many2one('reward.type', string='Reward Type')
    reward_title_id = fields.Many2one('reward.title', string='Reward Title')
    mark = fields.Float('Mark')
    reward_no = fields.Char('Reward No')
    linked_reward_id = fields.Many2one('hr.reward', 'Linked Reward')
    manager_reward_ids = fields.One2many('hr.reward', 'linked_reward_id')
    temp_lines = fields.One2many('hr.reward.temp', 'reward_id')
    state = fields.Selection([('draft', 'Draft'),
                              ('submit', ' Submitted'),
                              ('approve', 'Approved'),
                              ('decline', 'Declined'),
                              ('expire', 'Expired')], string='Status', readonly=True, index=True, copy=False,
                             default='draft', tracking=True)
    approved = fields.Boolean('Approved', copy=False, default=False)
    fiscal_year = fields.Many2one('account.fiscal.year', string='Fiscal Year')
    
    warn_date = fields.Date('Warning Date',default= UTC.localize(utc_time, is_dst=None).astimezone(tz).date())
    fine_amt = fields.Float('Reward Amount')
    warning_attach_id = fields.One2many('reward.attachment','attachment_reward_id')
    attachment = fields.Binary(string='Attachment')
    attached_filename = fields.Char("Attachment Filename")

    @api.onchange('employee_id', 'reward_type_id')
    def onchange_reward_type_id(self):
        if self.reward_type_id and self.employee_id:
            self.reward_title_id = self.reward_type_id.reward_title_ids and self.reward_type_id.reward_title_ids[0] or False
            self.mark = self.reward_type_id.mark
            temp_lines = self.env['hr.reward.temp']
            if self.reward_type_id.manager_mark != 0 and self.employee_id.parent_id.id:
                temp_lines += temp_lines.new({'employee_id': self.employee_id.parent_id.id, 'mark': self.reward_type_id.manager_mark})
            if self.employee_id.parent_id != self.employee_id.approve_manager and self.reward_type_id.approval_mark != 0 and self.employee_id.approve_manager.id:
                temp_lines += temp_lines.new({'employee_id': self.employee_id.approve_manager.id, 'mark': self.reward_type_id.approval_mark})
            if self.employee_id.approve_manager != self.employee_id.dotted_line_manager_id and self.reward_type_id.dotted_line_mark != 0 and self.employee_id.dotted_line_manager_id.id:
                temp_lines += temp_lines.new({'employee_id': self.employee_id.dotted_line_manager_id.id, 'mark': self.reward_type_id.dotted_line_mark})
            self.temp_lines = temp_lines

    def action_submit(self):
        self.state = 'submit'

    def action_approve(self):
        for temp in self.temp_lines:
            today = fields.Date.today()
            today_plus_one = today + timedelta(days=1)
            fiscal_year = self.env['account.fiscal.year'].sudo().search([('date_from', '<=', today_plus_one), 
                                                                        ('date_to', '>=', today_plus_one), 
                                                                        ('company_id', '=', temp.employee_id.company_id.id)], limit=1)
            self.create({
                'employee_id': temp.employee_id.id,
                'date': self.date,
                'description': self.description,
                'reward_type_id': self.reward_type_id.id,
                'reward_title_id': self.reward_title_id.id,
                'linked_reward_id': self.id,
                'mark': temp.mark,
                'fiscal_year': fiscal_year.id,
                'approved': True,
            })
        self.temp_lines.unlink()
        self.approved = True
        self.state = 'approve'
        self.manager_reward_ids.write({'state': 'approve'})
        one_signal_values = {'employee_id': self.employee_id.id,
                                     'contents': _('%s is rewarded for %s') % (self.employee_id.name, self.reward_title_id.name),
                                     'headings': _('WB B2B : Reward CREATED')}
        self.env['one.signal.notification.message'].create(one_signal_values)

    def action_decline(self):
        self.state = 'decline'

    @api.model
    def create(self, vals):
        reward_no = self.env['ir.sequence'].next_by_code('reward.code')
        if reward_no:
            vals['name'] = reward_no
        return super(HRReward, self).create(vals)
    
    def create_temp_lines(self):
        temp_lines = self.env['hr.reward.temp']
        if self.reward_type_id.manager_mark != 0 and self.employee_id.parent_id.id:
            temp_lines += temp_lines.new({'employee_id': self.employee_id.parent_id.id, 'mark': (self.reward_type_id.manager_mark * 0.5)})
        if self.employee_id.parent_id != self.employee_id.approve_manager and self.reward_type_id.approval_mark != 0 and self.employee_id.approve_manager.id:
            temp_lines += temp_lines.new({'employee_id': self.employee_id.approve_manager.id, 'mark': (self.reward_type_id.approval_mark * 0.5)})
        if self.employee_id.approve_manager != self.employee_id.dotted_line_manager_id and self.reward_type_id.dotted_line_mark != 0 and self.employee_id.dotted_line_manager_id.id:
            temp_lines += temp_lines.new({'employee_id': self.employee_id.dotted_line_manager_id.id, 'mark': (self.reward_type_id.dotted_line_mark * 0.5)})
        self.temp_lines = temp_lines
            
    def _generate_reward_carried_forward(self, employee_ids=None):
        today = fields.Date.today()
        prev_month = today - timedelta(days=30)
        today_plus_one = today + timedelta(days=1)
        fiscal_obj = self.env['account.fiscal.year'].sudo()
        fiscal_year = fiscal_obj.search([('date_from', '<=', prev_month), 
                                        ('date_to', '>=', prev_month)], limit=1)
        # if fiscal_year and today == fiscal_year.date_to:
        reward_obj = self.env['hr.reward'].sudo()
        reward_type_obj = self.env['reward.type'].sudo()
        
        # Change prev fiscal year old rewards to expired state
        domain = [('state', '=', 'approve'), ('date', '>=', fiscal_year.date_from), ('date', '<=', fiscal_year.date_to)]
        if employee_ids:
            employees = self.env['hr.employee'].sudo().search([('id', 'in', employee_ids)])
            domain += [('employee_id', 'in', employees.ids)]
        
        prev_rewards = reward_obj.search(domain)
        for reward in prev_rewards:
            prev_fiscal_year = fiscal_obj.search([('date_from', '<=', prev_month), 
                                                ('date_to', '>=', prev_month), 
                                                ('company_id', '=', reward.employee_id.company_id.id)], limit=1)
            reward.state = 'expire'
            reward.approved = False
            reward.fiscal_year = prev_fiscal_year

        for reward in prev_rewards.filtered(lambda x: not x.linked_reward_id and x.mark != 0):
            upcoming_fiscal_year = fiscal_obj.search([('date_from', '<=', today_plus_one), 
                                                    ('date_to', '>=', today_plus_one), 
                                                    ('company_id', '=', reward.employee_id.company_id.id)], limit=1)
            carry_mark = reward.mark * 0.5
            type_domain = [('name', 'ilike', reward.reward_type_id.name), ('carry_reward', '=', True)]
            reward_type_id = self.env['reward.type']
            if not reward_type_obj.search(type_domain):
                name = str(reward.reward_type_id.name) + ' Carried Forward'
                vals = {
                    'name': name,
                    'mark': reward.reward_type_id.mark,
                    'manager_mark': reward.reward_type_id.manager_mark,
                    'approval_mark': reward.reward_type_id.approval_mark,
                    'dotted_line_mark': reward.reward_type_id.dotted_line_mark,
                    'reward_title_ids': reward.reward_type_id.reward_title_ids.ids,
                    'carry_reward': True
                }
                reward_type_id = reward_type_obj.create(vals)
            else:
                reward_type_id = reward_type_obj.search(type_domain, limit=1)
            # existing_reward = reward_obj.search([
            #     ('employee_id', '=', reward.employee_id.id), 
            #     ('state', '=', 'approve'), 
            #     ('fiscal_year', '=', upcoming_fiscal_year.id),
            #     ('reward_type_id', '=', reward_type_id.id),
            #     ('reward_title_id', '=', reward.reward_title_id.id)
            # ])
            # if existing_reward:
            #     existing_reward.unlink()
            values = {
                'employee_id': reward.employee_id.id,
                'date': fields.Date.today(),
                'state': 'draft',
                'description': reward.description,
                'reward_type_id': reward_type_id.id,
                'reward_title_id': reward.reward_title_id.id,
                'mark': carry_mark,
                'fiscal_year': upcoming_fiscal_year.id,
            }
            carry_reward = reward_obj.create(values)
            if carry_reward:
                carry_reward.create_temp_lines()
                carry_reward.action_submit()
                carry_reward.action_approve()


class HrRewardTemp(models.Model):
    _name = 'hr.reward.temp'
    _description = 'Reward Temp'

    reward_id = fields.Many2one('hr.reward', required=True, ondelete="cascade")
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    mark = fields.Float('Mark', required=True)

class HrRewardAttachment(models.Model):
    _name = 'reward.attachment'

    attachment_reward_id = fields.Many2one('hr.reward')
    attachment = fields.Binary(string='Attachment')
    attached_filename = fields.Char("Attachment Filename")
