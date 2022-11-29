{
    'name': 'HR Replacement',
    'version': '1.0.0',
    'author': '7thcomputing',
    'license': 'AGPL-3',
    'category': 'TimeOff',
    'website': 'http://7thcomputing.com',
    'description': """
    Manager Replacement, Changing Shift
    """,
    'depends': ['base','hr'],
    'data': [
            'security/ir.model.access.csv',
            'data/data.xml',
            'views/manager_replacement_view.xml',
            'views/changing_shift_view.xml',
    ],    
    'installable': True,
    'auto_install': False,
}
