
{
    "name": """HR ORG Extended""",
    "version": "13.0",
    "depends": ['hr_ext'],
    'data': [
        'views/hr_view.xml',
        'views/res_branch_view.xml',
    ],
    'qweb': [
        'static/src/xml/hr_org_chart_extended.xml',
    ],
    "auto_install": False,
    "installable": True,
}
