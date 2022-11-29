{
    'name': 'Trip Type',
    'version': '1.0.0',
    'author': '7thcomputing',
    'license': 'AGPL-3',
    'category': 'Fleet',
    'website': 'http://7thcomputing.com',
    'description': """

Trip Type
    """,
    'depends': ['hr', 'fleet','stock'],
    'data': [
            'views/hr_trip_view.xml',
            'security/ir.model.access.csv',
    ],    
    'installable': True,
    'auto_install': False,
}
