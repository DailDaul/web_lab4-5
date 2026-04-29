import re

def validate_username(username):
    if not username or len(username) < 5:
        return False, "Логин должен содержать минимум 5 символов"
    
    if not re.match(r'^[a-zA-Z0-9]+$', username):
        return False, "Логин может содержать только латинские буквы и цифры"
    
    return True, None


def validate_password(password, confirm_password=None):
    errors = []
    
    if not password:
        errors.append("Пароль не может быть пустым")
        return False, errors
    
    if len(password) < 8:
        errors.append("Пароль должен содержать минимум 8 символов")
    
    if len(password) > 128:
        errors.append("Пароль должен содержать не более 128 символов")
    
    if ' ' in password:
        errors.append("Пароль не должен содержать пробелов")
    
    if not re.search(r'\d', password):
        errors.append("Пароль должен содержать минимум одну цифру")
    
    has_upper = re.search(r'[A-ZА-Я]', password)
    has_lower = re.search(r'[a-zа-я]', password)
    
    if not has_upper:
        errors.append("Пароль должен содержать минимум одну заглавную букву")
    
    if not has_lower:
        errors.append("Пароль должен содержать минимум одну строчную букву")
    
    #проверка допустимых символов
    allowed_pattern = r'^[A-Za-zА-Яа-я0-9~!?@#$%^&*_\-+()\[\]{}><\/\\|"\'.,:;]+$'
    if not re.match(allowed_pattern, password):
        errors.append("Пароль содержит недопустимые символы")
    
    #проверка совпадения паролей (если передано подтверждение)
    if confirm_password is not None and password != confirm_password:
        errors.append("Пароли не совпадают")
    
    return len(errors) == 0, errors


def validate_user_data(data):
    errors = {}
    
    if 'username' in data and data.get('username'):
        is_valid, msg = validate_username(data['username'])
        if not is_valid:
            errors['username'] = msg
    
    if 'password' in data and data.get('password'):
        is_valid, pwd_errors = validate_password(data['password'])
        if not is_valid:
            # Берем первую ошибку для отображения
            errors['password'] = pwd_errors[0] if pwd_errors else "Некорректный пароль"
    
    #проверка обязательных полей
    if 'first_name' in data and not data.get('first_name'):
        errors['first_name'] = "Имя не может быть пустым"
    
    #фамилия не обязательна, но если указана, должна быть строкой
    if 'last_name' in data and data.get('last_name') and not isinstance(data['last_name'], str):
        errors['last_name'] = "Некорректная фамилия"
    
    return errors