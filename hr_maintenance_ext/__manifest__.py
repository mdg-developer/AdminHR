{
    'name': 'Maintenance',
    'version': '1.0.0',
    'author': '7thcomputing',
    'license': 'AGPL-3',
    'category': 'Human Resources',
    'website': 'http://7thcomputing.com',
    'description': """

Maintenance
    """,
    'depends': ['hr', 'maintenance','res_branch', 'fleet', 'purchase', 'stock','employee_tax_info', 'fleet_ext', 'hr_ext', 'hr_loan'],
    'data': [
            'data/sequence.xml',
            'security/ir.model.access.csv',
            'security/security.xml',
            'views/hr_maintenance_ext_view.xml',
            'views/maintenance_schedule_data.xml',
    ],    
    'installable': True,
    'auto_install': False,
}
