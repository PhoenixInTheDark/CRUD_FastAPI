# FastAPI Contact Manager

Асинхронный REST API для управления контактами, построенный на FastAPI, SQLAlchemy и PostgreSQL.

## Стек

- FastAPI — HTTP API;
- SQLAlchemy 2 — асинхронная работа с данными;
- asyncpg — асинхронный драйвер PostgreSQL;
- Alembic — миграции схемы БД;
- Pydantic — валидация запросов и ответов;
- PostgreSQL 17 — база данных;
- Docker Compose — запуск API и базы данных;
- Uvicorn — ASGI-сервер.

## Архитектура

Приложение разделено на слои:

```text
Controller -> Service -> Repository -> Model -> Database
```

- `controllers` отвечают за HTTP-маршруты;
- `services` содержат бизнес-логику;
- `repositories` выполняют запросы через SQLAlchemy;
- `models` содержат ORM-модель и Pydantic-схемы;
- `database` настраивает async engine и `AsyncSession`;
- `exceptions` содержит прикладные исключения.

## Структура проекта

```text
CRUD_FastAPI/
├── app/
│   ├── main.py
│   ├── controllers/
│   │   └── contact_controller.py
│   ├── services/
│   │   └── contact_service.py
│   ├── repositories/
│   │   └── contact_repository.py
│   ├── models/
│   │   ├── contact_model.py
│   │   └── contact_schemas.py
│   ├── database/
│   │   ├── connection.py
│   │   ├── dependencies.py
│   │   └── settings.py
│   └── exceptions/
│       └── contact_exceptions.py
├── alembic/
│   └── versions/
├── .env.example
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Настройка окружения

Скопируйте пример переменных окружения:

```bash
cp .env.example .env
```

Значения по умолчанию:

```dotenv
POSTGRES_DB=contacts
POSTGRES_USER=contacts_user
POSTGRES_PASSWORD=change_me
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

Файл `.env` исключён из Git. Не сохраняйте в репозитории настоящий пароль.

При локальном запуске приложения `POSTGRES_HOST` должен быть равен `localhost`. В Docker Compose это значение автоматически заменяется на имя сервиса `postgres`.

## Запуск в Docker

В текущем окружении используется отдельная команда `docker-compose`:

```bash
docker-compose up --build -d
```

При запуске Compose:

1. поднимает PostgreSQL;
2. ожидает успешный healthcheck базы;
3. запускает `alembic upgrade head`;
4. запускает Uvicorn на порту `8000`.

Проверить состояние:

```bash
docker-compose ps
```

Посмотреть логи API:

```bash
docker-compose logs -f api
```

Посмотреть логи PostgreSQL:

```bash
docker-compose logs -f postgres
```

После запуска доступны:

- API: <http://localhost:8000>;
- Swagger UI: <http://localhost:8000/docs>;
- OpenAPI JSON: <http://localhost:8000/openapi.json>.

## Остановка и очистка

Остановить контейнеры с сохранением данных PostgreSQL:

```bash
docker-compose down
```

Остановить контейнеры и удалить данные PostgreSQL:

```bash
docker-compose down -v --remove-orphans
```

Вторая команда удаляет Docker volume проекта. Восстановить его данные после удаления нельзя.

## Локальный запуск API

PostgreSQL можно оставить в Docker, а FastAPI запустить локально:

```bash
docker-compose up -d postgres

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

alembic upgrade head
uvicorn app.main:app --reload
```

Для такого запуска в `.env` должно быть:

```dotenv
POSTGRES_HOST=localhost
```

## API

| Метод | URL | Назначение |
|---|---|---|
| `POST` | `/contacts` | Создать контакт |
| `GET` | `/contacts` | Получить все контакты |
| `GET` | `/contacts/{contact_id}` | Получить контакт по ID |
| `PATCH` | `/contacts/{contact_id}` | Частично обновить контакт |
| `DELETE` | `/contacts/{contact_id}` | Удалить контакт |

### Создание контакта

```http
POST /contacts
Content-Type: application/json
```

```json
{
  "nickname": "Ivan",
  "phone": "+79991234567",
  "is_active": true
}
```

Успешный ответ имеет статус `201 Created`.

### Частичное обновление

```http
PATCH /contacts/1
Content-Type: application/json
```

```json
{
  "phone": "+79997654321",
  "is_active": false
}
```

Передавать все поля не требуется: изменяются только присутствующие в запросе значения.

### Удаление

```http
DELETE /contacts/1
```

Успешный ответ имеет статус `204 No Content`.

## Миграции

Миграции автоматически применяются при запуске API-контейнера.

Создать миграцию после изменения ORM-моделей:

```bash
docker-compose run --rm api \
  alembic revision --autogenerate -m "describe change"
```

Применить миграции вручную:

```bash
docker-compose run --rm api alembic upgrade head
```

Показать текущую ревизию:

```bash
docker-compose run --rm api alembic current
```

Откатить последнюю миграцию:

```bash
docker-compose run --rm api alembic downgrade -1
```

Автоматически созданные миграции необходимо проверять перед применением.

## Полезные команды

Пересобрать только API:

```bash
docker-compose build api
```

Перезапустить API:

```bash
docker-compose restart api
```

Открыть PostgreSQL CLI:

```bash
docker-compose exec postgres \
  psql -U contacts_user -d contacts
```

Проверить таблицы:

```bash
docker-compose exec postgres \
  psql -U contacts_user -d contacts -c "\\dt"
```

Подробный план рефакторинга находится в [REFACTORING_GUIDE.md](REFACTORING_GUIDE.md).
