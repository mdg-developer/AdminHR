from odoo import fields, models, api, _

class FleetInsuranceType(models.Model):    
    _name = 'fleet.insurance.type'
    _description = 'Fleet Insurance Type'    

    name = fields.Char(string='Insurance Type', required=True)
    insurance_company = fields.Char(string='Insurance Company')
    contact_person = fields.Char(string='Contact Person')
    contact_phone = fields.Char(string='Contact Ph No')
    by = fields.Char(string='By')
    start_date = fields.Date(string='Start Date', required=True, copy=False)
    end_date = fields.Date(string='End Date', required=True, copy=False)

class FleetInsurance(models.Model):    
    _name = 'fleet.insurance'
    _description = 'Fleet Insurance'    

    name = fields.Char(string='Name', required=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle", required=True)
    insurance_type_id = fields.Many2one('fleet.insurance.type', string='Insurance Type', required=True)
    insurance_company = fields.Char(string='Insurance Company', related='insurance_type_id.insurance_company')
    contact_person = fields.Char(string='Contact Person', related='insurance_type_id.contact_person')
    contact_phone = fields.Char(string='Contact Ph No', related='insurance_type_id.contact_phone')
    by = fields.Char(string='By', related='insurance_type_id.by')
    start_date = fields.Date(string='Start Date', required=True, copy=False, related='insurance_type_id.start_date')
    end_date = fields.Date(string='End Date', required=True, copy=False, related='insurance_type_id.end_date')
    attachment_id = fields.Many2many('ir.attachment', 'fleet_insurance_doc_rel', 'fleet_insurance_doc_id', 'fleet_insurance_attach_id4',
                                     string="Attachment", help='You can attach the copy of your Letter') 
    
    
class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"
    _description = "Fleet Vehicle"


    fleet_insurance_ids = fields.One2many('fleet.insurance', 'vehicle_id', string='Fleet Insurance', copy=False)

    def return_action_to_open_fleet_insurance(self):
        """ This opens the xml view specified in xml_id for the current vehicle """
        self.ensure_one()
        xml_id = self.env.context.get('xml_id')
        if xml_id:
            res = self.env['ir.actions.act_window'].for_xml_id('fleet_insurance', xml_id)
            res.update(
                context=dict(self.env.context, default_vehicle_id=self.id, group_by=False),
                domain=[('vehicle_id', '=', self.id)]
            )
            return res
        return False