# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import qrcode
import base64
import io

class VolanPartner(models.Model):
    _inherit = 'res.partner'

    # 1. Doğum Tarixi Sahəsi
    birth_date = fields.Date(string="Doğum Tarixi")

    age = fields.Integer(string="Yaş", compute='_compute_age', store=False)

    # 2. Filial Sahəsi
    branch = fields.Selection([
        ('genclik', 'Gənclik'),
        ('yasamal', 'Yasamal')
    ], string="Filial", required=True)
    
    # 2.1. İdman Növü Sahəsi
    sport_type = fields.Selection([
        ('badminton', 'Badminton'),
        ('basketball', 'Basketbol'),
        ('both', 'Hər İkisi')
    ], string="İdman Növü", default='badminton', help="Müştərinin hansı idman növü ilə məşğul olduğunu göstərir")
    
    # 3. Müştəri Mənbəyi
    customer_source = fields.Selection([
        ('instagram', 'Instagram'),
        ('facebook', 'Facebook'),
        ('friends', 'Dost və Tanışlar'),
        ('outdoor', 'Küçə Reklamı'),
        ('other', 'Digər')
    ], string="Müştəri Mənbəyi")
    
    # 4. Əlavə Məlumatlar Sahəsi
    additional_info = fields.Text(string="Əlavə Məlumatlar")

    # 3. QR Kod Şəkli Sahəsi (Hesablanan)
    qr_code_image = fields.Binary(string="QR Kod", compute='_compute_qr_code', store=True)

    # 4. Badminton Balans Sahəsi
    badminton_balance = fields.Integer(string="Badminton Balansı (saat)", default=0, 
                                      help="Müştərinin qalan badminton saatlarının sayı")
    
    # 4.1. Badminton Depozit Balansı
    badminton_deposit_balance = fields.Float(string="Depozit Balansı", default=0.0,
                                            help="Müştərinin depozit hesabındakı qalıq məbləğ (AZN)")
    
    # 5. Badminton Satış Tarixçəsi
    badminton_sale_ids = fields.One2many('badminton.sale', 'partner_id', string="Badminton Satışları")
    """ Close history
    badminton_balance_history_ids = fields.One2many('badminton.balance.history', 'partner_id', string="Balans Tarixçəsi")
    """
    monthly_balance_ids = fields.One2many('badminton.monthly.balance', 'partner_id', string="Aylıq Paket Balansları")
    monthly_balance_units = fields.Float(string="Aylıq Balans (vahid)", compute='_compute_monthly_balances', store=False)
    monthly_balance_hours = fields.Float(string="Aylıq Balans (saat)", compute='_compute_monthly_balances', store=False)
    
    genclik_monthly_balance_ids = fields.One2many('badminton.monthly.balance.genclik', 'partner_id', string="Gənclik Aylıq Paket Balansları")
    genclik_monthly_balance_units = fields.Float(string="Gənclik Aylıq Balans (vahid)", compute='_compute_genclik_monthly_balances', store=False)
    genclik_monthly_balance_hours = fields.Float(string="Gənclik Aylıq Balans (saat)", compute='_compute_genclik_monthly_balances', store=False)

    # 5.1. Gənclik Filialı Satış Tarixçəsi
    genclik_sale_ids = fields.One2many(
        'badminton.sale.genclik',
        'partner_id',
        string="Gənclik Badminton Satışları",
        groups="volan_genclikk.group_genclik_admin,volan_genclikk.group_genclik_satici"
    )
    """ Close history
    genclik_balance_history_ids = fields.One2many(
        'badminton.balance.history.genclik',
        'partner_id',
        string="Gənclik Balans Tarixçəsi",
        groups="volan_genclikk.group_genclik_admin,volan_genclikk.group_genclik_satici"
    )
    """
    
    # 6. Basketbol Üzvlüklər
    basketball_membership_ids = fields.One2many('sport.membership', 'partner_id', string="Basketbol Üzvlüklər")
    
    # 7. Məşqçi bayrağı
    is_coach = fields.Boolean(string="Məşqçidir", default=False, help="İşçinin məşqçi olub olmadığını göstərir")

    @api.constrains('mobile', 'birth_date')
    def _check_duplicate_contact(self):
        """Eyni mobil nömrəsi və doğum tarixi olan kontaktın olmasını yoxlayır"""
        for partner in self:
            # Yalnız şirkət olmayan və doğum tarixi olan müştərilər üçün yoxla
            if partner.is_company or not partner.birth_date:
                continue
            
            # Telefon nömrəsi olmalıdır
            phone_number = partner.mobile
            if not phone_number:
                continue
            
            # Eyni telefon və doğum tarixi olan başqa kontakt var mı?
            domain = [
                ('id', '!=', partner.id),
                ('birth_date', '=', partner.birth_date),
                ('is_company', '=', False),
                ('mobile', '=', phone_number)
            ]
            
            duplicate = self.search(domain, limit=1)
            if duplicate:
                raise ValidationError(
                    f"Bu telefon nömrəsi ({phone_number}) və doğum tarixi ({partner.birth_date}) "
                    f"ilə artıq '{duplicate.name}' adlı kontakt mövcuddur!\n"
                    f"Dublikat yaratmaq olmaz."
                )

    @api.depends('birth_date')
    def _compute_age(self):
        """Müştərinin doğum tarixindən yaşını hesablayır"""
        today = fields.Date.today()
        for partner in self:
            if partner.birth_date:
                birth_date = partner.birth_date
                age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                partner.age = age
            else:
                partner.age = 0

    @api.depends('name', 'write_date')
    def _compute_qr_code(self):
        """Her müşteri üçün unikal ID və adına əsaslanan bir QR kod yaradır."""
        for partner in self:
            if partner.id and partner.name:
                # ID + Ad kombinasiyası ilə daha unikal QR kod
                qr_payload = f"https://volan.odoo.com.az/qr/genclik?pid={partner.id}&t={partner.qr_token}"
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

    @api.depends('monthly_balance_ids.remaining_units', 'monthly_balance_ids.state', 'monthly_balance_ids.expiry_date', 'monthly_balance_ids.deduction_factor')
    def _compute_monthly_balances(self):
        today = fields.Date.today()
        for partner in self:
            active_lines = partner._get_active_monthly_lines(today)
            partner.monthly_balance_units = sum(active_lines.mapped('remaining_units'))
            partner.monthly_balance_hours = sum(line.get_hours_available() for line in active_lines)

    @api.depends('genclik_monthly_balance_ids.remaining_units', 'genclik_monthly_balance_ids.state', 'genclik_monthly_balance_ids.expiry_date', 'genclik_monthly_balance_ids.deduction_factor')
    def _compute_genclik_monthly_balances(self):
        today = fields.Date.today()
        for partner in self:
            active_lines = partner._get_genclik_active_monthly_lines(today)
            partner.genclik_monthly_balance_units = sum(active_lines.mapped('remaining_units'))
            partner.genclik_monthly_balance_hours = sum(line.get_hours_available() for line in active_lines)

    def _get_active_monthly_lines(self, date_ref=None):
        self.ensure_one()
        date_ref = date_ref or fields.Date.today()
        return self.monthly_balance_ids.filtered(
            lambda l: l.remaining_units > 0 and l.state == 'active' and (not l.expiry_date or l.expiry_date >= date_ref)
        )

    def _get_genclik_active_monthly_lines(self, date_ref=None):
        self.ensure_one()
        date_ref = date_ref or fields.Date.today()
        return self.genclik_monthly_balance_ids.filtered(
            lambda l: l.remaining_units > 0 and l.state == 'active' and (not l.expiry_date or l.expiry_date >= date_ref)
        )

    def get_monthly_hours_available(self):
        self.ensure_one()
        return sum(line.get_hours_available() for line in self._get_active_monthly_lines())

    def get_genclik_monthly_hours_available(self):
        self.ensure_one()
        return sum(line.get_hours_available() for line in self._get_genclik_active_monthly_lines())

    def get_total_badminton_hours_available(self):
        self.ensure_one()
        return (self.badminton_balance or 0.0) + self.get_monthly_hours_available()

    def get_total_genclik_badminton_hours_available(self):
        self.ensure_one()
        return (self.badminton_balance or 0.0) + self.get_genclik_monthly_hours_available()

    def consume_badminton_hours(self, required_hours, transaction_type='usage', description='', session=None):
        self.ensure_one()
        if required_hours <= 0:
            return True

        remaining_hours = required_hours
        remaining_hours -= self._consume_from_monthly(remaining_hours, transaction_type, description, session)

        if remaining_hours <= 0:
            return True

        return self._consume_normal_hours(remaining_hours, transaction_type, description, session)

    def consume_genclik_badminton_hours(self, required_hours, transaction_type='usage', description='', session=None):
        self.ensure_one()
        if required_hours <= 0:
            return True

        remaining_hours = required_hours
        remaining_hours -= self._consume_from_genclik_monthly(remaining_hours, transaction_type, description, session)

        if remaining_hours <= 0:
            return True

        return self._consume_normal_hours(remaining_hours, transaction_type, description, session)

    def _consume_from_monthly(self, required_hours, transaction_type, description, session):
        lines = self._get_active_monthly_lines()
        if not lines:
            return 0.0

        """ Close history
        history_model = self.env['badminton.balance.history']
        """
        remaining_hours = required_hours
        hours_covered = 0.0

        for line in lines:
            hours_available = line.get_hours_available()
            if hours_available <= 0:
                continue

            hours_to_take = min(remaining_hours, hours_available)
            if hours_to_take <= 0:
                break

            units_used, before, after = line.consume_hours(hours_to_take)
            history_model.create({
                'partner_id': self.id,
                'session_id': session.id if session else False,
                'hours_used': units_used,
                'balance_before': before,
                'balance_after': after,
                'transaction_type': transaction_type,
                'description': description or 'Aylıq paket istifadə olundu',
                'balance_channel': 'monthly',
                'monthly_line_id': line.id,
            })

            hours_covered += hours_to_take
            remaining_hours -= hours_to_take
            if remaining_hours <= 0:
                break

        return hours_covered

    def _consume_from_genclik_monthly(self, required_hours, transaction_type, description, session):
        lines = self._get_genclik_active_monthly_lines()
        if not lines:
            return 0.0

        """ Close history
        history_model = self.env['badminton.balance.history.genclik']
        """
        remaining_hours = required_hours
        hours_covered = 0.0

        for line in lines:
            hours_available = line.get_hours_available()
            if hours_available <= 0:
                continue

            hours_to_take = min(remaining_hours, hours_available)
            if hours_to_take <= 0:
                break

            units_used, before, after = line.consume_hours(hours_to_take)
            """ Close history
            history_model.create({
                'partner_id': self.id,
                'session_id': session.id if session else False,
                'hours_used': units_used,
                'balance_before': before,
                'balance_after': after,
                'transaction_type': transaction_type,
                'description': description or 'Gənclik aylıq paket istifadə olundu',
                'balance_channel': 'monthly',
                'monthly_line_id': line.id,
            })
            """

            hours_covered += hours_to_take
            remaining_hours -= hours_to_take
            if remaining_hours <= 0:
                break

        return hours_covered

    def _consume_normal_hours(self, required_hours, transaction_type, description, session):
        current_balance = self.badminton_balance or 0.0
        if current_balance < required_hours:
            total_available = self.get_total_badminton_hours_available()
            raise ValidationError(
                f'{self.name} müştərisinin kifayət qədər balansı yoxdur! '
                f'Normal balans: {current_balance} saat, ümumi (aylıq+normal): {total_available} saat, '
                f'tələb olunan: {required_hours} saat'
            )

        new_balance = current_balance - required_hours
        self.badminton_balance = new_balance

        """ Close history
        self.env['badminton.balance.history'].create({
            'partner_id': self.id,
            'session_id': session.id if session else False,
            'hours_used': required_hours,
            'balance_before': current_balance,
            'balance_after': new_balance,
            'transaction_type': transaction_type,
            'description': description or 'Badminton balansından istifadə olundu',
            'balance_channel': 'normal',
        })
        return True
        """




    """@api.model
    def _auto_init(self):
        res = super(VolanPartner, self)._auto_init()
        
        # Check if badminton_balance column exists, if not add it
        try:
            self.env.cr.execute("SELECT badminton_balance FROM res_partner LIMIT 1")
        except Exception:
            # Column doesn't exist, create it
            self.env.cr.execute("ALTER TABLE res_partner ADD COLUMN badminton_balance INTEGER DEFAULT 0")
            self.env.cr.execute("UPDATE res_partner SET badminton_balance = 0 WHERE badminton_balance IS NULL")
            self.env.cr.commit()
        
        return res"""