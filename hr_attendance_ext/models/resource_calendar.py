from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo import _



class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    night_to_morning = fields.Boolean(string='Night to Morning Shift', default=False)
    no_attendance = fields.Boolean(string='No Attendance', default=False)
    holiday = fields.Boolean(string='Holiday', default=False)
    one_day_off = fields.Boolean(string='One Day Off', default=False)
    no_holidays = fields.Boolean(string='No Holidays', default=False)
    active = fields.Boolean(string='Active', default=True)


    @api.constrains('no_attendance','holiday','one_day_off','no_holidays')
    def _onchange_check_attendance(self):
        # import pdb
        # pdb.set_trace()
        return True
        if self.no_attendance== True:
            if self.holiday == True or self.one_day_off == True or self.no_holidays == True:
                
                raise UserError(_("Can check at least one of the leave types"))
        elif self.holiday== True:
            if self.no_attendance == True or self.one_day_off == True or self.no_holidays == True:
               
                raise UserError(_("Can check at least one of the leave types"))

        elif self.one_day_off== True:
            if self.no_attendance == True or self.holiday == True or self.no_holidays == True:
                
                raise UserError(_("Can check at least one of the leave types"))

        elif self.no_holidays== True:
            if self.no_attendance == True or self.holiday == True or self.one_day_off == True:
                
                raise UserError(_("Can check at least one of the leave types"))
        if self.no_holidays== False and self.one_day_off== False and self.holiday== False and self.no_attendance== False:
            raise UserError(_("Can check at least one of the leave types"))

        if self.no_holidays== True and self.one_day_off== True and self.holiday== True and self.no_attendance== True:
            raise UserError(_("Can check at least one of the leave types"))


class ResourceCalendarAttendance(models.Model):
    _inherit = "resource.calendar.attendance"

    ot_start_from = fields.Float(string='OT start from', required=True)
    lunch_from = fields.Float(string='Lunch from', required=True)
    lunch_to = fields.Float(string='Lunch to', required=True)
    start_end = fields.Selection([('start', 'Start'), ('end', 'End')], default='start', required=True)

