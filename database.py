from models import db

def init_db(app): #старт базы данных
    with app.app_context():
        db.create_all()
        
        #создание начальных ролей, если их нет
        from models import Role
        if Role.query.count() == 0:
            roles = [
                Role(name='admin', description='Администратор системы'),
                Role(name='user', description='Обычный пользователь'),
                Role(name='moderator', description='Модератор'),
                Role(name='guest', description='Гость')
            ]
            for role in roles:
                db.session.add(role)
            db.session.commit()
            print("Начальные роли созданы")
