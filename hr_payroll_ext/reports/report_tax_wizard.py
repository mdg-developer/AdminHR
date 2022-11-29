import io
import base64
import xlsxwriter
from odoo import models, fields, api, _
from calendar import monthrange
#from datetime import datetime, date
from datetime import date, datetime, time, timedelta
from dateutil.relativedelta import relativedelta

class ReportTaxWizard(models.TransientModel):
    _name = 'report.tax.wizard'
    _description = 'Yearly Tax Report'

    company_id = fields.Many2one('res.company', string='Company', required=True) 
                                 #default=lambda self: self.env.company)
    fiscal_year_id = fields.Many2one('hr.fiscal.year', string='Fiscal Years',domain="[('company_id', '=', company_id)]", required=True)
    branch_id = fields.Many2one('res.branch', string='Branch', domain="[('company_id', '=', company_id)]")
    department_id = fields.Many2one('hr.department', string='Department', domain="[('branch_id', '=', branch_id)]")
    employee_ids = fields.Many2many('hr.employee', string='Employee')    
    date_from = fields.Date('Date From', required=True, default=fields.Date.context_today)
    date_to = fields.Date('Date To', required=True, default=fields.Date.context_today)   
    excel_file = fields.Binary('Excel File')
        
    @api.onchange('branch_id','department_id')
    def onchange_employee_only(self):
        """
        Make warehouse compatible with company
        """
        employee_obj = self.env['hr.employee']
        employee_ids = []
        
        if self.department_id:
            location_ids = employee_obj.search([('department_id', '=', self.department_id.id)])
            employee_ids = [p.id for p in location_ids] 
            return {
                  'domain':
                            {
                             'employee_ids': [('id', 'in', employee_ids)]
                             },
                  'value':
                        {
                        'employee_ids': False
                        }
                }
        elif self.branch_id:
            
            location_ids = employee_obj.search([('branch_id', '=', self.branch_id.id)])
            employee_ids = [p.id for p in location_ids]        
            return {
                      'domain':
                                {
                                 'employee_ids': [('id', 'in', employee_ids)]
                                 },
                      'value':
                            {
                            'employee_ids': False
                            }
                    }
        else:
            if self.company_id:
                location_ids = employee_obj.search([('company_id', '=', self.company_id.id)])
            else:
                location_ids = employee_obj.search([])
                
            employee_ids = [p.id for p in location_ids]        
            return {
                      'domain':
                                {
                                 'employee_ids': [('id', 'in', employee_ids)]
                                 },
                      'value':
                            {
                            'employee_ids': False
                            }
                    }

    @api.onchange('month', 'year')
    def onchange_month_and_year(self):
        if self.year and self.month:
            self.date_from = date(year=int(self.year), month=int(self.month), day=1)
            self.date_to = date(year=int(self.year), month=int(self.month), day=monthrange(int(self.year), int(self.month))[1])

    def get_style(self, workbook):
        header_style = workbook.add_format({'font_name': 'Myanmar3', 'font_size': 11, 'align': 'center', 'bold': True, 'text_wrap': True, 'border': 1})
        header_style.set_align('vcenter')
        workedday_header_style = workbook.add_format({'font_name': 'Myanmar3', 'font_size': 11, 'align': 'center', 'bold': True, 'text_wrap': True, 'border': 1, 'bg_color': '#ebe188'})
        workedday_header_style.set_align('vcenter')
        rule_header_style = workbook.add_format({'font_name': 'Myanmar3', 'font_size': 11, 'align': 'center', 'bold': True, 'text_wrap': True, 'border': 1, 'bg_color': '#e3c1d5'})
        rule_header_style.set_align('vcenter')
        default_style = workbook.add_format({'font_name': 'Myanmar3', 'font_size': 11, 'align': 'vcenter', 'border': 1})
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
    
    def get_income(self,month_name,year,fiscal_year,employee_id):
        
        date_from = date(year=int(year), month=int(month_name), day=1)
        date_to = date(year=int(year), month=int(month_name), day=monthrange(int(year), int(month_name))[1])
        remaining_months = relativedelta(fiscal_year.date_to, date_to).months    
        if employee_id.joining_date and employee_id.joining_date > fiscal_year.date_from:
            total_months = 12 - relativedelta(employee_id.joining_date, fiscal_year.date_from).months
        payslips = self.env['hr.payslip'].search([('employee_id', '=', employee_id.id),
                                                  ('date_from', '>=', date_from),
                                                  ('date_to', '<=', date_to),
                                                  ('state', 'not in', ('draft', 'cancel'))])
        prev_income = remaining_months = total_months = prev_tax_paid = 0
        for pay in payslips:
            slipline_obj = self.env['hr.payslip.line']
            basic = slipline_obj.search([('slip_id', '=', pay.id), ('code', '=', 'BASIC')])
            # deductions = slipline_obj.search([('slip_id', '=', pay.id), ('code', 'in', ('UNPAID', 'SSB'))])
            deductions = slipline_obj.search([('slip_id', '=', pay.id), ('code', '=', 'D03')])
            tax_paid = slipline_obj.search([('slip_id', '=', pay.id), ('code', '=', 'ICT')])
            prev_income += basic and basic.total or 0
            prev_income -= sum([abs(ded.total) for ded in deductions])
            prev_tax_paid += tax_paid and tax_paid.total or 0
                
        return prev_income,remaining_months,total_months,prev_tax_paid
        

    def _write_excel_data(self, workbook, sheet):
        header_style, workedday_header_style, rule_header_style, default_style, number_style, float_style = self.get_style(workbook)

        titles = ['Sr. No',  'WBID',  'လခစားအမည်',  'ရာထူး/အလုပ်အကိုင်',  'GIR နံပါတ်',  'Join Date',  'Workdays',  'OT Hours',  'Unpaid leaves days',
                  'Basic', 'Increment', 'Meal OT', 'OT', 'OT Duty','OT GZ',
                  'Transportation Allowance', 'Relocation Allowance', 'Fixed Allowance', 'Meal Allowance', 'Phone Allowance', 'Commission', 'Other Allowance',
                  'Meal Deduction', 'Phone Allowance Deduction', 'Leave Deduction', 'Other Deduction', 'Late Deduction',
                  'Insurance', 'Absence', 'Loan Entitlement', 'Training Loan', 'SSB', 'Gross', 'Income Tax', 'Net Salary']

        tcol_no = 0
        y_offset = 0        
        
        company_name = "ကုမ္ပဏီအမည် - "  
        company_name += 'All Company' if not self.company_id else str(self.company_id.name)   
        
        month_count = 1#int(self.month) -1
        title_name = "၀င်ငွေခွန်ဥပဒေပုဒ်မ ၁၈ အရ ပေးပို့ရမည့် လစာနှစ်ချုပ်စာရင်း" 
        
        sheet.merge_range(y_offset, 22, y_offset, 6, _(title_name), header_style)
        y_offset += 1
        sheet.merge_range(y_offset, 22, y_offset, 6, _(company_name), header_style)
        sheet.write(y_offset, 28, "0%", header_style)
        sheet.write(y_offset, 29, "5%", header_style)
        sheet.write(y_offset, 30, "10%", header_style)
        sheet.write(y_offset, 31, "15%", header_style)
        sheet.write(y_offset, 32, "20%", header_style)
        sheet.write(y_offset, 33, "25%", header_style)
        y_offset += 1
        
        sheet.write(y_offset, 0, "စဥ္", header_style)
        sheet.write(y_offset, 1, "WBID", header_style)
        sheet.write(y_offset, 2, "လခစားအမည်", header_style)
        sheet.write(y_offset, 3, "ရာထူး/အလုပ်အကိုင်", header_style)
        sheet.write(y_offset, 4, "GIR နံပါတ်", header_style)
        sheet.merge_range(y_offset, 5,y_offset, 7, "Join Date", header_style)
        sheet.write(y_offset, 8, "Job Grade", header_style)
        income_title = ' Income  (Per Month)'        
        sheet.merge_range(y_offset, 9,y_offset, 20, income_title, header_style)
        ic_title="ဝင်ငွေနှစ်အတွင်းရရှိသည့်လစာ"
        sheet.write(y_offset, 21, ic_title, header_style)
        sheet.merge_range(y_offset, 22,y_offset, 26, "သက်သာခွင့်များ", header_style)        
        sheet.write(y_offset, 27, "အခွန်စည်းကြပ်ရန် ဝင်ငွေ", header_style)
        sheet.write(y_offset, 28, "2000000", header_style)
        sheet.write(y_offset, 29, "5000000", header_style)
        sheet.write(y_offset, 30, "10000000", header_style)
        sheet.write(y_offset, 31, "20000000", header_style)
        sheet.write(y_offset, 32, "30000000", header_style)
        sheet.write(y_offset, 33, "30000001", header_style)
        sheet.write(y_offset, 34, "ကျသင့်အခွန် ", header_style)
        sheet.merge_range(y_offset, 35,y_offset, 46, "Tax of Month", header_style)
        sheet.write(y_offset, 47, "ပေးသွင်းပြီးဝင်ငွေခွန် ", header_style)
        sheet.write(y_offset, 48, " ပိုငွေ(+)/ ", header_style)
        y_offset += 1
        
        sheet.write(y_offset, 0, "", header_style)
        sheet.write(y_offset, 1, "", header_style)
        sheet.write(y_offset, 2, "", header_style)
        sheet.write(y_offset, 3, "", header_style)
        sheet.write(y_offset, 4, "", header_style)
        sheet.write(y_offset, 5, "M", header_style)
        sheet.write(y_offset, 6, "D", header_style)
        sheet.write(y_offset, 7, "Y", header_style)        
        sheet.write(y_offset, 8, "", header_style)
        sheet.write(y_offset, 9, "Oct", header_style)
        sheet.write(y_offset, 10, "Nov", header_style) 
        sheet.write(y_offset, 11, "Dec", header_style) 
        sheet.write(y_offset, 12, "Jan", header_style)  
        sheet.write(y_offset, 13, "Feb", header_style)  
        sheet.write(y_offset, 14, "Mar", header_style)  
        sheet.write(y_offset, 15, "Apr", header_style) 
        sheet.write(y_offset, 16, "May", header_style)
        sheet.write(y_offset, 17, "Jun", header_style)  
        sheet.write(y_offset, 18, "Jul", header_style)
        sheet.write(y_offset, 19, "Aug", header_style)  
        sheet.write(y_offset, 20, "Sep", header_style)
        sheet.write(y_offset, 21, "", header_style)
        sheet.write(y_offset, 22, "အခြေခံ", header_style)
        sheet.write(y_offset, 23, "အတူနေမိဘ", header_style)
        sheet.write(y_offset, 24, "အိမ်ထောင်ဘက်", header_style)
        sheet.write(y_offset, 25, "သားသမီး", header_style)
        sheet.write(y_offset, 26, "SSB ကြေး", header_style)              
        sheet.write(y_offset, 27, "", header_style)
        sheet.write(y_offset, 28, "2000000", header_style)
        sheet.write(y_offset, 29, "3000000", header_style)
        sheet.write(y_offset, 30, "5000000", header_style)
        sheet.write(y_offset, 31, "10000000", header_style)
        sheet.write(y_offset, 32, "10000000", header_style)
        sheet.write(y_offset, 33, "", header_style)
        sheet.write(y_offset, 34, " ", header_style)
        sheet.write(y_offset, 35, "Oct", header_style)
        sheet.write(y_offset, 36, "Nov", header_style) 
        sheet.write(y_offset, 37, "Dec", header_style) 
        sheet.write(y_offset, 38, "Jan", header_style)  
        sheet.write(y_offset, 39, "Feb", header_style)  
        sheet.write(y_offset, 40, "Mar", header_style)  
        sheet.write(y_offset, 41, "Apr", header_style) 
        sheet.write(y_offset, 42, "May", header_style)
        sheet.write(y_offset, 43, "Jun", header_style)  
        sheet.write(y_offset, 44, "Jul", header_style)
        sheet.write(y_offset, 45, "Aug", header_style)  
        sheet.write(y_offset, 46, "Sep", header_style)        
        sheet.write(y_offset, 47, " ", header_style)
        sheet.write(y_offset, 48, "လိုငွေ (-)", header_style)
        y_offset += 1
        if len(self.employee_ids) > 0:
            employee_ids = self.employee_ids
        else:
            domain = [('company_id','=',self.company_id.id)]
            if self.branch_id:
                domain +=  [('branch_id','=',self.branch_id.id)]
            if self.department_id:
                domain +=  [('department_id','=',self.department_id.id)]
            employee_ids = self.env['hr.employee'].search(domain)
        sr_no = 0
        for emp in employee_ids:
            sr_no += 1
            sheet.write(y_offset, 0, sr_no, number_style)
            sheet.write(y_offset, 1, emp.fingerprint_id or '', default_style)
            sheet.write(y_offset, 2, emp.name or '', default_style)
            sheet.write(y_offset, 3, emp.job_id.name or '', default_style)
            sheet.write(y_offset, 4,  '', default_style) #GIR NO
            if emp.joining_date:
                print(emp.joining_date)
                print(emp.joining_date.month)
                join_day = str(emp.joining_date.day) if emp.joining_date.day > 9 else '0' + str(emp.joining_date.day)
                join_month = str(emp.joining_date.month) if emp.joining_date.month > 9 else '0' + str(emp.joining_date.month)
                sheet.write(y_offset, 5,  join_month, default_style)
                sheet.write(y_offset, 6,  join_day, default_style)
                sheet.write(y_offset, 7,  str(emp.joining_date.year), default_style)
            else:
                sheet.write(y_offset, 5,  '', default_style)
                sheet.write(y_offset, 6,  '', default_style)
                sheet.write(y_offset, 7,  '', default_style)
            contracts = emp._get_contracts(self.fiscal_year_id.date_from, self.fiscal_year_id.date_to)
            wage = 0
            if contracts:
                sheet.write(y_offset, 8,  contracts[0].job_grade_id.name, default_style)
                wage = contracts[0].wage
            total_income = 0 
            prev_income,remaining_months,total_months,prev_tax_paid = self.get_income(10, self.fiscal_year_id.date_from.year, self.fiscal_year_id, emp)
            total_income += prev_income
            sheet.write(y_offset, 9, prev_income, float_style)
            prev_income,remaining_months,total_months,prev_tax_paid = self.get_income(11, self.fiscal_year_id.date_from.year, self.fiscal_year_id, emp)
            total_income += prev_income
            sheet.write(y_offset, 10, prev_income, float_style) 
            prev_income,remaining_months,total_months,prev_tax_paid = self.get_income(12, self.fiscal_year_id.date_from.year, self.fiscal_year_id, emp)
            total_income += prev_income            
            sheet.write(y_offset, 11, prev_income, float_style)
            prev_income,remaining_months,total_months,prev_tax_paid = self.get_income(1, self.fiscal_year_id.date_to.year, self.fiscal_year_id, emp)
            total_income += prev_income 
            sheet.write(y_offset, 12, prev_income, float_style)  
            prev_income,remaining_months,total_months,prev_tax_paid = self.get_income(2, self.fiscal_year_id.date_to.year, self.fiscal_year_id, emp)
            total_income += prev_income
            sheet.write(y_offset, 13, prev_income, float_style)  
            prev_income,remaining_months,total_months,prev_tax_paid = self.get_income(3, self.fiscal_year_id.date_to.year, self.fiscal_year_id, emp)
            total_income += prev_income
            sheet.write(y_offset, 14, prev_income, float_style)  
            prev_income,remaining_months,total_months,prev_tax_paid = self.get_income(4, self.fiscal_year_id.date_to.year, self.fiscal_year_id, emp)
            total_income += prev_income
            sheet.write(y_offset, 15, prev_income, float_style) 
            prev_income,remaining_months,total_months,prev_tax_paid = self.get_income(5, self.fiscal_year_id.date_to.year, self.fiscal_year_id, emp)
            total_income += prev_income
            sheet.write(y_offset, 16, prev_income, float_style)
            prev_income,remaining_months,total_months,prev_tax_paid = self.get_income(6, self.fiscal_year_id.date_to.year, self.fiscal_year_id, emp)
            total_income += prev_income
            sheet.write(y_offset, 17, prev_income, float_style) 
            prev_income,remaining_months,total_months,prev_tax_paid = self.get_income(7, self.fiscal_year_id.date_to.year, self.fiscal_year_id, emp)
            total_income += prev_income 
            sheet.write(y_offset, 18, prev_income, float_style)
            prev_income,remaining_months,total_months,prev_tax_paid = self.get_income(8, self.fiscal_year_id.date_to.year, self.fiscal_year_id, emp)
            total_income += prev_income
            sheet.write(y_offset, 19, prev_income, float_style)  
            prev_income,remaining_months,total_months,prev_tax_paid = self.get_income(9, self.fiscal_year_id.date_to.year, self.fiscal_year_id, emp)
            total_income += prev_income            
            sheet.write(y_offset, 20, prev_income, float_style)
            total_income += total_income + (wage * remaining_months)
            sheet.write(y_offset, 21, total_income, float_style)
            twenty_percent_exemption = total_income * 0.2
            sheet.write(y_offset, 22, twenty_percent_exemption, float_style)
            family_exemption = 0
            if emp.father_exemption:
                family_exemption += 1000000
            if emp.mother_exemption:
                family_exemption += 1000000
            sheet.write(y_offset, 23, family_exemption, float_style)
            spouse_exemption = 0
            if emp.spouse_exemption:
                spouse_exemption += 1000000
            sheet.write(y_offset, 24, spouse_exemption, float_style)
            children_exemption = 0
            if emp.children > 0:
                children_exemption += emp.children * 500000
            sheet.write(y_offset, 25, children_exemption, float_style)
            ssb_amount =0
            if wage > 400000:
                ssb_amount = wage * 0.02
                if emp.ssb_not_calculate:
                    ssb_amount = 0
                elif abs(ssb_amount) > 6000:
                    ssb_amount = 6000      
            sheet.write(y_offset, 26, ssb_amount, float_style)
            twenty_percent_exemption = total_income * 0.2
            if twenty_percent_exemption <= 10000000:
                twenty_percent_exemption = twenty_percent_exemption
            else:
                twenty_percent_exemption = 10000000
            
            previous_month = total_months - (remaining_months + 1)
            taxable_income  = total_income - family_exemption - spouse_exemption - children_exemption - twenty_percent_exemption - ((remaining_months + 1 + previous_month) * ssb_amount)
            sheet.write(y_offset, 27, taxable_income, float_style)
            sheet.write(y_offset, 28, 0, float_style)
            payable_tax = total_payable_tax= 0
            if taxable_income <= 30000000:
                payable_tax = (taxable_income - 10000000 ) * 0.10
                total_payable_tax += payable_tax
            if taxable_income > 30000000:
                payable_tax = (30000000- 10000000 ) * 0.10
                total_payable_tax += payable_tax
            sheet.write(y_offset, 29, payable_tax, float_style)
            if taxable_income <= 50000000:
                payable_tax = (taxable_income - 30000000) * 0.15
                total_payable_tax += payable_tax
            if taxable_income > 50000000:
                payable_tax = (50000000 - 30000000) * 0.15
                total_payable_tax += payable_tax
            sheet.write(y_offset, 30, payable_tax, float_style)
            if taxable_income <= 70000000:
                payable_tax = (taxable_income - 50000000 ) * 0.20
                total_payable_tax += payable_tax
            if taxable_income > 70000000:
                payable_tax += (70000000 - 50000000 ) * 0.20
                total_payable_tax += payable_tax
            sheet.write(y_offset, 31, payable_tax, float_style)
            payable_tax += (taxable_income - 70000000) * 0.25;
            sheet.write(y_offset, 32, payable_tax, float_style)
            payable_tax = payable_tax - prev_tax_paid 
            result = payable_tax / (remaining_months + 1)
            if result < 0:
                result = 0
            result = round(result)
            sheet.write(y_offset, 33, result, float_style)
            sheet.write(y_offset, 34, result, float_style)
            total_prev_tax_paid = 0
            prev_income,remaining_months,total_months,prev_tax_paid = self.get_income(10, self.fiscal_year_id.date_from.year, self.fiscal_year_id, emp)
            total_prev_tax_paid += prev_tax_paid 
            sheet.write(y_offset, 35, prev_tax_paid, float_style)
            prev_income,remaining_months,total_months,prev_tax_paid = self.get_income(11, self.fiscal_year_id.date_from.year, self.fiscal_year_id, emp)
            total_prev_tax_paid += prev_tax_paid 
            sheet.write(y_offset, 36, prev_tax_paid, float_style)
            prev_income,remaining_months,total_months,prev_tax_paid = self.get_income(12, self.fiscal_year_id.date_from.year, self.fiscal_year_id, emp)
            total_prev_tax_paid += prev_tax_paid 
            sheet.write(y_offset, 37, prev_tax_paid, float_style)
            prev_income,remaining_months,total_months,prev_tax_paid = self.get_income(1, self.fiscal_year_id.date_to.year, self.fiscal_year_id, emp)
            total_prev_tax_paid += prev_tax_paid 
            sheet.write(y_offset, 38, prev_tax_paid, float_style)
            prev_income,remaining_months,total_months,prev_tax_paid = self.get_income(2, self.fiscal_year_id.date_to.year, self.fiscal_year_id, emp)
            total_prev_tax_paid += prev_tax_paid 
            sheet.write(y_offset, 39, prev_tax_paid, float_style)
            prev_income,remaining_months,total_months,prev_tax_paid = self.get_income(3, self.fiscal_year_id.date_to.year, self.fiscal_year_id, emp)
            total_prev_tax_paid += prev_tax_paid 
            sheet.write(y_offset, 40, prev_tax_paid, float_style)
            prev_income,remaining_months,total_months,prev_tax_paid = self.get_income(4, self.fiscal_year_id.date_to.year, self.fiscal_year_id, emp)
            total_prev_tax_paid += prev_tax_paid 
            sheet.write(y_offset, 41, prev_tax_paid, float_style)
            prev_income,remaining_months,total_months,prev_tax_paid = self.get_income(5, self.fiscal_year_id.date_to.year, self.fiscal_year_id, emp)
            total_prev_tax_paid += prev_tax_paid 
            sheet.write(y_offset, 42, prev_tax_paid, float_style)
            prev_income,remaining_months,total_months,prev_tax_paid = self.get_income(6, self.fiscal_year_id.date_to.year, self.fiscal_year_id, emp)
            total_prev_tax_paid += prev_tax_paid 
            sheet.write(y_offset, 43, prev_tax_paid, float_style)
            prev_income,remaining_months,total_months,prev_tax_paid = self.get_income(7, self.fiscal_year_id.date_to.year, self.fiscal_year_id, emp)
            total_prev_tax_paid += prev_tax_paid 
            sheet.write(y_offset, 44, prev_tax_paid, float_style)
            prev_income,remaining_months,total_months,prev_tax_paid = self.get_income(8, self.fiscal_year_id.date_to.year, self.fiscal_year_id, emp)
            total_prev_tax_paid += prev_tax_paid 
            sheet.write(y_offset, 45, prev_tax_paid, float_style)
            prev_income,remaining_months,total_months,prev_tax_paid = self.get_income(9, self.fiscal_year_id.date_to.year, self.fiscal_year_id, emp)
            total_prev_tax_paid += prev_tax_paid 
            sheet.write(y_offset, 46, prev_tax_paid, float_style)
            sheet.write(y_offset, 47, total_prev_tax_paid, float_style)
            sheet.write(y_offset, 48, taxable_income - total_prev_tax_paid, float_style)
            y_offset += 1
    def print_xlsx(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        month_name = self.fiscal_year_id.name or '' #dict(self._fields['month'].selection).get(self.month) + ' - ' + self.year
        report_name = 'Yearly Tax Report for ' + month_name + '.xlsx'
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
                'url': 'web/content/?model=report.tax.wizard&download=true&field=excel_file&id=%s&filename=%s' % (
                    active_id, report_name),
                'target': 'new',
            }
