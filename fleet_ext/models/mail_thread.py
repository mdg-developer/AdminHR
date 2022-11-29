from odoo import api, fields, models, tools, _

class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'
    
    def unlink(self):
        """ Override unlink to delete messages and followers. This cannot be
        cascaded, because link is done through (res_model, res_id). """
        if not self:
            return True
        context = (self._context or {})
        print("context123>>>",context)
        if self._name == 'hr.employee':
            return True
        self.env['mail.message'].search([('model', '=', self._name), ('res_id', 'in', self.ids), ('message_type', '!=', 'user_notification')]).unlink()
        res = super(MailThread, self).unlink()
        self.env['mail.followers'].sudo().search(
            [('res_model', '=', self._name), ('res_id', 'in', self.ids)]
        ).unlink()
        return res