from odoo import api, fields, models
import requests

class boom_sms_config(models.Model):        
    _name =  "boom.sms.config"
    
    mobile   =  fields.Char("Mobile") 
    template =  fields.Char("Template")
    auth_code =fields.Char("Authorization")

    def send_sms_check(self):
        headers = {
                   'Accept': 'application/json',
                   'Authorization' : 'Bearer {0}'.format(self.auth_code),
                   }
        url = 'https://boomsms.net/api/sms/json'
        data = {
                'from' : 'BOOM SMS',
                'text' : self.template,
                'to'   : self.mobile,
                }
        response = requests.post(url,json=data, headers=headers, timeout=60)
        response.raise_for_status()
        if response.status_code == 200:
            print ("success")
            
    def send_sms(self,mobile,template):
        auth = self.env['ir.config_parameter'].sudo().get_param('boom_sms_authorization')
        headers = {
                   'Accept': 'application/json',
                   'Authorization' : 'Bearer {0}'.format(auth),
                   }
        url = 'https://boomsms.net/api/sms/json'
        data = {
                'from' : 'BOOM SMS',
                'text' : template,
                'to'   : mobile,
                }
        response = requests.post(url,json=data, headers=headers, timeout=60)
        response.raise_for_status()
        if response.status_code == 200:
            print ("success")    
