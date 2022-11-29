{
    'name': 'Contract',
    'version': '1.0.0',
    'author': '7thcomputing',
    'license': 'AGPL-3',
    'category': 'hr_contract',
    'website': 'http://7thcomputing.com',
    'description': """

Contract
    """,
    'depends': ['base',
                'hr_contract',
                ],
    'data': [
            'security/security.xml',
            'views/hr_contract_view.xml',
            'wizard/extend_probation_view.xml',
            'views/hr_employee_view.xml',
    ],    
    'installable': True,
    'auto_install': False,
}
