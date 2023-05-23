{
    'name': 'Inventory Customization',
    "version": "13.0.1",
    'author': 'MDG',
    'website': '',
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'summary': 'Inventory Customization',
    'depends': [
        'base','product','stock','purchase',
    ],
    'data': [
        'views/product_template_view.xml',
        'views/product_product_view.xml',
    ],
}