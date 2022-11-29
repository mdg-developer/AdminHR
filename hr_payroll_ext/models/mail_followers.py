from odoo import api, fields, models


class Followers(models.Model):
    _inherit = 'mail.followers'
   
    _sql_constraints = [
        ('mail_followers_res_partner_res_model_id_uniq', 'Check(1=1)', 'Error, a partner cannot follow twice the same object.'),
        ('mail_followers_res_channel_res_model_id_uniq', 'Check(1=1)', 'Error, a channel cannot follow twice the same object.'),
        ('partner_xor_channel', 'Check(1=1)', 'Error: A follower must be either a partner or a channel (but not both).')
    ]
