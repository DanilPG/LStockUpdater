# Конфигурация для PythonAnywhere
# Этот файл используется для настройки WSGI на PythonAnywhere

import sys
import os

# Добавляем путь к приложению
path = '/home/yourusername/mysite'
if path not in sys.path:
    sys.path.append(path)

# Импортируем приложение Flask
from app import app as application

# Настройки для PythonAnywhere
application.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your-secret-key-here')
