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

#

{
    'name': 'HR Skills enhancement',
    'license':'GPL-3 or any later version',
    'version': '13.0.2',
    'category': 'Generic Modules/Human Resources',
    'description': "",
    'summary':
    """
    """,
    'author': 'IKS Consultance',
    'price':15,
    'currency':'EUR',
    'images': ['static/description/main_screenshot.png'],
    'website': '',
    'depends': ['hr','hr_skills','hr_skills_survey'],
 
    'data': [
        'security/ir.model.access.csv',
        'views/hr_skill_type_view.xml',
        'views/hr_employee_skill_view.xml',
        'views/hr_skill_need_view.xml',
        'views/hr_employee_skill_followup_view.xml',
        'views/hr_employee_view.xml',
        'views/hr_department_view.xml',
          ],

    'qweb': [
    ],


    
    
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
