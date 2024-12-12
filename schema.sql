-- Создание расширений
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Таблица roles
CREATE TABLE roles (
    role_id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL
);

-- Таблица users
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) NOT NULL,
    hashed_password TEXT NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL
);

-- Таблица user_roles
CREATE TABLE user_roles (
    user_id UUID NOT NULL,
    role_id INT NOT NULL,
    PRIMARY KEY (user_id, role_id),
    CONSTRAINT fk_user_roles_users FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_user_roles_roles FOREIGN KEY (role_id) REFERENCES roles(role_id) ON DELETE CASCADE
);

-- Таблица categories
CREATE TABLE categories (
    category_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL
);

-- Таблица products
CREATE TABLE products (
    product_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(150) NOT NULL,
    description TEXT,
    category_id UUID,
    price NUMERIC(10, 2) NOT NULL,
    stock INT NOT NULL,
    manufacturer VARCHAR(150),
    CONSTRAINT fk_products_categories FOREIGN KEY (category_id) REFERENCES categories(category_id) ON DELETE SET NULL
);

-- Таблица cart
CREATE TABLE cart (
    user_id UUID NOT NULL,
    product_id UUID NOT NULL,
    quantity INT NOT NULL,
    PRIMARY KEY (user_id, product_id),
    CONSTRAINT cart_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT cart_product_id_fkey FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
);

