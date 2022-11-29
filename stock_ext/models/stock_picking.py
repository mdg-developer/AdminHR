from odoo import fields, models,api, _
from datetime import date, datetime, timedelta
from odoo.exceptions import UserError, ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    _description = 'Stock Picking'

    move_id = fields.Many2one('account.move', string='Accounting Entry')

    def button_validate(self):
        res = super(StockPicking, self).button_validate()        
        if self.picking_type_id.code == 'outgoing':
            misc_journal = self.env['account.journal'].sudo().search([('company_id', '=', self.company_id.id), ('name', 'ilike', 'miscellaneous %')], limit=1)
            print("####", misc_journal.id)
            if not misc_journal:
                raise UserError('Please define journal first.')
            move_dict = {
                'narration': '',
                'ref': self.name,
                'date': date.today(),
                'invoice_date': date.today(),
                'journal_id' : misc_journal.id,
            }
            line_ids = []
            total_amount = 0
            if self.move_lines:
                for mline in self.move_lines:
                    if mline.product_id.type == 'product':
                        debit_account = mline.product_id.property_account_expense_id
                        credit_account = mline.product_id.product_tmpl_id.categ_id.property_stock_account_output_categ_id
                        amount = mline.product_id.standard_price * mline.product_uom_qty
                        total_amount += amount
                        if debit_account: 
                            debit = amount if amount > 0.0 else 0.0
                            credit = -amount if amount < 0.0 else 0.0
                            debit_line = {
                                'partner_id': self.partner_id.id,
                                'account_id': debit_account.id,
                                'journal_id': misc_journal.id,
                                'date': date.today(),
                                'debit': debit,
                                'credit': credit,
                                'exclude_from_invoice_tab': True
                            }
                            line_ids.append(debit_line)
                        else:
                            raise ValidationError(_("Please define expense account for %s") % mline.product_id.name)   
                        if credit_account:
                            debit = -amount if amount < 0.0 else 0.0
                            credit = amount if amount > 0.0 else 0.0
                            credit_line = {
                                'partner_id': self.partner_id.id,
                                'account_id': credit_account.id,
                                'journal_id': misc_journal.id,
                                'date': date.today(),
                                'debit': debit,
                                'credit': credit,
                                'exclude_from_invoice_tab': True
                            }
                            line_ids.append(credit_line)
                        else:
                            raise ValidationError(_("Please define stock output account for %s") % mline.product_id.product_tmpl_id.categ_id.name)   
                    else:
                        raise ValidationError(_('Accounting Entry can be created for storable product only.'))

            move_dict['line_ids'] = [(0, 0, line_vals) for line_vals in line_ids]
            move = self.env['account.move'].create(move_dict)      
            self.write({'move_id': move.id})  
        return res


class Orderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    reorder_qty = fields.Float('Minimum Quantity', digits='Product Unit of Measure', required=True)
    product_min_qty = fields.Float(string="Reorder Quantity")

