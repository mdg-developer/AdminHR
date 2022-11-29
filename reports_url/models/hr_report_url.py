import time
import math

from odoo.osv import expression
from odoo.tools.float_utils import float_round as round
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, _

class hr_report_url(models.Model):
    _name = 'hr.report.url'
    _description = 'Report_URL'
  
    url_link=fields.Char('URL', size=150, required=True)
    url_name=fields.Char('Report Name', size=150, required=True)

    def go_report(self):
        result =  {
                  'name'     : 'Go to Report',
                  'res_model': 'ir.actions.act_url',
                  'type'     : 'ir.actions.act_url',
                  'target'   : 'new',
               }
        for record in self.env['hr.report.url'].browse(self.ids):
            user_id = self._uid
            result['url'] = record.url_link+'&user_id='+ str(user_id)
            
        return result

hr_report_url()
    