from functools import wraps
from quart import session, redirect, url_for, flash, current_app
from app.db import *

def admin_required(func):
    @wraps(func)
    async def decorated_view(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            await flash("Пожалуйста, войдите в систему.", "warning")
            return redirect(url_for('main.login'))
        # Проверяем, есть ли у пользователя роль 'Admin'
        roles = await get_user_roles(current_app.db_pool, user_id)
        if 'Admin' not in roles:
            await flash("Доступ запрещен.", "danger")
            return redirect(url_for('main.home'))
        return await func(*args, **kwargs)
    return decorated_view
