from odoo import fields, models, api, _


class ResUsers(models.Model):
    _inherit = 'res.users'

    product_category_ids = fields.Many2many('product.category', 'product_categroy_users_rel', 'user_id', 'categ_id',
                                   string='Categories')