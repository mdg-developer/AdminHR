{
    'name': 'Payroll Structure Ext',
    'version': '1.0.0',
    'author': '7thcomputing',
    'license': 'AGPL-3',
    'category': 'Employee',
    'website': 'http://7thcomputing.com',
    'description': """

Payroll Structure Ext
    """,
    'depends': ['base', 'hr', 'hr_allowance', 'hr_deduction', 'hr_payroll',
                'hr_payroll_account', 'hr_loan', 'hr_insurance', 'hr_public_holiday',
                'job_grade', 'hr_ext', 'mail'
                ],
    'data': [
        'data/hr_payroll_structure_demo.xml',
        'data/hr_allowance_demo.xml',
        'data/hr_deduction_demo.xml',
        'views/hr_payslip_views.xml',
    ],    
    'installable': True,
    'auto_install': False,
}
