# -*- encoding: utf-8 -*-
##############################################################################
#    This module allows Clients to view external content through backend iframes
#    Aloui Med Amine (https://www.linkedin.com/in/med-amine-aloui-5b400988)
##############################################################################
{
    'name': "Iframes Backend Dashboard",
    'summary': """This module allows Clients to view external content through backend iframes.""",
    'description': """
        This module allows Clients to view external content through backend iframes.
    """,
    'version': '1.0',
    'category': 'Dashboards',
    'license': 'OPL-1',
    'author': "Aloui Mohamed Amine",
    'website': "",
    'contributors': [
    ],
    'support': 'mohammed.aminaloui@gmail.com',
    'depends': [
        'base',
        'web',
        'mail',
        'board',
    ],
    'data': [
        'security/backend_iframe_access_rules.xml',
        'security/ir.model.access.csv',
        'views/backend_iframe.xml',
        'views/template.xml',
    ],
    'images': [
        'static/description/main_screenshot.png'
    ],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'price': 75,
    'currency': 'EUR',
}
