{
    'name': 'Hr Recruitment Extended',
    'version': '1.0.0',
    'author': '7thcomputing',
    'license': 'AGPL-3',
    'category': 'Leave',
    'website': 'http://7thcomputing.com',
    'description': """

Public Holidays
    """,
    'depends': ['base', 'hr', 'hr_recruitment'],
    'data': [
        'views/hr_job_view.xml'
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
