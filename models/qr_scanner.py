# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta

class QRScannerWizard(models.TransientModel):
    _name = 'qr.scanner.wizard'
    _description = 'QR Kod Scanner'

    qr_code_input = fields.Char(string="QR Kod", help="QR scanner cihazından oxunan kodu bura yazın")
    result_message = fields.Text(string="Nəticə", readonly=True)
    session_id = fields.Many2one('badminton.session', string="Badminton Sessiyası", readonly=True)
    attendance_id = fields.Many2one('sport.attendance', string="Basketbol İştirakı", readonly=True)
    
    # Xidmət növü seçimi
    service_type = fields.Selection([
        ('badminton', 'Badminton (Saatlıq)'),
        ('basketball', 'Basketbol (Dərs)')
    ], string="Xidmət Növü", default='badminton', required=True)

    def scan_and_start_session(self):
        """QR kod oxuyub xidmət başlat"""
        if not self.qr_code_input:
            raise ValidationError("❌ QR kod daxil edilməyib! Zəhmət olmasa scanner cihazı ilə QR kodu oxuyun.")
        
        if self.service_type == 'badminton':
            return self._handle_badminton_session()
        elif self.service_type == 'basketball':
            return self._handle_basketball_attendance()
    
    def _handle_badminton_session(self):
        """Badminton sessiyası üçün QR kod oxuma"""
        try:
            qr_data = self.qr_code_input.strip()
            if "ID-" in qr_data and "NAME-" in qr_data:
                partner_id_str = qr_data.split("ID-")[1].split("-")[0]
                partner_name = qr_data.split("NAME-")[1]
                partner_id = int(partner_id_str)
                
                partner = self.env['res.partner'].browse(partner_id)
                
                if not partner.exists():
                    self.result_message = f"❌ Xəta: ID={partner_id} olan müştəri tapılmadı!\nQR Kod: {qr_data}"
                    return self._return_wizard()
                
                # Müştərinin badminton balansını yoxla
                current_balance = partner.badminton_balance or 0
                required_hours = 1.0  # Standart 1 saat
                
                if current_balance < required_hours:
                    self.result_message = f"❌ Balans kifayət deyil!\n👤 Müştəri: {partner.name}\n💰 Mövcud balans: {current_balance} saat\n⚠️ Tələb olunan: {required_hours} saat\n\nZəhmət olmasa balansı artırın!"
                    return self._return_wizard()
                
                # Aktiv badminton sessiya var mı yoxla
                active_session = self.env['badminton.session'].search([
                    ('partner_id', '=', partner_id),
                    ('state', 'in', ['active', 'extended'])
                ], limit=1)
                
                if active_session:
                    self.result_message = f"⚠️ Diqqət: {partner.name} üçün artıq aktiv badminton sessiyası var!\nSessiya: {active_session.name}\nBaşlama vaxtı: {active_session.start_time}"
                    return self._return_wizard()
                
                # Balansdan 1 saat çıx
                new_balance = current_balance - required_hours
                partner.badminton_balance = new_balance
                
                # Yeni sessiya yarat
                session = self.env['badminton.session'].create({
                    'partner_id': partner_id,
                    'start_time': fields.Datetime.now(),
                    'end_time': fields.Datetime.now() + timedelta(hours=1),
                    'state': 'active',
                    'qr_scanned': True,
                    'duration_hours': 1.0,
                })
                
                # Balans tarixçəsi yarat
                self.env['badminton.balance.history'].create({
                    'partner_id': partner_id,
                    'session_id': session.id,
                    'hours_used': required_hours,
                    'balance_before': current_balance,
                    'balance_after': new_balance,
                    'transaction_type': 'usage',
                    'description': f"QR kod ilə sessiya başladıldı: {session.name}"
                })
                
                self.result_message = f"✅ BADMINTON UĞURLU!\n👤 Müştəri: {partner.name}\n🎮 Sessiya: {session.name}\n⏰ Başlama: {session.start_time}\n💰 Köhnə balans: {current_balance} saat\n💰 Yeni balans: {new_balance} saat"
                self.session_id = session.id
                
                return self._return_wizard()
                
            else:
                self.result_message = f"❌ QR kod formatı səhvdir!\n\nOxunan kod: '{qr_data}'\n\nDüzgün format: 'ID-123-NAME-Ad Soyad'"
                return self._return_wizard()
                
        except Exception as e:
            self.result_message = f"❌ Badminton xətası: {str(e)}\nOxunan kod: '{self.qr_code_input}'"
            return self._return_wizard()
    
    def _handle_basketball_attendance(self):
        """Basketbol dərsinə iştirak üçün QR kod oxuma"""
        try:
            qr_data = self.qr_code_input.strip()

            if "ID-" in qr_data and "NAME-" in qr_data:
                partner_id_str = qr_data.split("ID-")[1].split("-")[0]
                partner_name = qr_data.split("NAME-")[1]
                partner_id = int(partner_id_str)
                
                partner = self.env['res.partner'].browse(partner_id)
                
                if not partner.exists():
                    self.result_message = f"❌ Xəta: ID={partner_id} olan müştəri tapılmadı!"
                    return self._return_wizard()
                
                # Müştərinin aktiv basketbol üzvlüyünü tap
                today = fields.Date.today()
                current_month = today.month
                current_year = today.year
                current_weekday = str(today.weekday())
                
                membership = self.env['sport.membership'].search([
                    ('partner_id', '=', partner_id),
                    ('month', '=', current_month),
                    ('year', '=', current_year),
                    ('state', '=', 'active'),
                    ('is_active', '=', True)
                ], limit=1)
                
                if not membership:
                    self.result_message = f"❌ Xəta: {partner.name} üçün bu ay aktiv basketbol üzvlüyü tapılmadı!\nAy: {current_month}/{current_year}"
                    return self._return_wizard()
                
                # Bu gün üçün uyğun qrafik var mı yoxla
                valid_schedule = None
                for schedule in membership.schedule_ids:
                    if schedule.day_of_week == current_weekday and schedule.is_active:
                        # Vaxt aralığını yoxla (isteğe bağlı)
                        current_time = fields.Datetime.now().time()
                        schedule_start = int(schedule.start_time)
                        schedule_end = int(schedule.end_time)
                        current_hour = current_time.hour
                        
                        # 2 saat əvvəl və 1 saat sonra QR kodu aktiv et
                        if schedule_start - 2 <= current_hour <= schedule_end + 1:
                            valid_schedule = schedule
                            break
                
                if not valid_schedule:
                    self.result_message = f"❌ Xəta: Bu gün {partner.name} üçün aktiv basketbol dərsi yoxdur!\nBugün: {today.strftime('%d.%m.%Y')} - {['B.ertəsi', 'Ç.axşamı', 'Çərşənbə', 'C.axşamı', 'Cümə', 'Şənbə', 'Bazar'][today.weekday()]}"
                    return self._return_wizard()
                
                # Bu gün artıq iştirak var mı yoxla
                existing_attendance = self.env['sport.attendance'].search([
                    ('membership_id', '=', membership.id),
                    ('schedule_id', '=', valid_schedule.id),
                    ('attendance_date', '=', today)
                ], limit=1)
                
                if existing_attendance:
                    self.result_message = f"⚠️ Diqqət: {partner.name} bu gün artıq bu dərsə iştirak edib!\nİştirak vaxtı: {existing_attendance.attendance_time}"
                    return self._return_wizard()
                
                # Qalan dərs sayını yoxla
                if membership.remaining_lessons <= 0:
                    self.result_message = f"❌ Xəta: {partner.name} üçün bu ay qalan dərs yoxdur!\nÜmumi dərs: {membership.total_lessons}\nİştirak: {membership.attended_lessons}"
                    return self._return_wizard()
                
                # Yeni iştirak qeydi yarat
                attendance = self.env['sport.attendance'].create({
                    'membership_id': membership.id,
                    'schedule_id': valid_schedule.id,
                    'attendance_date': today,
                    'attendance_time': fields.Datetime.now(),
                    'qr_scanned': True,
                    'scan_result': qr_data
                })
                
                # Üzvlükdə iştirak sayını artır
                membership.attended_lessons += 1
                
                self.result_message = f"✅ BASKETBOL UĞURLU!\n👤 Müştəri: {partner.name}\n🏀 Dərs: {valid_schedule.name}\n📅 Tarix: {today.strftime('%d.%m.%Y')}\n⏰ Vaxt: {attendance.attendance_time.strftime('%H:%M')}\n📊 Qalan dərs: {membership.remaining_lessons}"
                self.attendance_id = attendance.id
                
                return self._return_wizard()
                
            else:
                self.result_message = f"❌ QR kod formatı səhvdir!\nOxunan kod: '{qr_data}'\nDüzgün format: 'ID-123-NAME-Ad Soyad'"
                return self._return_wizard()
                
        except Exception as e:
            self.result_message = f"❌ Basketbol xətası: {str(e)}\nOxunan kod: '{self.qr_code_input}'"
            return self._return_wizard()

    def _return_wizard(self):
        """Wizard pəncərəsini yenilə"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'qr.scanner.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': self.env.context
        }

    def open_session(self):
        """Yaradılan sessiyanı aç"""
        if self.session_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'badminton.session',
                'view_mode': 'form',
                'res_id': self.session_id.id,
                'target': 'current'
            }

    def open_attendance(self):
        """Yaradılan basketbol iştirakını aç"""
        if self.attendance_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'sport.attendance',
                'view_mode': 'form',
                'res_id': self.attendance_id.id,
                'target': 'current'
            }

    def scan_new_qr(self):
        """Yeni QR kod scan etmək üçün sahələri təmizlə"""
        self.qr_code_input = False
        self.result_message = False
        self.session_id = False
        self.attendance_id = False
        return self._return_wizard()