-- Таблица orders
CREATE TABLE orders (
    order_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    order_date TIMESTAMP DEFAULT NOW(),
    status VARCHAR(50) NOT NULL,
    total_cost NUMERIC(10, 2) NOT NULL,
    CONSTRAINT fk_orders_users FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Таблица order_items
CREATE TABLE order_items (
    order_id UUID NOT NULL,
    product_id UUID NOT NULL,
    quantity INT NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    PRIMARY KEY (order_id, product_id),
    CONSTRAINT order_items_order_id_fkey FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    CONSTRAINT order_items_product_id_fkey FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
);

-- Таблица order_history
CREATE TABLE order_history (
    history_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID NOT NULL,
    status VARCHAR(50) NOT NULL,
    change_date TIMESTAMP DEFAULT NOW(),
    CONSTRAINT fk_order_history_orders FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
);

-- Таблица reviews
CREATE TABLE reviews (
    review_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID NOT NULL,
    user_id UUID NOT NULL,
    rating INT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    review_date TIMESTAMP DEFAULT NOW(),
    CONSTRAINT fk_reviews_products FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
    CONSTRAINT fk_reviews_users FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);




-- Таблица support_sessions
CREATE TABLE support_sessions (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    start_time TIMESTAMP DEFAULT NOW(),
    end_time TIMESTAMP,
    status VARCHAR(50) NOT NULL DEFAULT 'open',
    CONSTRAINT fk_support_sessions_users FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Таблица support_messages
CREATE TABLE support_messages (
    message_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL,
    sender VARCHAR(50) NOT NULL CHECK (sender IN ('user','support')),
    message TEXT NOT NULL,
    sent_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT fk_support_messages_sessions FOREIGN KEY (session_id) REFERENCES support_sessions(session_id) ON DELETE CASCADE
);


-- Заполнение таблиц тестовыми данными
INSERT INTO roles (name) VALUES ('User'), ('Admin');

CREATE OR REPLACE PROCEDURE process_user_order(uid UUID)
LANGUAGE plpgsql
AS $$
DECLARE
    cart_item RECORD;
    total_cost NUMERIC := 0;
    order_id UUID := uuid_generate_v4();
BEGIN
    -- Получаем товары из корзины
    FOR cart_item IN
        SELECT product_id, quantity, price, stock
        FROM cart_details
        WHERE user_id = uid
    LOOP
        -- Проверяем наличие на складе
        IF cart_item.quantity > cart_item.stock THEN
            RAISE EXCEPTION 'Недостаточно товара на складе для продукта %', cart_item.product_id;
        END IF;
        -- Считаем итоговую стоимость
        total_cost := total_cost + (cart_item.price * cart_item.quantity);
    END LOOP;

    IF total_cost = 0 THEN
        RAISE EXCEPTION 'Корзина пуста.';
    END IF;

    -- Создаем новый заказ
    INSERT INTO orders (order_id, user_id, total_cost, order_date, status)
    VALUES (order_id, uid, total_cost, NOW(), 'Pending');

    -- Добавляем товары из корзины в order_items и обновляем остатки
    FOR cart_item IN
        SELECT product_id, quantity, price, stock
        FROM cart_details
        WHERE user_id = uid
    LOOP
        INSERT INTO order_items (order_id, product_id, quantity, price)
        VALUES (order_id, cart_item.product_id, cart_item.quantity, cart_item.price);

        UPDATE products SET stock = stock - cart_item.quantity WHERE product_id = cart_item.product_id;
    END LOOP;

    -- Очищаем корзину пользователя
    DELETE FROM cart WHERE user_id = uid;
END;
$$;

CREATE OR REPLACE FUNCTION get_average_product_rating(product_id UUID)
RETURNS NUMERIC AS $$
BEGIN
    RETURN (SELECT AVG(rating)::NUMERIC FROM reviews WHERE product_id = product_id);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION log_order_history()
RETURNS TRIGGER AS $$
DECLARE
    history_id UUID := uuid_generate_v4();
BEGIN
    INSERT INTO order_history (history_id, order_id, status, change_date)
    VALUES (history_id, NEW.order_id, NEW.status, NOW());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION log_order_history()
RETURNS TRIGGER AS $$
DECLARE
    history_id UUID := uuid_generate_v4();
BEGIN
    INSERT INTO order_history (history_id, order_id, status, change_date)
    VALUES (history_id, NEW.order_id, NEW.status, NOW());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER order_history_trigger
   AFTER INSERT OR UPDATE ON orders
   FOR EACH ROW
   EXECUTE FUNCTION log_order_history();

CREATE OR REPLACE VIEW cart_details AS
SELECT 
    c.user_id,
    c.product_id,
    p.name,
    p.description,
    p.price,
    p.stock,
    c.quantity,
    (p.price * c.quantity) AS total_cost
FROM cart c
JOIN products p ON c.product_id = p.product_id;

CREATE OR REPLACE VIEW cart_details AS
SELECT 
    c.user_id,
    c.product_id,
    p.name,
    p.description,
    p.price,
    p.stock,
    c.quantity,
    (p.price * c.quantity) AS total_cost
FROM cart c
JOIN products p ON c.product_id = p.product_id;

CREATE OR REPLACE FUNCTION log_order_history()
RETURNS TRIGGER AS $$
DECLARE
    history_id UUID := uuid_generate_v4();
BEGIN
    INSERT INTO order_history (history_id, order_id, status, change_date)
    VALUES (history_id, NEW.order_id, NEW.status, NOW());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER order_history_trigger
AFTER INSERT OR UPDATE ON orders
FOR EACH ROW
EXECUTE FUNCTION log_order_history();

CREATE TRIGGER order_history_trigger
AFTER INSERT OR UPDATE ON orders
FOR EACH ROW
EXECUTE FUNCTION log_order_history();

CREATE OR REPLACE PROCEDURE process_user_order(uid UUID)
LANGUAGE plpgsql
AS $$
DECLARE
    cart_item RECORD;
    total_cost NUMERIC := 0;
    order_id UUID := uuid_generate_v4();
BEGIN
    -- Получаем товары из корзины
    FOR cart_item IN
        SELECT product_id, quantity, price, stock
        FROM cart_details
        WHERE user_id = uid
    LOOP
        -- Проверяем наличие на складе
        IF cart_item.quantity > cart_item.stock THEN
            RAISE EXCEPTION 'Недостаточно товара на складе для продукта %', cart_item.product_id;
        END IF;
        -- Считаем итоговую стоимость
        total_cost := total_cost + (cart_item.price * cart_item.quantity);
    END LOOP;

    IF total_cost = 0 THEN
        RAISE EXCEPTION 'Корзина пуста.';
    END IF;

    -- Создаем новый заказ
    INSERT INTO orders (order_id, user_id, total_cost, order_date, status)
    VALUES (order_id, uid, total_cost, NOW(), 'Pending');

    -- Добавляем товары из корзины в order_items и обновляем остатки
    FOR cart_item IN
        SELECT product_id, quantity, price, stock
        FROM cart_details
        WHERE user_id = uid
    LOOP
        INSERT INTO order_items (order_id, product_id, quantity, price)
        VALUES (order_id, cart_item.product_id, cart_item.quantity, cart_item.price);

        UPDATE products SET stock = stock - cart_item.quantity WHERE product_id = cart_item.product_id;
    END LOOP;

    -- Очищаем корзину пользователя
    DELETE FROM cart WHERE user_id = uid;
END;
$$;