import math
from odoo import api, models, fields, _
from odoo.tools import date_utils
from odoo.tools.misc import format_date
from pytz import timezone, UTC
from datetime import date, datetime, time, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from calendar import monthrange
from odoo.tools import float_compare, float_is_zero

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
class SaleAchievement(models.Model):
    _name = 'sale.achievement'

    def _get_selection(self):
        current_year = datetime.now().year
        return [(str(i), i) for i in range(current_year - 1, current_year + 10)]

    year = fields.Selection(selection='_get_selection', string='Year', default=lambda x: str(datetime.now().year))
    month = fields.Selection(selection=MONTH_SELECTION, string='Month', default=lambda x: str(datetime.now().month))
    employee_id = fields.Many2one('hr.employee', 'Employee', readonly=False)
    sale_percentage = fields.Float('Sale Achievement(%)')
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True,
                                 default=lambda self: self.env.company)
    date_from = fields.Date('Date From')
    date_to = fields.Date('Date To')

    @api.onchange('month', 'year')
    def onchange_month_and_year(self):
        if self.year and self.month:
            self.date_from = date(year=int(self.year), month=int(self.month), day=1)
            self.date_to = date(year=int(self.year), month=int(self.month),
                                day=monthrange(int(self.year), int(self.month))[1])

class WorkfromHome(models.Model):
    _name = 'work.from.home'

    def _get_selection(self):
        current_year = datetime.now().year
        return [(str(i), i) for i in range(current_year - 1, current_year + 10)]

    year = fields.Selection(selection='_get_selection', string='Year', default=lambda x: str(datetime.now().year))
    month = fields.Selection(selection=MONTH_SELECTION, string='Month', default=lambda x: str(datetime.now().month))
    employee_id = fields.Many2one('hr.employee', 'Employee', readonly=False)
    work_from_home_percentage = fields.Float('WFH Percentage(%)')
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True,
                                 default=lambda self: self.env.company)
    date_from = fields.Date('Date From')
    date_to = fields.Date('Date To')

    @api.onchange('month', 'year')
    def onchange_month_and_year(self):
        if self.year and self.month:
            self.date_from = date(year=int(self.year), month=int(self.month), day=1)
            self.date_to = date(year=int(self.year), month=int(self.month),
                                day=monthrange(int(self.year), int(self.month))[1])



class SaleContribution(models.Model):
    _name = 'sale.contribution'

    def _get_selection(self):
        current_year = datetime.now().year
        return [(str(i), i) for i in range(current_year - 1, current_year + 10)]

    year = fields.Selection(selection='_get_selection', string='Year', default=lambda x: str(datetime.now().year))
    month = fields.Selection(selection=MONTH_SELECTION, string='Month', default=lambda x: str(datetime.now().month))
    employee_id = fields.Many2one('hr.employee', 'Employee', readonly=False)
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True,
                                 default=lambda self: self.env.company)
    date_from = fields.Date('Date From')
    date_to = fields.Date('Date To')

    @api.onchange('month', 'year')
    def onchange_month_and_year(self):
        if self.year and self.month:
            self.date_from = date(year=int(self.year), month=int(self.month), day=1)
            self.date_to = date(year=int(self.year), month=int(self.month),
                                day=monthrange(int(self.year), int(self.month))[1])