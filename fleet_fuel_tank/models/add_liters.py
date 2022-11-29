# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from datetime import datetime
from odoo.exceptions import UserError
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

class liters_liters(models.Model):
    _name = 'liters.liters'
    
    liters = fields.Float('Liters')
    liter_price = fields.Float('Price Per Liter')

    def add_liters(self):
        liters = self.liters
        price_per_liter = self.liter_price
        wizard_total_liter_price = liters * price_per_liter
        fuel_tank_obj = self.env['fuel.tank']
        history_obj = self.env['fuel.filling.history']
        date = datetime.now()
        defaultdate =  date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        filldate = defaultdate.split()[0]
        if self._context.get('active_id',False):
            browse_obj = fuel_tank_obj.browse(self._context['active_id'])
            balance = browse_obj.liters + liters
            total_tank_litter_price = browse_obj.liters * browse_obj.average_price
            
            if browse_obj.capacity < balance:
                raise UserError(_('You can have only '+ str(float(browse_obj.capacity) - float(browse_obj.liters)) +' liters of capacity.'))
            final_average_price = 0
            if (balance != 0):
                final_average_price = (total_tank_litter_price + wizard_total_liter_price) / (balance)
            else:
                raise UserError(_('You cannot have fuel liter less than 1.'))
            
            res_history = {
                'fuel_liter': liters,
                'price_per_liter': price_per_liter,
                'filling_date': filldate,
                'source_doc': 'Opening',
                'fuel_filling_id': self._context.get('active_id'),
            }
            history_obj.create(res_history)

            browse_obj.write({
                'liters': balance,
                'average_price': final_average_price,
                'last_fuel_adding_date': filldate
            })
        return True
