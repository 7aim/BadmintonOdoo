# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta

class BadmintonSale(models.Model):
    _name = 'badminton.sale'
    _description = 'Badminton Satışı'
    _order = 'create_date desc'
    
    name = fields.Char(string="Satış Nömrəsi", readonly=True, default="Yeni")
    partner_id = fields.Many2one('res.partner', string="Müştəri", required=True)
    filial_id = fields.Many2one('sport.filial', string="Filial", required=True)
    
    # Satış məlumatları
    hours_quantity = fields.Integer(string="Saat Sayı", required=True, default=1)
    unit_price = fields.Float(string="Saatlıq Qiymət", compute='_compute_unit_price', store=True)
    total_amount = fields.Float(string="Ümumi Məbləğ", compute='_compute_total_amount', store=True)
    
    # Ödəniş məlumatları
    payment_method = fields.Selection([
        ('cash', 'Nəğd'),
        ('card', 'Kart'),
        ('bank_transfer', 'Bank Köçürməsi')
    ], string="Ödəniş Növü", required=True, default='cash')
    
    is_paid = fields.Boolean(string="Ödənib", default=False)
    payment_date = fields.Datetime(string="Ödəniş Tarixi")
    
    # Vəziyyət
    state = fields.Selection([
        ('draft', 'Layihə'),
        ('confirmed', 'Təsdiqlənib'),
        ('paid', 'Ödənilib'),
        ('cancelled', 'Ləğv Edilib')
    ], default='draft', string="Vəziyyət")
    
    # Müştəri hesabı məlumatları
    credited_hours = fields.Integer(string="Hesaba Əlavə Edilən Saatlar", default=0)
    
    # Tarix məlumatları
    sale_date = fields.Date(string="Satış Tarixi", default=fields.Date.today)
    expiry_date = fields.Date(string="Son İstifadə Tarixi", compute='_compute_expiry_date', store=True)
    
    # Qeydlər
    notes = fields.Text(string="Qeydlər")
    
    @api.depends('filial_id')
    def _compute_unit_price(self):
        for sale in self:
            if sale.filial_id:
                sale.unit_price = sale.filial_id.badminton_hourly_rate
            else:
                sale.unit_price = 0.0
    
    @api.depends('hours_quantity', 'unit_price')
    def _compute_total_amount(self):
        for sale in self:
            sale.total_amount = sale.hours_quantity * sale.unit_price
    
    @api.depends('sale_date')
    def _compute_expiry_date(self):
        for sale in self:
            if sale.sale_date:
                # Badminton saatları 6 ay ərzində istifadə edilməlidir
                sale.expiry_date = sale.sale_date + timedelta(days=180)
            else:
                sale.expiry_date = False
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'Yeni') == 'Yeni':
            vals['name'] = self.env['ir.sequence'].next_by_code('badminton.sale') or 'BS001'
        return super(BadmintonSale, self).create(vals)
    
    def action_confirm(self):
        """Satışı təsdiqləyir"""
        for sale in self:
            if sale.state == 'draft':
                sale.state = 'confirmed'
    
    def action_mark_paid(self):
        """Ödənişi qeyd edir və müştəri hesabına saatları əlavə edir"""
        for sale in self:
            if sale.state == 'confirmed' and not sale.is_paid:
                sale.is_paid = True
                sale.payment_date = fields.Datetime.now()
                sale.state = 'paid'
                
                # Müştəri hesabına saatları əlavə et
                sale._add_hours_to_customer()
                
                # Müştəri hesabında saatları yenilə
                sale.credited_hours = sale.hours_quantity
    
    def action_cancel(self):
        """Satışı ləğv edir"""
        for sale in self:
            if sale.state in ['draft', 'confirmed']:
                sale.state = 'cancelled'
    
    def _add_hours_to_customer(self):
        """Müştəri hesabına badminton saatlarını əlavə edir"""
        for sale in self:
            # Müştərinin badminton balansını yenilə
            partner = sale.partner_id
            current_balance = partner.badminton_balance or 0
            partner.badminton_balance = current_balance + sale.hours_quantity
            
            # Tarixçə yaradırıq
            self.env['badminton.balance.history'].create({
                'partner_id': partner.id,
                'sale_id': sale.id,
                'hours_added': sale.hours_quantity,
                'balance_before': current_balance,
                'balance_after': current_balance + sale.hours_quantity,
                'transaction_type': 'purchase',
                'description': f"Badminton saatları alışı: {sale.name}"
            })


class BadmintonBalanceHistory(models.Model):
    _name = 'badminton.balance.history'
    _description = 'Badminton Balans Tarixçəsi'
    _order = 'create_date desc'
    
    partner_id = fields.Many2one('res.partner', string="Müştəri", required=True)
    sale_id = fields.Many2one('badminton.sale', string="Satış")
    session_id = fields.Many2one('badminton.session', string="Sessiya")
    
    transaction_type = fields.Selection([
        ('purchase', 'Alış'),
        ('usage', 'İstifadə'),
        ('refund', 'Geri Ödəmə'),
        ('adjustment', 'Düzəliş')
    ], string="Əməliyyat Növü", required=True)

    hours_added = fields.Integer(string="Alındı", default=0)
    hours_used = fields.Integer(string="İstifadə", default=0)
    balance_before = fields.Integer(string="Əvvəlki Balans")
    balance_after = fields.Integer(string="Balans")
    
    description = fields.Text(string="Təsvir")
    transaction_date = fields.Datetime(string="Əməliyyat Tarixi", default=fields.Datetime.now)
