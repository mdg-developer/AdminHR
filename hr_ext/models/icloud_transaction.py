from odoo import models, fields, api, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from datetime import datetime, timedelta

class IcloudTransaction(models.Model):
    _name = 'iclock.transaction'
    _description = "Iclock Transaction"    
    
    emp_code = fields.Char('Badge ID')
    punch_time = fields.Datetime('Punch Time') 
    punch_state =  fields.Char('Punch State')
    verify_type =  fields.Char('Verify Type')
    work_code = fields.Char('Work Code')    
    terminal_sn = fields.Char('Terminal Sn')
    terminal_alias = fields.Char('Terminal Alias')
    area_alias = fields.Char('Area Alias')
    longitude = fields.Float('Longitude')
    latitude = fields.Float('Latitude')
    gps_location = fields.Float('GPS Location')
    mobile = fields.Char('Mobile')
    source = fields.Integer('Source')
    purpose = fields.Integer('Purpose')
    crc = fields.Char('CRC')
    is_attendance = fields.Integer('isAttendance')
    reserved = fields.Char('Reserved')
    upload_time = fields.Datetime('Upload time')
    sync_status = fields.Integer('Sync status')
    sync_time = fields.Datetime('Sync Time')
    is_mark = fields.Integer('isMark')
    temperature = fields.Float('Temperature')
    emp_id  = fields.Integer('Emp id')
    terminal_id  = fields.Integer('Terminal ID')
    move_to_raw = fields.Boolean("Move To Raw",default=False)
    
    def run_move_to_raw(self):
        iclouds = self.env['iclock.transaction'].search([('move_to_raw','=',False)])        
        raw_obj = self.env['hr.attendance.raw']
        
        self.env.cr.execute("""select i.id,emp_code,h.name as emp_name,c.name as company_name,(i.punch_time at time zone 'Asia/Rangoon')::timestamp without time zone as punch_time_moved0 
        from iclock_transaction i left join hr_employee h on h.fingerprint_id=i.emp_code
        left join res_company c on c.id=h.company_id
        where (i.move_to_raw is null or i.move_to_raw = 'f') and i.punch_time is not null order by h.id,i.punch_time limit 5000
        """)
        result = self.env.cr.dictfetchall()
        move_raws = []
        if result:
            i = 0    
            for cloud in result:
#                 if cloud['id'] in [73232,86488,83042,71964]:
#                     print("hello")
                emp_name = company_name = ''
                
                i += 1                
                data = {
                        'fingerprint_id':cloud['emp_code'],
                        'employee_name' : cloud['emp_name'],
                        'attendance_datetime':str(cloud['punch_time_moved0']),
                        'create_date' : cloud['punch_time_moved0'],
                        'company': cloud['company_name'],
                        }
                raws = self.env['hr.attendance.raw'].search([('fingerprint_id','=',cloud['emp_code']),('attendance_datetime','=',str(cloud['punch_time_moved0']))])
                print("raw >>>>> %s ",i , datetime.now())
                if not raws:
                    self.env.cr.execute("""insert into hr_attendance_raw (fingerprint_id,employee_name,attendance_datetime,create_date,company) 
                            values(%s,%s,%s,%s,%s)""", 
                               (cloud['emp_code'], cloud['emp_name'], cloud['punch_time_moved0'],cloud['punch_time_moved0'], cloud['company_name'],))
                
                move_raws.append(cloud['id'])
            if len(move_raws) > 0:
                
                for sync in  self.browse(move_raws):
                    sync.write({'move_to_raw':True})   
            
    