{
    'name': 'HR Leave Auto Allocation',
    'version': '1.0.0',
    'author': '7thcomputing',
    'license': 'AGPL-3',
    'category': 'TimeOff',
    'website': 'http://7thcomputing.com',
    'description': """

Travel Request
    """,
    'depends': ['base',
                'hr',
                'hr_employee_updation',
                'hr_holidays'],
    'data': [
            'security/ir.model.access.csv',
            'data/ir_cron_data.xml',
            'wizard/change_to_permanent_view.xml',
            'views/hr_leave_auto_allocation_view.xml',
            'views/hr_employee_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}