-- B-tree индексы
CREATE INDEX idx_users_email ON users USING btree(email);
CREATE INDEX idx_products_category_id ON products USING btree(category_id);

EXPLAIN ANALYZE
SELECT * 
FROM users 
WHERE email = 'test@example.com';

EXPLAIN ANALYZE
SELECT * 
FROM products 
WHERE category_id = '123e4567-e89b-12d3-a456-426614174000';

-- GIN индекс для полнотекстового поиска
CREATE INDEX idx_products_description_gin ON products USING gin(to_tsvector('english', description));
CREATE INDEX idx_reviews_comment_gin ON reviews USING gin(to_tsvector('english', comment));

-- Запрос
EXPLAIN ANALYZE
SELECT * FROM products
WHERE to_tsvector('english', description) @@ to_tsquery('laptop');

-- Запрос
EXPLAIN ANALYZE
SELECT * FROM reviews
WHERE to_tsvector('english', comment) @@ to_tsquery('good');

-- BRIN индексы для временных данных
-- 1. Создание BRIN-индекса с параметром pages_per_range
CREATE INDEX idx_orders_order_date_brin ON orders USING brin(order_date) WITH (pages_per_range = 64);

-- Запрос

EXPLAIN ANALYZE
SELECT * 
FROM orders 
WHERE order_date BETWEEN '2022-01-01' AND '2023-01-31';