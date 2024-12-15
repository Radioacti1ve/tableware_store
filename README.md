### Гайд по созданию базы данных и настройке `.env`

---

#### 1. **Установка PostgreSQL**

1. Убедитесь, что PostgreSQL установлен на вашем компьютере.
   - На **Ubuntu**:
     ```bash
     sudo apt update
     sudo apt install postgresql postgresql-contrib
     ```

2. Убедитесь, что PostgreSQL работает:
   ```bash
   sudo service postgresql start  # Для Ubuntu
   ```

3. Войдите в PostgreSQL:
   ```bash
   psql -U postgres
   ```

---

#### 2. **Создание базы данных и пользователя**

1. **Создайте нового пользователя и базу данных:**
   ```sql
   CREATE USER project_user WITH PASSWORD 'project_password';
   CREATE DATABASE project_db OWNER project_user;
   ```

2. **Дайте пользователю необходимые права:**
   ```sql
   GRANT ALL PRIVILEGES ON DATABASE project_db TO project_user;
   ```

3. **Подключитесь к базе данных:**
   ```bash
   psql -U project_user -d project_db
   ```

4. **Установите расширение `uuid-ossp` для работы с UUID:**
   ```sql
   CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
   ```

---

#### 3. **Создание файла `.env`**

Для удобного хранения конфиденциальных данных, таких как URL подключения к базе данных, создайте файл `.env` в корне вашего проекта.

**Пример содержимого `.env`:**
```dotenv
# Настройки базы данных
DB_HOST=localhost
DB_PORT=5432
DB_NAME=project_db
DB_USER=project_user
DB_PASSWORD=project_password

# Настройки приложения
APP_ENV=development
DEBUG=True

# Секретный ключ приложения
SECRET_KEY=your_secret_key
```

**Объяснение параметров:**
- `DB_HOST`: Адрес хоста базы данных (локально — `localhost`).
- `DB_PORT`: Порт подключения (стандартный для PostgreSQL — `5432`).
- `DB_NAME`: Имя вашей базы данных (`project_db`).
- `DB_USER`: Имя пользователя базы данных (`project_user`).
- `DB_PASSWORD`: Пароль пользователя (`project_password`).
---

#### 4. **Запуск скрипта для создания таблиц**

Если у вас есть SQL-скрипт для создания таблиц, запустите его в базе данных.

1. Сохраните скрипт (например, `schema.sql`).
2. Запустите его с помощью `psql`:
   ```bash
   psql -U project_user -d project_db -f schema.sql
   ```

---

#### 5. **Проверка базы данных**

После выполнения скрипта проверьте, что таблицы созданы:

1. Подключитесь к базе данных:
   ```bash
   psql -U project_user -d project_db
   ```

2. Выполните команду для отображения всех таблиц:
   ```sql
   \dt
   ```

---

#### 6. **Как использовать `.env` в Python**

Для работы с `.env` в Python используйте библиотеку `python-dotenv`.

1. Установите библиотеку:
   ```bash
   pip install python-dotenv
   ```


Ниже приведены реализации представления, триггера и функции в PostgreSQL.
Все уже написано в schema.sql. Нужно просто дообновить базу данных.

---

### 1. Представление для соединения `cart` и `products`

Цель: Упростить получение детальной информации о товарах в корзине без повторяющегося JOIN-запроса в коде приложения.

**SQL для создания представления:**
```sql
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
```
---

### 2. Триггер на формирование `order_history`

Цель: Автоматически добавлять запись в `order_history` при вставке нового заказа или изменении статуса заказа. При каждом изменении статуса в таблице `orders` мы хотим автоматически создать запись в `order_history`.


1. Триггерная функция, которая будет вставлять запись в `order_history` при изменении статуса заказа:
   
   ```sql
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
   ```

2. Создание триггера на таблицу `orders`, который будет вызываться при вставке и обновлении строки:

   ```sql
   CREATE TRIGGER order_history_trigger
   AFTER INSERT OR UPDATE ON orders
   FOR EACH ROW
   EXECUTE FUNCTION log_order_history();
   ```

---

### 3. Функция среднего рейтинга товара

Цель: Вынести вычисление среднего рейтинга товара на уровень базы данных.

**SQL для создания функции:**
```sql
CREATE OR REPLACE FUNCTION get_average_product_rating(product_id UUID)
RETURNS NUMERIC AS $$
BEGIN
    RETURN (SELECT AVG(rating)::NUMERIC FROM reviews WHERE product_id = product_id);
END;
$$ LANGUAGE plpgsql;
```

---

### 4. Процедура заказа 

```sql
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
```
