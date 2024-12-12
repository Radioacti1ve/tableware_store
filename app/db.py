import asyncpg
import uuid
import bcrypt
import logging

logger = logging.getLogger(__name__)

async def get_all_products(pool):
    """
    Получить список всех продуктов.
    """
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT product_id, name, description, price, stock, manufacturer
            FROM products
        """)

async def get_role_id_by_name(pool: asyncpg.pool.Pool, role_name: str) -> int:
    """
    Получить ID роли по её имени.
    """
    async with pool.acquire() as conn:
        role_id = await conn.fetchval("""
            SELECT role_id FROM roles WHERE name = $1
        """, role_name)
        if not role_id:
            logger.error(f"Роль с именем {role_name} не найдена.")
        return role_id

async def get_user_roles(pool: asyncpg.pool.Pool, user_id: str):
    """
    Получить список ролей пользователя.
    """
    async with pool.acquire() as conn:
        roles = await conn.fetch("""
            SELECT r.name
            FROM user_roles ur
            JOIN roles r ON ur.role_id = r.role_id
            WHERE ur.user_id = $1
        """, user_id)
        return [role['name'] for role in roles]

async def get_user_by_id(pool: asyncpg.pool.Pool, user_id: str):
    """
    Получить информацию о пользователе по user_id.
    """
    async with pool.acquire() as conn:
        return await conn.fetchrow("""
            SELECT username, email
            FROM users
            WHERE user_id = $1
        """, user_id)

async def create_user(pool: asyncpg.pool.Pool, username: str, hashed_password: str, email: str):
    """
    Создать нового пользователя и вернуть его user_id.
    """
    user_id = uuid.uuid4()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (user_id, username, hashed_password, email)
            VALUES ($1, $2, $3, $4)
        """, user_id, username, hashed_password, email)

        role_id = await get_role_id_by_name(pool, "User")
        await conn.execute("""
            INSERT INTO user_roles (user_id, role_id)
            VALUES ($1, $2)
        """, user_id, role_id)
    return user_id

async def get_user_by_email(pool: asyncpg.pool.Pool, email: str):
    """
    Получить пользователя по email.
    """
    async with pool.acquire() as conn:
        return await conn.fetchrow("""
            SELECT * FROM users WHERE email = $1
        """, email)

async def get_product_by_id(pool: asyncpg.pool.Pool, product_id: str):
    """
    Получить информацию о продукте по его ID.
    """
    async with pool.acquire() as conn:
        return await conn.fetchrow("""
            SELECT * FROM products WHERE product_id = $1
        """, product_id)

async def add_to_cart(pool: asyncpg.pool.Pool, user_id: str, product_id: str, quantity: int):
    """
    Добавить товар в корзину пользователя.
    """
    async with pool.acquire() as conn:
        # Проверяем, есть ли уже этот товар в корзине пользователя
        existing = await conn.fetchrow("""
            SELECT quantity FROM cart WHERE user_id = $1 AND product_id = $2
        """, user_id, product_id)

        if existing:
            # Обновляем количество товара в корзине
            await conn.execute("""
                UPDATE cart SET quantity = quantity + $1 WHERE user_id = $2 AND product_id = $3
            """, quantity, user_id, product_id)
        else:
            # Добавляем новый товар в корзину
            await conn.execute("""
                INSERT INTO cart (user_id, product_id, quantity)
                VALUES ($1, $2, $3)
            """, user_id, product_id, quantity)

async def get_cart_items(pool: asyncpg.pool.Pool, user_id: str):
    """
    Получить все товары в корзине пользователя.
    """
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT product_id, name, description, price, stock, quantity, total_cost
            FROM cart_details
            WHERE user_id = $1
        """, user_id)



async def remove_from_cart(pool: asyncpg.pool.Pool, user_id: str, product_id: str):
    """
    Удалить товар из корзины пользователя.
    """
    async with pool.acquire() as conn:
        await conn.execute("""
            DELETE FROM cart WHERE user_id = $1 AND product_id = $2
        """, user_id, product_id)

async def update_cart_quantities(pool: asyncpg.pool.Pool, user_id: str, quantities: dict):
    """
    Обновить количество товаров в корзине пользователя.
    """
    async with pool.acquire() as conn:
        async with conn.transaction():
            for product_id, quantity in quantities.items():
                quantity = int(quantity)
                if quantity <= 0:
                    # Удаляем товар из корзины, если количество <= 0
                    await conn.execute("""
                        DELETE FROM cart WHERE user_id = $1 AND product_id = $2
                    """, user_id, product_id)
                else:
                    # Проверяем доступность товара на складе
                    stock = await conn.fetchval("""
                        SELECT stock FROM products WHERE product_id = $1
                    """, product_id)
                    if quantity > stock:
                        raise ValueError(f"Недостаточно товара на складе для продукта {product_id}")
                    await conn.execute("""
                        UPDATE cart SET quantity = $1 WHERE user_id = $2 AND product_id = $3
                    """, quantity, user_id, product_id)

async def get_last_orders(pool: asyncpg.pool.Pool, user_id: str):
    """
    Получить последние пять заказов пользователя.
    """
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT o.order_id, o.order_date, o.total_cost, ARRAY(
                SELECT p.name
                FROM order_items oi
                JOIN products p ON oi.product_id = p.product_id
                WHERE oi.order_id = o.order_id
            ) AS products
            FROM orders o
            WHERE o.user_id = $1
            ORDER BY o.order_date DESC
            LIMIT 5
        """, user_id)


async def process_order(pool: asyncpg.pool.Pool, user_id: str):
    async with pool.acquire() as conn:
        # Вызов хранимой процедуры, которая сама проведет все операции
        await conn.execute("CALL process_user_order($1)", user_id)

async def add_product(pool, name, description, price, stock, manufacturer, category_id=None):
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO products (product_id, name, description, price, stock, manufacturer, category_id)
            VALUES (uuid_generate_v4(), $1, $2, $3, $4, $5, $6)
        """, name, description, price, stock, manufacturer, category_id)

async def update_product(pool, product_id, name, description, price, stock, manufacturer, category_id=None):
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE products
            SET name = $1, description = $2, price = $3, stock = $4, manufacturer = $5, category_id = $6
            WHERE product_id = $7
        """, name, description, price, stock, manufacturer, category_id, product_id)

async def delete_product(pool, product_id):
    async with pool.acquire() as conn:
        await conn.execute("""
            DELETE FROM products WHERE product_id = $1
        """, product_id)

async def get_all_products_with_categories(pool):
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT p.*, c.name AS category_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.category_id
            ORDER BY p.name
        """)

async def get_all_orders(pool):
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT o.order_id, o.user_id, u.username, o.total_cost, o.order_date, o.status
            FROM orders o
            JOIN users u ON o.user_id = u.user_id
            ORDER BY o.order_date DESC
        """)

async def update_order_status(pool, order_id, new_status):
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE orders SET status = $1 WHERE order_id = $2
        """, new_status, order_id)

async def get_product_by_id(pool: asyncpg.pool.Pool, product_id: str):
    """
    Получить информацию о продукте по его ID.
    """
    async with pool.acquire() as conn:
        return await conn.fetchrow("""
            SELECT * FROM products WHERE product_id = $1
        """, product_id)

async def add_review(pool: asyncpg.pool.Pool, product_id: str, user_id: str, rating: int, comment: str):
    """
    Добавить отзыв к товару.
    """
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO reviews (product_id, user_id, rating, comment)
            VALUES ($1, $2, $3, $4)
        """, product_id, user_id, rating, comment)

async def get_reviews_by_product_id(pool: asyncpg.pool.Pool, product_id: str):
    """
    Получить все отзывы для данного товара.
    """
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT r.*, u.username
            FROM reviews r
            JOIN users u ON r.user_id = u.user_id
            WHERE r.product_id = $1
            ORDER BY r.review_date DESC
        """, product_id)

async def get_average_rating(pool: asyncpg.pool.Pool, product_id: str):
    async with pool.acquire() as conn:
        return await conn.fetchval("""
            SELECT get_average_product_rating($1)
        """, product_id)

async def search_products(pool: asyncpg.pool.Pool, query: str = '', category_id: str = '', manufacturer: str = ''):
    """
    Поиск товаров по названию, описанию, категории (UUID) и производителю.
    """
    async with pool.acquire() as conn:
        sql = """
            SELECT p.product_id, p.name, p.description, p.price, p.stock, p.manufacturer, c.name AS category_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.category_id
            WHERE TRUE
        """
        params = []
        param_index = 1

        # Фильтр по ключевому слову
        if query:
            sql += f" AND (p.name ILIKE '%' || ${param_index} || '%' OR p.description ILIKE '%' || ${param_index} || '%')"
            params.append(query)
            param_index += 1

        # Фильтр по категории (UUID)
        if category_id:
            try:
                category_uuid = str(uuid.UUID(category_id))  # Проверка и преобразование в UUID
                sql += f" AND p.category_id = ${param_index}"
                params.append(category_uuid)  # Добавляем строку UUID
                param_index += 1
            except ValueError:
                raise ValueError(f"Неверный формат UUID для category_id: {category_id}")

        # Фильтр по производителю
        if manufacturer:
            sql += f" AND p.manufacturer ILIKE ${param_index}"
            params.append(f"%{manufacturer}%")
            param_index += 1

        sql += " ORDER BY p.name"
        return await conn.fetch(sql, *params)


async def get_all_categories(pool: asyncpg.pool.Pool):
    """
    Получить список всех категорий.
    """
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT category_id, name
            FROM categories
            ORDER BY name
        """)

