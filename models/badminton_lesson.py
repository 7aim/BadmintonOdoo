# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta

class BadmintonLesson(models.Model):
    _name = 'badminton.lesson'
    _description = 'Badminton Dərsi'
    _order = 'create_date desc'
    
    name = fields.Char(string="Dərs Nömrəsi", readonly=True, default="Yeni")
    partner_id = fields.Many2one('res.partner', string="Müştəri", required=True)
    filial_id = fields.Many2one('sport.filial', string="Filial", required=True)
    instructor_id = fields.Many2one('res.partner', string="Müəllim")
    
    # Dərs qrafiki
    schedule_ids = fields.One2many('badminton.lesson.schedule', 'lesson_id', string="Dərs Qrafiki")
    total_lessons = fields.Integer(string="Ümumi Dərs Sayı", compute='_compute_total_lessons', store=True)
    
    # Ödəniş məlumatları
    lesson_fee = fields.Float(string="Dərs Haqqı", required=True)
    total_amount = fields.Float(string="Ümumi Məbləğ", compute='_compute_total_amount', store=True)
    payment_method = fields.Selection([
        ('cash', 'Nəğd'),
        ('card', 'Kart'),
        ('bank_transfer', 'Bank Köçürməsi')
    ], string="Ödəniş Növü", required=True, default='cash')
    
    is_paid = fields.Boolean(string="Ödənib", default=False)
    payment_date = fields.Datetime(string="Ödəniş Tarixi")
    
    # Tarix məlumatları
    start_date = fields.Date(string="Başlama Tarixi", required=True)
    end_date = fields.Date(string="Bitmə Tarixi", required=True)
    
    # Vəziyyət
    state = fields.Selection([
        ('draft', 'Layihə'),
        ('confirmed', 'Təsdiqlənib'),
        ('active', 'Aktiv'),
        ('completed', 'Tamamlanıb'),
        ('cancelled', 'Ləğv Edilib')
    ], default='draft', string="Vəziyyət")
    
    # İştirak məlumatları
    attendance_ids = fields.One2many('badminton.lesson.attendance', 'lesson_id', string="İştiraklar")
    attended_lessons = fields.Integer(string="İştirak Etdiyi Dərslər", compute='_compute_attended_lessons')
    remaining_lessons = fields.Integer(string="Qalan Dərslər", compute='_compute_remaining_lessons')
    
    # Qeydlər
    notes = fields.Text(string="Qeydlər")
    
    @api.depends('schedule_ids')
    def _compute_total_lessons(self):
        for lesson in self:
            lesson.total_lessons = len(lesson.schedule_ids)
    
    @api.depends('total_lessons', 'lesson_fee')
    def _compute_total_amount(self):
        for lesson in self:
            lesson.total_amount = lesson.total_lessons * lesson.lesson_fee
    
    @api.depends('attendance_ids')
    def _compute_attended_lessons(self):
        for lesson in self:
            lesson.attended_lessons = len(lesson.attendance_ids.filtered('is_attended'))
    
    @api.depends('total_lessons', 'attended_lessons')
    def _compute_remaining_lessons(self):
        for lesson in self:
            lesson.remaining_lessons = lesson.total_lessons - lesson.attended_lessons
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'Yeni') == 'Yeni':
            vals['name'] = self.env['ir.sequence'].next_by_code('badminton.lesson') or 'BL001'
        return super(BadmintonLesson, self).create(vals)
    
    def action_confirm(self):
        """Dərsi təsdiqləyir və qrafik yaradır"""
        for lesson in self:
            if lesson.state == 'draft':
                lesson.state = 'confirmed'
                lesson._create_lesson_schedule()
    
    def action_activate(self):
        """Dərsi aktivləşdirir"""
        for lesson in self:
            if lesson.state == 'confirmed' and lesson.is_paid:
                lesson.state = 'active'
    
    def action_mark_paid(self):
        """Ödənişi qeyd edir"""
        for lesson in self:
            if lesson.state == 'confirmed' and not lesson.is_paid:
                lesson.is_paid = True
                lesson.payment_date = fields.Datetime.now()
                lesson.action_activate()
    
    def action_complete(self):
        """Dərsi tamamlayır"""
        for lesson in self:
            if lesson.state == 'active':
                lesson.state = 'completed'
    
    def action_cancel(self):
        """Dərsi ləğv edir"""
        for lesson in self:
            if lesson.state in ['draft', 'confirmed', 'active']:
                lesson.state = 'cancelled'
    
    def _create_lesson_schedule(self):
        """Dərs qrafiki yaradır"""
        # Bu funksiya manual olaraq dərs qrafiki yaratmaq üçün istifadə ediləcək
        # Hazırda boşdur, sonradan inkişaf etdiriləcək
        pass


