{
    'name': 'Fleet Insurance',
    'version': '1.0.0',
    'author': '7thcomputing',
    'license': 'AGPL-3',
    'category': 'Payroll',
    'website': 'http://7thcomputing.com',
    'description': """

Fleet Insurance 
    """,
    'depends': ['base','fleet'],
    'data': [
            'views/hr_vehicle_insurance_view.xml',
            'views/hr_trailer_insurance_view.xml',
            'security/ir.model.access.csv',
    ],    
    'installable': True,
    'auto_install': False,
}
