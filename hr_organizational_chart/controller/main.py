# -*- coding: utf-8 -*-
###################################################################################
#    A part of OpenHRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2018-TODAY Cybrosys Technologies (<https://www.cybrosys.com>).
#    Author: Cybrosys Technologies (<https://www.cybrosys.com>)
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

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request


class EmployeeChart(http.Controller):

    @http.route('/get/parent/colspan', type='json', auth='public', method=['POST'], csrf=False)
    def get_col_span(self, emp_id):
        if emp_id:
            employee = request.env['hr.org.chart.data'].sudo().browse(int(emp_id))
            child_ids = request.env['hr.org.chart.data'].sudo().search([('parent_id', '=', employee.record_id),('parent_type','=', employee.data_type)])
            if child_ids:
                child_count = len(child_ids) * 2
                return child_count

    @http.route('/get/parent/employee', type='json', auth='public', method=['POST'], csrf=False)
    def get_employee_ids(self):
        employees = request.env['hr.org.chart.data'].sudo().search([('id', '=', 1)])
        names = []
        key = []
        if len(employees) == 1:
            key.append(employees.record_id)
            child_ids = request.env['hr.org.chart.data'].sudo().search([('parent_id', '=', employees.record_id),('parent_type', '=', employees.data_type)])
            key.append(len(child_ids))
            return key
        elif len(employees) == 0:
            raise UserError(
                "Should not have manager for the employee in the top of the chart")
        else:
            for emp in employees:
                names.append(emp.name)
            raise UserError(
                "These employee have no Manager %s" % (names))

    def get_lines(self, loop_count):
        if loop_count:
            lines = """<tr class='lines'><td colspan='""" + str(loop_count) + """'>
                <div class='downLine'></div></td></tr><tr class='lines'>"""
            for i in range(0, loop_count):
                if i % 2 == 0:
                    if i == 0:
                        lines += """<td class="rightLine"></td>"""
                    else:
                        lines += """<td class="rightLine topLine"></td>"""
                else:
                    if i == loop_count-1:
                        lines += """<td class="leftLine"></td>"""
                    else:
                        lines += """<td class="leftLine topLine"></td>"""
            lines += """</tr>"""
            return lines

    def get_nodes(self, child_ids):
        if child_ids:
            child_nodes = """<tr>"""
            for child in child_ids:
                
                child_table = """<td colspan='""" + str(2) + """'>
                    <table><tr><td><div>"""
                
                job_info =""
                if child.job_title and child.employee_name:
                    job_info = str(child.job_title).upper() + """</p><p>""" + str(child.employee_name).upper()
                if child.employee_name and not child.job_title:
                    job_info = """<p style="color:#8B0000;">""" + """**VACCANT**""" + """</p><p>""" + str(child.employee_name).upper()
                if child.job_title and not child.employee_name:
                    job_info = str(child.job_title).upper() + """</p><p style="color:red;">""" + """VACANT"""
                if not child.job_title and len(child.employee_name) > 0:#not child.employee_name:
                    job_info = """<p style="color:#8B0000;">""" + """**VACCANT**""" + """</p><p style="color:red;">""" + """VACANT"""
                view = """ <div id='""" + str(child.id) + """' class='o_level_1'><a>
                                           <div id='""" + str(child.id) + """' class="o_employee_border">
                                           <img src='/web/image/hr.employee.public/""" + str(child.record_id) + """/image_1024/'/></div>
                                            <div class='employee_name'><p>""" + str(child.name) + """</p>
                                            <div class='employee_name'><p style="color:green;">""" + str(child.data_type).upper() + """</p>
                                            <p>""" + job_info + """</p></div></a></div>"""
                child_nodes += child_table + view + """</div></td></tr></table></td>"""
            nodes = child_nodes + """</tr>"""
            return nodes

    @http.route('/get/parent/child', type='http', auth='user', method=['POST'], csrf=False)
    def get_parent_child(self, **post):
        if post:
            val = 0
            for line in post:
                if line:
                    val = int(line)
            emp = request.env['hr.org.chart.data'].sudo().browse(val)
            child_ids = request.env['hr.org.chart.data'].sudo().search([('parent_id', '=', emp.record_id),('parent_type', '=', emp.data_type)])
            job_info =""
            table = """<table><tr><td colspan='""" + str(len(child_ids) * 2) + """'><div class="node">"""
            
            if emp.job_title and emp.employee_name:
                job_info = str(emp.job_title).upper() + """</p><p>""" + str(emp.employee_name).upper()
            if emp.employee_name and not emp.job_title:
                job_info = """<p style="color:#8B0000;">""" + """**VACCANT**""" + """</p><p>""" + str(emp.employee_name).upper()
            if emp.job_title and not emp.employee_name:
                job_info = str(emp.job_title).upper() + """</p><p style="color:red;">""" + """VACANT"""
            if not emp.job_title and not emp.employee_name:
                job_info = """<p style="color:#8B0000;">""" + """**VACCANT**""" + """</p><p style="color:red;">""" + """VACANT"""
            
            view = """ <div id="parent" class='o_chart_head'><a>
                <div id='""" + str(emp.record_id) + """' class="o_employee_border">
                <div class='employee_name o_width'><p>""" + str(emp.name) + """</p>
                 <p>""" + job_info + """</p></div></a></div>"""
            # view = """ <div id="parent" class='o_chart_head'><a>
            #     <div id='""" + str(emp.record_id) + """' class="o_employee_border">
            #     <div class='employee_name o_width'><p>""" + str(emp.name) + """</p>
            #      <p>""" + str(emp.job_title) if emp.job_title else str("") + """</p>
            #      <p>""" + str(emp.employee_name) if emp.employee_name else str("") + """</p></div></a></div>"""
            table += view + """</div></td></tr>"""
            loop_len = len(child_ids)*2
            lines = self.get_lines(loop_len)
            nodes = self.get_nodes(child_ids)
            table += lines + nodes
            return table

    @http.route('/get/child/data', type='json', auth='user', method=['POST'], csrf=False)
    def get_child_data(self, click_id):
        if click_id:
            emp_data = request.env['hr.org.chart.data'].sudo().browse(int(click_id))
            parent_id = emp_data.record_id
            data_type = emp_data.data_type
            #child_ids = request.env['hr.org.chart.data'].sudo().search([('parent_id', '=', parent_id), ('parent_type', '=', data_type)])
            # child_ids= request.env['hr.org.chart.data'].sudo().search([
            #     ('parent_id', '=', parent_id),
            #     ('parent_type', '=', data_type),
            # ])
            request.env.cr.execute("select * from hr_org_chart_data where parent_id=%s and parent_type=%s",(parent_id,data_type))
            records = request.env.cr.fetchall()
            child_ids = []
            for record in records:
                child_ids.append(request.env['hr.org.chart.data'].sudo().browse(record[0]))
            if child_ids:
                    child_count = len(child_ids) * 2
                    value = [child_count]
                    lines = self.get_lines(child_count)
                    nodes = self.get_nodes(child_ids)
                    child_table = lines + nodes
                    value.append(child_table)
                    return child_table






