
-- ============================================
-- 1. ГРЯЗНОЕ ЧТЕНИЕ (Dirty Read) — не работает в PostgreSQL
-- ============================================

-- СЕССИЯ 1
-- Открыть в первой сессии:
BEGIN;
UPDATE products
SET price = 3000
WHERE product_id = '8149336b-96c9-4d36-9763-5f02900d2d20';
-- НЕ ДЕЛАТЬ COMMIT/ROLLBACK пока

-- СЕССИЯ 2
-- Открыть во второй сессии:
BEGIN ISOLATION LEVEL READ COMMITTED;
SELECT price
FROM products
WHERE product_id = '8149336b-96c9-4d36-9763-5f02900d2d20';
-- PostgreSQL НЕ покажет 3000, а покажет старую цену

COMMIT;

-- СЕССИЯ 1
-- Вернуть всё назад
ROLLBACK;



-- ============================================
-- 2. НЕВТОРЯЮЩЕЕСЯ ЧТЕНИЕ (Non-repeatable Read)
-- ============================================

-- СЕССИЯ 1
BEGIN ISOLATION LEVEL READ COMMITTED;

-- Первый SELECT
SELECT price
FROM products
WHERE product_id = '8149336b-96c9-4d36-9763-5f02900d2d20';

-- Ожидаем…

-- СЕССИЯ 2
BEGIN;
UPDATE products
SET price = 30000
WHERE product_id = '8149336b-96c9-4d36-9763-5f02900d2d20';
COMMIT;

-- СЕССИЯ 1
-- Второй SELECT
SELECT price
FROM products
WHERE product_id = '8149336b-96c9-4d36-9763-5f02900d2d20';
-- Видим другую цену — это и есть non-repeatable read

COMMIT;



-- ============================================
-- 3. ФАНТОМНОЕ ЧТЕНИЕ (Phantom Read)
-- ============================================

-- Подготовка: создать категорию Electronics, если её нет
INSERT INTO categories (category_id, name)
VALUES ('00000000-0000-0000-0000-000000000099', 'Electronics')
ON CONFLICT DO NOTHING;


-- СЕССИЯ 1
BEGIN ISOLATION LEVEL READ COMMITTED;

-- Первый COUNT
SELECT COUNT(*) 
FROM products p
JOIN categories c ON p.category_id = c.category_id
WHERE c.name = 'Electronics';

-- Ожидаем…

-- СЕССИЯ 2
BEGIN;
INSERT INTO products (product_id, name, category_id, price, stock, manufacturer)
VALUES (
    uuid_generate_v4(),
    'Headphones',
    '00000000-0000-0000-0000-000000000099',
    149.99,
    20,
    'Sony'
);
COMMIT;

-- СЕССИЯ 1
-- Повторный COUNT
SELECT COUNT(*) 
FROM products p
JOIN categories c ON p.category_id = c.category_id
WHERE c.name = 'Electronics';
-- Если количество увеличилось — фантомное чтение

COMMIT;
