import re
from odoo import fields, models, api


class Allowance(models.Model):
    _inherit = 'hr.allowance'

    # @api.model
    # def create(self, vals):
    #     vals['name'] = " ".join(vals['name'].split())
    #     vals['code'] = (re.sub(r"\s+", "", vals['code'])).upper()
    #     result = super(Allowance, self).create(vals)
    #     return result

    # def write(self, vals):
    #     if vals.get('name'):
    #         vals['name'] = " ".join(vals['name'].split())
    #     if vals.get('code'):
    #         vals['code'] = (re.sub(r"\s+", "", vals['code'])).upper()
    #     result = super(Allowance, self).write(vals)
    #     return result


class Deduction(models.Model):
    _inherit = 'hr.deduction'

    # @api.model
    # def create(self, vals):
    #     vals['name'] = " ".join(vals['name'].split())
    #     vals['code'] = (re.sub(r"\s+", "", vals['code'])).upper()
    #     result = super(Deduction, self).create(vals)
    #     return result

    # def write(self, vals):
    #     if vals.get('name'):
    #         vals['name'] = " ".join(vals['name'].split())
    #     if vals.get('code'):
    #         vals['code'] = (re.sub(r"\s+", "", vals['code'])).upper()
    #     result = super(Deduction, self).write(vals)
    #     return result
