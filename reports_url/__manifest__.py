# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
    'name' : 'Reports URL',
    'version' : '1.0',
    'author' : '7th Computing Software Development ',
    'summary': 'Reports URL',
    'description': """
    
Report URL

    """,
    'author': ' 7th Computing Software Development Team',
    'website': 'http://www.7thcomputing.com',
    'category': 'Report URL',
    'sequence': 4,
    'depends': ['account','stock'],
    'demo' : [],
    'data' : [
        'security/ir.model.access.csv',
        'views/hr_report_url_view.xml',
        
    ],
    'test' : [
    ],
    'auto_install': False,
    'application': True,
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
