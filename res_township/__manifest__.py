# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014-Today OpenERP SA (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'res_township',
    'version': '1.0',
    'sequence': 14,
    'summary': 'Township',
    'description': """
Manage Township part of state
======================================
With this module for township.
    """,
    'author': '7thcomputing developers',
    'website': 'https://www.odoo.com/page/crm',
    'depends': ['base', 'crm'],
    'data' : [
        'security/ir.model.access.csv',
        'views/res_township_view.xml',
        'views/res_city_view.xml',
        'views/res_partner_view.xml',
    ],
    'demo': [],
    'installable': True,
}
