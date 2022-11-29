# -*- coding: utf-8 -*-
###################################################################################
#    A part of OpenHRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2018-TODAY Cybrosys Technologies (<https://www.cybrosys.com>).
#    Author: Yadhu K (<https://www.cybrosys.com>)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###################################################################################

from odoo import models, fields, api


class OrganizationalChart(models.Model):
    _name = 'hr.organizational.chart'
    _description = "HR Organizational Chart"

    @api.model
    def get_employee_data(self, emp_id):
        parent_emp = self.env['hr.org.chart.data'].search([('record_id', '=', str(emp_id))])
        data = {
            'name': parent_emp.name,
            'title': parent_emp.job_title,
            'emp_name': parent_emp.employee_name,
            'children': [],
            'office': parent_emp.data_type,
        }
        employees = self.env['hr.org.chart.data'].search([('parent_id', '=', parent_emp.record_id)])
        for employee in employees:
            data['children'].append(self.get_children(employee, 'middle-level'))

        return {'values': data}

    @api.model
    def get_children(self, emp, style=False):
        data = []
        emp_data = {'name': emp.name, 'title': emp.job_title, 'office': emp.data_type,'emp_name': emp.employee_name,}
        childrens = self.env['hr.org.chart.data'].search([('parent_id', '=', emp.record_id),('data_type','=', emp.data_type)])
        for child in childrens:
            sub_child = self.env['hr.org.chart.data'].search([('parent_id', '=', child.record_id)])
            next_style = self._get_style(emp,style)
            if not sub_child:
                data.append({'name': child.name, 'title': child.job_title, 'emp_name': child.employee_name, 'office': child.data_type,'className': next_style,
                             })
            else:
                data.append(self.get_children(child, next_style))

        if childrens:
            emp_data['children'] = data
        if style:
            emp_data['className'] = style

        return emp_data

    def _get_style(self, emp,last_style):
        if emp.data_type == 'employee' or emp.data_type=='manager':
            return 'product-dept'
        if last_style == 'product-dept':
            return 'rd-dept'
        if last_style == 'rd-dept':
            return 'pipeline1'
        if last_style == 'pipeline1':
            return 'frontend1'

        return 'middle-level'

    def _get_image(self, emp):
        image_path = """<img src='/web/image/hr.employee.public/""" + str(emp.record_id) + """/image_1024/' id='""" + str(
            emp.record_id) + """'/>"""
        return image_path


