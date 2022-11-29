{
    'name': 'Employment Contract',
    'version': '1.0.0',
    'author': '7thcomputing',
    'license': 'AGPL-3',
    'category': 'Employee',
    'website': 'http://7thcomputing.com',
    'description': """
Employment Contract
    """,
    'depends': ['base','hr'],
    'data': [                
            'views/hr_employee_view.xml',
            'views/contract_config.xml',
            'security/ir.model.access.csv',
    ],    
    'installable': True,
    'auto_install': False,
}
