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

    # --- Hesablama Funksiyası ---

    @api.depends('name', 'write_date')
    def _compute_qr_code(self):
        """Her müşteri üçün unikal ID və adına əsaslanan bir QR kod yaradır."""
        for partner in self:
            if partner.id and partner.name:
                # ID + Ad kombinasiyası ilə daha unikal QR kod
                qr_payload = f"ID:{partner.id}-NAME:{partner.name}"
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