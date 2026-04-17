# 🔧 Как исправить деплой на Render

## Проблема

Вы загрузили всю папку `StockApp` на GitHub, а нужно загрузить только `flask_app`.

## Решение

### Вариант 1: Создать новый репозиторий (Рекомендуется)

1. **Удалите старый репозиторий на GitHub**
   - Зайдите на https://github.com/DanilPG/lstock-android
   - Settings → Danger Zone → Delete this repository

2. **Создайте новый репозиторий только для flask_app**
   - Нажмите "New repository"
   - Name: `lstock-updater`
   - Public/Private: на ваш выбор
   - Нажмите "Create repository"

3. **Загрузите только flask_app**
   ```bash
   cd /Users/danil/Desktop/StockApp/flask_app
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/DanilPG/lstock-updater.git
   git push -u origin main
   ```

4. **Настройте Render**
   - Удалите старый Web Service
   - Создайте новый
   - Подключите новый репозиторий `lstock-updater`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python app.py`

---

### Вариант 2: Использовать существующий репозиторий

Если не хотите удалять репозиторий:

1. **Очистите репозиторий**
   ```bash
   cd /Users/danil/Desktop/StockApp
   rm -rf .git
   ```

2. **Инициализируйте только flask_app**
   ```bash
   cd flask_app
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/DanilPG/lstock-android.git
   git push -u origin main --force
   ```

3. **Настройте Render**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python app.py`

---

## Важные моменты

✅ В репозитории должны быть только файлы из папки `flask_app/`
✅ Файл `app.py` должен быть в корне репозитория
✅ Папки `templates/` и `static/` должны быть в корне репозитория
✅ Файл `requirements.txt` должен быть в корне репозитория

❌ НЕ должны быть в репозитории:
- Папка `modules/` (она в родительской директории)
- Папка `assets/` (она в родительской директории)
- Файл `main.py` (это старое приложение)
- Любые другие файлы из родительской папки

---

## После исправления

1. Render автоматически начнет новый деплой
2. Дождитесь завершения (5-10 минут)
3. Откройте Logs и найдите пароль администратора
4. Войдите на сайт и смените пароль
