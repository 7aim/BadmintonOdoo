# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta

class QRScannerWizard(models.TransientModel):
    _name = 'qr.scanner.wizard'
    _description = 'QR Kod Scanner'

    qr_code_input = fields.Char(string="QR Kod", help="QR scanner cihazından oxunan kodu bura yazın")
    result_message = fields.Text(string="Nəticə", readonly=True)
    session_id = fields.Many2one('badminton.session', string="Yaradılan Sessiya", readonly=True)

    def scan_and_start_session(self):
        """QR kod oxuyub sessiya başlat"""
        if not self.qr_code_input:
            raise ValidationError("❌ QR kod daxil edilməyib! Zəhmət olmasa scanner cihazı ilə QR kodu oxuyun.")
        
        try:
            # QR koddan müştəri məlumatlarını çıxart
            qr_data = self.qr_code_input.strip()
            
            # Debug məlumatı əlavə edək
            if "ID:" in qr_data and "NAME:" in qr_data:
                # ID-ni çıxart
                partner_id_str = qr_data.split("ID:")[1].split("-")[0]
                partner_name = qr_data.split("NAME:")[1]
                partner_id = int(partner_id_str)
                
                partner = self.env['res.partner'].browse(partner_id)
                
                if not partner.exists():
                    self.result_message = f"❌ Xəta: ID={partner_id} olan müştəri tapılmadı!\nQR Kod: {qr_data}"
                    return self._return_wizard()
                
                # Aktiv sessiya var mı yoxla
                active_session = self.env['badminton.session'].search([
                    ('partner_id', '=', partner_id),
                    ('state', 'in', ['active', 'extended'])
                ], limit=1)
                
                if active_session:
                    self.result_message = f"⚠️ Diqqət: {partner.name} üçün artıq aktiv sessiya var!\nSessiya: {active_session.name}\nBaşlama vaxtı: {active_session.start_time}"
                    return self._return_wizard()
                
                # Yeni sessiya yarat
                session = self.env['badminton.session'].create({
                    'partner_id': partner_id,
                    'start_time': fields.Datetime.now(),
                    'end_time': fields.Datetime.now() + timedelta(hours=1),
                    'state': 'active',
                    'qr_scanned': True,
                    'duration_hours': 1.0,
                    'hourly_rate': 15.0
                })
                
                # Əlçatan kortu tap və təyin et
                available_court = self.env['badminton.court'].search([
                    ('is_available', '=', True)
                ], limit=1)
                
                if available_court:
                    available_court.assign_session(session.id)
                    court_info = f"\n🏸 Kort: {available_court.name}"
                else:
                    court_info = "\n⚠️ Bütün kortlar doludur"
                
                self.result_message = f"✅ UĞURLU!\n👤 Müştəri: {partner.name}\n🎮 Sessiya: {session.name}\n⏰ Başlama: {session.start_time}\n💰 Qiymət: {session.hourly_rate} AZN/saat{court_info}"
                self.session_id = session.id
                
                return self._return_wizard()
                
            else:
                self.result_message = f"❌ QR kod formatı səhvdir!\n\nOxunan kod: '{qr_data}'\n\nDüzgün format: 'ID:123-NAME:Ad Soyad'\n\n💡 Müştərinin QR kodunu yenidən oxuyun."
                return self._return_wizard()
                
        except ValueError as e:
            self.result_message = f"❌ QR kodda ID nömrəsi düzgün deyil!\nOxunan kod: '{self.qr_code_input}'\nXəta: {str(e)}"
            return self._return_wizard()
        except Exception as e:
            self.result_message = f"❌ Gözlənilməz xəta: {str(e)}\nOxunan kod: '{self.qr_code_input}'"
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

    def scan_new_qr(self):
        """Yeni QR kod scan etmək üçün sahəni təmizlə"""
        self.qr_code_input = False
        self.result_message = False
        self.session_id = False
        return self._return_wizard()
