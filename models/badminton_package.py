# -*- coding: utf-8 -*-

from odoo import models, fields, api

class BadmintonPackage(models.Model):
    _name = 'badminton.package'
    _description = 'Badminton Paketləri'
    _order = 'name'

    name = fields.Char(string="Paket Adı", required=True)
    price = fields.Float(string="Qiymət", required=True)
    student_price = fields.Float(string="Tələbə Qiyməti", required=True)
    balance_count = fields.Integer(string="Badminton Balans Sayı", required=True, default=1)
    
    active = fields.Boolean(string="Aktiv", default=True)