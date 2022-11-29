import io
import base64
import xlsxwriter
from odoo import models, fields, api, _
from calendar import monthrange
from datetime import datetime, date
from pytz import timezone, UTC


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


class ReportBankAndPayroll(models.TransientModel):
    _name = 'report.bank.and.payroll'
    _description = 'Bank and Payroll Report'

    def _get_selection(self):
        current_year = datetime.now().year
        return [(str(i), i) for i in range(current_year - 1, current_year + 10)]

    year = fields.Selection(selection='_get_selection', string='Year', required=True, default=lambda x: str(datetime.now().year))
    month = fields.Selection(selection=MONTH_SELECTION, string='Month', required=True, default=lambda x: str(datetime.now().month))
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    excel_file = fields.Binary('Excel File')

    def get_style(self, workbook):
        header_style = workbook.add_format({'font_name': 'Arial', 'font_size': 13, 'align': 'center', 'bold': True})
        header_style.set_align('vcenter')
        filter_style = workbook.add_format({'font_name': 'Arial', 'font_size': 11, 'align': 'vcenter'})
        title_style = workbook.add_format({'font_name': 'Arial', 'font_size': 11, 'align': 'vcenter', 'bold': True, 'border': 1})
        default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 11, 'align': 'vcenter', 'border': 1})
        number_style = workbook.add_format({'font_name': 'Arial', 'font_size': 11, 'num_format': '#,##0', 'align': 'vcenter', 'border': 1})
        float_style = workbook.add_format({'font_name': 'Arial', 'font_size': 11, 'num_format': '#,##0.00', 'align': 'vcenter', 'border': 1})
        return header_style, filter_style, title_style, default_style, number_style, float_style

    def _get_net_salary(self, payslip_lines):
        line = payslip_lines.filtered(lambda l: l.code == 'NET')
        if line:
            return line.total
        else:
            return 0

    def _write_excel_data(self, workbook, sheet):
        header_style, filter_style, title_style, default_style, number_style, float_style = self.get_style(workbook)
        lctz = timezone(self.env.context.get('tz') or 'Asia/Yangon')
        current_date = UTC.localize((fields.Datetime.now()).replace(tzinfo=None), is_dst=True).astimezone(tz=lctz)
        sheet.write(0, 3, self.company_id.name, header_style)
        sheet.write(1, 0, 'Payroll Period: ' + dict(self._fields['month'].selection).get(self.month) + ' - ' + self.year, filter_style)
        sheet.write(1, 5, 'Report Date: ' + current_date.strftime(_("%d/%m/%Y")), filter_style)
        titles = ['Sr. No', 'Employee Code', 'Employee Name', 'Display Name', 'Bank Branch', 'Bank Account Number', 'Net Amount']
        tcol_no = 0
        for title in titles:
            sheet.write(2, tcol_no, title, title_style)
            tcol_no += 1
        sheet.set_row(2, 30)

        col_width = [5, 15, 15, 25, 15, 20, 15]
        for col, width in enumerate(col_width):
            sheet.set_column(col, col, width)

        domain = [('month', '=', self.month), ('year', '=', self.year), ('company_id', '=', self.company_id.id), ('state', '!=', 'draft')]
        payslips = self.env['hr.payslip'].sudo().search(domain)

        y_offset = 3
        total_amount = 0
        for sr_no, payslip in enumerate(payslips):
            employee = payslip.employee_id
            payslip_lines = payslip.line_ids
            bank_account = employee.bank_account_id
            sheet.write(y_offset, 0, sr_no + 1, number_style)
            sheet.write(y_offset, 1, employee.barcode, default_style)
            sheet.write(y_offset, 2, employee.name, default_style)
            sheet.write(y_offset, 3, employee.name_get()[0][1], default_style)
            sheet.write(y_offset, 4, bank_account and bank_account.bank_id and bank_account.bank_id.name or '-', default_style)
            sheet.write(y_offset, 5, bank_account and bank_account.acc_number or '-', default_style)
            sheet.write(y_offset, 6, self._get_net_salary(payslip_lines), float_style)
            total_amount += self._get_net_salary(payslip_lines)
            y_offset += 1
        
        sheet.merge_range(y_offset, 0, y_offset, 5, 'Total ', default_style)   
        sheet.set_column(0, 5, 20)
        sheet.write(y_offset,6, total_amount, float_style)
        sheet.set_column(6, 6, 20)           
        y_offset += 1

    def print_xlsx(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        month_name = dict(self._fields['month'].selection).get(self.month) + ' - ' + self.year
        report_name = 'Bank and Payroll Report for ' + month_name + '.xlsx'
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
                'url': 'web/content/?model=report.bank.and.payroll&download=true&field=excel_file&id=%s&filename=%s' % (
                    active_id, report_name),
                'target': 'new',
            }

