{
    'name': 'HR Access Right',
    'version': '1.0.0',
    'author': '7thcomputing',
    'license': 'AGPL-3',
    'category': 'Access Right',
    'website': 'http://7thcomputing.com',
    'description': """

Allowance
    """,
    'depends': ['base','hr','hr_attendance','hr_resignation','hr_warning','hr_reward','hr_warning','hr_ext','fleet','maintenance','route_plan','stock','product'],
    'data': [
            
            'security/hr_security.xml',
            'security/ir.model.access.csv',
    ],    
    'installable': True,
    'auto_install': False,
}
