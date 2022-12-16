{
    'name': 'Employee Tax Information',
    'version': '1.0.0',
    'author': '7thcomputing',
    'license': 'AGPL-3',
    'category': 'Employee Tax',
    'website': 'http://7thcomputing.com',
    'description': """

Employee Tax Information
    """,
    'depends': ['base','hr'],
    'data': [
            'security/ir.model.access.csv',
            'views/employee_tax_info_view.xml',
            'views/employee_bus.xml',
    ],    
    'installable': True,
    'auto_install': False,
}
