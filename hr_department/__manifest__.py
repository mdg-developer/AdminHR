# -*- coding: utf-8 -*-
{
    'name': "Hr Department Ext Module",

    'description': """
        Hr Department, Sections and Teams
    """,

    'category': 'hr.department',
    'version': '1.0',
    'depends': ['base','hr', 'res_branch'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_section_team_view.xml',
        'views/view_hr_department.xml',
    ],
}
