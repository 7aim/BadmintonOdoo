# -*- coding: utf-8 -*-
from odoo import models, fields, api
import qrcode
import base64
import io

class VolanPartner(models.Model):
    _inherit = 'res.partner'

    # --- Yeni Sahələri (Fields) Təyin Edirik ---

    # 1. Doğum Tarixi Sahəsi
    birth_date = fields.Date(string="Doğum Tarixi")

    # 2. Əlavə Məlumatlar Sahəsi
    additional_info = fields.Text(string="Əlavə Məlumatlar")

    # 3. QR Kod Şəkli Sahəsi (Hesablanan)
    qr_code_image = fields.Binary(string="QR Kod", compute='_compute_qr_code', store=True)

    # 4. Badminton Balans Sahəsi
    badminton_balance = fields.Integer(string="Badminton Balansı (saat)", default=0, 
                                      help="Müştərinin qalan badminton saatlarının sayı")
    
    # Note: One2many fields will be added after module installation is complete
    # badminton_sale_ids = fields.One2many('badminton.sale', 'partner_id', string="Badminton Satışları")
    # badminton_balance_history_ids = fields.One2many('badminton.balance.history', 'partner_id', string="Balans Tarixçəsi")
    # basketball_membership_ids = fields.One2many('sport.membership', 'partner_id', string="Basketbol Üzvlüklər")

    @api.model
    def _auto_init(self):
        """Ensure badminton_balance column exists"""
        res = super(VolanPartner, self)._auto_init()
        
        # Check if badminton_balance column exists, if not add it
        try:
            self.env.cr.execute("SELECT badminton_balance FROM res_partner LIMIT 1")
        except Exception:
            # Column doesn't exist, create it
            self.env.cr.execute("ALTER TABLE res_partner ADD COLUMN badminton_balance INTEGER DEFAULT 0")
            self.env.cr.execute("UPDATE res_partner SET badminton_balance = 0 WHERE badminton_balance IS NULL")
            self.env.cr.commit()
        
        return res

    # --- Hesablama Funksiyası ---

    @api.depends('name', 'write_date')
    def _compute_qr_code(self):
        """Her müşteri üçün unikal ID və adına əsaslanan bir QR kod yaradır."""
        for partner in self:
            if partner.id and partner.name:
                # ID + Ad kombinasiyası ilə daha unikal QR kod
                qr_payload = f"ID-{partner.id}-NAME-{partner.name}"
                try:
                    img = qrcode.make(qr_payload)
                    temp = io.BytesIO()
                    img.save(temp, format="PNG")
                    qr_image = base64.b64encode(temp.getvalue())
                    partner.qr_code_image = qr_image
                except Exception:
                    partner.qr_code_image = False
            else:
                partner.qr_code_image = False