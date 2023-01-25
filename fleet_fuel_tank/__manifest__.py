
{
    "name" : "Fuel Tank Integration with Fleet Management in Odoo",
    "version" : "13.0.0.0",
    "category" : "industries",
    "summary": 'Fleet Fuel Tank management vehicle fuel Tank management vehicle tank management Manage vehicle tank with fleet vehicle fuel consumption Tank  car fuel consumption car fuel tank vehicle fuel tank vehicle consumption fuel consumption tank',
    'description': """
    odoo Fleet fuel Tank management Fleet tank management  Manage Fuel tank with fleet management.
    odoo vehicle fuel Tank management vehicle tank management  Manage vehicle tank with fleet management.
    odoo car fuel Tank management car tank management  Manage car tank with fleet management.

    odoo Fleet fuel consumption Tank management Fleet consumption tank management  Manage Fuel consumption tank with fleet management.
    odoo vehicle fuel consumption Tank management vehicle consumption tank management  Manage vehicle fuel consumption tank with fleet consumptionmanagement.
    odoo car fuel consumption Tank management car fuel consumption tank management  Manage car tank with fleet management.

This is very useful module fuel management, specially fleet management companies will require module,

Module keeps logs of all filling by different vehicle, How much consumption for particular vehicle and also shows history of it,

This can be useful keep track fuel consumption. 

Odoo vehicle fuel consumption fleet fuel consumption vehicle
Odoo car fuel consumption fuel on vehicle consumption fuel on car
""",
    "author": "BrowseInfo",
    "website" : "https://www.browseinfo.in",
    'price': 79,
    'currency': "EUR",
    'depends': ['base','fleet','hr', 'fleet_insurance', 'account','hr_fleet_ext'],
    'data': [
        "security/ir.model.access.csv",
        'views/add_liters.xml',
        'views/fleet_tank_view.xml',
        'views/preventive_reminder_view.xml',
        'views/fleet_tyre_history_view.xml',
    ],
    "auto_install": False,
    "application": True,
    "installable": True,
    "live_test_url":'https://youtu.be/GGKLVj4yzow',
    "images":['static/description/Banner.png'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: