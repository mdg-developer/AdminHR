# -*- coding: utf-8 -*-

from odoo import api, fields, models  


class ResPartner(models.Model):
	_inherit = "res.partner"

	custom_is_faculty = fields.Boolean(string='Is Trainer?',copy=False)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: