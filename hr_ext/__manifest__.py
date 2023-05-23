{
    'name': 'HR Customization',
    'version': '1.0.0',
    'author': '7thcomputing',
    'license': 'AGPL-3',
    'category': 'Recruitment',
    'website': 'http://7thcomputing.com',
    'description': """

Job Position Customization
    """,
    'depends': ['base','hr','mail','job_grade','res_branch','hr_job', 'hr_skills','hr_travel_request','product','hr_expense','account','analytic','route_plan','hr_recruitment','hr_contract','hr_contract_ext','hr_payroll'],
    'data': [
            'security/hr_security.xml',
            'security/ir.model.access.csv',
            'data/badge_sequence.xml',
            'data/report_paperformat_data.xml',
            'data/config_parameter.xml',
            'data/one_signal_reminder.xml',
            'data/hr_resignation_scheduler.xml',
            'data/decimal_precision_data.xml',
            'wizard/hr_resignation_wizard_view.xml',
            'wizard/employee_custom_view.xml',
            'views/hr_view.xml',
            'views/hr_leave_type_view.xml',
            'views/insurance_type_view.xml',
            'views/hr_employee_view.xml',
            'views/hr_employment_status_view.xml',
            'views/hr_employee_benefit_view.xml',
            'views/res_company_view.xml',
            'views/res_branch_view.xml',
            'views/hr_fiscal_year_view.xml',
            'report/hr_employee_ext.xml',
            'report/hr_probation_templates.xml',
            'report/hr_employee_offer_templates.xml',
            'report/hr_employee_transfer_template.xml',
            'report/hr_pocket_view.xml',
            'report/hr_travel_expense_view.xml',
            'views/product_view.xml',
            'views/ir_sequence_view.xml',
            'views/hr_job_benefit_config_view.xml',
            'views/hr_pocket_view.xml',
            'views/hr_travel_view.xml',
            'views/hr_employment_status_view.xml',
            'views/res_users_view.xml',
            'views/hr_icloud_view.xml',
            'views/admin_trip_expense_view.xml',
            'views/admin_menu_view.xml',
            'views/account_move_view.xml',
            'views/assets.xml',
            'views/hr_leave_view.xml',
            'views/hr_job_position_detail_view.xml',
            #'views/hr_job_benefit_config_view.xml',
            'report/hr_extend_probation_templates.xml',
            'views/res_partner_view.xml',
            'views/hr_reasons_view.xml',
            'views/hr_comment_view.xml',
            'views/hr_application.xml',
    ],
    'installable': True,
    'auto_install': False,
}
