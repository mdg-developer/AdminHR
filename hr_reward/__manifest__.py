{
    'name': 'HR Reward',
    'version': '1.0.0',
    'author': '7thcomputing',
    'license': 'AGPL-3',
    'category': 'Employee',
    'website': 'http://7thcomputing.com',
    'description': """

Reward Type
    """,
    'depends': ['base','hr'],
    'data': [
            'data/ir_cron_data.xml',
            'security/ir.model.access.csv',
            'views/reward_type_view.xml',
            'views/reward_view.xml',
            'views/hr_employee_view.xml',
            'reports/report_reward_letter.xml',
            'views/reports.xml',
    ],    
    'installable': True,
    'auto_install': False,
}
