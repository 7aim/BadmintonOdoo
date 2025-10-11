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
    
    # Sport növü əlavə edək
    sport_type = fields.Selection([
        ('badminton', 'Badminton'),
        ('basketball', 'Basketbol'),
        ('general', 'Ümumi')
    ], string='İdman Növü', required=True, default='general', help='Bu əməliyyatın hansı idman növünə aid olduğunu göstərir')
    notes = fields.Text('Qeydlər')
    partner_id = fields.Many2one('res.partner', string='Müştəri')
    related_model = fields.Char('Əlaqəli Model', readonly=True)
    related_id = fields.Integer('Əlaqəli ID', readonly=True)
    
    @api.constrains('amount', 'transaction_type')
    def _check_negative_balance(self):
        """Xərc əməliyyatı balansı mənfiyə düşürməməlidir"""
        for record in self:
            if record.transaction_type == 'expense':
                # Cari balansı hesablayırıq
                cash_balance = self.env['volan.cash.balance'].create({})
                if cash_balance.current_balance < record.amount:
                    raise ValidationError('Xəbərdarlıq: Yetərsiz balans! Bu xərc əməliyyatı balansı mənfiyə düşürəcək. '
                                          'Cari balans: {:.2f}, Xərc məbləği: {:.2f}'.format(
                                              cash_balance.current_balance, record.amount))
                    
    @api.model
    def create(self, vals):
        """Yazarkən xərc üçün balans yoxlaması"""
        # Əvvəlcə yaratmadan xərc və məbləğ kontrolunu yoxlayaq
        if vals.get('transaction_type') == 'expense':
            amount = vals.get('amount', 0)
            if amount > 0:  # Məbləğ müsbət olarsa (xərclər üçün normal)
                cash_balance = self.env['volan.cash.balance'].create({})
                if cash_balance.current_balance < amount:
                    raise ValidationError('Xəbərdarlıq: Yetərsiz balans! Bu xərc əməliyyatı balansı mənfiyə düşürəcək. '
                                          'Cari balans: {:.2f}, Xərc məbləği: {:.2f}'.format(
                                              cash_balance.current_balance, amount))
        return super(CashFlow, self).create(vals)

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
    
    # Xərclər
    total_expenses = fields.Float('📉 Ümumi Xərclər', readonly=True)
    
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
        
        # Ümumi xərclər - sadə şəkildə bütün xərcləri hesablayırıq
        expense_domain = [
            ('transaction_type', '=', 'expense')
        ] + date_domain
        total_expenses = sum(cash_flow_obj.search(expense_domain).mapped('amount'))
        
        # Cari balans = Ümumi gəlir - Ümumi xərc
        current_balance = total_income - total_expenses
        
        res.update({
            'badminton_sales_income': badminton_sales_income,
            'badminton_lessons_income': badminton_lessons_income,
            'basketball_lessons_income': basketball_lessons_income,
            'other_income': other_income,
            'total_income': total_income,
            'total_expenses': total_expenses,
            'current_balance': current_balance,
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
        
    @api.model
    def create_expense_transaction(self, values):
        """
        Kassa axınında yeni xərc əməliyyatı yaradır
        Xarici modellərin cash.flow yaratması üçün istifadə olunur
        """
        cash_flow_obj = self.env['volan.cash.flow']
        values['transaction_type'] = 'expense'
        
        # Xərc əməliyyatı yaratmadan əvvəl balansı yoxlayırıq
        if values.get('amount', 0) > 0:
            # Cari balansı hesablayırıq
            current_balance = self._calculate_current_balance()
            if current_balance < values.get('amount', 0):
                raise ValidationError('Xəbərdarlıq: Yetərsiz balans! Bu xərc əməliyyatı balansı mənfiyə düşürəcək. '
                                      'Cari balans: {:.2f}, Xərc məbləği: {:.2f}'.format(
                                          current_balance, values.get('amount', 0)))
        
        return cash_flow_obj.create(values)
        
    def _calculate_current_balance(self):
        """Cari balansı hesablayır"""
        cash_flow_obj = self.env['volan.cash.flow']
        
        # Gəlirlər
        income = sum(cash_flow_obj.search([('transaction_type', '=', 'income')]).mapped('amount'))
        
        # Xərclər
        expenses = sum(cash_flow_obj.search([('transaction_type', '=', 'expense')]).mapped('amount'))
        
        return income - expenses
        
    def generate_cash_report(self):
        """Nağd pul hesabat səhifəsini açır"""
        self.ensure_one()
        domain = self._get_date_domain()
        action = {
            'name': 'Kassa Hesabatı',
            'type': 'ir.actions.act_window',
            'res_model': 'volan.cash.flow',
            'view_mode': 'pivot,graph,list,form',
            'domain': domain,  # Bütün əməliyyatları göstər (həm gəlir, həm xərc)
            'context': {
                'pivot_measures': ['amount'],
                'search_default_group_by_transaction_type': 1,  # Əməliyyat növünə görə qruplaşdır
                'search_default_group_by_category': 1,
                'search_default_group_by_date': 1
            }
        }
        return action
        
    def _open_cash_flow_view(self, title, domain):
        """Filtrələnmiş kassa əməliyyatı siyahısını göstərir"""
        self.ensure_one()
        action = {
            'name': title,
            'type': 'ir.actions.act_window',
            'res_model': 'volan.cash.flow',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {'create': False}
        }
        return action
        
    def show_badminton_sales(self):
        """Badminton satışlarını göstərir"""
        self.ensure_one()
        domain = self._get_date_domain() + [
            ('category', '=', 'badminton_sale'),
            ('transaction_type', '=', 'income')
        ]
        return self._open_cash_flow_view('Badminton Satışları', domain)
        
    def show_badminton_lessons(self):
        """Badminton dərs gəlirlərini göstərir"""
        self.ensure_one()
        domain = self._get_date_domain() + [
            ('category', '=', 'badminton_lesson'),
            ('transaction_type', '=', 'income')
        ]
        return self._open_cash_flow_view('Badminton Dərs Gəlirləri', domain)
        
    def show_basketball_lessons(self):
        """Basketbol dərs gəlirlərini göstərir"""
        self.ensure_one()
        domain = self._get_date_domain() + [
            ('category', '=', 'basketball_lesson'),
            ('transaction_type', '=', 'income')
        ]
        return self._open_cash_flow_view('Basketbol Dərs Gəlirləri', domain)
        
    def show_other_income(self):
        """Digər gəlirləri göstərir"""
        self.ensure_one()
        domain = self._get_date_domain() + [
            ('category', '=', 'other'),
            ('transaction_type', '=', 'income')
        ]
        return self._open_cash_flow_view('Digər Gəlirlər', domain)
        
    def show_expenses(self):
        """Xərcləri göstərir"""
        self.ensure_one()
        domain = self._get_date_domain() + [
            ('transaction_type', '=', 'expense')
        ]
        return self._open_cash_flow_view('Xərclər', domain)

    @api.onchange('date_filter', 'date_from', 'date_to')
    def _onchange_date_filter(self):
        """Tarix filtri dəyişəndə balansı yenilə"""
        values = {}
        self._calculate_balance_data(values)
        for field, value in values.items():
            setattr(self, field, value)


class BasketballCashBalance(models.TransientModel):
    _name = 'basketball.cash.balance'
    _description = 'Basketbol Kassa Balansı'

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

    # Basketbol gəlirləri
    basketball_lessons_income = fields.Float('🏀 Basketbol Dərs Abunəlikləri', readonly=True)
    basketball_other_income = fields.Float('💰 Digər Basketbol Gəlirləri', readonly=True)
    
    # Basketbol xərcləri
    basketball_expenses = fields.Float('📉 Basketbol Xərcləri', readonly=True)
    
    # Ümumi məlumatlar
    total_basketball_income = fields.Float('📈 Ümumi Basketbol Gəliri', readonly=True)
    basketball_balance = fields.Float('🏀 Basketbol Balansı', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # İlkin yükləmədə cari ay filtri ilə hesabla
        self._calculate_basketball_balance(res)
        return res

    def _get_date_domain(self):
        """Tarix filtrinə əsasən domain qaytarır"""
        today = fields.Date.today()
        domain = []
        
        if self.date_filter == 'today':
            domain = [('date', '=', today)]
        elif self.date_filter == 'week':
            week_start = today - timedelta(days=today.weekday())
            domain = [('date', '>=', week_start), ('date', '<=', today)]
        elif self.date_filter == 'month':
            month_start = today.replace(day=1)
            domain = [('date', '>=', month_start), ('date', '<=', today)]
        elif self.date_filter == 'year':
            year_start = today.replace(month=1, day=1)
            domain = [('date', '>=', year_start), ('date', '<=', today)]
        elif self.date_filter == 'custom' and self.date_from and self.date_to:
            domain = [('date', '>=', self.date_from), ('date', '<=', self.date_to)]
        
        return domain

    def _calculate_basketball_balance(self, values):
        """Basketbol balansını hesablayır"""
        cash_flow_obj = self.env['volan.cash.flow']
        domain = self._get_date_domain()
        
        # Basketbol dərs gəlirləri - ümumi kassadakı kimi
        basketball_lessons_domain = domain + [
            ('transaction_type', '=', 'income'),
            ('category', '=', 'basketball_lesson')
        ]
        basketball_lessons_income = sum(cash_flow_obj.search(basketball_lessons_domain).mapped('amount'))
        
        # Digər basketbol gəlirləri - yalnız sport_type=basketball olanlar
        basketball_other_domain = domain + [
            ('transaction_type', '=', 'income'),
            ('sport_type', '=', 'basketball'),
            ('category', '!=', 'basketball_lesson')
        ]
        basketball_other_income = sum(cash_flow_obj.search(basketball_other_domain).mapped('amount'))
        
        # Basketbol xərcləri - yalnız sport_type=basketball olanlar
        basketball_expenses_domain = domain + [
            ('transaction_type', '=', 'expense'),
            ('sport_type', '=', 'basketball')
        ]
        basketball_expenses = sum(cash_flow_obj.search(basketball_expenses_domain).mapped('amount'))
        
        # Ümumi hesablamalar
        total_basketball_income = basketball_lessons_income + basketball_other_income
        basketball_balance = total_basketball_income - basketball_expenses
        
        values.update({
            'basketball_lessons_income': basketball_lessons_income,
            'basketball_other_income': basketball_other_income,
            'basketball_expenses': basketball_expenses,
            'total_basketball_income': total_basketball_income,
            'basketball_balance': basketball_balance,
        })

    def action_refresh(self):
        """Basketbol balansını yenilə"""
        values = {}
        self._calculate_basketball_balance(values)
        self.write(values)
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def _open_basketball_cash_view(self, name, domain):
        """Basketbol kassa əməliyyatları view-nı açır"""
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': 'volan.cash.flow',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {'default_sport_type': 'basketball'},
            'target': 'current'
        }

    def show_basketball_lessons(self):
        """Basketbol dərs gəlirlərini göstərir"""
        self.ensure_one()
        domain = self._get_date_domain() + [
            ('sport_type', '=', 'basketball'),
            ('category', '=', 'basketball_lesson'),
            ('transaction_type', '=', 'income')
        ]
        return self._open_basketball_cash_view('Basketbol Dərs Gəlirləri', domain)

    def show_basketball_other_income(self):
        """Digər basketbol gəlirlərini göstərir"""
        self.ensure_one()
        domain = self._get_date_domain() + [
            ('sport_type', '=', 'basketball'),
            ('category', '!=', 'basketball_lesson'),
            ('transaction_type', '=', 'income')
        ]
        return self._open_basketball_cash_view('Digər Basketbol Gəlirləri', domain)
        
    def show_basketball_expenses(self):
        """Basketbol xərclərini göstərir"""
        self.ensure_one()
        domain = self._get_date_domain() + [
            ('sport_type', '=', 'basketball'),
            ('transaction_type', '=', 'expense')
        ]
        return self._open_basketball_cash_view('Basketbol Xərcləri', domain)

    @api.onchange('date_filter', 'date_from', 'date_to')
    def _onchange_date_filter(self):
        """Tarix filtri dəyişəndə basketbol balansını yenilə"""
        values = {}
        self._calculate_basketball_balance(values)
        for field, value in values.items():
            setattr(self, field, value)


class BadmintonCashBalance(models.TransientModel):
    _name = 'badminton.cash.balance'
    _description = 'Badminton Kassa Balansı'

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

    # Badminton gəlirləri
    badminton_sales_income = fields.Float('🏸 Badminton Satışları', readonly=True)
    badminton_lessons_income = fields.Float('📚 Badminton Dərs Abunəlikləri', readonly=True)
    badminton_other_income = fields.Float('💰 Digər Badminton Gəlirləri', readonly=True)
    
    # Badminton xərcləri
    badminton_expenses = fields.Float('📉 Badminton Xərcləri', readonly=True)
    
    # Ümumi məlumatlar
    total_badminton_income = fields.Float('📈 Ümumi Badminton Gəliri', readonly=True)
    badminton_balance = fields.Float('🏸 Badminton Balansı', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # İlkin yükləmədə cari ay filtri ilə hesabla
        self._calculate_badminton_balance(res)
        return res

    def _get_date_domain(self):
        """Tarix filtrinə əsasən domain qaytarır"""
        today = fields.Date.today()
        domain = []
        
        if self.date_filter == 'today':
            domain = [('date', '=', today)]
        elif self.date_filter == 'week':
            week_start = today - timedelta(days=today.weekday())
            domain = [('date', '>=', week_start), ('date', '<=', today)]
        elif self.date_filter == 'month':
            month_start = today.replace(day=1)
            domain = [('date', '>=', month_start), ('date', '<=', today)]
        elif self.date_filter == 'year':
            year_start = today.replace(month=1, day=1)
            domain = [('date', '>=', year_start), ('date', '<=', today)]
        elif self.date_filter == 'custom' and self.date_from and self.date_to:
            domain = [('date', '>=', self.date_from), ('date', '<=', self.date_to)]
        
        return domain

    def _calculate_badminton_balance(self, values):
        """Badminton balansını hesablayır"""
        cash_flow_obj = self.env['volan.cash.flow']
        domain = self._get_date_domain()
        
        # Badminton satış gəlirləri - ümumi kassadakı kimi
        badminton_sales_domain = domain + [
            ('transaction_type', '=', 'income'),
            ('category', '=', 'badminton_sale')
        ]
        badminton_sales_income = sum(cash_flow_obj.search(badminton_sales_domain).mapped('amount'))
        
        # Badminton dərs gəlirləri - ümumi kassadakı kimi
        badminton_lessons_domain = domain + [
            ('transaction_type', '=', 'income'),
            ('category', '=', 'badminton_lesson')
        ]
        badminton_lessons_income = sum(cash_flow_obj.search(badminton_lessons_domain).mapped('amount'))
        
        # Digər badminton gəlirləri - yalnız sport_type=badminton olanlar
        badminton_other_domain = domain + [
            ('transaction_type', '=', 'income'),
            ('sport_type', '=', 'badminton'),
            ('category', 'not in', ['badminton_sale', 'badminton_lesson'])
        ]
        badminton_other_income = sum(cash_flow_obj.search(badminton_other_domain).mapped('amount'))
        
        # Badminton xərcləri - yalnız sport_type=badminton olanlar
        badminton_expenses_domain = domain + [
            ('transaction_type', '=', 'expense'),
            ('sport_type', '=', 'badminton')
        ]
        badminton_expenses = sum(cash_flow_obj.search(badminton_expenses_domain).mapped('amount'))
        
        # Ümumi hesablamalar
        total_badminton_income = badminton_sales_income + badminton_lessons_income + badminton_other_income
        badminton_balance = total_badminton_income - badminton_expenses
        
        values.update({
            'badminton_sales_income': badminton_sales_income,
            'badminton_lessons_income': badminton_lessons_income,
            'badminton_other_income': badminton_other_income,
            'badminton_expenses': badminton_expenses,
            'total_badminton_income': total_badminton_income,
            'badminton_balance': badminton_balance,
        })

    def action_refresh(self):
        """Badminton balansını yenilə"""
        values = {}
        self._calculate_badminton_balance(values)
        self.write(values)
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def _open_badminton_cash_view(self, name, domain):
        """Badminton kassa əməliyyatları view-nı açır"""
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': 'volan.cash.flow',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {'default_sport_type': 'badminton'},
            'target': 'current'
        }

    def show_badminton_sales(self):
        """Badminton satış gəlirlərini göstərir"""
        self.ensure_one()
        domain = self._get_date_domain() + [
            ('sport_type', '=', 'badminton'),
            ('category', '=', 'badminton_sale'),
            ('transaction_type', '=', 'income')
        ]
        return self._open_badminton_cash_view('Badminton Satış Gəlirləri', domain)

    def show_badminton_lessons(self):
        """Badminton dərs gəlirlərini göstərir"""
        self.ensure_one()
        domain = self._get_date_domain() + [
            ('sport_type', '=', 'badminton'),
            ('category', '=', 'badminton_lesson'),
            ('transaction_type', '=', 'income')
        ]
        return self._open_badminton_cash_view('Badminton Dərs Gəlirləri', domain)

    def show_badminton_other_income(self):
        """Digər badminton gəlirlərini göstərir"""
        self.ensure_one()
        domain = self._get_date_domain() + [
            ('sport_type', '=', 'badminton'),
            ('category', 'not in', ['badminton_sale', 'badminton_lesson']),
            ('transaction_type', '=', 'income')
        ]
        return self._open_badminton_cash_view('Digər Badminton Gəlirləri', domain)
        
    def show_badminton_expenses(self):
        """Badminton xərclərini göstərir"""
        self.ensure_one()
        domain = self._get_date_domain() + [
            ('sport_type', '=', 'badminton'),
            ('transaction_type', '=', 'expense')
        ]
        return self._open_badminton_cash_view('Badminton Xərcləri', domain)

    @api.onchange('date_filter', 'date_from', 'date_to')
    def _onchange_date_filter(self):
        """Tarix filtri dəyişəndə badminton balansını yenilə"""
        values = {}
        self._calculate_badminton_balance(values)
        for field, value in values.items():
            setattr(self, field, value)