# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta

class BasketballDemoLesson(models.Model):
    _name = 'basketball.demo.lesson'
    _description = 'Basketbol Demo Dərs'
    _order = 'date desc, time'
    
    name = fields.Char(string="Demo Dərs №", readonly=True, default="Yeni")
    partner_id = fields.Many2one('res.partner', string="Müştəri", required=True)
    
    # Demoqrafik məlumatlar (müştəri ilə əlaqəli)
    partner_phone = fields.Char(related='partner_id.phone', string="Telefon")
    partner_email = fields.Char(related='partner_id.email', string="E-mail")
    
    # Tarix və vaxt
    date = fields.Date(string="Tarix", required=True, default=fields.Date.today)
    time = fields.Float(string="Vaxt", required=True, help="Məsələn 19.5 = 19:30")
    duration = fields.Float(string="Müddət (saat)", default=1.0)
    
    # Demo dərs məlumatları
    coach_id = fields.Many2one('res.partner', string="Məşqçi", domain=[('is_coach', '=', True)])
    # Vəziyyət
    state = fields.Selection([
        ('draft', 'Planlaşdırılıb'),
        ('confirmed', 'Təsdiqlənib'),
        ('done', 'Keçirilib'),
        ('cancelled', 'Ləğv edilib')
    ], string="Vəziyyət", default='draft')
    
    # Qeydlər
    notes = fields.Text(string="Qeydlər")
    
    # İştirak edilib?
    attended = fields.Boolean(string="İştirak edilib?", default=False)
    attendance_time = fields.Datetime(string="İştirak vaxtı")
    
    # Abunə oldu?
    converted = fields.Boolean(string="Abunə oldu?", default=False)
    conversion_date = fields.Date(string="Abunə tarixi")
    subscription_id = fields.Many2one('basketball.lesson.simple', string="Əlaqəli abunəlik")
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'Yeni') == 'Yeni':
            vals['name'] = self.env['ir.sequence'].next_by_code('basketball.demo.lesson') or 'BDL001'
        return super(BasketballDemoLesson, self).create(vals)
    
    def action_confirm(self):
        for demo in self:
            demo.state = 'confirmed'
    
    def action_mark_done(self):
        for demo in self:
            demo.state = 'done'
            if demo.attended:
                demo.attendance_time = fields.Datetime.now()
    
    def action_cancel(self):
        for demo in self:
            demo.state = 'cancelled'
    
    def action_reset_to_draft(self):
        for demo in self:
            demo.state = 'draft'
    
    def action_mark_converted(self):
        for demo in self:
            demo.converted = True
            demo.conversion_date = fields.Date.today()
            # Burada yeni abunəlik yaratma hissəsi də əlavə edilə bilər
            # self.env['basketball.lesson.simple'].create({...})
