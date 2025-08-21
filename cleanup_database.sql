-- PostgreSQL database-də orphaned records-ları təmizləmək üçün SQL
-- Bu SQL-ləri pgAdmin və ya psql ilə işlədin:

-- 1. Mövcud olmayan modellərə aid ir.model.data record-larını sil
DELETE FROM ir_model_data 
WHERE model = 'badminton.court' 
   OR model LIKE '%badminton.court%';

-- 2. Mövcud olmayan modelləri ir_model table-dan sil
DELETE FROM ir_model 
WHERE model = 'badminton.court';

-- 3. Mövcud olmayan model field-lərini sil
DELETE FROM ir_model_fields 
WHERE model = 'badminton.court';

-- 4. Access rights-ları təmizlə
DELETE FROM ir_model_access 
WHERE model_id NOT IN (SELECT id FROM ir_model);

-- 5. Constraint-ləri yoxla və təmizlə
DELETE FROM ir_model_constraint 
WHERE model NOT IN (SELECT model FROM ir_model);

-- 6. Cache-i təmizlə (Odoo restart lazımdır)
-- Bu SQL-dən sonra Odoo serveri restart edin
