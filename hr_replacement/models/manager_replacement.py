# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date
from pytz import timezone, UTC


class ManagerReplacement(models.Model):
    _name = 'manager.replacement'
    _description = 'Manager Replacement'

    def _domain_manager_id(self):
        manager_ids = []
        self._cr.execute('''SELECT DISTINCT manager_id
                            FROM
                                (SELECT DISTINCT parent_id as manager_id FROM hr_employee WHERE parent_id IS NOT NULL
                                UNION ALL
                                SELECT DISTINCT approve_manager as manager_id FROM hr_employee WHERE approve_manager IS NOT NULL
                                UNION ALL
                                SELECT DISTINCT dotted_line_manager_id as manager_id FROM hr_employee WHERE dotted_line_manager_id IS NOT NULL
                            ) manager''')
        result = self._cr.fetchall()
        for res in result:
            manager_ids.append(res[0])
        return [('id', 'in', manager_ids)]

    name = fields.Char('Name', default='New', required=True)
    date = fields.Date('Effective Date', default=fields.Date.today, required=True)
    employee_id = fields.Many2one('hr.employee', string='Manager', required=True, domain=_domain_manager_id)
    replaced_employee_id = fields.Many2one('hr.employee', string='Replaced Manager', required=True)
    state = fields.Selection([('draft', 'Draft'),
                              ('submit', 'Submitted'),
                              ('approve', 'Approved')], default='draft', copy=False, required=True)
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

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('manager.replacement') or _('New')
        return super(ManagerReplacement, self).create(vals)

    def action_submit(self):
        self.state = 'submit'

    def action_approve(self):
        source = self._context.get('source', False) or False
        local = self._context.get('tz', 'Asia/Yangon')
        local_tz = timezone(local)
        current_date = UTC.localize(fields.Datetime.now(), is_dst=True).astimezone(tz=local_tz)
        if self.date > current_date.date() and source and source == 'schedule':
            return
        manager = self.env['hr.employee'].search([('parent_id', '=', self.employee_id.id)])
        for m in manager:
            m.parent_id = self.replaced_employee_id.id

        approve_manager = self.env['hr.employee'].search([('approve_manager', '=', self.employee_id.id)])
        for a in approve_manager:
            a.approve_manager = self.replaced_employee_id.id

        dotted_line_manager = self.env['hr.employee'].search([('dotted_line_manager_id', '=', self.employee_id.id)])
        for d in dotted_line_manager:
            d.dotted_line_manager_id = self.replaced_employee_id.id
        self.state = 'approve'

    def action_draft(self):
        self.state = 'draft'
