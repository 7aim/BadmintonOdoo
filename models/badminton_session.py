# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import json

class BadmintonSession(models.Model):
    _name = 'badminton.session'
    _description = 'Badminton Oyun Sessiyası'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # Mail funksiyaları üçün
    _order = 'start_time desc'

    name = fields.Char(string="Sessiya Nömrəsi", readonly=True, default="Yeni")
    partner_id = fields.Many2one('res.partner', string="Müştəri", required=True)
    start_time = fields.Datetime(string="Başlama Vaxtı", readonly=True)
    end_time = fields.Datetime(string="Bitmə Vaxtı")
    duration_hours = fields.Float(string="Müddət (saat)", default=1.0)
    
    state = fields.Selection([
        ('draft', 'Gözləmədə'),
        ('active', 'Aktiv'),
        ('extended', 'Uzadılıb'),
        ('completed', 'Tamamlanıb'),
        ('cancelled', 'Ləğv edilib')
    ], string="Vəziyyət", default='draft')
    
    qr_scanned = fields.Boolean(string="QR Oxunub", default=False)
    extended_time = fields.Float(string="Əlavə Vaxt (saat)", default=0.0)
    notes = fields.Text(string="Qeydlər")
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'Yeni') == 'Yeni':
            vals['name'] = self.env['ir.sequence'].next_by_code('badminton.session') or 'BS001'
        return super(BadmintonSession, self).create(vals)
    
    # Manual sessiya başlatma funksiyası (QR oxuyucu pəncərəsi üçün)
    def start_session_manual(self):
        """Manual olaraq sessiya başlat"""
        if self.partner_id:
            # Müştərinin badminton balansını yoxla
            customer_balance = self.partner_id.badminton_balance or 0
            required_hours = self.duration_hours
            
            if customer_balance < required_hours:
                raise ValidationError(f'{self.partner_id.name} müştərisinin kifayət qədər balansı yoxdur! '
                                     f'Mövcud balans: {customer_balance} saat, Tələb olunan: {required_hours} saat')
            
            # Aktiv sessiya var mı yoxla
            active_session = self.search([
                ('partner_id', '=', self.partner_id.id),
                ('state', 'in', ['active', 'extended'])
            ], limit=1)
            
            if active_session:
                raise ValidationError(f'{self.partner_id.name} üçün artıq aktiv sessiya var!')
            
            # Balansdan çıx
            new_balance = customer_balance - required_hours
            self.partner_id.badminton_balance = new_balance
            
            # Balans tarixçəsi yarat
            self.env['badminton.balance.history'].create({
                'partner_id': self.partner_id.id,
                'session_id': self.id,
                'hours_used': required_hours,
                'balance_before': customer_balance,
                'balance_after': new_balance,
                'transaction_type': 'usage',
                'description': f"Manual sessiya başladıldı: {self.name}"
            })
            
            # Sessiya məlumatlarını yenilə
            self.start_time = fields.Datetime.now()
            self.end_time = fields.Datetime.now() + timedelta(hours=self.duration_hours)
            self.state = 'active'
            self.qr_scanned = False  # Manual başladıldığı üçün
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f'{self.partner_id.name} üçün sessiya başladıldı! Köhnə balans: {customer_balance}, Yeni balans: {new_balance} saat',
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            raise ValidationError('Zəhmət olmasa müştəri seçin!')
    
    # QR Kod oxuma funksiyası
    def start_session_by_qr(self, qr_data):
        """QR kod oxunduqda sessiyanı başlat"""
        try:
            # QR koddan müştəri məlumatlarını çıxart
            if "ID:" in qr_data and "NAME:" in qr_data:
                partner_id = int(qr_data.split("ID:")[1].split("-")[0])
                partner = self.env['res.partner'].browse(partner_id)
                
                if partner.exists():
                    # Müştərinin badminton balansını yoxla
                    customer_balance = partner.badminton_balance or 0
                    required_hours = 1.0  # Standart 1 saat
                    
                    if customer_balance < required_hours:
                        return {
                            'status': 'error',
                            'message': f'{partner.name} müştərisinin kifayət qədər balansı yoxdur! '
                                     f'Mövcud balans: {customer_balance} saat'
                        }
                    
                    # Aktiv sessiya var mı yoxla
                    active_session = self.search([
                        ('partner_id', '=', partner_id),
                        ('state', 'in', ['active', 'extended'])
                    ], limit=1)
                    
                    if active_session:
                        return {
                            'status': 'error',
                            'message': f'{partner.name} üçün artıq aktiv sessiya var!'
                        }
                    
                    # Balansdan çıx
                    new_balance = customer_balance - required_hours
                    partner.badminton_balance = new_balance
                    
                    # Yeni sessiya yarat
                    session = self.create({
                        'partner_id': partner_id,
                        'start_time': fields.Datetime.now(),
                        'end_time': fields.Datetime.now() + timedelta(hours=1),
                        'state': 'active',
                        'qr_scanned': True
                    })
                    
                    # Balans tarixçəsi yarat
                    self.env['badminton.balance.history'].create({
                        'partner_id': partner_id,
                        'session_id': session.id,
                        'hours_used': required_hours,
                        'balance_before': customer_balance,
                        'balance_after': new_balance,
                        'transaction_type': 'usage',
                        'description': f"QR kod ilə sessiya başladıldı: {session.name}"
                    })
                    
                    return {
                        'status': 'success',
                        'message': f'{partner.name} üçün sessiya başladıldı! Köhnə balans: {customer_balance}, Yeni balans: {new_balance} saat',
                        'session_id': session.id
                    }
                else:
                    return {
                        'status': 'error',
                        'message': 'Müştəri tapılmadı!'
                    }
            else:
                return {
                    'status': 'error',
                    'message': 'QR kod formatı səhvdir!'
                }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Xəta baş verdi: {str(e)}'
            }
    
    # Sessiya uzatma funksiyası
    def extend_session(self, additional_hours=1.0):
        """Sessiyanı uzat və balansdan çıx"""
        for session in self:
            if session.state in ['active', 'extended']:
                # Müştərinin balansını yoxla
                current_balance = session.partner_id.badminton_balance or 0
                
                if current_balance < additional_hours:
                    raise ValidationError(f'{session.partner_id.name} müştərisinin kifayət qədər balansı yoxdur! '
                                         f'Mövcud balans: {current_balance} saat, '
                                         f'Uzatmaq üçün tələb olunan: {additional_hours} saat')
                
                # Balansdan çıx
                new_balance = current_balance - additional_hours
                session.partner_id.badminton_balance = new_balance
                
                # Balans tarixçəsi yarat
                self.env['badminton.balance.history'].create({
                    'partner_id': session.partner_id.id,
                    'session_id': session.id,
                    'hours_used': additional_hours,
                    'balance_before': current_balance,
                    'balance_after': new_balance,
                    'transaction_type': 'extension',
                    'description': f"Sessiya uzadıldı: {session.name} (+{additional_hours} saat)"
                })
                
                session.extended_time += additional_hours
                session.end_time = session.end_time + timedelta(hours=additional_hours)
                session.state = 'extended'
                session.notes = f"Sessiya {additional_hours} saat uzadıldı. Balans: {current_balance} → {new_balance} saat"
    
    def action_extend_session_wizard(self):
        """Sessiya uzatma wizard-ini aç"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sessiyanı Uzat',
            'res_model': 'badminton.session.extend.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_session_id': self.id,
            }
        }
    
    # Sessiyanı tamamla
    def complete_session(self):
        """Sessiyanı tamamla (balans artıq çıxılıb)"""
        for session in self:
            if session.state in ['active', 'extended']:
                session.state = 'completed'
                session.notes = f"Sessiya tamamlandı: {fields.Datetime.now()}. İstifadə edilən saat: {session.duration_hours + session.extended_time}"
    
    # Sessiyaları avtomatik yoxla (cron job üçün)
    @api.model
    def check_expired_sessions(self):
        """Vaxtı bitən sessiyaları yoxla"""
        expired_sessions = self.search([
            ('state', 'in', ['active', 'extended']),
            ('end_time', '<=', fields.Datetime.now())
        ])
        
        for session in expired_sessions:
            session.message_post(
                body=f"Diqqət! {session.partner_id.name} müştərisinin vaxtı bitib. Reception ilə əlaqə saxlayın.",
                message_type='notification'
            )
    
    # Aktiv sessiyaları göstər
    @api.model
    def get_active_sessions(self):
        """Hal-hazırda aktiv olan sessiyaları gətir"""
        active_sessions = self.search([
            ('state', 'in', ['active', 'extended'])
        ])
        
        session_data = []
        for session in active_sessions:
            remaining_time = session.end_time - fields.Datetime.now()
            remaining_minutes = max(0, int(remaining_time.total_seconds() / 60))
            
            session_data.append({
                'id': session.id,
                'partner_name': session.partner_id.name,
                'start_time': session.start_time,
                'end_time': session.end_time,
                'remaining_minutes': remaining_minutes,
                'state': session.state,
                'total_amount': session.total_amount
            })
        
        return session_data
