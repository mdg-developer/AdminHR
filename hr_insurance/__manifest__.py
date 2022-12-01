{
    'name': 'Insurance',
    'version': '1.0.0',
    'author': '7thcomputing',
    'license': 'AGPL-3',
    'category': 'Employee',
    'website': 'http://7thcomputing.com',
    'description': """

Insurance
    """,
    'depends': ['base','hr', 'hr_ext'],
    'data': [
            'data/ir_sequence_data.xml',
            'security/ir.model.access.csv',
            'views/hr_insurance_view.xml',
            'views/hr_claims_view.xml',


    ],    
    'installable': True,
    'auto_install': False,
}
