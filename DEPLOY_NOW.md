# 🚀 ИНСТРУКЦИЯ ДЛЯ ДЕПЛОЯ НА RENDER.COM

## ✅ Все готово к деплою!

### Структура папки flask_app/ (правильная):
```
flask_app/
├── app.py                 # Основное приложение
├── requirements.txt       # Зависимости
├── .gitignore            # Git ignore
├── modules/              # Модули обновления остатков
│   ├── ozon_updater.py
│   ├── wb_updater.py
│   ├── yandex_updater.py
│   ├── config.py
│   ├── history.py
│   ├── dashboard.py
│   ├── script_runner.py
│   └── app_logger.py
├── assets/               # Скрипты обновления
│   ├── ozon/
│   ├── wb/
│   └── yandex/
├── templates/            # HTML шаблоны
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── settings.html
│   └── error.html
└── static/               # Статические файлы
    ├── manifest.json
    └── sw.js
```

## 📋 Шаги для деплоя:

### 1. Инициализируйте Git в папке flask_app

```bash
cd /Users/danil/Desktop/StockApp/flask_app
git init
git add .
git commit -m "Ready for deployment"
```

### 2. Создайте новый репозиторий на GitHub

1. Перейдите на https://github.com/new
2. Name: `lstock-updater`
3. Public/Private: на ваш выбор
4. Нажмите "Create repository"

### 3. Свяжите локальный репозиторий с GitHub

```bash
git branch -M main
git remote add origin https://github.com/DanilPG/lstock-updater.git
git push -u origin main
```

### 4. Настройте Render

1. Перейдите на https://dashboard.render.com
2. Нажмите "New +" → "Web Service"
3. Подключите репозиторий `lstock-updater`
4. Настройте:
   - **Name:** `lstock-updater`
   - **Region:** Frankfurt (или ближайший)
   - **Branch:** main
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python app.py`

### 5. Добавьте переменные окружения

В разделе "Environment Variables" добавьте:
- `FLASK_SECRET_KEY` - сгенерируйте случайный ключ на https://randomkeygen.com/

### 6. Деплой

Нажмите "Create Web Service" и дождитесь завершения (5-10 минут).

### 7. Получите пароль

После деплоя:
1. Откройте вкладку "Logs"
2. Найдите строку с паролем администратора
3. Сохраните пароль!

## 🔐 Первый вход

1. Откройте ваш сайт (например: https://lstock-updater.onrender.com)
2. Войдите с логином `admin` и паролем из логов
3. Срочно смените пароль в настройках!

## 📱 Установка на телефон

### iOS (iPhone/iPad)
1. Откройте приложение в Safari
2. Нажмите "Поделиться"
3. Выберите "На экран «Домой»"
4. Нажмите "Добавить"

### Android
1. Откройте приложение в Chrome
2. Нажмите на меню (три точки)
3. Выберите "Добавить на главный экран"
4. Нажмите "Добавить"

## ✅ Что исправлено:

1. ✅ Удалена строка с sys.path.insert (была проблема с импортами)
2. ✅ Исправлены пути к users.json и логам
3. ✅ Скопированы все модули и assets в flask_app/
4. ✅ Удалена лишняя папка flask_app/flask_app/
5. ✅ Обновлен requirements.txt (без PyQt5 и PyInstaller)

## 🎉 Готово!

Приложение полностью готово к деплою и будет работать корректно!
