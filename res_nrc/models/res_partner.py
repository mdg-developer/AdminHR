from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _default_nrc_type(self):
        return self.env['res.nrc.type'].search([('name', '=', 'N')]).id

    @api.model
    def _default_nrc_region_code(self):
        return self.env['res.nrc.region'].search([('name', '=', '12')]).id

    @api.onchange('nrc_region_code')
    def _onchange_nrc_region_code(self):
        if self.nrc_region_code and self.nrc_prefix:
            if self.nrc_region_code != self.nrc_prefix.nrc_region:
                self.nrc_prefix = False

    @api.onchange('nrc_region_code', 'nrc_region_code', 'nrc_type', 'nrc_number')
    def _onchange_nrc_number(self):
        if self.nrc_region_code and self.nrc_prefix and self.nrc_type and self.nrc_number:
            self.nrc = self.nrc_region_code.name + '/' + self.nrc_prefix.name + '(' + self.nrc_type.name + ')' + str(self.nrc_number)

    nrc_region_code = fields.Many2one("res.nrc.region", string='Region', default=_default_nrc_region_code)
    nrc_prefix = fields.Many2one("res.nrc.prefix", string='Prefix')
    nrc_type = fields.Many2one("res.nrc.type", string='Type', default=_default_nrc_type)
    nrc_number = fields.Char('NRC Entry', size=6)
    nrc = fields.Char(string='NRC', store=True)

    @api.model
    def create(self, val):
        if val.get('nrc_region_code') and val.get('nrc_prefix') and val.get('nrc_type') and val.get('nrc_number'):
            nrc_region_code = self.env['res.nrc.region'].browse(val['nrc_region_code'])
            nrc_prefix = self.env['res.nrc.prefix'].browse(val['nrc_prefix'])
            nrc_type = self.env['res.nrc.type'].browse(val['nrc_type'])
            val['nrc'] = nrc_region_code.name + '/' + nrc_prefix.name + '(' + nrc_type.name + ')' + str(val['nrc_number'])
        return super(ResPartner, self).create(val)


    def write(self, val):
        if val.get('nrc_region_code') or val.get('nrc_prefix') or val.get('nrc_type') or val.get('nrc_number'):
            val_nrc_region_code = val['nrc_region_code'] if val.get('nrc_region_code') else self.nrc_region_code.id
            val_nrc_prefix = val['nrc_prefix'] if val.get('nrc_prefix') else self.nrc_prefix.id
            val_nrc_type = val['nrc_type'] if val.get('nrc_type') else self.nrc_type.id
            val_nrc_number = val['nrc_number'] if val.get('nrc_number') else self.nrc_number
            nrc_region_code = self.env['res.nrc.region'].browse(val_nrc_region_code)
            nrc_prefix = self.env['res.nrc.prefix'].browse(val_nrc_prefix)
            nrc_type = self.env['res.nrc.type'].browse(val_nrc_type)
            val['nrc'] = nrc_region_code.name + '/' + nrc_prefix.name + '(' + nrc_type.name + ')' + str(val_nrc_number)
            print(val)
        return super(ResPartner, self).write(val)

    @api.constrains('nrc')
    def check_duplicate_nrc(self):
        for partner in self:
            if partner.nrc:
                domain = [
                    ('id', '!=', partner.id),
                    ('nrc', '=', partner.nrc)]
                if self.with_context(active_test=False).search_count(domain) > 0:
                    raise ValidationError(_('Your NRC number already exists!'))



