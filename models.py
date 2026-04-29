from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Role(db.Model):
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    
    #cвязь с пользователями
    users = db.relationship('User', back_populates='role')
    
    def __repr__(self):
        return f'<Role {self.name}>'


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    last_name = db.Column(db.String(100))
    first_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    #cвязь с ролью
    role = db.relationship('Role', back_populates='users')
    #cвязь с журналом посещений
    visit_logs = db.relationship('VisitLog', back_populates='user')
    
    @property
    def full_name(self):
        """Полное имя пользователя"""
        parts = []
        if self.last_name:
            parts.append(self.last_name)
        if self.first_name:
            parts.append(self.first_name)
        if self.middle_name:
            parts.append(self.middle_name)
        return ' '.join(parts) if parts else 'Не указано'
    
    @property
    def short_name(self):
        #ФИО
        name_parts = []
        if self.last_name:
            name_parts.append(self.last_name)
        if self.first_name:
            name_parts.append(f"{self.first_name[0]}.")
        if self.middle_name:
            name_parts.append(f"{self.middle_name[0]}.")
        return ' '.join(name_parts) if name_parts else 'Не указано'
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def has_role(self, role_name):
        return self.role and self.role.name == role_name
    
    def __repr__(self):
        return f'<User {self.username}>'


class VisitLog(db.Model): #Модель журнала посещений
    __tablename__ = 'visit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    #связь с пользователем
    user = db.relationship('User', back_populates='visit_logs')
    
    @property
    def user_display_name(self):
        if self.user:
            return self.user.full_name
        return "Неаутентифицированный пользователь"
    
    def __repr__(self):
        return f'<VisitLog {self.path} by {self.user_id}>'