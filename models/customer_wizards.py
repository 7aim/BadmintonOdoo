# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class CustomerLookupWizard(models.TransientModel):
    _name = 'customer.lookup.wizard'
    _description = 'Müştəri Axtarış Sihirbazı'
    
    search_term = fields.Char(string="Axtarış", required=True, help="Müştəri adı və ya telefon nömrəsi")
    customer_ids = fields.Many2many('res.partner', string="Tapılan Müştərilər")
    
    @api.onchange('search_term')
    def _onchange_search_term(self):
        if self.search_term and len(self.search_term) >= 2:
            domain = [
                '|', '|',
                ('name', 'ilike', self.search_term),
                ('qr', 'ilike', self.search_term),
                ('phone', 'ilike', self.search_term),
                ('mobile', 'ilike', self.search_term)
            ]
            customers = self.env['res.partner'].search(domain, limit=10)
            self.customer_ids = [(6, 0, customers.ids)]
        else:
            self.customer_ids = [(5, 0, 0)]
    
    def action_view_customer(self):
        """Seçilən müştərinin səhifəsini aç"""
        if len(self.customer_ids) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Müştəri Məlumatları',
                'res_model': 'res.partner',
                'res_id': self.customer_ids[0].id,
                'view_mode': 'form',
                'target': 'current'
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Müştərilər',
                'res_model': 'res.partner',
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.customer_ids.ids)],
                'target': 'current'
            }


class BadmintonSaleWizard(models.TransientModel):
    _name = 'badminton.sale.wizard'
    _description = 'Badminton Satış Sihirbazı'
    
    partner_id = fields.Many2one('res.partner', string="Müştəri", required=True)
    hours_quantity = fields.Integer(string="Saat Sayı", required=True, default=1)
    
    unit_price = fields.Float(string="Saatlıq Qiymət", compute='_compute_unit_price', store=True)
    total_amount = fields.Float(string="Ümumi Məbləğ", compute='_compute_total_amount', store=True)
    
    # Display müştərinin cari balansını
    current_balance = fields.Integer(string="Cari Balans", related='partner_id.badminton_balance', readonly=True)
    
    @api.depends('hours_quantity', 'unit_price')
    def _compute_total_amount(self):
        for wizard in self:
            wizard.total_amount = wizard.hours_quantity * wizard.unit_price
    
    def action_create_sale(self):
        """Satış yaradır və dərhal balansı artırır"""
        if not self.partner_id  or self.hours_quantity <= 0:
            raise ValidationError("Zəhmət olmasa bütün sahələri doldurun!")
        
        # Badminton satışı yaradırıq (dərhal ödənilib statusunda)
        sale = self.env['badminton.sale'].create({
            'partner_id': self.partner_id.id,
            'hours_quantity': self.hours_quantity,
            'state': 'paid',  # Dərhal ödənilib
            'payment_date': fields.Datetime.now(),
        })
        
        # Balans create funksiyasında avtomatik artırılacaq
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'{self.partner_id.name} üçün {self.hours_quantity} saat badminton satışı tamamlandı! '
                          f'Yeni balans: {self.partner_id.badminton_balance} saat',
                'type': 'success',
                'sticky': True,
            }
        }
