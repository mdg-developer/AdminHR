{
    'name': 'Loan',
    'version': '1.0.0',
    'author': '7thcomputing',
    'license': 'AGPL-3',
    'category': 'Payroll',
    'website': 'http://7thcomputing.com',
    'description': """

Loan
    """,
    'depends': ['base', 'hr_payroll', 'hr', 'account',
                'one_signal_notification_connector', 'purchase','stock','purchase_stock','purchase_requisition'],
    'data': [
            'wizard/loan_clear_wizard_view.xml',
            'views/hr_loan_view.xml',
            'views/hr_payroll_view.xml',
            'security/ir.model.access.csv',
            'views/account_journal_view.xml',
            'views/purchase_order_view.xml',
    ],    
    'installable': True,
    'auto_install': False,
}
