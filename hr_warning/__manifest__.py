{
    'name': 'HR Warning',
    'version': '1.0.0',
    'author': '7thcomputing',
    'license': 'AGPL-3',
    'category': 'Employee',
    'website': 'http://7thcomputing.com',
    'description': """

Warning Type
    """,
    'depends': ['base','hr'],
    'data': [
            'data/ir_cron_data.xml',
            'security/ir.model.access.csv',
            'views/warning_type_view.xml',
            'views/warning_view.xml',
            'views/hr_employee_view.xml',
            'views/reports.xml',
            'reports/report_warning_letter.xml',
    ],    
    'installable': True,
    'auto_install': False,
}
