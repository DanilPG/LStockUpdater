"""
Flask веб-приложение для управления остатками на маркетплейсах.
Мобильная версия с системой аутентификации.
"""
import os
import sys
import json
import secrets
import logging
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, List, Optional
from flask import (
    Flask, render_template, request, jsonify, session, redirect, url_for,
    flash, send_from_directory, make_response
)

from modules.ozon_updater import list_stores_from_assets as ozon_list_stores, update_stocks as ozon_update, reset_stocks as ozon_reset
from modules.wb_updater import list_stores_from_assets as wb_list_stores, update_stocks as wb_update, reset_stocks as wb_reset
from modules.yandex_updater import list_stores_from_assets as yandex_list_stores, update_stocks as yandex_update, reset_stocks as yandex_reset
from modules.config import load_config, save_config
from modules.history import get_history, clear_history, clear_history_by_date_range
from modules.dashboard import get_history_stats, get_top_products, get_daily_summary

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Файл для хранения пользователей
USERS_FILE = 'users.json'
SESSION_TIMEOUT = 3600  # 1 час в секундах

# Функции хеширования паролей (совместимые с Python 3.9+)
def hash_password(password: str) -> str:
    """Хеширует пароль с использованием SHA-256 + соль."""
    salt = secrets.token_hex(16)
    hash_obj = hashlib.sha256((password + salt).encode())
    return f"{salt}${hash_obj.hexdigest()}"

def verify_password(password: str, password_hash: str) -> bool:
    """Проверяет пароль."""
    try:
        salt, hash_value = password_hash.split('$')
        hash_obj = hashlib.sha256((password + salt).encode())
        return hash_obj.hexdigest() == hash_value
    except:
        return False

# Инициализация файла пользователей
def init_users_file():
    """Создает файл пользователей, если его нет."""
    if not os.path.exists(USERS_FILE):
        os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
        # Создаем администратора по умолчанию
        default_password = secrets.token_urlsafe(16)
        users = {
            'admin': {
                'password_hash': hash_password(default_password),
                'created_at': datetime.now().isoformat(),
                'last_login': None
            }
        }
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        logger.warning(f"Создан пользователь admin с паролем: {default_password}")
        logger.warning("Срочно измените пароль после первого входа!")
        return default_password
    return None

def load_users() -> Dict:
    """Загружает пользователей из файла."""
    if not os.path.exists(USERS_FILE):
        init_users_file()
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки пользователей: {e}")
        return {}

def save_users(users: Dict):
    """Сохраняет пользователей в файл."""
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения пользователей: {e}")

# Декоратор для проверки авторизации
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        # Проверка времени сессии
        if 'last_activity' in session:
            last_activity = datetime.fromisoformat(session['last_activity'])
            if datetime.now() - last_activity > timedelta(seconds=SESSION_TIMEOUT):
                session.clear()
                flash('Сессия истекла. Войдите снова.', 'warning')
                return redirect(url_for('login'))
        
        # Обновляем время активности
        session['last_activity'] = datetime.now().isoformat()
        return f(*args, **kwargs)
    return decorated_function

