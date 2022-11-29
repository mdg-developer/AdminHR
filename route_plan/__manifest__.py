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
    'name': 'Route Plan',
    'version': '1.0',
    'sequence': 14,
    'summary': 'Route Plan',
    'description': """
Manage Route Plan
======================================
With this module for Route Plan.
    """,
    'author': '7thcomputing developers',
    'website': 'http://www.7thcomputing.com',
    'category': 'Employee',
    'depends': ['base','account', 'fleet', 'fleet_fuel_tank', 'base_geolocalize','gws_google_maps','hr', 'hr_travel_request', 'product'],
    'data' : [
        'data/sequence.xml',
        'security/hr_security.xml',
        'security/ir.model.access.csv',
        'security/admin_security.xml',
        'wizard/map_view.xml',
        'views/trailer_view.xml',
        'views/vehicle_trailer_history_views.xml',
        'views/route_plan_view.xml',
        'views/plan_trip_waybill_view.xml',
        'views/plan_trip_product_view.xml',
        'views/day_plan_trip_view.xml',
        'views/product_view.xml',
        'views/account_payment_view.xml',
        'views/commission_config_view.xml',
        'views/res_partner_view.xml',

    ],
    'demo': [],
    'installable': True,
}
