{
    'name': 'Salary Table',
    'version': '1.0.0',
    'author': '7thcomputing',
    'license': 'AGPL-3',
    'category': 'Payroll',
    'website': 'http://7thcomputing.com',
    'description': """

Salary Level
    """,
    'depends': ['base','hr_payroll','job_grade','salary_level'],
    'data': [
            'views/hr_salary_view.xml',
            'security/ir.model.access.csv',
    ],    
    'installable': True,
    'auto_install': False,
}
