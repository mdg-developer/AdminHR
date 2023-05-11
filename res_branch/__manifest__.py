{
    'name': 'Branches',
    'version': '1.0.0',
    'author': '7thcomputing',
    'license': 'AGPL-3',
    'category': 'Employee',
    'website': 'http://7thcomputing.com',
    'description': """

Branches
    """,
    'depends': ['base','base_setup','portal'],
    'data': [
            'security/ir.model.access.csv',
            'security/res_branch_security.xml',
            'views/res_branch_view.xml',
    ],    
    'installable': True,
    'auto_install': False,
}
