{
    'name': 'Organizational Chart Data',
    'version': '1.0.0',
    'author': '7thcomputing',
    'license': 'AGPL-3',
    'category': 'HR',
    'website': 'http://7thcomputing.com',
    'description': """

Organizational Chart Data
    """,
    'depends': ['base', 'hr'],
    'data': [
            'security/ir.model.access.csv',
            'views/org_chart_data_view.xml',            
    ],    
    'installable': True,
    'auto_install': False,
}
