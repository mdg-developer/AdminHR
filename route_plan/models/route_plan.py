from odoo import api, fields, models, _
from odoo.osv import expression
# from geopy.distance import geodesic
# from geopy.geocoders import Nominatim
# import haversine as hs
import requests, json 
from decimal import Decimal
from odoo.exceptions import UserError


class RoutePlan(models.Model):    
    _name = 'route.plan'    
    _description = 'Route Plan'
    _rec_name = 'code'
    _order = 'id desc'
    
    name = fields.Char(string='Name')
    code = fields.Char(string='Code')
    street = fields.Char(string='Street')
    departure_id = fields.Many2one('res.city',string='Departure')
    arrival_id = fields.Many2one('res.city',string='Arrival')
    ar1 = fields.Float(string='AR1')
    ar2 = fields.Float(string='AR2')
    distance = fields.Char(string='Distance (Km)')
    d1 = fields.Float(string='D1')
    d2 = fields.Float(string='D2')
    travel_time = fields.Char(string='Travel Time(hrs)')
    distance_loaded = fields.Char(string='Distance Loaded(km)')
    distance_empty = fields.Char(string='Distance Empty(km)')
    expense_ids = fields.One2many('route.expense','route_plan_id',string='Travel Info line')
    allowance_ids = fields.One2many('route.allowance','route_plan_id',string='Travel Info line')
    checkin_location = fields.Char(
        string="CheckIn Location"
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('approve', 'Approved'),
        ('decline', 'Rejected'),
        ('verify', 'Verified'),
        ('expired', 'Expired')
        ], string='Status', readonly=True, copy=False, index=True,default='draft',track_visibility='always')
    from_street = fields.Char(string='Search Departure')
    from_complete_address = fields.Char(string='Departure Address')
    to_street = fields.Char(string='Search Arrival')
    to_complete_address = fields.Char(string='Arrival Address')
    street2 = fields.Char()
    zip = fields.Char(change_default=True)
    city = fields.Char()
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict', domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict')
    type = fields.Selection(
        [('contact', 'Contact'),
         ('invoice', 'Invoice Address'),
         ('delivery', 'Delivery Address'),
         ('other', 'Other Address'),
         ("private", "Private Address"),
        ], string='Address Type',
        default='contact',
        help="Invoice & Delivery addresses are used in sales orders. Private addresses are only visible by authorized users.")
    #type_name = fields.Char('Type Name', compute='_compute_type_name')
    duration_days = fields.Float('Duration (Days)')
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, default=lambda self: self.env.company)
    branch_id = fields.Many2one('res.branch', string='Branch', domain="[('company_id', '=', company_id)]")
    fuel_liter = fields.Integer('Fuel (Liter)')
    commission_driver = fields.Integer('Commission (Driver)')
    commission_spare = fields.Integer('Commission (Spare)')
    approved_advance = fields.Float('Approved Advance')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    
    @api.model
    def create(self, vals):
        if 'company_id' in vals:
            code = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code('route.code')
            vals['code'] = code
        else:
            code = self.env['ir.sequence'].next_by_code('route.code')
            vals['code'] = code
        return super(RoutePlan, self).create(vals)

    def unlink(self):
        for rec in self:
            if rec.state not in ('draft','submit'):
                raise UserError(_('Record(s) can\'t be deleted'))
        return super(RoutePlan, self).unlink()

    def get_route(self):
        #geolocator = Nominatim(user_agent="Win Brother")
        url="https://maps.googleapis.com/maps/api/distancematrix/json?origins="
        distance = 0
        if self.from_complete_address and self.to_complete_address:
            try:
                url+= self.from_complete_address
                url += "&destinations=" + self.to_complete_address
                url += "&mode=driving&language=fr-FR&key=AIzaSyCjqCUo5CJJoN2mB281e_1vrc65mluV2E8"
                response = requests.get(url) 
                distance_val = duration_val = ""
                if response.status_code == 200:
                    data =  response.json()
                    
                    for record in data['rows']:
                        print(record['elements'][0])
                        value = record['elements'][0]
                        distance_val = value['distance']['text']                    
                        duration_val = value['duration']['text']
                        distance_val = distance_val.replace(" km", "")
                        duration_val = duration_val.replace("heures", "h")
                        distance = Decimal(distance_val.replace(',','.'))
                        if distance_val.isdigit():
                            for s in distance_val.split():
                                distance = s 
            except requests.HTTPError as error:
                raise UserError(_("Please check your departure and arrival address."))       
            self.write({'distance':distance,'distance_loaded':distance,'travel_time':duration_val})        
