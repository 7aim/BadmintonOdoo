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
        ('badminton', 'Badminton'),
        ('basketball', 'Basketbol')
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
                
                # ÖNCə AKTIV DƏRS ABUNƏLİYİNİ YOXLA
                lesson_check = self._check_active_lesson(partner)
                if lesson_check['has_lesson']:
                    self.result_message = lesson_check['message']
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
    
    def _check_active_lesson(self, partner):
        """Müştərinin aktiv dərs abunəliyini və dərs vaxtını yoxla"""
        try:
            # Aktiv dərs abunəliyini tap
            active_lesson = self.env['badminton.lesson.simple'].search([
                ('partner_id', '=', partner.id),
                ('state', '=', 'active'),
                ('start_date', '<=', fields.Date.today()),
                ('end_date', '>=', fields.Date.today())
            ], limit=1)
            
            if not active_lesson:
                return {'has_lesson': False, 'message': ''}
            
            # İndi dərs vaxtında olub-olmadığını yoxla
            today = fields.Date.today()
            current_time = fields.Datetime.now().time()
            current_weekday = str(today.weekday())  # 0=Bazar ertəsi, 6=Bazar
            current_hour = current_time.hour + current_time.minute / 60.0
            
            # Bu günə aid qrafik var mı?
            matching_schedule = active_lesson.schedule_ids.filtered(
                lambda s: s.day_of_week == current_weekday and s.is_active
            )
            
            if not matching_schedule:
                return {'has_lesson': False, 'message': ''}
            
            # Dərs vaxtında mı?
            for schedule in matching_schedule:
                # 30 dəqiqə əvvəl və 30 dəqiqə sonra QR kodu qəbul et
                start_with_buffer = schedule.start_time - 0.5  # 30 dəq əvvəl
                end_with_buffer = schedule.end_time + 0.5     # 30 dəq sonra
                
                if start_with_buffer <= current_hour <= end_with_buffer:
                    # Həftənin günü adlarını əlavə edək
                    day_names = {
                        '0': 'Bazar ertəsi',
                        '1': 'Çərşənbə axşamı', 
                        '2': 'Çərşənbə',
                        '3': 'Cümə axşamı',
                        '4': 'Cümə',
                        '5': 'Şənbə',
                        '6': 'Bazar'
                    }
                    
                    # Bu gün artıq bu dərsə iştirak var mı yoxla
                    existing_attendance = self.env['badminton.lesson.attendance.simple'].search([
                        ('lesson_id', '=', active_lesson.id),
                        ('schedule_id', '=', schedule.id),
                        ('attendance_date', '=', today)
                    ], limit=1)
                    
                    if existing_attendance:
                        return {
                            'has_lesson': True,
                            'message': f"⚠️ ARTIQ İŞTİRAK EDİB!\n👤 Müştəri: {partner.name}\n📚 Abunəlik: {active_lesson.name}\n📅 Bu gün artıq bu dərsə iştirak edilib\n⏰ İştirak vaxtı: {existing_attendance.attendance_time.strftime('%H:%M')}"
                        }
                    
                    # Yeni attendance yarat
                    attendance = self.env['badminton.lesson.attendance.simple'].create({
                        'lesson_id': active_lesson.id,
                        'schedule_id': schedule.id,
                        'attendance_date': today,
                        'attendance_time': fields.Datetime.now(),
                        'qr_scanned': True,
                        'scan_result': f"QR: {partner.name} (ID: {partner.id})"
                    })
                    
                    return {
                        'has_lesson': True,
                        'message': f"✅ DƏRSƏ GİRİŞ UĞURLU!\n👤 Müştəri: {partner.name}\n📚 Abunəlik: {active_lesson.name}\n📅 Dərs günü: {day_names.get(schedule.day_of_week, 'N/A')}\n⏰ Dərs saatı: {int(schedule.start_time):02d}:{int((schedule.start_time % 1) * 60):02d} - {int(schedule.end_time):02d}:{int((schedule.end_time % 1) * 60):02d}\n💡 Balans dəyişmədi (Dərs abunəliyi aktiv)\n📊 Bu aya iştirak: {active_lesson.total_attendances + 1}"
                    }
            
            return {'has_lesson': False, 'message': ''}
            
        except Exception as e:
            return {'has_lesson': False, 'message': f'Dərs yoxlama xətası: {str(e)}'}
    
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
                
                # Əvvəlcə yeni basketbol lesson sistemini yoxla
                basketball_lesson = self.env['basketball.lesson.simple'].search([
                    ('partner_id', '=', partner_id),
                    ('state', '=', 'active'),
                    ('start_date', '<=', today),
                    ('end_date', '>=', today)
                ], limit=1)
                
                if basketball_lesson:
                    # Basketball lesson sistemində QR yoxlaması
                    valid_schedule = None
                    for schedule in basketball_lesson.schedule_ids:
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
                    
                    # Bu gün artıq iştirak var mı yoxla (basketball lesson simple üçün)
                    existing_attendance = self.env['basketball.lesson.attendance.simple'].search([
                        ('lesson_id', '=', basketball_lesson.id),
                        ('schedule_id', '=', valid_schedule.id),
                        ('attendance_date', '=', today)
                    ], limit=1)
                    
                    if existing_attendance:
                        self.result_message = f"⚠️ Diqqət: {partner.name} bu gün artıq bu dərsə iştirak edib!\nİştirak vaxtı: {existing_attendance.attendance_time}"
                        return self._return_wizard()
                    
                    # Yeni iştirak qeydi yarat (basketball lesson simple)
                    attendance = self.env['basketball.lesson.attendance.simple'].create({
                        'lesson_id': basketball_lesson.id,
                        'schedule_id': valid_schedule.id,
                        'attendance_date': today,
                        'attendance_time': fields.Datetime.now(),
                        'qr_scanned': True,
                        'scan_result': qr_data
                    })
                    
                    # Schedule adını vaxt məlumatlarından yaradırıq
                    day_names = {
                        '0': 'Bazar ertəsi',
                        '1': 'Çərşənbə axşamı', 
                        '2': 'Çərşənbə',
                        '3': 'Cümə axşamı',
                        '4': 'Cümə',
                        '5': 'Şənbə',
                        '6': 'Bazar'
                    }
                    schedule_name = f"{day_names.get(valid_schedule.day_of_week, 'N/A')} {int(valid_schedule.start_time):02d}:{int((valid_schedule.start_time % 1) * 60):02d}-{int(valid_schedule.end_time):02d}:{int((valid_schedule.end_time % 1) * 60):02d}"
                    
                    self.result_message = f"✅ BASKETBOL UĞURLU!\n👤 Müştəri: {partner.name}\n🏀 Dərs: {schedule_name}\n📅 Tarix: {today.strftime('%d.%m.%Y')}\n⏰ Vaxt: {attendance.attendance_time.strftime('%H:%M')}\n📚 Abunəlik: {basketball_lesson.name}"
                    # attendance_id-ni təyin etmirik çünki yeni sistem fərqli modeldir
                    
                    return self._return_wizard()
                
                # Əgər basketball lesson tapılmadısa, köhnə sport.membership sistemini yoxla
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
