{
    'name': 'Attendance Customization',
    'version': '1.0.0',
    'author': '7thcomputing',
    'license': 'AGPL-3',
    'category': 'Employee',
    'website': 'http://7thcomputing.com',
    'description': """

Attendance Customization
    """,
    'depends': ['base', 'hr',
                'one_signal_notification_connector'],
    'data': [
        'data/attendance_data.xml',
        'security/ir.model.access.csv',
        'views/hr_attendance_view.xml',
        'views/resource_calendar_view.xml',
        'views/absent_log_view.xml',
        'wizard/leave_update_wizard.xml',
    ],    
    'installable': True,
    'auto_install': False,
}
