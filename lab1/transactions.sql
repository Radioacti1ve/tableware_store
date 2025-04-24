-- ============================================
--  Пример 1: Обычная транзакция (корзина + заказ)
-- ============================================

BEGIN;

-- Добавим товар в корзину пользователя
INSERT INTO cart (user_id, product_id, quantity)
VALUES (
    '867e5f02-ba17-4f06-8b7e-f0f464bfa3dc',
    '8149336b-96c9-4d36-9763-5f02900d2d20',
    2
)
ON CONFLICT (user_id, product_id)
DO UPDATE SET quantity = cart.quantity + 2;

-- Создание заказа (цена товара 99.99 * 2 = 199.98)
INSERT INTO orders (order_id, user_id, total_cost, status)
VALUES (
    uuid_generate_v4(),
    '867e5f02-ba17-4f06-8b7e-f0f464bfa3dc',
    199.98,
    'Pending'
);

COMMIT;

--  Проверка корзины и заказов после Примера 1
SELECT * FROM cart
WHERE user_id = '867e5f02-ba17-4f06-8b7e-f0f464bfa3dc'
  AND product_id = '8149336b-96c9-4d36-9763-5f02900d2d20';

SELECT * FROM orders
WHERE user_id = '867e5f02-ba17-4f06-8b7e-f0f464bfa3dc'
ORDER BY order_date DESC
LIMIT 1;


-- ============================================
--  Пример 2: Ошибочная транзакция с откатом
-- ============================================

BEGIN;

-- Попытка вставки отзыва с недопустимым рейтингом (вызовет ошибку)
INSERT INTO reviews (review_id, product_id, user_id, rating, comment)
VALUES (
    uuid_generate_v4(),
    '8149336b-96c9-4d36-9763-5f02900d2d20',
    '867e5f02-ba17-4f06-8b7e-f0f464bfa3dc',
    10,  --  Ошибка: CHECK (rating >= 1 AND rating <= 5)
    'Excellent product!'
);

-- Этот запрос не выполнится
INSERT INTO cart (user_id, product_id, quantity)
VALUES (
    '867e5f02-ba17-4f06-8b7e-f0f464bfa3dc',
    '8149336b-96c9-4d36-9763-5f02900d2d20',
    1
);

ROLLBACK;

--  Проверка: отзыв с рейтингом 10 не добавлен
SELECT * FROM reviews
WHERE user_id = '867e5f02-ba17-4f06-8b7e-f0f464bfa3dc'
  AND rating > 5;


-- ============================================
--  Пример 3: Транзакция с REPEATABLE READ
-- ============================================

BEGIN ISOLATION LEVEL REPEATABLE READ;

-- Чтение остатка товара
SELECT stock
FROM products
WHERE product_id = '8149336b-96c9-4d36-9763-5f02900d2d20';

-- Уменьшение остатков
UPDATE products
SET stock = stock - 1
WHERE product_id = '8149336b-96c9-4d36-9763-5f02900d2d20';

COMMIT;

--  Проверка остатка товара после Примера 3
SELECT stock
FROM products
WHERE product_id = '8149336b-96c9-4d36-9763-5f02900d2d20';


-- ============================================
--  Пример 4: READ COMMITTED с блокировкой строки
-- ============================================

SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
BEGIN;

-- Блокируем строку товара
SELECT stock
FROM products
WHERE product_id = '8149336b-96c9-4d36-9763-5f02900d2d20'
FOR UPDATE;

-- Уменьшаем остаток
UPDATE products
SET stock = stock - 2
WHERE product_id = '8149336b-96c9-4d36-9763-5f02900d2d20';

-- Создаем заказ
INSERT INTO orders (order_id, user_id, total_cost, status)
VALUES (
    uuid_generate_v4(),
    '867e5f02-ba17-4f06-8b7e-f0f464bfa3dc',
    199.98,
    'Pending'
);

COMMIT;

--  Проверка остатков и заказов после Примера 4
SELECT stock
FROM products
WHERE product_id = '8149336b-96c9-4d36-9763-5f02900d2d20';

SELECT * FROM orders
WHERE user_id = '867e5f02-ba17-4f06-8b7e-f0f464bfa3dc'
ORDER BY order_date DESC
LIMIT 1;
