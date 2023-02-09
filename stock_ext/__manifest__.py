{
    'name': 'Stock',
    'version': '1.0.0',
    'author': '7thcomputing',
    'license': 'AGPL-3',
    'category': 'Inventory',
    'website': 'http://7thcomputing.com',
    'description': """
Stock
    """,
    'depends': ['stock', 'account'],
    'data': [
            'views/stock_location_view_inherit.xml',
            'views/stock_picking_view.xml',
    ],    
    'installable': True,
    'auto_install': False,
}
