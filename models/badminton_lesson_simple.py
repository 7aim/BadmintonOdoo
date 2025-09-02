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
    group_id = fields.Many2one('badminton.group', string="Qrup")
    
    # Dərs Qrafiki (həftənin günləri)
    schedule_ids = fields.One2many('badminton.lesson.schedule.simple', 'lesson_id', string="Həftəlik Qrafik")
    
    # İştiraklar
    attendance_ids = fields.One2many('badminton.lesson.attendance.simple', 'lesson_id', string="Dərsə İştiraklar")
    total_attendances = fields.Integer(string="Ümumi İştirak", compute='_compute_total_attendances')
    
    # Ödəniş məlumatları
    lesson_fee = fields.Float(string="Aylıq Dərs Haqqı", compute='_compute_lesson_fee', store=True)
    
    @api.depends('group_id')
    def _compute_lesson_fee(self):
        """Qrupun haqqı və ya standart bir dəyər təyin edir"""
        for lesson in self:
            if lesson.group_id:
                # Burada qrupun dərs haqqını təyin edə bilərsiniz
                lesson.lesson_fee = 100.0  # Default dəyər, gələcəkdə qrup modelində saxlana bilər
            else:
                lesson.lesson_fee = 100.0  # Qrup olmadıqda standart dəyər

    # Tarix məlumatları
    start_date = fields.Date(string="Cari Dövr Başlama", required=True, default=fields.Date.today)
    end_date = fields.Date(string="Cari Dövr Bitmə", compute='_compute_end_date', store=True)
    
    # Abunəlik məlumatları
    total_months = fields.Integer(string="Ümumi Abunəlik (ay)", default=1)
    total_payments = fields.Float(string="Ümumi Ödəniş", compute='_compute_total_payments')
    
    # Vəziyyət
    state = fields.Selection([
        ('draft', 'Layihə'),
        ('active', 'Aktiv'),
        ('frozen', 'Dondurulmuş'),
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
    

    
    @api.depends('total_months', 'lesson_fee')
    def _compute_total_payments(self):
        for lesson in self:
            lesson.total_payments = lesson.total_months * lesson.lesson_fee
    
    @api.depends('attendance_ids')
    def _compute_total_attendances(self):
        for lesson in self:
            lesson.total_attendances = len(lesson.attendance_ids)
    
    @api.onchange('group_id')
    def _onchange_group_id(self):
        """Qrup seçildikdə avtomatik qrafik əlavə et"""
        if self.group_id:
            # Əvvəlki qrafiki sil
            self.schedule_ids = [(5, 0, 0)]
            
            # Qrupun qrafikini kopyala
            schedule_vals = []
            for group_schedule in self.group_id.schedule_ids:
                if group_schedule.is_active:
                    schedule_vals.append((0, 0, {
                        'day_of_week': group_schedule.day_of_week,
                        'start_time': group_schedule.start_time,
                        'end_time': group_schedule.end_time,
                        'is_active': True,
                        'notes': f"Qrup qrafiki: {self.group_id.name}"
                    }))
            
            if schedule_vals:
                self.schedule_ids = schedule_vals
    
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
                # Başlama tarixi sabit qalır, yalnız end_date uzanır
                lesson.end_date = lesson.end_date + timedelta(days=30)
                lesson.total_months += 1
                lesson.payment_date = fields.Datetime.now()
                
                # Yeni sequence nömrəsi ver (isteğe bağlı)
                lesson.name = f"{lesson.name.split('-')[0]}-R{lesson.total_months}"
    
    def action_complete(self):
        """Dərsi tamamla"""
        for lesson in self:
            if lesson.state == 'active':
                lesson.state = 'completed'
    
    def action_freeze(self):
        """Abunəliyi dondur"""
        for lesson in self:
            if lesson.state == 'active':
                lesson.state = 'frozen'
    
    def action_unfreeze(self):
        """Abunəliyi aktiv et"""
        for lesson in self:
            if lesson.state == 'frozen':
                lesson.state = 'active'
    
    def action_cancel(self):
        """Dərsi ləğv et"""
        for lesson in self:
            if lesson.state in ['draft', 'active', 'frozen']:
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


class BadmintonLessonAttendanceSimple(models.Model):
    _name = 'badminton.lesson.attendance.simple'
    _description = 'Badminton Dərs İştirakı (Sadə)'
    _order = 'attendance_date desc, attendance_time desc'
    
    lesson_id = fields.Many2one('badminton.lesson.simple', string="Dərs Abunəliyi", required=True)
    schedule_id = fields.Many2one('badminton.lesson.schedule.simple', string="Dərs Qrafiki", required=True)
    partner_id = fields.Many2one(related='lesson_id.partner_id', string="Müştəri", store=True)
    
    # İştirak məlumatları
    attendance_date = fields.Date(string="İştirak Tarixi", default=fields.Date.today)
    attendance_time = fields.Datetime(string="İştirak Vaxtı", default=fields.Datetime.now)
    
    # QR scan məlumatları  
    qr_scanned = fields.Boolean(string="QR ilə Giriş", default=True)
    scan_result = fields.Text(string="QR Nəticəsi")
    
    # Qeydlər
    notes = fields.Text(string="Qeydlər")