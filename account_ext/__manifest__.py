# -*- coding: utf-8 -*-
{
    'name': "Account Customization Module",

    'description': """
        Account Customization Module
    """,

    'category': '',
    'version': '1.0',
    'depends': ['base','account','account_asset'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_asset_view.xml',
    ],
}