class BadmintonLessonSchedule(models.Model):
    _name = 'badminton.lesson.schedule'
    _description = 'Badminton Dərs Qrafiki'
    _order = 'lesson_date, lesson_time'
    
    lesson_id = fields.Many2one('badminton.lesson', string="Dərs", required=True, ondelete='cascade')
    partner_id = fields.Many2one(related='lesson_id.partner_id', string="Müştəri", store=True)
    filial_id = fields.Many2one(related='lesson_id.filial_id', string="Filial", store=True)
    instructor_id = fields.Many2one(related='lesson_id.instructor_id', string="Müəllim", store=True)
    
    # Tarix və vaxt
    lesson_date = fields.Date(string="Dərs Tarixi", required=True)
    lesson_time = fields.Float(string="Dərs Saatı", required=True, help="Məsələn 19.5 = 19:30")
    duration = fields.Float(string="Müddət (saat)", default=1.0)
    
    # Həftənin günü
    day_of_week = fields.Selection([
        ('0', 'Bazar ertəsi'),
        ('1', 'Çərşənbə axşamı'),
        ('2', 'Çərşənbə'),
        ('3', 'Cümə axşamı'),
        ('4', 'Cümə'),
        ('5', 'Şənbə'),
        ('6', 'Bazar')
    ], string="Həftənin Günü", compute='_compute_day_of_week', store=True)
    
    # Vəziyyət
    is_completed = fields.Boolean(string="Tamamlanıb", default=False)
    is_cancelled = fields.Boolean(string="Ləğv Edilib", default=False)
    
    # İştirak
    attendance_id = fields.One2many('badminton.lesson.attendance', 'schedule_id', string="İştirak")
    
    # Qeydlər
    notes = fields.Text(string="Qeydlər")
    
    @api.depends('lesson_date')
    def _compute_day_of_week(self):
        for schedule in self:
            if schedule.lesson_date:
                schedule.day_of_week = str(schedule.lesson_date.weekday())
            else:
                schedule.day_of_week = False


class BadmintonLessonAttendance(models.Model):
    _name = 'badminton.lesson.attendance'
    _description = 'Badminton Dərs İştirakı'
    _order = 'attendance_date desc'
    
    lesson_id = fields.Many2one('badminton.lesson', string="Dərs", required=True)
    schedule_id = fields.Many2one('badminton.lesson.schedule', string="Dərs Qrafiki", required=True)
    partner_id = fields.Many2one(related='lesson_id.partner_id', string="Müştəri", store=True)
    
    # İştirak məlumatları
    attendance_date = fields.Date(string="İştirak Tarixi", default=fields.Date.today)
    attendance_time = fields.Datetime(string="İştirak Vaxtı", default=fields.Datetime.now)
    is_attended = fields.Boolean(string="İştirak Etdi", default=True)
    
    # QR scan məlumatları
    qr_scanned = fields.Boolean(string="QR Oxunub", default=False)
    scan_result = fields.Text(string="Scan Nəticəsi")
    
    # Qeydlər
    notes = fields.Text(string="Qeydlər")
    excuse_reason = fields.Text(string="Bəhanə Səbəbi")
