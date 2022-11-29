from odoo import api, fields, models, _


class Trailer(models.Model):
    _name = 'trip.trailer'

    name = fields.Char(string='Name', required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    branch_id = fields.Many2one('res.branch', string='Branch')
    trailer_no = fields.Char('Trailer No')
    axal_type = fields.Char('Axal Type')
    trailer_type = fields.Many2one('trailer.type', string='Trailer Type')
    chassis = fields.Char('Chassis')
    size = fields.Char('Size')
    model = fields.Char('Model')
    ton = fields.Char('Ton')
    made = fields.Char('Made')
    photo = fields.Binary('Photo')
    photo_filename = fields.Char("Photo Name")
    remark = fields.Text('Remark')


class TrailerType(models.Model):
    _name = 'trailer.type'

    name = fields.Char('Name', required=True)
