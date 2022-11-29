import io
import base64
import xlsxwriter
from odoo import models, fields, api, _
from calendar import monthrange
from datetime import datetime, date


MONTH_SELECTION = [
    ('1', 'January'),
    ('2', 'February'),
    ('3', 'March'),
    ('4', 'April'),
    ('5', 'May'),
    ('6', 'June'),
    ('7', 'July'),
    ('8', 'August'),
    ('9', 'September'),
    ('10', 'October'),
    ('11', 'November'),
    ('12', 'December'),
]


class ReportPayrollWizard(models.TransientModel):
    _name = 'report.payroll.wizard'
    _description = 'Payroll Report'

    def _get_selection(self):
        current_year = datetime.now().year
        return [(str(i), i) for i in range(current_year - 1, current_year + 10)]

    year = fields.Selection(selection='_get_selection', string='Year', required=True,
                            default=lambda x: str(datetime.now().year))
    month = fields.Selection(selection=MONTH_SELECTION, string='Month', required=True)
    date_from = fields.Date('From Date', required=True)
    date_to = fields.Date('To Date', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    payslip_run_id = fields.Many2one('hr.payslip.run', string='Batch')
    job_id = fields.Many2one('hr.job', string='Position')
    department_id = fields.Many2one('hr.department', string='Department')
    branch_id = fields.Many2one('res.branch', string='Branch')
    excel_file = fields.Binary('Excel File')

    @api.onchange('month', 'year')
    def onchange_month_and_year(self):
        if self.year and self.month:
            self.date_from = date(year=int(self.year), month=int(self.month), day=1)
            self.date_to = date(year=int(self.year), month=int(self.month), day=monthrange(int(self.year), int(self.month))[1])

    def get_style(self, workbook):
        header_style = workbook.add_format({'font_name': 'Arial', 'font_size': 11, 'align': 'center', 'bold': True, 'text_wrap': True, 'border': 1})
        header_style.set_align('vcenter')
        workedday_header_style = workbook.add_format({'font_name': 'Arial', 'font_size': 11, 'align': 'center', 'bold': True, 'text_wrap': True, 'border': 1, 'bg_color': '#ebe188'})
        workedday_header_style.set_align('vcenter')
        rule_header_style = workbook.add_format({'font_name': 'Arial', 'font_size': 11, 'align': 'center', 'bold': True, 'text_wrap': True, 'border': 1, 'bg_color': '#e3c1d5'})
        rule_header_style.set_align('vcenter')
        default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 11, 'align': 'vcenter', 'border': 1})
        number_style = workbook.add_format({'font_name': 'Arial', 'font_size': 11, 'num_format': '#,##0', 'align': 'vcenter', 'border': 1})
        float_style = workbook.add_format({'font_name': 'Arial', 'font_size': 11, 'num_format': '#,##0.00', 'align': 'vcenter', 'border': 1})
        return header_style, workedday_header_style, rule_header_style, default_style, number_style, float_style

    def worked_day_by_code(self, worked_days, code, day=False):
        type = worked_days.filtered(lambda w: w.work_entry_type_id.code == code)
        if type:
            if day:
                return type.number_of_days
            else:
                type.number_of_hours
        else:
            return 0

    def salary_by_code(self, payslip_lines, code):
        line = payslip_lines.filtered(lambda l: l.code == code)
        if line:
            return line.total
        else:
            return 0

    def _write_excel_data(self, workbook, sheet):
        header_style, workedday_header_style, rule_header_style, default_style, number_style, float_style = self.get_style(workbook)

        titles = ['Sr. No',  'Employee',  'Position',  'Department',  'Branch',  'Company',  'Workdays',  'OT Hours',  'Unpaid leaves days',
                  'Basic', 'Increment', 'Meal OT', 'OT', 'OT Duty','OT GZ',
                  'Transportation Allowance', 'Relocation Allowance', 'Fixed Allowance', 'Meal Allowance', 'Phone Allowance', 'Commission', 'Other Allowance',
                  'Meal Deduction', 'Phone Allowance Deduction', 'Leave Deduction', 'Other Deduction', 'Late Deduction',
                  'Insurance', 'Absence', 'Loan Entitlement', 'Training Loan', 'SSB', 'Gross', 'Income Tax', 'Net Salary']

        tcol_no = 0
        y_offset = 0        
        
        company_name = str(self.company_id.name) + ' - '   
        company_name += 'All Department' if not self.department_id else str(self.department_id.name)   
        company_name += ' - ' +  'All Branch' if not self.branch_id else ' - ' + str(self.branch_id.name)
        month_count = int(self.month) -1
        title_name = "Payroll Report (" +  str(MONTH_SELECTION[month_count][1]) + ' - ' + str(self.year) + ')'
        #company_name = str(self.company_id.name) or 'All Company'  + ' - ' + str(self.department_id.name) or 'All Department' - str(self.branch_id.name) or 'ALL Branch'
        batch_name = 'All Batch' if not self.payslip_run_id else str(self.payslip_run_id.name) 
        batch_name += ' - ' +  'All Position' if not self.job_id else ' - ' + str(self.job_id.name)
        
        #batch_name = str(self.payslip_run_id.name) or 'All Batch' + ' - ' + str(self.job_id.name) or ' All Position'
        sheet.merge_range(y_offset, 3, y_offset, 6, _(title_name), header_style)
        y_offset += 1
        sheet.merge_range(y_offset, 3, y_offset, 6, _(company_name), header_style)
        y_offset += 1
        sheet.merge_range(y_offset, 3, y_offset, 6, _(batch_name), header_style)
        y_offset += 1
        
        for i, title in enumerate(titles):
            if 5 < i < 9:
                sheet.write(y_offset, tcol_no, title, workedday_header_style)
            elif i > 8:
                sheet.write(y_offset, tcol_no, title, rule_header_style)
            else:
                sheet.write(y_offset, tcol_no, title, header_style)
            tcol_no += 1
        sheet.set_row(y_offset, 25)
        y_offset += 1
        col_width = [5, 25, 15, 15, 15, 25, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15]
        for col, width in enumerate(col_width):
            sheet.set_column(col, col, width)
            
        domain = [('date_from', '>=', self.date_from), ('date_to', '<=', self.date_to), ('state', '!=', 'draft')]
        if self.payslip_run_id:
            domain += [('payslip_run_id', '=', self.payslip_run_id.id)]
        if self.job_id:
            domain += [('employee_id.job_id', '=', self.job_id.id)]
        if self.department_id:
            domain += [('employee_id.department_id', '=', self.department_id.id)]
        if self.branch_id:
            domain += [('employee_id.branch_id', '=', self.branch_id.id)]
        if self.company_id:
            domain += [('employee_id.company_id', '=', self.company_id.id)]
        payslips = self.env['hr.payslip'].sudo().search(domain)

        
        
       
        total_basic = total_inc = total_otaw = total_ot = total_otdt = total_otgz = total_ao1 = total_a02 = 0
        total_a03 = total_a04 = total_a05 = total_a06 = total_a00 = total_d01 = total_d02 = total_d03 = 0
        total_d00 = total_late = total_ins = total_abs = total_eloan = total_tloan = total_ssb = total_gross = total_ict = total_net =0
        for sr_no, payslip in enumerate(payslips):
            employee = payslip.employee_id
            worked_days = payslip.worked_days_line_ids
            payslip_lines = payslip.line_ids
            sheet.write(y_offset, 0, sr_no + 1, number_style)
            sheet.write(y_offset, 1, employee.name_get()[0][1], default_style)
            sheet.write(y_offset, 2, employee.job_id.name, default_style)
            sheet.write(y_offset, 3, employee.department_id.name, default_style)
            sheet.write(y_offset, 4, employee.branch_id and employee.branch_id.name or '', default_style)
            sheet.write(y_offset, 5, employee.company_id.name, default_style)
            sheet.write(y_offset, 6, self.worked_day_by_code(worked_days, 'WORK100', day=True), float_style)
            sheet.write(y_offset, 7, self.worked_day_by_code(worked_days, 'OVERTIME100'), float_style)
            sheet.write(y_offset, 8, self.worked_day_by_code(worked_days, 'LEAVE90', day=True), float_style)
            sheet.write(y_offset, 9, self.salary_by_code(payslip_lines, 'BASIC'), float_style)
            sheet.write(y_offset, 10, self.salary_by_code(payslip_lines, 'INC'), float_style)
            sheet.write(y_offset, 11, self.salary_by_code(payslip_lines, 'OTALW'), float_style)
            sheet.write(y_offset, 12, self.salary_by_code(payslip_lines, 'OT'), float_style)
            sheet.write(y_offset, 13, self.salary_by_code(payslip_lines, 'OTDT'), float_style)
            sheet.write(y_offset, 14, self.salary_by_code(payslip_lines, 'OTGZ'), float_style)            
            sheet.write(y_offset, 15, self.salary_by_code(payslip_lines, 'A01'), float_style)
            sheet.write(y_offset, 16, self.salary_by_code(payslip_lines, 'A02'), float_style)
            sheet.write(y_offset, 17, self.salary_by_code(payslip_lines, 'A03'), float_style)
            sheet.write(y_offset, 18, self.salary_by_code(payslip_lines, 'A04'), float_style)
            sheet.write(y_offset, 19, self.salary_by_code(payslip_lines, 'A05'), float_style)
            sheet.write(y_offset, 20, self.salary_by_code(payslip_lines, 'A06'), float_style)
            sheet.write(y_offset, 21, self.salary_by_code(payslip_lines, 'A00'), float_style)
            sheet.write(y_offset, 22, self.salary_by_code(payslip_lines, 'D01'), float_style)
            sheet.write(y_offset, 23, self.salary_by_code(payslip_lines, 'D02'), float_style)
            sheet.write(y_offset, 24, self.salary_by_code(payslip_lines, 'D03'), float_style)
            sheet.write(y_offset, 25, self.salary_by_code(payslip_lines, 'D00'), float_style)
            sheet.write(y_offset, 26, self.salary_by_code(payslip_lines, 'LATE'), float_style)
            sheet.write(y_offset, 27, self.salary_by_code(payslip_lines, 'INS'), float_style)
            sheet.write(y_offset, 28, self.salary_by_code(payslip_lines, 'ABSENCE'), float_style)
            sheet.write(y_offset, 29, self.salary_by_code(payslip_lines, 'ELOAN'), float_style)
            sheet.write(y_offset, 30, self.salary_by_code(payslip_lines, 'TLOAN'), float_style)
            sheet.write(y_offset, 31, self.salary_by_code(payslip_lines, 'SSB'), float_style)
            sheet.write(y_offset, 32, self.salary_by_code(payslip_lines, 'GROSS'), float_style)
            sheet.write(y_offset, 33, self.salary_by_code(payslip_lines, 'ICT'), float_style)
            sheet.write(y_offset, 34, self.salary_by_code(payslip_lines, 'NET'), float_style)
            total_basic += self.salary_by_code(payslip_lines, 'BASIC')
            total_inc += self.salary_by_code(payslip_lines, 'INC')
            total_otaw += self.salary_by_code(payslip_lines, 'OTALW')
            total_ot += self.salary_by_code(payslip_lines, 'OT')
            total_otdt += self.salary_by_code(payslip_lines, 'OTDT')
            total_otgz += self.salary_by_code(payslip_lines, 'OTGZ')
            total_ao1 += self.salary_by_code(payslip_lines, 'A01')
            total_a02 += self.salary_by_code(payslip_lines, 'A02')
            total_a03 += self.salary_by_code(payslip_lines, 'A03')
            total_a04 += self.salary_by_code(payslip_lines, 'A04')
            total_a05 += self.salary_by_code(payslip_lines, 'A05')
            total_a06 += self.salary_by_code(payslip_lines, 'A06')
            total_a00 += self.salary_by_code(payslip_lines, 'A00')
            total_d01 += self.salary_by_code(payslip_lines, 'D01')
            total_d02 += self.salary_by_code(payslip_lines, 'D02')
            total_d03 += self.salary_by_code(payslip_lines, 'D03')
            total_d00 += self.salary_by_code(payslip_lines, 'D00')
            total_late += self.salary_by_code(payslip_lines, 'LATE')
            total_ins += self.salary_by_code(payslip_lines, 'INS')
            total_abs += self.salary_by_code(payslip_lines, 'ABSENCE')
            total_eloan += self.salary_by_code(payslip_lines, 'ELOAN')
            total_tloan += self.salary_by_code(payslip_lines, 'TLOAN')
            total_ssb += self.salary_by_code(payslip_lines, 'SSB')
            total_gross += self.salary_by_code(payslip_lines, 'GROSS')
            total_ict += self.salary_by_code(payslip_lines, 'ICT')
            total_net += self.salary_by_code(payslip_lines, 'NET')
            y_offset += 1
        
        sheet.merge_range(y_offset, 0, y_offset,8, 'Total ', default_style)   
        sheet.set_column(0, 8, 34)
        sheet.write(y_offset,9, total_basic, float_style)
        sheet.set_column(9, 9, 34)
        sheet.write(y_offset,10, total_inc, float_style)
        sheet.set_column(10, 10, 34) 
        sheet.write(y_offset,11, total_otaw, float_style)
        sheet.set_column(11, 11, 34) 
        sheet.write(y_offset,12, total_ot, float_style)
        sheet.set_column(12, 12, 34) 
        sheet.write(y_offset,13, total_otdt, float_style)
        sheet.set_column(13, 13, 34)
        sheet.write(y_offset,14, total_otgz, float_style)
        sheet.set_column(14, 14, 34) 
        sheet.write(y_offset,15, total_ao1, float_style)
        sheet.set_column(15, 15, 34) 
        sheet.write(y_offset,16, total_a02, float_style)
        sheet.set_column(16, 16, 34)   
        sheet.write(y_offset,17, total_a03, float_style)
        sheet.set_column(17, 17, 34)
        sheet.write(y_offset,18, total_a04, float_style)
        sheet.set_column(18, 18, 34) 
        sheet.write(y_offset,19, total_a05, float_style)
        sheet.set_column(19, 19, 34)  
        sheet.write(y_offset,20, total_a06, float_style)
        sheet.set_column(20, 20, 34)  
        sheet.write(y_offset,21, total_a00, float_style)
        sheet.set_column(21, 21, 34)
        sheet.write(y_offset,22, total_d01, float_style)
        sheet.set_column(22, 22, 34) 
        sheet.write(y_offset,23, total_d02, float_style)
        sheet.set_column(23, 23, 34)
        sheet.write(y_offset,24, total_d03, float_style)
        sheet.set_column(24, 24, 34) 
        sheet.write(y_offset,25, total_d00, float_style)
        sheet.set_column(25, 25, 34) 
        sheet.write(y_offset,26, total_late, float_style)
        sheet.set_column(26, 26, 34) 
        sheet.write(y_offset,27, total_ins, float_style)
        sheet.set_column(27, 27, 34)
        sheet.write(y_offset,28, total_abs, float_style)
        sheet.set_column(28, 28, 34)
        sheet.write(y_offset,29, total_eloan, float_style)
        sheet.set_column(29, 29, 34) 
        sheet.write(y_offset,30, total_tloan, float_style)
        sheet.set_column(30, 30, 34)
        sheet.write(y_offset,31, total_ssb, float_style)
        sheet.set_column(31, 31, 34) 
        sheet.write(y_offset,32, total_gross, float_style)
        sheet.set_column(32, 32, 34) 
        sheet.write(y_offset,33, total_ict, float_style)
        sheet.set_column(33, 33, 34) 
        sheet.write(y_offset,34, total_net, float_style)
        sheet.set_column(34, 34, 34)   
         
        y_offset += 1
    def print_xlsx(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        month_name = dict(self._fields['month'].selection).get(self.month) + ' - ' + self.year
        report_name = 'Payroll Report for ' + month_name + '.xlsx'
        sheet = workbook.add_worksheet(month_name)
        self._write_excel_data(workbook, sheet)

        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()
        excel_file = base64.encodestring(generated_file)
        self.write({'excel_file': excel_file})

        if self.excel_file:
            active_id = self.ids[0]
            return {
                'type': 'ir.actions.act_url',
                'url': 'web/content/?model=report.payroll.wizard&download=true&field=excel_file&id=%s&filename=%s' % (
                    active_id, report_name),
                'target': 'new',
            }
