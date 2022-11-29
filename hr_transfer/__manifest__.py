{
    'name': 'Transfers',
    'version': '1.0.0',
    'author': '7thcomputing',
    'license': 'AGPL-3',
    'category': 'Recruitment',
    'website': 'http://7thcomputing.com',
    'description': """

Transfers
    """,
    'depends': ['base',
                'hr',
                'hr_contract',
                'hr_employee_updation',
                'job_grade',],
    'data': [
            'security/ir.model.access.csv',
            'views/hr_transfer_view.xml',

    ],    
    'installable': True,
    'auto_install': False,
}
