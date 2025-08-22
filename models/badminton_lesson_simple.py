# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta

class BadmintonLessonSimple(models.Model):
    _name = 'badminton.lesson.simple'
    _description = 'Badminton Dərsi (Sadə)'
    _order = 'create_date desc'
    
    name = fields.Char(string="Dərs Nömrəsi", readonly=True, default="Yeni")
    partner_id = fields.Many2one('res.partner', string="Müştəri", required=True)
    
    # Dərs Qrafiki (həftənin günləri)
    schedule_ids = fields.One2many('badminton.lesson.schedule.simple', 'lesson_id', string="Həftəlik Qrafik")
    
    # Ödəniş məlumatları
    lesson_fee = fields.Float(string="Aylıq Dərs Haqqı", required=True, default=50.0)
    
    # Tarix məlumatları (1 aylıq)
    start_date = fields.Date(string="Başlama Tarixi", default=fields.Date.today, required=True)
    end_date = fields.Date(string="Bitmə Tarixi", compute='_compute_end_date', store=True)
    
    # Vəziyyət
    state = fields.Selection([
        ('draft', 'Layihə'),
        ('active', 'Aktiv'),
        ('completed', 'Tamamlanıb'),
        ('cancelled', 'Ləğv Edilib')
    ], default='draft', string="Vəziyyət")
    
    # Ödəniş tarixi
    payment_date = fields.Datetime(string="Ödəniş Tarixi")
    
    # Qeydlər
    notes = fields.Text(string="Qeydlər")
    
    @api.depends('start_date')
    def _compute_end_date(self):
        for lesson in self:
            if lesson.start_date:
                # 1 ay əlavə et
                lesson.end_date = lesson.start_date + timedelta(days=30)
            else:
                lesson.end_date = False
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'Yeni') == 'Yeni':
            vals['name'] = self.env['ir.sequence'].next_by_code('badminton.lesson.simple') or 'BLS001'
        return super(BadmintonLessonSimple, self).create(vals)
    
    def action_confirm(self):
        """Dərsi təsdiqlə və ödənişi qəbul et"""
        for lesson in self:
            if lesson.state == 'draft':
                lesson.state = 'active'
                lesson.payment_date = fields.Datetime.now()
    
    def action_renew(self):
        """Abunəliyi 1 ay uzat və yenidən ödəniş qəbul et"""
        for lesson in self:
            if lesson.state == 'active':
                # Tarixi uzat
                lesson.start_date = lesson.end_date
                lesson.end_date = lesson.end_date + timedelta(days=30)
                lesson.payment_date = fields.Datetime.now()
                
                # Yeni sequence nömrəsi ver
                lesson.name = self.env['ir.sequence'].next_by_code('badminton.lesson.simple') or f"{lesson.name}-R"
    
    def action_complete(self):
        """Dərsi tamamla"""
        for lesson in self:
            if lesson.state == 'active':
                lesson.state = 'completed'
    
    def action_cancel(self):
        """Dərsi ləğv et"""
        for lesson in self:
            if lesson.state in ['draft', 'active']:
                lesson.state = 'cancelled'


class BadmintonLessonScheduleSimple(models.Model):
    _name = 'badminton.lesson.schedule.simple'
    _description = 'Həftəlik Dərs Qrafiki (Sadə)'
    _order = 'day_of_week, start_time'
    
    lesson_id = fields.Many2one('badminton.lesson.simple', string="Dərs", required=True, ondelete='cascade')
    partner_id = fields.Many2one(related='lesson_id.partner_id', string="Müştəri", store=True)
    
    # Həftənin günü
    day_of_week = fields.Selection([
        ('0', 'Bazar ertəsi'),
        ('1', 'Çərşənbə axşamı'),
        ('2', 'Çərşənbə'),
        ('3', 'Cümə axşamı'),
        ('4', 'Cümə'),
        ('5', 'Şənbə'),
        ('6', 'Bazar')
    ], string="Həftənin Günü", required=True)
    
    # Vaxt aralığı
    start_time = fields.Float(string="Başlama Vaxtı", required=True, help="Məsələn 19.5 = 19:30")
    end_time = fields.Float(string="Bitmə Vaxtı", required=True, help="Məsələn 20.5 = 20:30")
    
    # Aktivlik
    is_active = fields.Boolean(string="Aktiv", default=True)
    
    # Qeydlər
    notes = fields.Text(string="Qeydlər")
    
    @api.constrains('start_time', 'end_time')
    def _check_time_range(self):
        for schedule in self:
            if schedule.start_time >= schedule.end_time:
                raise ValidationError("Başlama vaxtı bitmə vaxtından kiçik olmalıdır!")
            if schedule.start_time < 0 or schedule.start_time > 24:
                raise ValidationError("Başlama vaxtı 0-24 aralığında olmalıdır!")
            if schedule.end_time < 0 or schedule.end_time > 24:
                raise ValidationError("Bitmə vaxtı 0-24 aralığında olmalıdır!")