#             from_location = geolocator.geocode(self.from_complete_address)#(self.departure_id.state_id.name)
#             print((from_location.latitude, from_location.longitude))
#             to_location = geolocator.geocode(self.to_complete_address)#(self.arrival_id.state_id.name)
#             
#             distance = geodesic((from_location.latitude, from_location.longitude), (to_location.latitude, to_location.longitude)).km            
#             self.write({'distance':distance,'distance_loaded':distance}) 
    
    def get_view_google_map(self):
        #geolocator = Nominatim(user_agent="Win Brother")
        url = "https://www.google.com/maps/dir/?api=1"
        
        if self.from_complete_address:
            #from_location = geolocator.geocode(self.departure_id.state_id.name)
            
            url += "&origin=" + self.from_complete_address#str(from_location.latitude) + ',' + str(from_location.longitude)
            #url += "&origin=17.322071,96.466331"# + str(from_location.latitude) + ',' + str(from_location.longitude)
            
        if self.to_complete_address:
            
            #to_location =  geolocator.geocode(self.arrival_id.state_id.name)
            url += "&destination=" + self.to_complete_address #str(to_location.latitude) + ',' + str(to_location.longitude)
           
        url += "&travelmode=driving" 
        
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': url,
        }
        
#     @api.onchange('departure','arrival')
#     def _save_distance(self):
#         if self.departure and self.arrival:  
#             start =  (self.d1, -self.d2) 
#             end = (self.ar1, -self.ar2)
#              
#             self.distance = geodesic(start, end).km       
#         else:
#             self.distance = 0.0

    def action_submit(self):
        self.state = 'submit'
        if self.branch_id.manager_id:
            one_signal_values = {'employee_id': self.branch_id.manager_id.id,
                                'contents': _('ROUTE : To Approve Route Plan %s.') % (self.name),
                                'headings': _('WB B2B : APPROVAL ROUTE PLAN')}
            self.env['one.signal.notification.message'].create(one_signal_values)

    def action_approve(self):
        self.state = 'approve'
        self.start_date = fields.Date.today()

    def action_decline(self):
        self.state = 'decline'

    # def action_verify(self):
    #     self.state = 'verify'

    def action_expired(self):
        self.state = 'expired'
        self.end_date = fields.Date.today()
    
    def action_set_to_draft(self):
        self.state = 'draft'

    def name_get(self):
        self.browse(self.ids).read(['name', 'code'])
        return [(route.id, '%s%s' % (route.code and '[%s] ' % route.code or '', route.name)) for route in self]

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', '=ilike', name.split(' ')[0] + '%'), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        route_ids = self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
        return models.lazy_name_get(self.browse(route_ids).with_user(name_get_uid))
    

class RouteExpense(models.Model):    
    _name = 'route.expense'    
    _description = 'Route Expense'
    
    company_id = fields.Many2one('res.company', string='Company')
    product_id = fields.Many2one('product.product', string='Expense', domain=[('can_be_expensed', '=', True)])
    name = fields.Char(string='Description')
    amount = fields.Float(string='Standard Amount')
    remark = fields.Char(string='Remark')
    route_plan_id = fields.Many2one('route.plan',string='Route Plan')

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.name


class RouteAllowance(models.Model):    
    _name = 'route.allowance'    
    _description = 'Route Allowance'    
    
    name = fields.Char(string='Allowance')
    amount = fields.Float(string='Standard Amount')
    remark = fields.Char(string='Remark')
    route_plan_id = fields.Many2one('route.plan',string='Route Plan')
    
    

#     checkin_location = fields.Char(
#         string="CheckIn Location"  , compute='_save_location'
#     )
    
    
#     def button_create_to_map(self):
#         route_id = self._context.get('active_ids')
#         route_obj=self.env['route.plan'].search([('id', '=', route_id[0])])
#         if self.partner_latitude and self.partner_longitude:
#             arrival =  "("+str(self.partner_latitude)+","+"-"+str(self.partner_longitude)+")"
#             route_obj.arrival = arrival
# 
#     
#     def button_create_from_map(self):
#         route_id = self._context.get('active_ids')
#         route_obj=self.env['route.plan'].search([('id', '=', route_id[0])])
#         if self.partner_latitude and self.partner_longitude:
#             departur =  "("+str(self.partner_latitude)+","+"-"+str(self.partner_longitude)+")"
#             route_obj.departur = departur
#             newport_ri = (self.partner_latitude, -self.partner_longitude)
#             cleveland_oh =  (41.499498, -81.695391)
#             route_obj.distance = geodesic(newport_ri, cleveland_oh).km
#              
#             self.checkin_location = "https://www.google.com/maps/?q=%s,%s" % (
#                 self.partner_latitude,
#                 self.partner_longitude
    
    
#     def _save_location(self):
#         if self.partner_latitude and self.partner_longitude:
#             departur =  "("+str(self.partner_latitude)+","+"-"+str(self.partner_longitude)+")"
#             self.departur = departur
#             newport_ri = (self.partner_latitude, -self.partner_longitude)
#             cleveland_oh =  (41.499498, -81.695391)
#             print(departur)
#             self.distance = geodesic(newport_ri, cleveland_oh).km
#              
#             self.checkin_location = "https://www.google.com/maps/?q=%s,%s" % (
#                 self.partner_latitude,
#                 self.partner_longitude
#             )
#         else:
#             self.checkin_location = None