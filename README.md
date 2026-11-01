# AutoService CRM — управление заказами СТО

Учебный веб-проект на Flask + SQLAlchemy. По умолчанию использует SQLite, при необходимости переключается на MySQL через `DATABASE_URL`.

## Возможности
- Авторизация и роли пользователей (администратор / мастер-приёмщик и др.)
- Главная панель с ключевыми показателями
- Клиенты и автомобили
- Заказы-наряды, статусы, назначение сотрудников и сроки
- Добавление запчастей к заказу со списанием со склада
- Регистрация платежей и расчёт остатка
- Склад, сотрудники и сводные отчёты
- Поиск заказов по номеру, клиенту, марке и госномеру

## Запуск (Windows / macOS / Linux)
1. Установите Python 3.10 или новее.
2. Распакуйте архив и откройте терминал в папке проекта.
3. Создайте виртуальное окружение:
   ```bash
   python -m venv .venv
   ```
4. Активируйте его:
   - Windows: `.venv\\Scripts\\activate`
   - macOS/Linux: `source .venv/bin/activate`
5. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
6. Создайте демонстрационную БД:
   ```bash
   flask --app app init-db
   ```
7. Запустите сервер:
   ```bash
   flask --app app run --debug
   ```
8. Откройте `http://127.0.0.1:5000`.

**Демо-вход:** `admin` / `admin123`. Смените пароль и `SECRET_KEY` перед любым реальным использованием.

## Подключение MySQL
Создайте базу данных и пользователя, затем задайте переменную окружения:
```sql
CREATE DATABASE sto_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'sto_user'@'localhost' IDENTIFIED BY 'strong_password';
GRANT ALL PRIVILEGES ON sto_db.* TO 'sto_user'@'localhost';
FLUSH PRIVILEGES;
```
Linux/macOS:
```bash
export DATABASE_URL='mysql+pymysql://sto_user:strong_password@localhost/sto_db?charset=utf8mb4'
```
Windows PowerShell:
```powershell
$env:DATABASE_URL='mysql+pymysql://sto_user:strong_password@localhost/sto_db?charset=utf8mb4'
```
Затем выполните `flask --app app init-db`.

## Структура
- `app.py` — модели данных, маршруты, бизнес-логика
- `templates/` — HTML-шаблоны
- `static/css/style.css` — оформление
- `static/js/app.js` — интерактивность интерфейса

## Важное замечание
Это учебный MVP, а не готовая к промышленной эксплуатации система. Перед публикацией добавьте управление пользователями и смену паролей, CSRF-защиту, журнал аудита, резервное копирование, проверку прав на каждую операцию и тесты. Демонстрационные данные условные.
