-- Подключаем расширения для поиска
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS pg_bigm;

-- Подключаем расширение для криптографии
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Индекс для быстрого поиска по name в products
CREATE INDEX IF NOT EXISTS trgm_idx_products_name
ON products USING gin (name gin_trgm_ops);

-- Индекс для быстрого поиска по username в users
CREATE INDEX IF NOT EXISTS bigm_idx_products_name
ON products USING gin (name gin_bigm_ops);

-- Шифруем существующие пароли (если ещё не зашифрованы)
UPDATE users
SET hashed_password = pgp_sym_encrypt(hashed_password, 'encryption_key')
WHERE hashed_password NOT LIKE '-----BEGIN PGP MESSAGE-----%';

-- Вставка нового пользователя с шифрованием

INSERT INTO users (username, hashed_password, email)
VALUES (
    'test_user',
    pgp_sym_encrypt('securepassword', 'encryption_key'),
    'test@example.com'
)
ON CONFLICT (email) DO NOTHING;

-- Проверка: выводим зашифрованный пароль
SELECT username, hashed_password
FROM users
WHERE username = 'test_user';

-- Проверка: расшифровка пароля
SELECT username,
       pgp_sym_decrypt(hashed_password::bytea, 'encryption_key') AS decrypted_password
FROM users
WHERE username = 'test_user';


--  Поиск с использованием индекса (LIKE)

EXPLAIN ANALYZE
SELECT *
FROM products
WHERE name LIKE '%Adaptive zero administration conglomeration%';
