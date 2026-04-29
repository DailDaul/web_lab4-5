from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def check_rights(required_role=None):
    def decorator(f): #декоратор для проверки прав доступа
        @wraps(f)
        def decorated_function(*args, **kwargs):
            #проверяем, аутентифицирован ли пользователь
            if not current_user.is_authenticated:
                flash('Пожалуйста, войдите для доступа к этой странице.', 'warning')
                return redirect(url_for('login', next=request.path))
            
            #если указана конкретная роль, проверяем её
            if required_role:
                if not current_user.has_role(required_role):
                    flash('У вас недостаточно прав для доступа к данной странице.', 'danger')
                    return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

#импортируем request здесь, чтобы избежать циклического импорта
from flask import request