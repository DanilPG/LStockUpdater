# 🚀 Инструкция по деплою LStock Updater

Это руководство поможет вам развернуть Flask приложение на бесплатных хостингах.

## 📋 Требования

- Аккаунт на выбранной платформе деплоя
- Git репозиторий (GitHub, GitLab, Bitbucket)
- Python 3.11+ (для локальной разработки)

## 🔐 Безопасность

**ВАЖНО:** Приложение имеет систему аутентификации. При первом запуске будет создан пользователь `admin` со случайным паролем. Пароль будет выведен в консоль. Срочно измените его после первого входа!

## 🌐 Бесплатные платформы для деплоя

### 1. Render.com (Рекомендуется)

**Преимущества:**
- Бесплатный план с SSL
- Автоматический деплой из Git
- Поддержка Python
- Стабильная работа

**Инструкция:**

1. **Подготовка репозитория**
   ```bash
   cd flask_app
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/lstock-updater.git
   git push -u origin main
   ```

2. **Создание аккаунта на Render**
   - Перейдите на https://render.com
   - Зарегистрируйтесь через GitHub

3. **Создание нового сервиса**
   - Нажмите "New +"
   - Выберите "Web Service"
   - Подключите ваш GitHub репозиторий
   - Настройте параметры:
     - Name: `lstock-updater`
     - Region: `Frankfurt` (или ближайший к вам)
     - Branch: `main`
     - Runtime: `Python 3`
     - Build Command: `pip install -r requirements.txt`
     - Start Command: `gunicorn app:app`

4. **Переменные окружения**
   Добавьте в Environment Variables:
   - `FLASK_SECRET_KEY` (сгенерируйте случайный ключ)
   - `PYTHON_VERSION`: `3.11.0`

5. **Деплой**
   - Нажмите "Create Web Service"
   - Дождитесь завершения деплоя (5-10 минут)

6. **Получение пароля**
   - После деплоя откройте Logs
   - Найдите строку с паролем администратора

### 2. Railway.app

**Преимущества:**
- Бесплатный план ($5 кредитов/месяц)
- Простая настройка
- Поддержка PostgreSQL (если понадобится)

**Инструкция:**

1. **Подготовка репозитория**
   ```bash
   cd flask_app
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/lstock-updater.git
   git push -u origin main
   ```

2. **Создание проекта**
   - Перейдите на https://railway.app
   - Нажмите "New Project"
   - Выберите "Deploy from GitHub repo"
   - Выберите ваш репозиторий

3. **Настройка**
   - Railway автоматически определит Python проект
   - Добавьте переменные окружения:
     - `FLASK_SECRET_KEY` (случайный ключ)
     - `PORT`: `5000`

4. **Деплой**
   - Нажмите "Deploy"
   - Дождитесь завершения

### 3. PythonAnywhere

**Преимущества:**
- Бесплатный аккаунт "Beginner"
- Стабильная работа
- Поддержка WSGI

**Инструкция:**

1. **Регистрация**
   - Перейдите на https://www.pythonanywhere.com
   - Создайте бесплатный аккаунт "Beginner"

2. **Создание Web App**
   - Перейдите в "Web" tab
   - Нажмите "Add a new web app"
   - Выберите "Flask"
   - Выберите Python 3.11
   - Укажите путь к приложению: `/home/yourusername/mysite`

3. **Загрузка файлов**
   ```bash
   # Через консоль PythonAnywhere
   cd ~/mysite
   git clone https://github.com/yourusername/lstock-updater.git
   cp -r lstock-updater/* .
   ```

4. **Настройка WSGI**
   - В "Web" tab нажмите на "WSGI configuration file"
   - Замените содержимое на:
   ```python
   import sys
   import os
   
   path = '/home/yourusername/mysite'
   if path not in sys.path:
       sys.path.append(path)
   
   from app import app as application
   ```

5. **Установка зависимостей**
   ```bash
   pip install -r requirements.txt
   ```

6. **Переменные окружения**
   - В "Web" tab → "Variables"
   - Добавьте `FLASK_SECRET_KEY`

7. **Перезагрузка**
   - Нажмите "Reload" в "Web" tab

### 4. Vercel (с адаптацией)

**Преимущества:**
- Бесплатный хостинг
- Быстрый деплой
- Глобальная CDN

**Инструкция:**

1. **Установка Vercel CLI**
   ```bash
   npm install -g vercel
   ```

2. **Создание vercel.json**
   ```json
   {
     "version": 2,
     "builds": [
       {
         "src": "app.py",
         "use": "@vercel/python"
       }
     ],
     "routes": [
       {
         "src": "/(.*)",
         "dest": "app.py"
       }
     ]
   }
   ```

3. **Деплой**
   ```bash
   cd flask_app
   vercel
   ```

## 📱 Установка на телефон как PWA

После деплоя:

1. **iOS (iPhone/iPad)**
   - Откройте приложение в Safari
   - Нажмите "Поделиться" (квадрат со стрелкой вверх)
   - Прокрутите вниз и выберите "На экран «Домой»"
   - Нажмите "Добавить"

2. **Android**
   - Откройте приложение в Chrome
   - Нажмите на меню (три точки)
   - Выберите "Добавить на главный экран"
   - Нажмите "Добавить"

## 🔧 Локальный запуск

Для тестирования перед деплоем:

```bash
cd flask_app

# Создание виртуального окружения
python -m venv venv

# Активация (Mac/Linux)
source venv/bin/activate

# Активация (Windows)
venv\Scripts\activate

# Установка зависимостей
pip install -r requirements.txt

# Запуск
python app.py
```

Приложение будет доступно по адресу: http://localhost:5000

## 🛡️ Меры безопасности

Приложение включает следующие меры безопасности:

1. **Аутентификация**
   - Система входа по логину/паролю
   - Хеширование паролей (bcrypt)
   - Таймаут сессии (1 час)

2. **Защита данных**
   - HTTPS шифрование (на хостинге)
   - CSRF защита
   - Валидация входных данных

3. **Логирование**
   - Все действия записываются в лог
   - Отслеживание неудачных попыток входа

4. **Рекомендации**
   - Используйте сложный пароль (минимум 12 символов)
   - Регулярно меняйте пароль
   - Не передавайте учетные данные третьим лицам
   - Используйте VPN при работе с публичных сетей

## 📊 Мониторинг

После деплоя:

1. **Проверьте работоспособность**
   - Откройте приложение
   - Войдите в систему
   - Попробуйте обновить остатки

2. **Просмотрите логи**
   - Render: Logs tab
   - Railway: Logs tab
   - PythonAnywhere: Web tab → Logs

3. **Настройте уведомления** (если доступно)
   - О простоях
   - О ошибках

## 🔄 Обновление приложения

Для обновления:

```bash
# Внесите изменения
git add .
git commit -m "Update"
git push
```

Платформа автоматически выполнит redeploy.

## 🆘 Решение проблем

### Приложение не запускается

1. Проверьте логи
2. Убедитесь, что все зависимости установлены
3. Проверьте переменные окружения

### Ошибка 500

1. Проверьте flask_app.log
2. Убедитесь, что модули доступны
3. Проверьте права доступа к файлам

### Проблемы с PWA

1. Убедитесь, что HTTPS включен
2. Проверьте manifest.json
3. Очистите кэш браузера

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи приложения
2. Проверьте документацию платформы хостинга
3. Убедитесь, что все требования выполнены

## 📝 Дополнительные ресурсы

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Render Documentation](https://render.com/docs)
- [Railway Documentation](https://docs.railway.app/)
- [PythonAnywhere Documentation](https://help.pythonanywhere.com/)