# Декоратор для проверки прав администратора
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Недостаточно прав доступа.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Маршруты
@app.route('/')
def index():
    """Главная страница - перенаправление на дашборд или логин."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Введите имя пользователя и пароль.', 'error')
            return render_template('login.html')
        
        users = load_users()
        if username in users and verify_password(password, users[username]['password_hash']):
            session['user_id'] = username
            session['role'] = 'admin'  # Все пользователи - админы для простоты
            session['last_activity'] = datetime.now().isoformat()
            session['login_time'] = datetime.now().isoformat()
            
            # Обновляем время последнего входа
            users[username]['last_login'] = datetime.now().isoformat()
            save_users(users)
            
            logger.info(f"Пользователь {username} вошел в систему")
            flash('Добро пожаловать!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Неверное имя пользователя или пароль.', 'error')
            logger.warning(f"Неудачная попытка входа: {username}")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Выход из системы."""
    username = session.get('user_id', 'unknown')
    session.clear()
    logger.info(f"Пользователь {username} вышел из системы")
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Главная панель управления."""
    config = load_config()
    stats = get_history_stats()
    summary = get_daily_summary()
    
    # Получаем список магазинов для каждой платформы
    ozon_stores = list(ozon_list_stores().keys())
    wb_stores = list(wb_list_stores().keys())
    yandex_stores = list(yandex_list_stores().keys())
    
    return render_template('dashboard.html',
                          ozon_stores=ozon_stores,
                          wb_stores=wb_stores,
                          yandex_stores=yandex_stores,
                          stats=stats,
                          summary=summary,
                          config=config)

@app.route('/api/stores')
@login_required
def api_stores():
    """API для получения списка магазинов."""
    return jsonify({
        'ozon': list(ozon_list_stores().keys()),
        'wb': list(wb_list_stores().keys()),
        'yandex': list(yandex_list_stores().keys())
    })

@app.route('/api/update', methods=['POST'])
@login_required
def api_update():
    """API для обновления остатков."""
    data = request.get_json()
    marketplace = data.get('marketplace', '').lower()
    stores = data.get('stores', [])
    
    if not stores:
        return jsonify({'success': False, 'message': 'Не выбраны магазины'}), 400
    
    try:
        result = ''
        if marketplace == 'ozon':
            result = ozon_update(stores)
        elif marketplace == 'wb':
            result = wb_update(stores)
        elif marketplace == 'yandex':
            result = yandex_update(stores)
        else:
            return jsonify({'success': False, 'message': 'Неизвестная платформа'}), 400
        
        logger.info(f"Обновление {marketplace} для магазинов: {stores}")
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        logger.error(f"Ошибка при обновлении: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/reset', methods=['POST'])
@login_required
def api_reset():
    """API для обнуления остатков."""
    data = request.get_json()
    marketplace = data.get('marketplace', '').lower()
    stores = data.get('stores', [])
    
    if not stores:
        return jsonify({'success': False, 'message': 'Не выбраны магазины'}), 400
    
    try:
        result = ''
        if marketplace == 'ozon':
            result = ozon_reset(stores)
        elif marketplace == 'wb':
            result = wb_reset(stores)
        elif marketplace == 'yandex':
            result = yandex_reset(stores)
        else:
            return jsonify({'success': False, 'message': 'Неизвестная платформа'}), 400
        
        logger.info(f"Обнуление {marketplace} для магазинов: {stores}")
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        logger.error(f"Ошибка при обнулении: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/history')
@login_required
def api_history():
    """API для получения истории операций."""
    limit = request.args.get('limit', 50, type=int)
    history = get_history(limit=limit)
    return jsonify({'history': history})

@app.route('/api/stats')
@login_required
def api_stats():
    """API для получения статистики."""
    stats = get_history_stats()
    summary = get_daily_summary()
    top_products = get_top_products(limit=10)
    
    return jsonify({
        'stats': stats,
        'summary': summary,
        'top_products': top_products
    })

@app.route('/api/clear-history', methods=['POST'])
@login_required
def api_clear_history():
    """API для очистки истории."""
    data = request.get_json()
    date_from = data.get('date_from')
    date_to = data.get('date_to')
    
    try:
        if date_from and date_to:
            result = clear_history_by_date_range(date_from, date_to)
        else:
            result = clear_history()
        
        logger.info(f"Очистка истории: {result}")
        return jsonify({'success': True, 'message': result})
    except Exception as e:
        logger.error(f"Ошибка при очистке истории: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/settings')
@login_required
def settings():
    """Страница настроек."""
    users = load_users()
    return render_template('settings.html', users=users)

@app.route('/api/change-password', methods=['POST'])
@login_required
def api_change_password():
    """API для смены пароля."""
    data = request.get_json()
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    
    if not current_password or not new_password:
        return jsonify({'success': False, 'message': 'Заполните все поля'}), 400
    
    if len(new_password) < 8:
        return jsonify({'success': False, 'message': 'Пароль должен быть не менее 8 символов'}), 400
    
    username = session['user_id']
    users = load_users()
    
    if username not in users:
        return jsonify({'success': False, 'message': 'Пользователь не найден'}), 404
    
    if not verify_password(current_password, users[username]['password_hash']):
        return jsonify({'success': False, 'message': 'Неверный текущий пароль'}), 401
    
    users[username]['password_hash'] = hash_password(new_password)
    users[username]['password_changed'] = datetime.now().isoformat()
    save_users(users)
    
    logger.info(f"Пользователь {username} изменил пароль")
    return jsonify({'success': True, 'message': 'Пароль успешно изменен'})

@app.route('/api/session-info')
@login_required
def api_session_info():
    """API для получения информации о сессии."""
    return jsonify({
        'user_id': session.get('user_id'),
        'role': session.get('role'),
        'login_time': session.get('login_time'),
        'last_activity': session.get('last_activity'),
        'timeout': SESSION_TIMEOUT
    })

# Обработка ошибок
@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error_code=404, error_message='Страница не найдена'), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Внутренняя ошибка: {error}")
    return render_template('error.html', error_code=500, error_message='Внутренняя ошибка сервера'), 500

# Инициализация при запуске
def init_app():
    """Инициализация приложения."""
    default_password = init_users_file()
    if default_password:
        print("\n" + "="*60)
        print("ВНИМАНИЕ! Создан пользователь admin с паролем:")
        print(default_password)
        print("Срочно измените пароль после первого входа!")
        print("="*60 + "\n")

if __name__ == '__main__':
    init_app()
    # В продакшене используйте Gunicorn или uWSGI
    app.run(host='0.0.0.0', port=5000, debug=False)
