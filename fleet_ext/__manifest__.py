
{
    "name" : "Fleet Customization",
    "version" : "1.0.0.",
    "category" : "Fleet",
    "summary": 'Fleet Customization',
    'description': """ """,
    "author": "7thcomputing",
    "website" : "http://7thcomputing.com",
    'depends': ['base','fleet','hr','mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/fleet_scheduled_data.xml',
        'views/fleet_ext_view.xml',
    ],
    "auto_install": False,
    "installable": True,
}
