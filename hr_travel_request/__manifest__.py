{
    'name': 'Travel Request',
    'version': '1.0.0',
    'author': '7thcomputing',
    'license': 'AGPL-3',
    'category': 'TimeOff',
    'website': 'http://7thcomputing.com',
    'description': """

Travel Request
    """,
    'depends': ['base', 'hr',
                'hr_payroll',
                'one_signal_notification_connector','job_grade'],
    'data': [
            'security/ir.model.access.csv',
            'data/travel_request_data.xml',
            'data/work_entry_type.xml',
            'views/hr_travel_request_view.xml',
            'views/hr_travel_type_view.xml',
    ],    
    'installable': True,
    'auto_install': False,
}
