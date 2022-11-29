{
    'name': 'Calendar Customization',
    'version': '1.0.0',
    'author': '7thcomputing',
    'license': 'AGPL-3',
    'category': 'Employee',
    'website': 'http://7thcomputing.com',
    'description': """

Calendar Customization
    """,
    'depends': ['base', 'hr', 'hr_ext', 'calendar', 'employee_tax_info'],
    'data': [
        'views/calendar_views.xml',
    ],    
    'installable': True,
    'auto_install': False,
}
