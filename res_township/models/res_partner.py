from odoo import api, fields, models

ADDRESS_FIELDS = ('street', 'street2', 'zip', 'city', 'township_id', 'state_id', 'country_id')

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    def _default_country_id(self):
        country_id = False

        country = self.env['res.country'].search([('code', '=', 'MM')])
        if country:
            country_id = country.id
        return country_id
    
    township_id = fields.Many2one("res.township", string='Township')
    city_id = fields.Many2one("res.city", string='City')   
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict', default=_default_country_id)
    
    @api.model
    def _address_fields(self):
        """Returns the list of address fields that are synced from the parent."""
        return list(ADDRESS_FIELDS)
    
    @api.model
    def _get_default_address_format(self):
        return "%(street)s\n%(street2)s\n%(township_name)s\n%(city)s %(state_name)s %(zip)s\n%(country_name)s"
    
    def _display_address(self, without_company=False):

        '''
        The purpose of this function is to build and return an address formatted accordingly to the
        standards of the country where it belongs.

        :param address: browse record of the res.partner to format
        :returns: the address formatted in a display that fit its country habits (or the default ones
            if not country is specified)
        :rtype: string
        '''
        # get the information that will be injected into the display format
        # get the address format
        address_format = self._get_address_format()
        args = {
            'city_code': self.city_id.code or '',
            'city_name': self.city_id.name or '',
            'township_code': self.township_id.code or '',
            'township_name': self.township_id.name or '',
            'state_code': self.state_id.code or '',
            'state_name': self.state_id.name or '',
            'country_code': self.country_id.code or '',
            'country_name': self._get_country_name(),
            'company_name': self.commercial_company_name or '',
        }
        for field in self._formatting_address_fields():
            args[field] = getattr(self, field) or ''
        if without_company:
            args['company_name'] = ''
        elif self.commercial_company_name:
            address_format = '%(company_name)s\n' + address_format
        return address_format % args
    
    def _display_address_depends(self):
        # field dependencies of method _display_address()
        return self._formatting_address_fields() + [
            'country_id.address_format', 'country_id.code', 'country_id.name',
            'company_name', 'state_id.code', 'state_id.name', 'city_id.code', 'city_id.name',
            'township_id.code', 'township_id.name',
        ]           
