{
    'name': 'BOOM SMS CONFIGURATION',
    'version': '1.0',
    'sequence': 14,
    'summary': 'BOOM SMS CONFIGURATION',
    'description': """
BOOM SMS CONFIGURATION
    """,
    'author': '7thcomputing developers',
    'website': 'https://www.odoo.com/page/crm',
    'depends': ['base'],
    'data' : [
                'security/ir.model.access.csv', 

            'views/boom_sms_view.xml',
     ],
    'demo': [],
    'installable': True,
}
