# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import models, fields, api, _


class HrPopupReminder(models.Model):
    _name = 'hr.reminder'

    name = fields.Char(string='Title', required=True)
    model_name = fields.Many2one('ir.model', help="Choose the model name", string="Model", required=True, domain="[('model', 'like','hr')]")
    model_field = fields.Many2one('ir.model.fields', string='Field', help="Choose the field",
                                  domain="[('model_id', '=',model_name),('ttype', 'in', ['datetime','date'])]",
                                  required=True)
    search_by = fields.Selection([('today', 'Today'),
                                  ('set_period', 'Set Period'),
                                  ('set_date', 'Set Date'), ],
                                 required=True, string="Search By")
    days_before = fields.Integer(string='Reminder before', help="NUmber of days before the reminder")
    active = fields.Boolean(string="Active", default=True)
    # exclude_year = fields.Boolean(string="Consider day alone")
    reminder_active = fields.Boolean(string="Reminder Active", help="Reminder active")
    date_set = fields.Date(string='Select Date', help="Select the reminder set date")
    date_from = fields.Date(string="Start Date", help="Start date")
    date_to = fields.Date(string="End Date", help="End date")
    expiry_date = fields.Date(string="Reminder Expiry Date", help="Expiry date")
    company_id = fields.Many2one('res.company', string='Company', required=True, help="Company",
                                 default=lambda self: self.env.user.company_id)
    def send_reminder(self,reminder,reminder_list):
        for emp_id in reminder_list:
            one_signal_values = {'employee_id': emp_id,
                                 'contents': _('Reminder: %s .') % reminder.name,
                                 'headings': _('WB B2B : Reminder %s .') % reminder.name,
                                 'message_type': 'announcement',#'reminder',
                                 }

            message_id = self.env['one.signal.notification.message'].create(one_signal_values)
            print(message_id)
    def reminder_scheduler(self):
        now = fields.Datetime.from_string(fields.Datetime.now())
        today = fields.Date.today()
        obj = self.env['hr.reminder'].sudo().search([])
        for i in obj:
            if i.search_by != "today":
                if i.expiry_date and datetime.strptime(str(today), "%Y-%m-%d") == datetime.strptime(str(i.expiry_date), "%Y-%m-%d"):
                    i.active = False
                else:
                        if i.search_by == "set_date":
                            d1 = datetime.strptime(str(i.date_set), "%Y-%m-%d")
                            d2 = datetime.strptime(str(today), "%Y-%m-%d")
                            daydiff = abs((d2 - d1).days)
                            if daydiff <= i.days_before:
                                i.reminder_active = True
                            else:
                                i.reminder_active = False
                        elif i.search_by == "set_period":
                            d1 = datetime.strptime(str(i.date_from), "%Y-%m-%d")
                            d2 = datetime.strptime(str(today), "%Y-%m-%d")
                            daydiff = abs((d2 - d1).days)
                            if daydiff <= i.days_before:
                                i.reminder_active = True
                            else:
                                i.reminder_active = False
            else:
                reminder_list = []
                today = fields.Date.today() + timedelta(days=i.days_before)
                if i.model_name.model == 'hr.employee':

                    for emp in self.env['hr.employee'].sudo().search([(i.model_field.name,'<=',today)]):
                        reminder_list.append(emp.id)
                        if emp.approve_manager:
                            reminder_list.append(emp.approve_manager.id)
                    if len(reminder_list) > 0:
                        self.send_reminder(i,reminder_list)
                        #i.reminder_active = False
                elif i.model_name.model == 'hr.contract' and i.model_field.name == 'trial_date_end':
                    for contract in self.env['hr.contract'].sudo().search([(i.model_field.name, '<=', today),('state','=','open'),('employee_id.state','=','probation')]):
                        reminder_list.append(contract.employee_id.id)
                        if contract.employee_id.approve_manager:
                            reminder_list.append(contract.employee_id.approve_manager.id)
                    if len(reminder_list) > 0:
                        self.send_reminder(i, reminder_list)
                elif i.model_name.model == 'fleet.vehicle':
                    for emp in self.env['fleet.vehicle'].sudo().search([(i.model_field.name, '<=', today)]):
                        if emp.hr_driver_id:
                            reminder_list.append(emp.hr_driver_id.id)
                        if emp.incharge_id:
                            reminder_list.append(emp.incharge_id.id)
                        if len(reminder_list) > 0:
                            self.send_reminder(i, reminder_list)
                        #i.reminder_active = False
                i.reminder_active = True
