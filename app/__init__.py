from quart import Quart
from dotenv import load_dotenv
from .redis_client import init_redis
from .pubsub import listen_to_orders
import asyncpg
import os
import logging
from datetime import timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def create_app():
    app = Quart(__name__, template_folder="../templates", static_folder="../static")

    app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')

    @app.before_serving
    async def startup():
        """
        Создание пула соединений с базой данных при запуске приложения.
        """
        try:
            app.db_pool = await asyncpg.create_pool(
                database=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                host=os.getenv("DB_HOST"),
                port=int(os.getenv("DB_PORT")),
                min_size=1,
                max_size=10,
            )
            logger.info("Пул соединений с базой данных успешно создан.")
        except Exception as e:
            logger.error(f"Ошибка при создании пула соединений: {e}")
            raise e
        
        try:
            await init_redis()
            logger.info("Подключение к Redis установлено.")
            app.add_background_task(listen_to_orders)
        except Exception as e:
            logger.error(f"Ошибка при подключении к Redis: {e}")
            raise e

    @app.after_serving
    async def shutdown():
        """
        Закрытие пула соединений с базой данных.
        """
        try:
            await app.db_pool.close()
            logger.info("Пул соединений с базой данных закрыт.")
        except Exception as e:
            logger.error(f"Ошибка при закрытии пула соединений: {e}")

    from .routes import main as main_blueprint
    from .admin_routes import admin as admin_blueprint

    app.register_blueprint(main_blueprint)
    app.register_blueprint(admin_blueprint)
    app.permanent_session_lifetime = timedelta(minutes=30)  

    return app