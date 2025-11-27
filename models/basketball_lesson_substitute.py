# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class BasketballLessonSubstitute(models.Model):
    _name = 'basketball.lesson.substitute'
    _description = 'Basketbol Əvəzedici Dərs'
    _order = 'substitute_date desc, id desc'

    lesson_id = fields.Many2one(
        'basketball.lesson.simple',
        string="Abunəlik",
        required=True,
        ondelete='cascade'
    )
    partner_id = fields.Many2one(
        'res.partner',
        string="Müştəri",
        related='lesson_id.partner_id',
        store=True,
        readonly=True
    )
    origin_group_ids = fields.Many2many(
        'basketball.group',
        string="Cari Qruplar",
        related='lesson_id.group_ids',
        readonly=True
    )
    group_id = fields.Many2one(
        'basketball.group',
        string="Əvəzedici Qrup",
        required=True,
        domain=[('is_active', '=', True)]
    )
    schedule_id = fields.Many2one(
        'basketball.group.schedule',
        string="Əvəzedici Qrafik",
        domain="[('group_id', '=', group_id), ('is_active', '=', True)]"
    )
    substitute_date = fields.Date(
        string="Tarix",
        required=True,
        default=fields.Date.context_today
    )
    day_of_week = fields.Selection(
        related='schedule_id.day_of_week',
        string="Həftənin Günü",
        store=True,
        readonly=True
    )
    note = fields.Text(string="Qeyd")
    state = fields.Selection(
        [
            ('draft', 'Planlaşdırılıb'),
            ('used', 'İstifadə Olundu'),
            ('cancelled', 'Ləğv Edilib')
        ],
        string="Vəziyyət",
        default='draft'
    )
    attendance_id = fields.Many2one(
        'basketball.lesson.attendance.simple',
        string="İştirak Qeydi",
        readonly=True
    )
    attendance_check_line_id = fields.Many2one(
        'basketball.attendance.check.line',
        string="İştirak Yoxlama Sətri",
        readonly=True
    )
    attendance_check_id = fields.Many2one(
        'basketball.attendance.check',
        string="İştirak Yoxlaması",
        related='attendance_check_line_id.attendance_check_id',
        store=True,
        readonly=True
    )

    @api.constrains('schedule_id', 'group_id')
    def _check_schedule_group(self):
        for rec in self:
            if rec.schedule_id and rec.schedule_id.group_id != rec.group_id:
                raise ValidationError("Seçilən qrafik seçilmiş əvəzedici qrupa aid deyil.")

    def action_mark_used(self, attendance, line):
        for rec in self:
            vals = {
                'state': 'used',
                'attendance_id': attendance.id if attendance else False,
                'attendance_check_line_id': line.id if line else False,
            }
            rec.write(vals)

    def action_reset_to_draft(self):
        for rec in self:
            rec.write({
                'state': 'draft',
                'attendance_id': False,
                'attendance_check_line_id': False,
            })

    def action_cancel(self):
        for rec in self:
            rec.write({'state': 'cancelled'})
