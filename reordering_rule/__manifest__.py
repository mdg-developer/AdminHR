{
    'name': 'Reordering Rule',
    'version': '1.0.0',
    'author': '7thcomputing',
    'license': 'AGPL-3',
    'category': 'Employee',
    'website': 'http://7thcomputing.com',
    'description': """

Branches
    """,
    'depends': ['base','stock','purchase'],
    'data': [
            'security/ir.model.access.csv',
            
            'views/stock_scheduler_inherit.xml',
            
            
    ],    
    'installable': True,
    'auto_install': False,
}
