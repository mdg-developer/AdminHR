{
    'name': 'HR Logistics Commission',
    'version': '1.0.0',
    'author': '7thcomputing',
    'license': 'AGPL-3',
    'category': 'HR Logistics Commission',
    'website': 'http://7thcomputing.com',
    'description': """
HR Logistics Commission
    """,
    'depends': ['base', 'hr', 'hr_payroll'],
    'data': [
            'security/ir.model.access.csv',
            'views/hr_logistics_commission_view.xml',
    ],    
    'installable': True,
    'auto_install': False,
}
