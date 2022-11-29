from odoo import api, fields, models


class TrainingCost(models.Model):
    _name = "training.cost"

    name = fields.Char(
          string='Name',
          required=True
          )
    cost = fields.Float(string='Cost')