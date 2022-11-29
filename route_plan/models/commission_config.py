from odoo import api, fields, models, _


class CommissionConfig(models.Model):
    _name = 'commission.config'
    _description = 'Commission Config'
    _rec_name = 'journal_id'

    company_id = fields.Many2one('res.company', string='Company', required=True)
    journal_id = fields.Many2one('account.journal', string='Journal', domain="[('company_id', '=', company_id)]")
    debit_account_id = fields.Many2one('account.account', string='Debit Account', domain="[('company_id', '=', company_id)]")