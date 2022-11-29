from odoo import fields, models, api, _


class AccountJournal(models.Model):
    _inherit = "account.journal"

    is_loan_journal = fields.Boolean(string='Is a Loan Journal?', default=False)