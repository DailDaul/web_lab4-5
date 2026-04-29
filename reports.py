from flask import Blueprint, render_template, request, Response, current_app
from flask_login import login_required, current_user
from models import db, VisitLog, User
from sqlalchemy import func, desc
import csv
import io
from datetime import datetime

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.before_request
def log_visit(): #Логирование посещений страниц отчета
    #Не логируем запросы к API экспорта
    if not request.path.endswith('/export'):
        from app import log_visit as log_visit_func
        log_visit_func()

@reports_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    #Получаем записи в зависимости от роли пользователя
    if current_user.has_role('admin'):
        logs = VisitLog.query.order_by(VisitLog.created_at.desc())
    else:
        logs = VisitLog.query.filter_by(user_id=current_user.id).order_by(VisitLog.created_at.desc())
    
    pagination = logs.paginate(page=page, per_page=per_page, error_out=False)
    logs_list = pagination.items
    
    return render_template('reports/index.html', 
                         logs=logs_list, 
                         pagination=pagination,
                         page=page)

@reports_bp.route('/by-pages')
@login_required
def by_pages():
    #получаем статистику по страницам
    if current_user.has_role('admin'):
        stats = db.session.query(
            VisitLog.path,
            func.count(VisitLog.id).label('count')
        ).group_by(VisitLog.path).order_by(desc('count')).all()
    else:
        stats = db.session.query(
            VisitLog.path,
            func.count(VisitLog.id).label('count')
        ).filter_by(user_id=current_user.id).group_by(VisitLog.path).order_by(desc('count')).all()
    
    return render_template('reports/by_pages.html', stats=stats)

@reports_bp.route('/by-users')
@login_required
def by_users():
    if current_user.has_role('admin'):
        stats = db.session.query(
            VisitLog.user_id,
            func.count(VisitLog.id).label('count')
        ).group_by(VisitLog.user_id).order_by(desc('count')).all()
        
        #формируем данные с именами пользователей
        result = []
        for user_id, count in stats:
            if user_id:
                user = User.query.get(user_id)
                user_name = user.full_name if user else f"Пользователь {user_id}"
            else:
                user_name = "Неаутентифицированный пользователь"
            result.append({'user_name': user_name, 'count': count})
    else:
        #обычный пользователь видит только свои посещения
        count = VisitLog.query.filter_by(user_id=current_user.id).count()
        result = [{'user_name': current_user.full_name, 'count': count}]
    
    return render_template('reports/by_users.html', stats=result)

@reports_bp.route('/by-pages/export')
@login_required
def export_pages_csv():
    if current_user.has_role('admin'):
        stats = db.session.query(
            VisitLog.path,
            func.count(VisitLog.id).label('count')
        ).group_by(VisitLog.path).order_by(desc('count')).all()
    else:
        stats = db.session.query(
            VisitLog.path,
            func.count(VisitLog.id).label('count')
        ).filter_by(user_id=current_user.id).group_by(VisitLog.path).order_by(desc('count')).all()
    
    #создаем CSV файл в памяти
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    
    #заголовок
    writer.writerow(['№', 'Страница', 'Количество посещений'])
    
    #информация
    for idx, (path, count) in enumerate(stats, 1):
        writer.writerow([idx, path, count])
    
    #формирование ответа
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=page_stats_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'}
    )

@reports_bp.route('/by-users/export')
@login_required
def export_users_csv():
    if current_user.has_role('admin'):
        stats = db.session.query(
            VisitLog.user_id,
            func.count(VisitLog.id).label('count')
        ).group_by(VisitLog.user_id).order_by(desc('count')).all()
        
        result = []
        for user_id, count in stats:
            if user_id:
                user = User.query.get(user_id)
                user_name = user.full_name if user else f"Пользователь {user_id}"
            else:
                user_name = "Неаутентифицированный пользователь"
            result.append({'user_name': user_name, 'count': count})
    else:
        count = VisitLog.query.filter_by(user_id=current_user.id).count()
        result = [{'user_name': current_user.full_name, 'count': count}]
    
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    
    writer.writerow(['№', 'Пользователь', 'Количество посещений'])
    
    for idx, item in enumerate(result, 1):
        writer.writerow([idx, item['user_name'], item['count']])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=user_stats_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'}
    )