# Генерация данных

import psycopg2
import uuid
from faker import Faker
import random
from tqdm import tqdm
from dotenv import load_dotenv
import os

# Загружаем переменные из .env
load_dotenv()

# Читаем из .env
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
SECRET_KEY = os.getenv('SECRET_KEY')

fake = Faker()

# Настройки подключения к базе
conn = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT
)
conn.autocommit = True
cur = conn.cursor()

# Число записей
NUM_USERS = 500_000
NUM_CATEGORIES = 50
NUM_PRODUCTS = 500_000
NUM_ORDERS = 1_000_000
NUM_REVIEWS = 500_000
NUM_SUPPORT_SESSIONS = 100_000
NUM_MESSAGES_PER_SESSION = 5

def save_secret_key():
    # Для примера сохраним SECRET_KEY в таблицу настроек приложения
    cur.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key VARCHAR PRIMARY KEY,
            value VARCHAR NOT NULL
        )
    """)
    cur.execute("""
        INSERT INTO app_settings (key, value) VALUES ('SECRET_KEY', %s)
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
    """, (SECRET_KEY,))

def create_roles():
    # Сначала создаем уникальное ограничение, если его нет
    cur.execute("""
        ALTER TABLE roles ADD CONSTRAINT roles_name_unique UNIQUE (name)
        """)
    # Затем выполняем вставку с ON CONFLICT
    cur.execute("""
        INSERT INTO roles (name) VALUES ('User'), ('Admin') 
        ON CONFLICT (name) DO NOTHING
        """)

def create_categories():
    categories = [(str(uuid.uuid4()), fake.word()) for _ in range(NUM_CATEGORIES)]
    cur.executemany("""
        INSERT INTO categories (category_id, name) 
        VALUES (%s, %s) 
        ON CONFLICT (category_id) DO NOTHING
    """, categories)
    return [c[0] for c in categories]

def create_users():
    users = [(str(uuid.uuid4()), fake.user_name(), fake.password(), fake.unique.email()) for _ in range(NUM_USERS)]
    cur.executemany("""
        INSERT INTO users (user_id, username, hashed_password, email)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (email) DO NOTHING
    """, users)
    return [u[0] for u in users]

def assign_user_roles(user_ids):
    roles = [1, 2]
    user_roles = [(uid, random.choice(roles)) for uid in user_ids]
    cur.executemany("""
        INSERT INTO user_roles (user_id, role_id) 
        VALUES (%s, %s)
        ON CONFLICT (user_id, role_id) DO NOTHING
    """, user_roles)

def create_products(category_ids):
    products = []
    for _ in range(NUM_PRODUCTS):
        products.append((
            str(uuid.uuid4()),
            fake.catch_phrase(),
            fake.text(max_nb_chars=200),
            random.choice(category_ids),
            round(random.uniform(5.0, 500.0), 2),
            random.randint(10, 1000),
            fake.company()
        ))
    cur.executemany("""
        INSERT INTO products (product_id, name, description, category_id, price, stock, manufacturer)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (product_id) DO NOTHING
    """, products)
    return [p[0] for p in products]

def create_orders(user_ids):
    orders = []
    for _ in range(NUM_ORDERS):
        orders.append((
            str(uuid.uuid4()),
            random.choice(user_ids),
            fake.date_time_this_decade(),
            random.choice(['Pending', 'Completed', 'Cancelled']),
            round(random.uniform(20.0, 2000.0), 2)
        ))
    cur.executemany("""
        INSERT INTO orders (order_id, user_id, order_date, status, total_cost)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (order_id) DO NOTHING
    """, orders)
    return [o[0] for o in orders]

def create_order_items(order_ids, product_ids):
    order_items = []
    for order_id in tqdm(order_ids, desc="Inserting order_items"):
        products_in_order = set()  # Множество для хранения уникальных product_id
        for _ in range(random.randint(1, 5)):  # Случайное количество товаров в заказе
            product_id = random.choice(product_ids)
            while product_id in products_in_order:  # Проверяем, чтобы товар не повторялся
                product_id = random.choice(product_ids)
            products_in_order.add(product_id)  # Добавляем товар в заказ
            quantity = random.randint(1, 10)
            price = round(random.uniform(5.0, 500.0), 2)
            order_items.append((order_id, product_id, quantity, price))
    cur.executemany("""
        INSERT INTO order_items (order_id, product_id, quantity, price)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (order_id, product_id) DO NOTHING
    """, order_items)

def create_reviews(user_ids, product_ids):
    reviews = []
    for _ in tqdm(range(NUM_REVIEWS), desc="Inserting reviews"):
        reviews.append((
            str(uuid.uuid4()),
            random.choice(product_ids),
            random.choice(user_ids),
            random.randint(1, 5),
            fake.sentence(),
            fake.date_time_this_year()
        ))
    cur.executemany("""
        INSERT INTO reviews (review_id, product_id, user_id, rating, comment, review_date)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (review_id) DO NOTHING
    """, reviews)

def create_support_sessions(user_ids):
    sessions = []
    for _ in range(NUM_SUPPORT_SESSIONS):
        start_time = fake.date_time_this_year()
        end_time = None if random.random() < 0.3 else fake.date_time_between(start_date=start_time)
        sessions.append((
            str(uuid.uuid4()),
            random.choice(user_ids),
            start_time,
            end_time,
            random.choice(['open', 'closed'])
        ))
    cur.executemany("""
        INSERT INTO support_sessions (session_id, user_id, start_time, end_time, status)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (session_id) DO NOTHING
    """, sessions)
    return [s[0] for s in sessions]

def create_support_messages(session_ids):
    messages = []
    for session_id in tqdm(session_ids, desc="Inserting support_messages"):
        for _ in range(NUM_MESSAGES_PER_SESSION):
            messages.append((
                str(uuid.uuid4()),
                session_id,
                random.choice(['user', 'support']),
                fake.sentence(),
                fake.date_time_this_year()
            ))
    cur.executemany("""
        INSERT INTO support_messages (message_id, session_id, sender, message, sent_at)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (message_id) DO NOTHING
    """, messages)

def main():
    print("Starting data generation...")
    save_secret_key()
    create_roles()
    category_ids = create_categories()
    user_ids = create_users()
    assign_user_roles(user_ids)
    product_ids = create_products(category_ids)
    order_ids = create_orders(user_ids)
    create_order_items(order_ids, product_ids)
    create_reviews(user_ids, product_ids)
    session_ids = create_support_sessions(user_ids)
    create_support_messages(session_ids)
    print("Data generation completed!")

if __name__ == "__main__":
    main()
