# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, date
from odoo.exceptions import ValidationError
from odoo.tools import float_compare

class BasketballAttendanceCheck(models.Model):
    _name = 'basketball.attendance.check'
    _description = 'Basketbol Dərs İştirakı Yoxlaması'
    _order = 'create_date desc'
    
    name = fields.Char(string="Yoxlama Adı", readonly=True, default="Yeni")
    coach_id = fields.Many2one('res.partner', string="Məşqçi", required=True, domain=[('is_coach', '=', True)])
    group_id = fields.Many2one('basketball.group', string="Qrup", required=True)

    # Yoxlama təfərrüatları
    check_date = fields.Date(string="Yoxlama Tarixi", required=True, default=fields.Date.today)
    schedule_id = fields.Many2one('basketball.group.schedule', string="Dərs Vaxtı", required=False,
                                  domain="[('group_id', '=', group_id)]")
    day_of_week = fields.Selection(related='schedule_id.day_of_week', string="Həftənin Günü", store=True, readonly=True)
    
    # İştirakçılar
    attendee_ids = fields.One2many('basketball.attendance.check.line', 'attendance_check_id', string="İştirakçılar")
    attendee_count = fields.Integer(string="İştirakçı Sayı", compute='_compute_attendee_count')
    present_count = fields.Integer(string="İştirak Edənlərin Sayı", compute='_compute_present_count')

    demo_lesson_ids = fields.Many2many(
        'basketball.demo.lesson',
        string='Demo dərsləri',
        compute='_compute_demo_lessons',
        help='Eyni qrup və tarixdə planlaşdırılmış demo dərslər',
    )
    demo_lesson_count = fields.Integer(string='Demo dərs sayı', compute='_compute_demo_lessons')
    
    # Vəziyyət
    state = fields.Selection([
        ('draft', 'Təsdiqlənməyib'),
        ('confirmed', 'Təsdiqlənib'),
        ('cancelled', 'Ləğv Edilib')
    ], default='draft', string="Vəziyyət")
    
    # Qeydlər
    notes = fields.Text(string="Qeydlər")

    # helper: bu günün həftə günü (0..6) – user timezone-a görə
    def _today_weekday_str(self, check_date=None):
        d = check_date or fields.Date.context_today(self)
        # Python: 0 = B.e, 6 = Bazar
        return str(d.weekday())

    @api.onchange('group_id', 'check_date')
    def _onchange_group_date_set_schedule(self):
        if not self.group_id:
            self.schedule_id = False
            self.attendee_ids = [(5, 0, 0)]
            return
        weekday = self._today_weekday_str(self.check_date)
        sched = self.env['basketball.group.schedule'].search([
            ('group_id', '=', self.group_id.id),
            ('day_of_week', '=', weekday),
            ('is_active', '=', True),
        ], order='start_time asc', limit=1)

        self.schedule_id = sched.id if sched else False
        # >>> BU MÜTLƏQ OLSUN:
        self._onchange_schedule_id()

    
    @api.depends('attendee_ids')
    def _compute_attendee_count(self):
        for check in self:
            check.attendee_count = len(check.attendee_ids)
    
    @api.depends('attendee_ids.is_present')
    def _compute_present_count(self):
        for check in self:
            check.present_count = len(check.attendee_ids.filtered(lambda a: a.is_present))

    @api.depends('group_id', 'check_date')
    def _compute_demo_lessons(self):
        DemoLesson = self.env['basketball.demo.lesson']
        for check in self:
            if check.group_id and check.check_date:
                demos = DemoLesson.search([
                    ('group_id', '=', check.group_id.id),
                    ('date', '=', check.check_date),
                    ('state', '!=', 'cancelled'),
                ])
            else:
                demos = DemoLesson.browse()
            check.demo_lesson_ids = demos
            check.demo_lesson_count = len(demos)

    def _prepare_attendee_commands(self, commands):
        """Ensure partner_id is set for every attendee command before create/write."""
        if not commands:
            return commands

        lesson_model = self.env['basketball.lesson.simple']
        prepared = []

        for command in commands:
            if not isinstance(command, (tuple, list)) or len(command) < 1:
                prepared.append(command)
                continue

            code = command[0]

            if code not in (0, 1):  # Only create and update commands carry values
                prepared.append(command)
                continue

            data = command[2] or {}
            lesson_id = data.get('lesson_id')

            if lesson_id and not data.get('partner_id'):
                lesson = lesson_model.browse(lesson_id)
                if lesson and lesson.partner_id:
                    data = dict(data, partner_id=lesson.partner_id.id)

            if code == 0:
                prepared.append((0, 0, data))
            else:  # code == 1
                prepared.append((1, command[1], data))

        return prepared

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # 1) Ad (sequence) – yalnız boş, '/', ya da 'Yeni' olanda ver
            name = vals.get('name')
            if not name or name in ('/', 'Yeni'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'basketball.attendance.check'
                ) or 'BBAC001'

            # 2) schedule_id boşdursa avtomatik təyin et
            if vals.get('group_id') and not vals.get('schedule_id'):
                group = self.env['basketball.group'].browse(vals['group_id'])
                check_date = vals.get('check_date')
                if isinstance(check_date, str):
                    check_date = fields.Date.from_string(check_date)
                weekday = str((check_date or fields.Date.context_today(self)).weekday())
                sched = self.env['basketball.group.schedule'].search([
                    ('group_id', '=', group.id),
                    ('day_of_week', '=', weekday),
                    ('is_active', '=', True),
                ], order='start_time asc', limit=1)
                if sched:
                    vals['schedule_id'] = sched.id

            # 3) attendee_ids üçün partner_id-ni doldur (sənin mövcud util)
            if 'attendee_ids' in vals:
                vals['attendee_ids'] = self._prepare_attendee_commands(vals['attendee_ids'])
        return super().create(vals_list)

    def write(self, vals):
        if 'attendee_ids' in vals:
            vals['attendee_ids'] = self._prepare_attendee_commands(vals['attendee_ids'])
        return super().write(vals)
    
    @api.onchange('schedule_id')
    def _onchange_schedule_id(self):
        """Dərs qrafiki seçildikdə qrup üzvlərini əlavə et"""
        if self.group_id and self.schedule_id:
            # Clear previous attendees
            self.attendee_ids = [(5, 0, 0)]
            attendee_vals = []
            added_partner_ids = set()

            # Qrupun aktiv üzvlərini əldə et
            members = self.env['basketball.lesson.simple'].search([
                ('group_ids', 'in', self.group_id.id),
                ('state', 'in', ['active', 'frozen'])
            ])

            for member in members:
                if not member.partner_id:
                    continue
                existing_qr_attendance = False
                if self.schedule_id:
                    existing_qr_attendance = self.env['basketball.lesson.attendance.simple'].search([
                        ('lesson_id', '=', member.id),
                        ('schedule_id.day_of_week', '=', self.schedule_id.day_of_week),
                        ('attendance_date', '=', self.check_date),
                        ('qr_scanned', '=', True)
                    ], limit=1)

                attendee_vals.append((0, 0, {
                    'partner_id': member.partner_id.id,
                    'lesson_id': member.id,
                    'origin': 'member',
                    'is_present': False,
                    'qr_scanned': bool(existing_qr_attendance)
                }))
                added_partner_ids.add(member.partner_id.id)

            # Əvəzedici dərslər
            substitutes = self.env['basketball.lesson.substitute'].search([
                ('group_id', '=', self.group_id.id),
                ('substitute_date', '=', self.check_date),
                ('state', '=', 'draft')
            ])

            for substitute in substitutes:
                lesson = substitute.lesson_id
                partner = substitute.partner_id
                if not lesson or not partner:
                    continue
                if partner.id in added_partner_ids:
                    continue

                existing_qr_attendance = False
                if self.schedule_id:
                    existing_qr_attendance = self.env['basketball.lesson.attendance.simple'].search([
                        ('lesson_id', '=', lesson.id),
                        ('schedule_id.day_of_week', '=', self.schedule_id.day_of_week),
                        ('attendance_date', '=', self.check_date),
                        ('qr_scanned', '=', True)
                    ], limit=1)

                attendee_vals.append((0, 0, {
                    'partner_id': partner.id,
                    'lesson_id': lesson.id,
                    'origin': 'substitute',
                    'substitute_id': substitute.id,
                    'is_present': False,
                    'qr_scanned': bool(existing_qr_attendance),
                    'notes': substitute.note
                }))
                added_partner_ids.add(partner.id)

            if attendee_vals:
                self.attendee_ids = attendee_vals
    
    def action_confirm(self):
        """İştirak yoxlamasını təsdiqlə və iştirakları qeydə al"""
        for check in self:
            if check.state == 'draft':
                # İştirakları qeydə al
                for attendee in check.attendee_ids:
                    if attendee.is_present and attendee.lesson_id:
                        # Uyğun dərs qrafikini tap
                        schedule = attendee.lesson_id.schedule_ids.filtered(
                            lambda s: s.day_of_week == check.schedule_id.day_of_week
                        )
                        
                        if schedule:
                            # İştiraklara əlavə et
                            self.env['basketball.lesson.attendance.simple'].create({
                                'lesson_id': attendee.lesson_id.id,
                                'schedule_id': schedule[0].id,
                                'attendance_date': check.check_date,
                                'attendance_time': datetime.now(),
                                'qr_scanned': attendee.qr_scanned,  # QR məlumatını əlavə et
                                'notes': f"Yoxlama ilə əlavə edilib: {check.name}"
                            })
                
                check.state = 'confirmed'
    
    def action_cancel(self):
        """İştirak yoxlamasını ləğv et"""
        for check in self:
            check.state = 'cancelled'
    
    def action_draft(self):
        """İştirak yoxlamasını təsdiqlənməyib vəziyyətinə qaytar"""
        for check in self:
            check.state = 'draft'


