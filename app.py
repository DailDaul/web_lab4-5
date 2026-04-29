from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify, g
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime
import os
import traceback

from models import db, User, Role, VisitLog
from database import init_db
from utils import validate_user_data, validate_password
from decorators import check_rights
from reports import reports_bp

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['DEBUG'] = True

# Инициализация расширений
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице.'
login_manager.login_message_category = 'warning'

# Регистрация Blueprint для отчетов
app.register_blueprint(reports_bp)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Декоратор для логирования посещений
@app.before_request
def log_visit(): #все посещения
    #исключаем статические файлы и некоторые специальные маршруты
    if request.endpoint and not request.endpoint.startswith('static') and request.endpoint not in ['login', 'logout']:
        try:
            log = VisitLog(
                path=request.path,
                user_id=current_user.id if current_user.is_authenticated else None
            )
            db.session.add(log)
            db.session.commit()
        except Exception as e:
            print(f"Ошибка логирования: {e}")
            db.session.rollback()

#создание таблиц при первом запуске
with app.app_context():
    db.create_all()
    # Создание начальных ролей
    if Role.query.count() == 0:
        roles = [
            Role(name='admin', description='Администратор системы'),
            Role(name='user', description='Обычный пользователь'),
        ]
        for role in roles:
            db.session.add(role)
        db.session.commit()
        
        #создание тестового администратора
        admin = User(
            username='admin',
            first_name='Admin',
            last_name='System',
            role_id=1  # admin role
        )
        admin.set_password('Admin123!')
        db.session.add(admin)
        
        #создание тестового пользователя
        user = User(
            username='user',
            first_name='Test',
            last_name='User',
            role_id=2  # user role
        )
        user.set_password('User123!')
        db.session.add(user)
        
        db.session.commit()
        print("Тестовые пользователи созданы:")
        print("Администратор: admin / Admin123!")
        print("Пользователь: user / User123!")

#для передачи ролей в шаблоны
@app.context_processor
def utility_processor():
    return dict(enumerate=enumerate)

