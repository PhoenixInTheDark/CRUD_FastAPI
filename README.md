# FastAPI Contact Manager

REST API for managing contacts built with FastAPI, SQLAlchemy and Alembic.

---

**[English](#english)** | **[Русский](#русский)**

---

## English

### Tech Stack

- **FastAPI** — async web framework
- **SQLAlchemy** — ORM for database operations
- **Alembic** — database migrations
- **Pydantic** — data validation
- **SQLite** — database
- **Uvicorn** — ASGI server

### Project Structure

```
fastapiMyProject/
├── main.py                 # Root app with demo routes
├── contact/
│   ├── __init__.py
│   ├── main.py             # Contact CRUD endpoints
│   ├── models.py           # SQLAlchemy models
│   ├── schemas.py          # Pydantic schemas
│   └── database.py         # DB engine and session config
├── alembic/
│   └── versions/           # Migration files
├── alembic.ini
├── requirements.txt
└── .gitignore
```

### Installation

```bash
git clone <repo-url>
cd fastapiMyProject

python -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows

pip install -r requirements.txt
```

### Database Setup

```bash
alembic upgrade head
```

### Run

```bash
uvicorn contact.main:app --reload
```

API docs available at: http://127.0.0.1:8000/docs

### API Endpoints

| Method | URL               | Description            |
|--------|-------------------|------------------------|
| POST   | `/contact_add`    | Create a new contact   |
| GET    | `/contact_getAll` | Get all contacts       |
| POST   | `/contact_get`    | Find contact by name   |
| POST   | `/contact_update` | Update contact by name |
| POST   | `/contact_delete` | Delete contact by name |

### Request Examples

**Create contact:**
```json
POST /contact_add
{
    "nickname": "John",
    "phone": 79991234567,
    "isActive": true
}
```

**Find contact:**
```json
POST /contact_get
{
    "nickname": "John"
}
```

**Update contact:**
```json
POST /contact_update?nickname=John
{
    "nickname": "Johnny",
    "phone": 79997654321,
    "isActive": false
}
```

### Migrations

```bash
# Create new migration after model changes
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1
```

---

## Русский

### Стек технологий

- **FastAPI** — асинхронный веб-фреймворк
- **SQLAlchemy** — ORM для работы с базой данных
- **Alembic** — миграции базы данных
- **Pydantic** — валидация данных
- **SQLite** — база данных
- **Uvicorn** — ASGI-сервер

### Структура проекта

```
fastapiMyProject/
├── main.py                 # Корневое приложение с демо-роутами
├── contact/
│   ├── __init__.py
│   ├── main.py             # CRUD-эндпоинты для контактов
│   ├── models.py           # SQLAlchemy-модели
│   ├── schemas.py          # Pydantic-схемы
│   └── database.py         # Настройка движка БД и сессий
├── alembic/
│   └── versions/           # Файлы миграций
├── alembic.ini
├── requirements.txt
└── .gitignore
```

### Установка

```bash
git clone <repo-url>
cd fastapiMyProject

python -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows

pip install -r requirements.txt
```

### Настройка базы данных

```bash
alembic upgrade head
```

### Запуск

```bash
uvicorn contact.main:app --reload
```

Документация API доступна по адресу: http://127.0.0.1:8000/docs

### API-эндпоинты

| Метод  | URL               | Описание                    |
|--------|-------------------|-----------------------------|
| POST   | `/contact_add`    | Создать новый контакт       |
| GET    | `/contact_getAll` | Получить все контакты       |
| POST   | `/contact_get`    | Найти контакт по имени      |
| POST   | `/contact_update` | Обновить контакт по имени   |
| POST   | `/contact_delete` | Удалить контакт по имени    |

### Примеры запросов

**Создание контакта:**
```json
POST /contact_add
{
    "nickname": "Иван",
    "phone": 79991234567,
    "isActive": true
}
```

**Поиск контакта:**
```json
POST /contact_get
{
    "nickname": "Иван"
}
```

**Обновление контакта:**
```json
POST /contact_update?nickname=Иван
{
    "nickname": "Ваня",
    "phone": 79997654321,
    "isActive": false
}
```

### Миграции

```bash
# Создать миграцию после изменения моделей
alembic revision --autogenerate -m "описание"

# Применить миграции
alembic upgrade head

# Откатить последнюю миграцию
alembic downgrade -1
```
