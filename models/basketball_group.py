# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class BasketballGroup(models.Model):
    _name = 'basketball.group'
    _description = 'Basketbol Qrupu'
    _order = 'code_number, name'
    
    code = fields.Char(string="Qrup Kodu", readonly=True, default="Yeni")
    code_number = fields.Integer(string="Kod Nömrəsi", compute="_compute_code_number", store=True, help="Q-1 → 1, Q-10 → 10")
    name = fields.Char(string="Qrup Adı", required=True)
    description = fields.Text(string="Təsvir")
    
    # Qrup qrafiki
    schedule_ids = fields.One2many('basketball.group.schedule', 'group_id', string="Qrup Qrafiki")
    
    # Qrup üzvləri
    member_ids = fields.One2many('basketball.lesson.simple', 'group_id', string="Qrup Üzvləri")
    member_count = fields.Integer(string="Üzv Sayı", compute='_compute_member_count')
    
    # Aktivlik
    is_active = fields.Boolean(string="Aktiv", default=True)
    
    # Qeydlər
    notes = fields.Text(string="Qeydlər")
    
    @api.depends('member_ids')
    def _compute_member_count(self):
        for group in self:
            group.member_count = len(group.member_ids.filtered(lambda l: l.state in ['active', 'frozen']))
    
    @api.depends('code')
    def _compute_code_number(self):
        """Qrup kodundan rəqəmi çıxarır (Q-1 → 1, Q-10 → 10)"""
        for group in self:
            if group.code and group.code.startswith('Q-'):
                try:
                    group.code_number = int(group.code.split('-')[1])
                except (ValueError, IndexError):
                    group.code_number = 0
            else:
                group.code_number = 0
    
    @api.model
    def create(self, vals):
        # Qrup kodu: Q-1, Q-2, Q-3... formatında (sıralama ilə)
        # Mövcud qrupların sayını tap və 1 əlavə et
        group_count = self.search_count([])
        next_number = group_count + 1
        
        vals['code'] = f"Q-{next_number}"
        
        return super(BasketballGroup, self).create(vals)


class BasketballGroupSchedule(models.Model):
    _name = 'basketball.group.schedule'
    _description = 'Basketbol Qrup Qrafiki'
    _order = 'day_of_week, start_time'

    group_id = fields.Many2one('basketball.group', string="Qrup", required=True, ondelete='cascade')
    
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
    
    @api.model
    def create(self, vals):
        """Qrup qrafiki yaradılanda bütün üzvlərin qrafikini yenilə"""
        schedule = super(BasketballGroupSchedule, self).create(vals)
        schedule._sync_member_schedules()
        return schedule
    
    def write(self, vals):
        """Qrup qrafiki dəyişəndə bütün üzvlərin qrafikini yenilə"""
        result = super(BasketballGroupSchedule, self).write(vals)
        self._sync_member_schedules()
        return result
    
    def unlink(self):
        """Qrup qrafiki silinəndə üzvlərdən də sil"""
        for schedule in self:
            schedule._sync_member_schedules(delete=True)
        return super(BasketballGroupSchedule, self).unlink()
    
    def _sync_member_schedules(self, delete=False):
        """Qrup üzvlərinin qrafikini sinxronlaşdır"""
        self.ensure_one()
        
        # Bu qrupun bütün aktiv üzvlərini tap
        members = self.env['basketball.lesson.simple'].search([
            ('group_id', '=', self.group_id.id),
            ('state', 'in', ['active', 'frozen'])
        ])
        
        for member in members:
            if delete:
                # Qrup qrafiki silinir - üzvdən də sil
                member_schedule = member.schedule_ids.filtered(
                    lambda s: s.day_of_week == self.day_of_week and 
                             s.start_time == self.start_time and
                             s.end_time == self.end_time
                )
                if member_schedule:
                    member_schedule.unlink()
            else:
                # Qrup qrafiki yaradılır və ya dəyişir - üzvdə yenilə
                # Əvvəlcə eyni günə aid köhnə qrafiki tap
                existing_schedule = member.schedule_ids.filtered(
                    lambda s: s.day_of_week == self.day_of_week
                )
                
                if existing_schedule:
                    # Mövcud qrafiki yenilə
                    existing_schedule.write({
                        'start_time': self.start_time,
                        'end_time': self.end_time,
                        'is_active': self.is_active,
                        'notes': f"Qrup qrafiki: {self.group_id.name} (avtomatik yeniləndi)"
                    })
                else:
                    # Yeni qrafik yarat
                    self.env['basketball.lesson.schedule.simple'].create({
                        'lesson_id': member.id,
                        'day_of_week': self.day_of_week,
                        'start_time': self.start_time,
                        'end_time': self.end_time,
                        'is_active': self.is_active,
                        'notes': f"Qrup qrafiki: {self.group_id.name} (avtomatik əlavə edildi)"
                    })
