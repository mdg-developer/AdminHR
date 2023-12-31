# -*- coding: utf-8 -*-

{
    'name': 'Odoo13 Employee Contracts Types',
    'version': '13.0.1.1.0',
    'category': 'Generic Modules/Human Resources',
    'summary': """
        Contract type in contracts
    """,
    'description': """Odoo13 Employee Contracts Types,Odoo13 Employee, Employee Contracts, Odoo 13""",
    'author': 'Odoo SA,Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['hr','hr_contract'],
    'data': [
        'security/ir.model.access.csv',
        'data/hr_contract_type_data.xml',
        'views/contract_view.xml',
    ],
    'installable': True,
    'images': ['static/description/banner.png'],
    'auto_install': False,
    'application': False,
    'license': 'AGPL-3',
}