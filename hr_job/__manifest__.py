{
    'name': 'Job Position Benefit',
    'version': '1.0.0',
    'author': '7thcomputing',
    'license': 'AGPL-3',
    'category': 'Recruitment',
    'website': 'http://7thcomputing.com',
    'description': """

Job Position Benefit
    """,
    'depends': ['base','hr'],
    'data': [
            'security/ir.model.access.csv',
            'views/hr_job_view.xml',

    ],    
    'installable': True,
    'auto_install': False,
}