@app.route('/')
def index():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('index.html', users=users)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash('Вы успешно вошли в систему!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))

@app.route('/user/<int:user_id>')
def user_view(user_id):
    user = User.query.get_or_404(user_id)
    
    #проверяем права доступа к просмотру
    if not current_user.is_authenticated:
        flash('Пожалуйста, войдите для просмотра профиля.', 'warning')
        return redirect(url_for('login', next=request.path))
    
    if not current_user.has_role('admin') and current_user.id != user.id:
        flash('У вас недостаточно прав для просмотра этого профиля.', 'danger')
        return redirect(url_for('index'))
    
    return render_template('user_view.html', user=user)

@app.route('/user/create', methods=['GET', 'POST'])
@check_rights('admin')
def user_create():
    roles = Role.query.all()
    errors = {}
    form_data = {}
    
    if request.method == 'POST':
        #сбор данных из формы
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        last_name = request.form.get('last_name', '').strip()
        first_name = request.form.get('first_name', '').strip()
        middle_name = request.form.get('middle_name', '').strip()
        role_id = request.form.get('role_id')
        
        #охранение данные формы для отображения в случае ошибки
        form_data = {
            'username': username,
            'last_name': last_name,
            'first_name': first_name,
            'middle_name': middle_name,
            'role_id': role_id
        }
        
        #валидация данных
        data = {
            'username': username,
            'password': password,
            'first_name': first_name,
            'last_name': last_name
        }
        errors = validate_user_data(data)
        
        #проверка уникальности логина
        if User.query.filter_by(username=username).first():
            errors['username'] = 'Пользователь с таким логином уже существует'
        
        if errors:
            for field, error in errors.items():
                flash(f'{field}: {error}', 'danger')
            return render_template('user_form.html', 
                                 user=None, 
                                 roles=roles, 
                                 form_data=form_data,
                                 errors=errors)
        
        #создание пользователя
        try:
            user = User(
                username=username,
                last_name=last_name,
                first_name=first_name,
                middle_name=middle_name,
                role_id=int(role_id) if role_id and role_id != '' else None
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            flash(f'Пользователь {user.full_name} успешно создан!', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Ошибка при создании пользователя: {str(e)}")
            print(traceback.format_exc())
            flash(f'Ошибка при создании пользователя: {str(e)}', 'danger')
            return render_template('user_form.html', 
                                 user=None, 
                                 roles=roles, 
                                 form_data=form_data,
                                 errors=errors)
    
    return render_template('user_form.html', user=None, roles=roles, form_data={}, errors={})

@app.route('/user/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def user_edit(user_id):
    user = User.query.get_or_404(user_id)
    
    #проверка прав: только администратор или сам пользователь
    if not current_user.has_role('admin') and current_user.id != user.id:
        flash('У вас недостаточно прав для редактирования этого пользователя.', 'danger')
        return redirect(url_for('index'))
    
    roles = Role.query.all()
    errors = {}
    
    if request.method == 'POST':
        #сбор данных из формы
        last_name = request.form.get('last_name', '').strip()
        first_name = request.form.get('first_name', '').strip()
        middle_name = request.form.get('middle_name', '').strip()
        role_id = request.form.get('role_id')
        
        #валидация данных
        data = {
            'first_name': first_name,
            'last_name': last_name
        }
        errors = validate_user_data(data)
        
        if errors:
            for field, error in errors.items():
                flash(f'{field}: {error}', 'danger')
            return render_template('user_form.html', user=user, roles=roles, errors=errors)
        
        #обновление пользователя
        try:
            user.last_name = last_name
            user.first_name = first_name
            user.middle_name = middle_name
            
            #только администратор может изменять роль
            if current_user.has_role('admin'):
                user.role_id = int(role_id) if role_id and role_id != '' else None
            
            db.session.commit()
            
            flash(f'Данные пользователя {user.full_name} обновлены!', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Ошибка при обновлении пользователя: {str(e)}")
            print(traceback.format_exc())
            flash(f'Ошибка при обновлении пользователя: {str(e)}', 'danger')
            return render_template('user_form.html', user=user, roles=roles, errors=errors)
    
    return render_template('user_form.html', user=user, roles=roles, errors={})

@app.route('/user/<int:user_id>/delete', methods=['POST'])
@check_rights('admin')
def user_delete(user_id):
    user = User.query.get_or_404(user_id)
    
    #запрещаем удаление самого себя
    if user.id == current_user.id:
        flash('Вы не можете удалить свою собственную учетную запись', 'danger')
        return redirect(url_for('index'))
    
    try:
        full_name = user.full_name
        db.session.delete(user)
        db.session.commit()
        flash(f'Пользователь {full_name} удален', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка при удалении пользователя: {str(e)}")
        print(traceback.format_exc())
        flash(f'Ошибка при удалении пользователя: {str(e)}', 'danger')
    
    return redirect(url_for('index'))

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        #проверка старого пароля
        if not current_user.check_password(old_password):
            flash('Неверный текущий пароль', 'danger')
            return render_template('change_password.html')
        
        #валидация нового пароля
        is_valid, errors = validate_password(new_password, confirm_password)
        
        if not is_valid:
            for error in errors:
                flash(error, 'danger')
            return render_template('change_password.html')
        
        #смена пароля
        try:
            current_user.set_password(new_password)
            db.session.commit()
            flash('Пароль успешно изменен!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            print(f"Ошибка при смене пароля: {str(e)}")
            print(traceback.format_exc())
            flash(f'Ошибка при смене пароля: {str(e)}', 'danger')
            return render_template('change_password.html')
    
    return render_template('change_password.html')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    print(f"Ошибка 500: {str(e)}")
    print(traceback.format_exc())
    flash('Произошла внутренняя ошибка сервера. Пожалуйста, попробуйте позже.', 'danger')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)