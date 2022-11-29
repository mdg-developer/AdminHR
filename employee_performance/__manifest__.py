# -*- coding: utf-8 -*-
###################################################################################
#
#    inteslar software trading llc.
#    Copyright (C) 2018-TODAY inteslar software trading llc (<https://www.inteslar.com>).
#
###################################################################################
{
    'name': "Employee Performance Evaluation",
    'version': '13.0',
    'category': 'HR',
    'price':   700.00,
    'currency': 'EUR',
    'maintainer': 'inteslar',
    'website': "https://www.inteslar.com",
    'license': 'OPL-1',
    'author': 'inteslar',
    'summary': 'Employee Performance Evaluation From Website',
    'images': ['static/images/main_screenshot.png'],
    'depends': ['resource', 'hr','web', 'portal','website','account', 'account_reports','hr_ext'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/perfomarnce_data.xml',
        'data/decimal_precision_data.xml',
        'wizard/job_position_check_list_wizard_view.xml',
        'wizard/employee_performance_wizard_view.xml',
        'views/performance_view.xml',
        'views/portal_performance_templates.xml',
        'report/job_position_checklist_template.xml',
    ],
    'installable': True,
    'application': True,
}