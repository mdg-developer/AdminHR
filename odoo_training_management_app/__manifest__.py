# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

{
    'name': 'Employee Training Management Application',
    'price': 99.0,
    'version': '1.1.3',
    'currency': 'EUR',
    'license': 'Other proprietary',
    'summary': " This module allow applicant to create an applications for training.",
    'description': """  
Training
Training erp
erp Training
Training odoo
Subjects
Applications
Employee Trainings

Trainers
Courses and Subjects
training Courses
training Subjects
Subjects
Training Centres
Class Rooms
Subjects
Employee Training Management
Employee Training
odoo Employee Training Management
education
edu
trainer
Courses
odoo training
training app
training module

Application Stages
Employee Traininig Stages
print Applications
print Employee Trainings Ticket
user Training
project Training

 """,
    'author': "Probuse Consulting Service Pvt. Ltd.",
    'website': "http://www.probuse.com",
    'support': 'contact@probuse.com',
    'images': ['static/description/img1.jpg'],
    # 'live_test_url': 'https://youtu.be/nRAPM1rrtxU',
    'live_test_url':'https://youtu.be/3PQ6VWc5z6o',
    'depends': [
               'base','hr','job_grade','hr_ext','project','website_slides','res_branch'
                ],
    'data':[
        'security/application_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'report/training_application_report.xml',
        'report/training_application_line_report.xml',
        'views/application_view.xml',
        'views/application_line_view.xml',
        # 'views/course_view.xml',
        # 'views/subject_view.xml',
        'views/application_stage_view.xml',
        'views/training_center_view.xml',
        'views/project_task_view.xml',
        'views/hr_employee_view.xml',
        'views/res_partner_view.xml',
        'views/training_classroom_view.xml',
        'views/training_type_view.xml',
        'views/training_cost_view.xml',
        'views/menu_item.xml',
        ],
    'installable' : True,
    'application' : False,
    'auto_install' : False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