async def get_all_manufacturers(pool: asyncpg.pool.Pool):
    """
    Получить список всех производителей.
    """
    async with pool.acquire() as conn:
        records = await conn.fetch("""
            SELECT DISTINCT manufacturer
            FROM products
            WHERE manufacturer IS NOT NULL AND manufacturer != ''
            ORDER BY manufacturer
        """)
        # Преобразуем список записей в список строк
        return [record['manufacturer'] for record in records]


async def add_category(pool: asyncpg.pool.Pool, name: str):
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO categories (category_id, name)
            VALUES (uuid_generate_v4(), $1)
        """, name)

async def update_category(pool: asyncpg.pool.Pool, category_id: str, name: str):
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE categories
            SET name = $1
            WHERE category_id = $2
        """, name, category_id)

async def delete_category(pool: asyncpg.pool.Pool, category_id: str):
    async with pool.acquire() as conn:
        await conn.execute("""
            DELETE FROM categories WHERE category_id = $1
        """, category_id)


async def get_top_sales(pool: asyncpg.pool.Pool, start_date: str, end_date: str, limit: int) -> list[dict]:
    """
    Получить топ X товаров по количеству продаж за указанный период.
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                p.name AS product_name,
                SUM(oi.quantity) AS total_quantity_sold,
                SUM(oi.price * oi.quantity) AS total_revenue
            FROM 
                order_items oi
            JOIN 
                products p ON oi.product_id = p.product_id
            JOIN 
                orders o ON oi.order_id = o.order_id
            WHERE 
                o.order_date BETWEEN $1 AND $2
            GROUP BY 
                p.name
            ORDER BY 
                total_quantity_sold DESC
            LIMIT $3;
        """, start_date, end_date, limit)
    return [dict(row) for row in rows]

async def get_analytics(
    pool: asyncpg.pool.Pool,
    start_date: str,
    end_date: str,
    group_by: str = 'day'
) -> list[dict]:
    """
    Получить аналитические данные за указанный период с группировкой.

    :param pool: Пул соединений с базой данных.
    :param start_date: Начальная дата периода (YYYY-MM-DD).
    :param end_date: Конечная дата периода (YYYY-MM-DD).
    :param group_by: 'day' или 'month' для группировки по дню или месяцу.
    :return: Список словарей с аналитическими данными.
    """
    if group_by not in ['day', 'month']:
        raise ValueError("Параметр group_by должен быть 'day' или 'month'.")

    group_by_clause = f"DATE_TRUNC('{group_by}', o.order_date)"

    async with pool.acquire() as conn:
        rows = await conn.fetch(f"""
            SELECT 
                {group_by_clause} AS period,
                SUM(oi.price * oi.quantity) AS total_revenue,
                SUM(oi.quantity) AS total_items_sold
            FROM 
                orders o
            JOIN 
                order_items oi ON o.order_id = oi.order_id
            JOIN 
                products p ON oi.product_id = p.product_id
            WHERE 
                o.order_date BETWEEN $1 AND $2
            GROUP BY 
                period
            ORDER BY 
                period ASC;
        """, start_date, end_date)
    return [dict(row) for row in rows]

async def get_reviews_by_category(pool: asyncpg.pool.Pool) -> list[dict]:
    """
    Получить анализ отзывов по категориям.
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                c.name AS category_name,
                AVG(r.rating) AS average_rating,
                COUNT(r.review_id) AS total_reviews
            FROM 
                reviews r
            JOIN 
                products p ON r.product_id = p.product_id
            JOIN 
                categories c ON p.category_id = c.category_id
            GROUP BY 
                c.name
            ORDER BY 
                average_rating DESC;
        """)
    return [dict(row) for row in rows]

