# -*- coding: utf-8 -*-

from odoo import models, fields, api

class BasketballPackage(models.Model):
    _name = 'basketball.package'
    _description = 'Basketbol Paketləri'
    _order = 'name'

    name = fields.Char(string="Paket Adı", required=True)
    adult_price = fields.Float(string="Böyük Qiyməti", required=True)
    child_price = fields.Float(string="Kiçik Qiyməti", required=True)
    
    # Endirim
    discount_percent = fields.Float(string="Endirim Faizi (%)", default=0.0)
    
    active = fields.Boolean(string="Aktiv", default=True)
