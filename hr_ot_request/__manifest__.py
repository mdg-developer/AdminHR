{
    'name': 'Overtime Request',
    'version': '1.0.0',
    'author': '7thcomputing',
    'license': 'AGPL-3',
    'category': 'Attendances',
    'website': 'http://7thcomputing.com',
    'description': """

Overtime Request
    """,
    'depends': ['base','hr','mail',
                'hr_travel_request'],
    'data': [
            'views/hr_ot_request_view.xml',
            'views/hr_ot_response_view.xml',
            'security/ir.model.access.csv',
            # 'data/ot.request.csv',
            'data/hr_ot_request.xml',
    ],    
    'installable': True,
    'auto_install': False,
}
