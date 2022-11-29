# -*- coding: utf-8 -*-
from odoo import http, fields
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
import json
from odoo.exceptions import AccessError

from odoo.addons.hr_org_chart.controllers.hr_org_chart import HrOrgChartController

class HrOrgChartController(HrOrgChartController):
        
    def _check_employee(self, employee_id, **kw):
        if not employee_id:  # to check
            return None
        employee_id = int(employee_id)

        if 'allowed_company_ids' in request.env.context:
            cids = request.env.context['allowed_company_ids']
        else:
            cids = [request.env.company.id]

        Employee = request.env['hr.employee.public'].sudo().with_context(allowed_company_ids=cids)
        # check and raise
        if not Employee.check_access_rights('read', raise_exception=False):
            return None
        try:
            Employee.browse(employee_id).check_access_rule('read')
        except AccessError:
            return None
        else:
            return Employee.browse(employee_id)
    
    def _prepare_employee_data(self, employee, company_name=None, branch_name=None):
        values = super(HrOrgChartController, self)._prepare_employee_data(employee)
        employee = request.env['hr.employee'].sudo().browse(values.get('id'))
        res_id = request.env['hr.employee'].sudo().browse(values.get('link').split("res_id=")[1])
        if employee.id != res_id.id and employee.active == False:
            values.update({
                'name' : '',
                })
        values.update({
                'company_name' : company_name if company_name else '',
                'branch_name' : branch_name,
                })
        return values

    def _prepare_department_data(self, department):
        if department.sudo().job_id and department.sudo().branch_id and department.sudo().company_id:            
            employee = request.env['hr.employee'].sudo().search([('job_id', '=', department.sudo().job_id.id),
                                                                 ('department_id','=',department.sudo().id),
                                                                 ('branch_id', '=', department.sudo().branch_id.id),
                                                                 ('company_id', '=', department.sudo().company_id.id)], limit=1)
        else:
            employee = ''#False
            
        if not department.sudo().job_id:
            managername = ''
            
        else:
            managername = 'Vacant'        
        
        return dict(
            id=department.id,
            department_name=department.name,
            job_id= employee.sudo().job_id.id  if employee and employee.sudo().job_id and employee.active == True else 0,
            job_name=employee.sudo().job_id.name  if employee and employee.sudo().job_id and employee.active == True else '',#department.sudo().job_id.name,
            job_title=employee.sudo().job_id.name  if employee and employee.sudo().job_id and employee.active == True else '',#department.sudo().job_id.name,
            link='/mail/view?model=%s&res_id=%s' % ('hr.department', department.id,),
            manager_name=employee.sudo().name if employee and employee.sudo().active == True else managername,
        )

    @http.route('/hr/get_org_chart_bk', type='json', auth='user')
    def get_org_chart_bk(self, employee_id, **kw):
        employee = self._check_employee(employee_id, **kw)
        employee_list = []
        manager_list = []
        if not employee:  # to check
            return {
                'managers': [],
                'children': [],
            }
#         dotted_line = request.env.ref('hr_org_chart_extended.dotted_line_manager')
#         approve_line = request.env.ref('hr_org_chart_extended.approve_manager')
#         dotted_line_id = request.env['hr.employee.public'].sudo().browse(dotted_line.id)
#         approve_line_id = request.env['hr.employee.public'].sudo().browse(approve_line.id)
        
        ancestors, current = request.env['hr.employee.public'].sudo(), employee.sudo()
        ancestors_department = request.env['hr.department'].sudo()

        if employee.department_id:
            current_department = employee.department_id
            ancestors_department |= current_department
            while current_department.parent_id:
                ancestors_department += current_department.parent_id
                current_department = current_department.parent_id
        
        for department in ancestors_department:
            emp_id =request.env['hr.employee'].sudo().search([('job_id', '=', department.sudo().job_id.id),
                                                              ('department_id','=',department.sudo().id),
                                                                 ('branch_id', '=', department.sudo().branch_id.id),
                                                                 ('company_id', '=', department.sudo().company_id.id)], limit=1)
            if emp_id:
                employee_list.append(emp_id.id)
        
        if employee.department_id.branch_id.manager_id:
            employee_list.append(employee.department_id.branch_id.manager_id.id)
        
        if employee.department_id.manager_id:
            employee_list.append(employee.department_id.manager_id.id)
                
        if len(employee_list) > 0:
            top_emp = request.env['hr.employee.public'].sudo().browse(employee_list)
        company = employee.company_id
        company_employee = self._check_employee(company.managing_director_id, **kw)
#         ancestors  += employee.dotted_line_manager_id if employee.dotted_line_manager_id else dotted_line_id
#         ancestors  += employee.approve_manager if employee.approve_manager else approve_line_id
#         ancestors  += employee.dotted_line_manager_id
#         ancestors  += employee.approve_manager

#         while current.parent_id and len(ancestors) < self._managers_level+2:
#             ancestors += current.parent_id
            
        if current.parent_id and current.parent_id.id not in employee_list:
            current = current.parent_id
            ancestors += current.parent_id
            print("ancestors>>>",current.parent_id)
#         else:
#             ancestors += current    
        child_ids = [] 
        
        for child in request.env['hr.employee'].sudo().search([('parent_id','=',employee.id)]):
            if (child.id != child.parent_id.id)or (child.department_id.manager_id.id != child.id) or (child.id != child.parent_id.id and child.branch_id.manager_id.id != child.id):
                #child_ids.append(child)
                emp = request.env['hr.employee.public'].sudo().search([('id','=',child.id)])
                if child.parent_id and child.parent_id.id not in employee_list:
                    manager_list.append(child)
                #ancestors += emp.id
                print("child_ids>>>",child_ids)
#         if current not in employee_list:
#             employee_list.append(current.id)
        
        if not ancestors:
            ancestors = manager_list
        values = dict(
            self=self._prepare_employee_data(employee),
            company=self._prepare_employee_data(company_employee, company_employee.company_id.name),
            managers=[
                self._prepare_employee_data(ancestor)
                for idx, ancestor in enumerate(ancestors)
                if idx < 1
            ],
            managers_more=len(ancestors) > self._managers_level,
            children=[],#[self._prepare_employee_data(child) for child in child_ids],
        )
        if not ancestors:
            values.update(managers=[])
#         if not employee.child_ids:
#             values['children'] = [{}]
        if ancestors_department:
            values.update(
                departments=[self._prepare_department_data(ancestor) for ancestor in ancestors_department],
                )
        branch = employee.department_id.sudo().branch_id
        if branch and branch.manager_id:
            branch_employee = self._check_employee(branch.manager_id, **kw)
            values.update(
                branch=self._prepare_employee_data(branch_employee, branch.name),
                )
        group_company = request.env['res.company'].sudo().search([('id', '=', 1)])
        if group_company and group_company.managing_director_id:
            group_company_employee = self._check_employee(group_company.managing_director_id, **kw)
            values.update(
                group_company=self._prepare_employee_data(group_company_employee,company_name=group_company.name),
                )
        if values.get('departments'):
            values['departments'].reverse()
        print(values)
        return values
    