# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date
from pytz import timezone, UTC


class ChangingShift(models.Model):
    _name = 'changing.shift'
    _description = 'Changing Shift'

    name = fields.Char('Name', default='New', required=True)
    date = fields.Date('Effective Date', default=fields.Date.today)
    resource_calendar_id = fields.Many2one('resource.calendar', string='Working Hours', required=True)
    department_id = fields.Many2one('hr.department', string='Department')
    new_resource_calendar_id = fields.Many2one('resource.calendar', string='New Working Hours', required=True)
    state = fields.Selection([('draft', 'Draft'),
                              ('submit', 'Submitted'),
                              ('approve', 'Approved')], default='draft', copy=False, required=True)
    line_ids = fields.One2many('changing.shift.line', 'changing_shift_id', string='Changing Shift Line')
    allow_immediate_approve = fields.Boolean('Immediate Approve', compute='_allow_approve')

    @api.depends('date')
    def _allow_approve(self):
        local = self._context.get('tz', 'Asia/Yangon')
        local_tz = timezone(local)
        today_date = UTC.localize(fields.Datetime.now(), is_dst=True).astimezone(tz=local_tz).date()
        for rec in self:
            if rec.date <= today_date:
                rec.allow_immediate_approve = True
            else:
                rec.allow_immediate_approve = False

    @api.onchange('resource_calendar_id', 'department_id')
    def onchange_resource_calendar_id(self):
        if self.resource_calendar_id:
            domain = [('resource_calendar_id', '=', self.resource_calendar_id.id)]
            if self.department_id:
                domain += [('department_id', '=', self.department_id.id)]
            new_lines = self.env['changing.shift.line']
            employees = self.env['hr.employee'].search(domain)
            for emp in employees:
                new_line_value = {'employee_id': emp.id}
                new_line = new_lines.new(new_line_value)
                new_lines += new_line
            self.line_ids = new_lines

    @api.model
    def create(self, vals):
        calendar_obj = self.env['resource.calendar']
        old_schedule = calendar_obj.browse(vals.get('resource_calendar_id'))
        new_schedule = calendar_obj.browse(vals.get('new_resource_calendar_id'))
        vals['name'] = old_schedule.name + ' to ' + new_schedule.name
        return super(ChangingShift, self).create(vals)

    def write(self, vals):
        calendar_obj = self.env['resource.calendar']
        if vals.get('resource_calendar_id') or vals.get('new_resource_calendar_id'):
            old_schedule = calendar_obj.browse(vals.get('resource_calendar_id')) or self.resource_calendar_id
            new_schedule = calendar_obj.browse(vals.get('new_resource_calendar_id')) or self.new_resource_calendar_id
            vals['name'] = old_schedule + ' to ' + new_schedule
        return super(ChangingShift, self).write(vals)

    def action_submit(self):
        self.state = 'submit'

    def action_approve(self):
        source = self._context.get('source', False) or False
        local = self._context.get('tz', 'Asia/Yangon')
        local_tz = timezone(local)
        current_date = UTC.localize(fields.Datetime.now(), is_dst=True).astimezone(tz=local_tz)
        if self.date > current_date.date() and source and source == 'schedule':
            return
        for line in self.line_ids:
            employee = line.employee_id
            employee.resource_calendar_id = self.new_resource_calendar_id.id
            if employee.contract_id:
                employee.contract_id.resource_calendar_id = self.new_resource_calendar_id.id
        self.state = 'approve'

    def action_draft(self):
        self.state = 'draft'


class ChangingShiftLine(models.Model):
    _name = 'changing.shift.line'
    _description = 'Changing Shift Line'

    employee_id = fields.Many2one('hr.employee', 'Employee')
    changing_shift_id = fields.Many2one('changing.shift')
    date = fields.Date('Effective Date', related='changing_shift_id.date')
    department_id = fields.Many2one('hr.department', related='changing_shift_id.department_id', string='Department')
    resource_calendar_id = fields.Many2one('resource.calendar', related='changing_shift_id.resource_calendar_id', string='Working Hours')
    new_resource_calendar_id = fields.Many2one('resource.calendar', related='changing_shift_id.new_resource_calendar_id', string='New Working Hours')
    state = fields.Selection(related='changing_shift_id.state', store=True)
