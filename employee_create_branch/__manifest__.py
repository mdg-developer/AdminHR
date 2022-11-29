{
    'name': 'Employees From User Branch',
    'version': '1.0.0',
    'author': '7thcomputing',
    'license': 'AGPL-3',
    'category': 'User',
    'website': 'http://7thcomputing.com',
    'description': """

Employees From User Branch
    """,
    'depends': ['base','hr'],
    'data': [
            'views/employee_create_branch_view.xml',
    ],    
    'installable': True,
    'auto_install': False,
}
