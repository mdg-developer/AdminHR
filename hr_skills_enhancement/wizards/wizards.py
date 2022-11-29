# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################





from datetime import datetime, date

import time

import pytz

from odoo import models, fields, api, _




class hr_position_wizard_update(models.TransientModel):
    """

    """

    _name = 'hr.position.wizard.update'

    def update_records(self):
        """

        """


        for record in self:
           
            for position in record.env['hr.position'].search([('id', 'in', self._context.get('active_ids'))], order='id'):
            
                if record.department_id:
                    position.department_id = record.department_id.id
                    
                if record.quotity:
                    position.quotity = record.quotity        
                    
                if record.analytic_account_id:
                    position.analytic_account_id = record.analytic_account_id.id

                if record.contract_type_id:
                    position.contract_type_id = record.contract_type_id.id
                
                
        return

    department_id = fields.Many2one('hr.department', 'Department', index=True)
    quotity = fields.Integer('Quotity')
    analytic_account_id = fields.Many2one('account.analytic.account',onupdate='cascade', string='Analytic Account')
    contract_type_id = fields.Many2one('hr.contract.type',onupdate='cascade', string='Contract type')




class hr_position_wizard_copy(models.TransientModel):
    """

    """

    _name = 'hr.position.wizard.copy'

    def copy_records(self):
        """

        """

        for record in self:

            for position in record.env['hr.position'].search([('id', 'in', self._context.get('active_ids'))], order='id'):

                new_id = record.env['hr.position'].create({
                'employee_id':position.employee_id.id,
                'date_start':record.date_start,
                'date_end': record.date_end,
                'analytic_account_id':position.analytic_account_id.id,
                'quotity' : position.quotity,
                'contract_type_id' : position.contract_type_id.id,
                'is_valide': True
                })

        return

    date_start = fields.Date('Date start', required=True)
    date_end = fields.Date('Date end')
