from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta

class CashFlow(models.Model):
    _name = 'volan.cash.flow'
    _description = 'Kassa Axını'
    _order = 'date desc, id desc'
    
    name = fields.Char('Ad', required=True)
    date = fields.Date('Tarix', required=True, default=fields.Date.today)
    amount = fields.Float('Məbləğ', required=True)
    transaction_type = fields.Selection([
        ('income', 'Gəlir'),
        ('expense', 'Xərc'),
    ], string='Əməliyyat Növü', required=True)
    category = fields.Selection([
        ('badminton_sale', 'Badminton Satışı'),
        ('badminton_lesson', 'Badminton Dərs'),
        ('basketball_lesson', 'Basketbol Dərs'),
        ('other', 'Digər'),
    ], string='Kateqoriya', required=True, default='other')
    notes = fields.Text('Qeydlər')
    partner_id = fields.Many2one('res.partner', string='Müştəri')
    related_model = fields.Char('Əlaqəli Model', readonly=True)
    related_id = fields.Integer('Əlaqəli ID', readonly=True)

class CashBalance(models.TransientModel):
    _name = 'volan.cash.balance'
    _description = 'Kassa Balansı'

    # Tarix filtr sahələri
    date_filter = fields.Selection([
        ('all', 'Bütün Tarixlər'),
        ('today', 'Bu Gün'),
        ('week', 'Bu Həftə'),
        ('month', 'Bu Ay'),
        ('year', 'Bu İl'),
        ('custom', 'Özel Tarix')
    ], string='📅 Tarix Filtri', default='month', required=True)
    
    date_from = fields.Date('📅 Başlanğıc Tarix')
    date_to = fields.Date('📅 Bitmə Tarix')

    # Gəlir növləri
    badminton_sales_income = fields.Float('🏸 Badminton Satışları', readonly=True)
    badminton_lessons_income = fields.Float('📚 Badminton Dərs Abunəlikləri', readonly=True)
    basketball_lessons_income = fields.Float('🏀 Basketbol Dərs Abunəlikləri', readonly=True)
    other_income = fields.Float('💰 Digər Gəlirlər', readonly=True)
    
    # Ümumi məlumatlar
    total_income = fields.Float('📈 Ümumi Gəlir', readonly=True)
    current_balance = fields.Float('💵 Cari Balans', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # İlkin yükləmədə cari ay filtri ilə hesabla
        self._calculate_balance_data(res)
        return res

    def _get_date_domain(self):
        """Tarix filtrinə əsasən domain qaytarır"""
        today = fields.Date.today()
        
        if self.date_filter == 'all':
            return []
        elif self.date_filter == 'today':
            return [('date', '=', today)]
        elif self.date_filter == 'week':
            # Həftənin ilk və son gününü hesabla (Bazar ertəsi - Bazar)
            weekday = today.weekday()
            date_from = today - timedelta(days=weekday)
            date_to = date_from + timedelta(days=6)
            return [('date', '>=', date_from), ('date', '<=', date_to)]
        elif self.date_filter == 'month':
            # Ayın ilk və son günlərini hesabla
            date_from = today.replace(day=1)
            if today.month == 12:
                date_to = today.replace(year=today.year+1, month=1, day=1) - timedelta(days=1)
            else:
                date_to = today.replace(month=today.month+1, day=1) - timedelta(days=1)
            return [('date', '>=', date_from), ('date', '<=', date_to)]
        elif self.date_filter == 'year':
            # İlin ilk və son günlərini hesabla
            date_from = today.replace(month=1, day=1)
            date_to = today.replace(month=12, day=31)
            return [('date', '>=', date_from), ('date', '<=', date_to)]
        elif self.date_filter == 'custom' and self.date_from and self.date_to:
            return [('date', '>=', self.date_from), ('date', '<=', self.date_to)]
        return []

    def _calculate_balance_data(self, res=None):
        """Balans məlumatlarını tarix filtrinə əsasən hesablayır"""
        if res is None:
            res = {}
            
        cash_flow_obj = self.env['volan.cash.flow']
        date_domain = self._get_date_domain()
        
        # Badminton satış gəlirləri
        badminton_sales_domain = [
            ('transaction_type', '=', 'income'),
            ('category', '=', 'badminton_sale')
        ] + date_domain
        badminton_sales_income = sum(cash_flow_obj.search(badminton_sales_domain).mapped('amount'))
        
        # Badminton dərs gəlirləri
        badminton_lessons_domain = [
            ('transaction_type', '=', 'income'),
            ('category', '=', 'badminton_lesson')
        ] + date_domain
        badminton_lessons_income = sum(cash_flow_obj.search(badminton_lessons_domain).mapped('amount'))
        
        # Basketbol dərs gəlirləri
        basketball_lessons_domain = [
            ('transaction_type', '=', 'income'),
            ('category', '=', 'basketball_lesson')
        ] + date_domain
        basketball_lessons_income = sum(cash_flow_obj.search(basketball_lessons_domain).mapped('amount'))
        
        # Digər gəlirlər
        other_income_domain = [
            ('transaction_type', '=', 'income'),
            ('category', '=', 'other')
        ] + date_domain
        other_income = sum(cash_flow_obj.search(other_income_domain).mapped('amount'))
        
        # Ümumi gəlir
        total_income = badminton_sales_income + badminton_lessons_income + basketball_lessons_income + other_income
        
        res.update({
            'badminton_sales_income': badminton_sales_income,
            'badminton_lessons_income': badminton_lessons_income,
            'basketball_lessons_income': basketball_lessons_income,
            'other_income': other_income,
            'total_income': total_income,
            'current_balance': total_income,
        })
        
        return res

    def action_refresh(self):
        """Balansı yenilə düyməsi"""
        values = {}
        self._calculate_balance_data(values)
        self.write(values)
        # Sadəcə True qaytarmaq formu yenilənməyə məcbur edir
        return True
        
    @api.model
    def create_income_transaction(self, values):
        """
        Kassa axınında yeni gəlir əməliyyatı yaradır
        Xarici modellərin cash.flow yaratması üçün istifadə olunur
        """
        cash_flow_obj = self.env['volan.cash.flow']
        values['transaction_type'] = 'income'
        return cash_flow_obj.create(values)
        
    def generate_cash_report(self):
        """Nağd pul hesabat səhifəsini açır"""
        self.ensure_one()
        domain = self._get_date_domain()
        action = {
            'name': 'Kassa Hesabatı',
            'type': 'ir.actions.act_window',
            'res_model': 'volan.cash.flow',
            'view_mode': 'pivot,graph,list,form',
            'domain': [('transaction_type', '=', 'income')] + domain,
            'context': {
                'search_default_group_by_category': 1,
                'search_default_group_by_date': 1
            }
        }
        return action

    @api.onchange('date_filter', 'date_from', 'date_to')
    def _onchange_date_filter(self):
        """Tarix filtri dəyişəndə balansı yenilə"""
        values = {}
        self._calculate_balance_data(values)
        for field, value in values.items():
            setattr(self, field, value)