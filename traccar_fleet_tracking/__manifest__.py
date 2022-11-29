# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
{
    'name': 'Odoo Fleet Tracking',
    "version": "12.0.1.0.5",
    'summary': 'GPS Tracking for your fleet',
    'author': "Odoo Engineering, InfoTerra",
    'maintainer': 'Elsie Vernon Hogan <evhogan3@gmail.com>, Antonio Buric <antonio.burich@gmail.com>',
    'category': 'Industries',
    'description': """
Traccar GPS tracking integration with the Fleet Management module.

==========================

Track your vehicles with the free and open source Traccar solution.
""",
    'depends': [
        #'web_google_maps',
        'fleet'
    ],
    "external_dependencies": {
        "python": ['bokeh'],
    },
    'website': '',
    'data': [
         'security/ir.model.access.csv',
#         'data/ir_cron_data.xml',
#         'views/templates.xml',
         'views/res_config.xml',
         'views/fleet_vehicle_view.xml',
        'views/track_solid_view.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'price': 300,
    'currency': 'EUR',
    'images': ['static/description/banner.jpg'],
}