class BasketballAttendanceCheckLine(models.Model):
    _name = 'basketball.attendance.check.line'
    _description = 'Basketbol Dərs İştirakı Yoxlaması Sətri'
    
    attendance_check_id = fields.Many2one('basketball.attendance.check', string="İştirak Yoxlaması", 
                                         required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string="İştirakçı", required=True)
    lesson_id = fields.Many2one('basketball.lesson.simple', string="Abunəlik", 
                               domain="[('partner_id', '=', partner_id), ('state', 'in', ['active', 'frozen'])]")
    origin = fields.Selection([
        ('member', 'Abunəlik'),
        ('substitute', 'Əvəzedici'),
    ], string="Mənbə", default='member', required=True)
    substitute_id = fields.Many2one('basketball.lesson.substitute', string="Əlaqəli Əvəzedici", ondelete='set null')
    # İştirak statusu
    is_present = fields.Boolean(string="İştirak edir", default=False)
    qr_scanned = fields.Boolean(string="QR Oxunub", default=False, help="Müştəri QR kod ilə giriş edib?")
    
    # Qeydlər
    notes = fields.Text(string="Qeydlər")
    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Partner seçildikdə uyğun dərsləri yüklə"""
        if self.partner_id and self.origin == 'member':
            # Find active lessons for this partner in the same group
            domain = [
                ('partner_id', '=', self.partner_id.id),
                ('state', 'in', ['active', 'frozen'])
            ]
            
            if self.attendance_check_id.group_id:
                domain.append(('group_id', '=', self.attendance_check_id.group_id.id))
                
            lessons = self.env['basketball.lesson.simple'].search(domain)
            
            if lessons:
                self.lesson_id = lessons[0].id
            else:
                self.lesson_id = False
        elif self.origin != 'member':
            return
    
    _sql_constraints = [
    ('unique_partner_attendance', 'unique(attendance_check_id, partner_id)', 
     'Hər müştəri bir yoxlamada yalnız bir dəfə ola bilər!')
    ]
    
    @api.constrains('partner_id', 'lesson_id')
    def _check_lesson_partner(self):
        """İştirakçı və dərsin uyğun olub olmadığını yoxlayır"""
        for record in self:
            if record.partner_id and record.lesson_id and record.lesson_id.partner_id != record.partner_id:
                raise ValidationError(f"Seçilmiş dərs {record.partner_id.name} üçün deyil. Xahiş edirik doğru dərsi seçin.")
            if record.origin == 'substitute' and not record.substitute_id:
                raise ValidationError("Əvəzedici sətirlər üçün əlaqəli əvəzedici qeyd mütləqdir.")