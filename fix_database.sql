-- PostgreSQL database-də manual olaraq sütun əlavə etmək üçün SQL
-- Bu SQL-i pgAdmin və ya psql ilə işlədin:

ALTER TABLE res_partner ADD COLUMN IF NOT EXISTS badminton_balance INTEGER DEFAULT 0;
UPDATE res_partner SET badminton_balance = 0 WHERE badminton_balance IS NULL;

-- Əlavə təhlükəsizlik üçün:
CREATE INDEX IF NOT EXISTS idx_res_partner_badminton_balance ON res_partner(badminton_balance);

-- SQL tamamlandıqdan sonra Odoo serveri yenidən başladın
