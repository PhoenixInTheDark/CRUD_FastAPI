# Гайд по рефакторингу FastAPI CRUD в асинхронную слоистую архитектуру

## 1. Цель рефакторинга

Сейчас CRUD-операции, HTTP-маршруты и работа с SQLAlchemy находятся в одном файле `contact/main.py`. Цель рефакторинга — разделить эти обязанности на понятные слои и перевести работу с PostgreSQL на асинхронный SQLAlchemy:

```text
Controller -> Service -> Repository -> Model -> Database
```

- **Controller** принимает HTTP-запрос и формирует HTTP-ответ.
- **Service** выполняет бизнес-сценарий и принимает решения.
- **Repository** асинхронно читает и изменяет данные в базе.
- **Model** описывает таблицу SQLAlchemy.
- **Schema** проверяет входные данные и описывает ответы API.
- **Database** настраивает соединение и создаёт сессии.

После рефакторинга контроллер не должен содержать SQLAlchemy-запросы, а репозиторий не должен знать о FastAPI и HTTP-кодах.

---

## 2. Что важно сохранить перед началом

Перед изменениями стоит зафиксировать текущее состояние отдельным Git-коммитом:

```bash
git add .
git commit -m "chore: save project before layered refactoring"
```

Это позволит выполнять рефакторинг небольшими шагами и легко сравнивать результат с исходной реализацией.

В проекте есть две точки входа:

- корневой `main.py` содержит демонстрационные маршруты;
- `contact/main.py` содержит основной CRUD контактов.

В результате рефакторинга рекомендуется оставить одну точку входа — `app/main.py`.

---

## 3. Целевая структура проекта

```text
CRUD_FastAPI/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── controllers/
│   │   ├── __init__.py
│   │   └── contact_controller.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── contact_service.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── contact_repository.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── contact_model.py
│   │   └── contact_schemas.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   └── dependencies.py
│   └── exceptions/
│       ├── __init__.py
│       └── contact_exceptions.py
├── tests/
│   ├── conftest.py
│   ├── test_contact_service.py
│   └── test_contact_api.py
├── alembic/
├── alembic.ini
├── docker-compose.yml
├── .env
├── .env.example
├── requirements.txt
└── README.md
```

Не обязательно создавать всё сразу. Безопаснее переносить проект по одному слою и после каждого шага запускать приложение.

---

## 4. Шаг 1. PostgreSQL в Docker

В целевой версии проекта база данных работает в Docker, а FastAPI на первом этапе запускается локально. Это упрощает разработку: приложение доступно через Uvicorn, а PostgreSQL изолирован в контейнере.

Добавьте асинхронный драйвер PostgreSQL и пакет настроек в `requirements.txt`:

```text
asyncpg==0.30.0
pydantic-settings==2.10.1
```

Номера версий приведены как пример. Перед установкой можно выбрать версии, совместимые с остальными зависимостями проекта.

Создайте в корне `docker-compose.yml`:

```yaml
services:
  postgres:
    image: postgres:17-alpine
    container_name: contacts-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "${POSTGRES_PORT}:5432"
    volumes:
      - contacts_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  contacts_postgres_data:
```

Создайте `.env`:

```dotenv
POSTGRES_DB=contacts
POSTGRES_USER=contacts_user
POSTGRES_PASSWORD=change_me
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

Файл `.env` уже исключён из Git текущим `.gitignore`. Дополнительно создайте безопасный `.env.example` без настоящего пароля:

```dotenv
POSTGRES_DB=contacts
POSTGRES_USER=contacts_user
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

Поднимите базу:

```bash
docker compose up -d postgres
docker compose ps
docker compose logs postgres
```

Проверить готовность PostgreSQL можно командой:

```bash
docker compose exec postgres pg_isready \
  -U contacts_user \
  -d contacts
```

Остановка контейнера без удаления данных:

```bash
docker compose down
```

Удаление контейнера **вместе со всеми данными PostgreSQL**:

```bash
docker compose down -v
```

Последнюю команду используйте только для намеренного пересоздания учебной базы.

---

## 5. Шаг 2. Настройки и подключение к PostgreSQL

Создайте `app/database/settings.py`:

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    postgres_db: str
    postgres_user: str
    postgres_password: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    @property
    def database_url(self) -> str:
        return (
            "postgresql+asyncpg://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}"
            f"/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

Если пароль может содержать `@`, `:`, `/` или другие специальные символы, безопаснее собирать URL через `sqlalchemy.URL.create()`, а не через f-string.

Создайте `app/database/connection.py` и перенесите туда создание `engine`, `AsyncSessionLocal` и `Base`.

```python
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.database.settings import get_settings


settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,
)


class Base(DeclarativeBase):
    pass
```

SQLAlchemy 2 поддерживает `DeclarativeBase`, поэтому его удобнее использовать вместо старого вызова `declarative_base()`.

`create_async_engine()` создаёт асинхронный engine, а `async_sessionmaker()` — фабрику `AsyncSession`. Параметр `expire_on_commit=False` оставляет загруженные атрибуты доступными после `commit()` и помогает избежать неожиданных дополнительных запросов в async-коде.

Параметр SQLite `connect_args={"check_same_thread": False}` для PostgreSQL не нужен и должен быть удалён.

Затем создайте `app/database/dependencies.py`:

```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as db:
        yield db
```

Эта функция относится к инфраструктуре FastAPI и отвечает только за жизненный цикл асинхронной сессии. `async with` гарантированно закрывает её после запроса.

Не вызывайте `Base.metadata.create_all()` при импорте приложения. Если в проекте используется Alembic, структуру базы должны создавать миграции.

---

## 6. Шаг 3. ORM-модель

Создайте `app/models/contact_model.py`:

```python
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class ContactModel(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    nickname: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
```

### Почему предлагаются такие изменения

- `ContactModel` явно показывает, что это ORM-модель, а не Pydantic-схема.
- `nickname` получает ограничение уникальности, поскольку он используется для поиска.
- Телефон хранится как строка: номера могут содержать `+`, ведущие нули и форматирование.
- `is_active` соответствует стилю `snake_case` в Python.
- `nullable=False` не позволяет записать неопределённое состояние вместо `True` или `False`.

Если нужно полностью сохранить существующую базу без изменения колонок, сначала перенесите модель как есть. Изменение `phone` и `isActive` выполните позже отдельной миграцией.

---

## 7. Шаг 4. Pydantic-схемы

Создайте `app/models/contact_schemas.py`:

```python
from pydantic import BaseModel, ConfigDict, Field


class ContactCreate(BaseModel):
    nickname: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=1, max_length=32)
    is_active: bool = True


class ContactUpdate(BaseModel):
    nickname: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, min_length=1, max_length=32)
    is_active: bool | None = None


class ContactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nickname: str
    phone: str
    is_active: bool
```

Назначение схем:

- `ContactCreate` — тело запроса при создании;
- `ContactUpdate` — частичное обновление, поэтому поля необязательны;
- `ContactRead` — публичное представление контакта в ответах.

Не используйте ORM-модель в качестве тела запроса. API-схемы и таблица имеют разные обязанности и со временем меняются независимо.

Если вы временно сохраняете имя колонки `isActive`, внешний API всё равно можно перевести на `is_active`, явно сопоставив поле в коде.

---

## 8. Шаг 5. Репозиторий

Создайте `app/repositories/contact_repository.py`:

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact_model import ContactModel


class ContactRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, contact: ContactModel) -> ContactModel:
        self.db.add(contact)
        await self.db.flush()
        await self.db.refresh(contact)
        return contact

    async def get_all(self) -> list[ContactModel]:
        statement = select(ContactModel).order_by(ContactModel.id)
        result = await self.db.scalars(statement)
        return list(result.all())

    async def get_by_id(self, contact_id: int) -> ContactModel | None:
        return await self.db.get(ContactModel, contact_id)

    async def get_by_nickname(
        self,
        nickname: str,
    ) -> ContactModel | None:
        statement = select(ContactModel).where(
            ContactModel.nickname == nickname
        )
        return await self.db.scalar(statement)

    async def delete(self, contact: ContactModel) -> None:
        await self.db.delete(contact)
        await self.db.flush()
```

Репозиторий должен:

- содержать SQLAlchemy-запросы;
- возвращать ORM-объекты или `None`;
- ничего не знать о `HTTPException`, статусах 404/409 и FastAPI;
- не принимать Pydantic request-схемы без необходимости.

В этом варианте репозиторий вызывает `await flush()`, но не `commit()`. Границу транзакции контролирует сервис, потому что один бизнес-сценарий потенциально может включать несколько операций с данными.

Все операции `AsyncSession`, которые выполняют ввод-вывод, вызываются через `await`. Метод `add()` — исключение: он только помещает объект в сессию и выполняется без `await`.

Не создавайте пока абстрактный generic repository. Для одного ресурса он усложнит код и скроет смысл конкретных запросов.

---

## 9. Шаг 6. Исключения приложения

Создайте `app/exceptions/contact_exceptions.py`:

```python
class ContactNotFoundError(Exception):
    pass


class NicknameAlreadyExistsError(Exception):
    pass
```

Это обычные Python-исключения, не связанные с HTTP. Благодаря этому сервис можно использовать и тестировать без FastAPI.

---

## 10. Шаг 7. Сервис

Создайте `app/services/contact_service.py`:

```python
from sqlalchemy.exc import SQLAlchemyError

from app.exceptions.contact_exceptions import (
    ContactNotFoundError,
    NicknameAlreadyExistsError,
)
from app.models.contact_model import ContactModel
from app.models.contact_schemas import ContactCreate, ContactUpdate
from app.repositories.contact_repository import ContactRepository


class ContactService:
    def __init__(self, repository: ContactRepository) -> None:
        self.repository = repository

    async def create_contact(self, data: ContactCreate) -> ContactModel:
        existing_contact = await self.repository.get_by_nickname(data.nickname)
        if existing_contact is not None:
            raise NicknameAlreadyExistsError(data.nickname)

        contact = ContactModel(
            nickname=data.nickname,
            phone=data.phone,
            is_active=data.is_active,
        )

        try:
            created_contact = await self.repository.create(contact)
            await self.repository.db.commit()
            return created_contact
        except SQLAlchemyError:
            await self.repository.db.rollback()
            raise

    async def get_contacts(self) -> list[ContactModel]:
        return await self.repository.get_all()

    async def get_contact(self, contact_id: int) -> ContactModel:
        contact = await self.repository.get_by_id(contact_id)
        if contact is None:
            raise ContactNotFoundError(contact_id)
        return contact

    async def update_contact(
        self,
        contact_id: int,
        data: ContactUpdate,
    ) -> ContactModel:
        contact = await self.get_contact(contact_id)
        changes = data.model_dump(exclude_unset=True)

        if "nickname" in changes:
            duplicate = await self.repository.get_by_nickname(
                changes["nickname"]
            )
            if duplicate is not None and duplicate.id != contact.id:
                raise NicknameAlreadyExistsError(changes["nickname"])

        for field, value in changes.items():
            setattr(contact, field, value)

        try:
            await self.repository.db.commit()
            await self.repository.db.refresh(contact)
            return contact
        except SQLAlchemyError:
            await self.repository.db.rollback()
            raise

    async def delete_contact(self, contact_id: int) -> None:
        contact = await self.get_contact(contact_id)

        try:
            await self.repository.delete(contact)
            await self.repository.db.commit()
        except SQLAlchemyError:
            await self.repository.db.rollback()
            raise
```

Этот вариант намеренно простой. Он уже отделяет бизнес-логику от HTTP, но сервис пока знает о транзакциях SQLAlchemy через `repository.db`.

Позже это можно улучшить одним из двух способов:

1. добавить в репозиторий методы `commit`, `rollback` и `refresh`;
2. ввести отдельный Unit of Work.

Для текущего размера проекта Unit of Work не обязателен. Сначала добейтесь работающего и тестируемого разделения на слои.

### Что считается бизнес-логикой

В сервисе должны находиться решения вроде:

- запретить повторяющийся nickname;
- сообщить, что контакт отсутствует;
- определить допустимые поля обновления;
- выполнить несколько изменений в одной транзакции.

В сервисе не должно быть `HTTPException` или декораторов FastAPI.

---

## 11. Шаг 8. Контроллер

Создайте `app/controllers/contact_controller.py`:

```python
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_db
from app.models.contact_schemas import (
    ContactCreate,
    ContactRead,
    ContactUpdate,
)
from app.repositories.contact_repository import ContactRepository
from app.services.contact_service import ContactService


router = APIRouter(prefix="/contacts", tags=["Contacts"])


async def get_contact_service(
    db: AsyncSession = Depends(get_db),
) -> ContactService:
    repository = ContactRepository(db)
    return ContactService(repository)


@router.post(
    "",
    response_model=ContactRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_contact(
    data: ContactCreate,
    service: ContactService = Depends(get_contact_service),
) -> ContactRead:
    return await service.create_contact(data)


@router.get("", response_model=list[ContactRead])
async def get_contacts(
    service: ContactService = Depends(get_contact_service),
) -> list[ContactRead]:
    return await service.get_contacts()


@router.get("/{contact_id}", response_model=ContactRead)
async def get_contact(
    contact_id: int,
    service: ContactService = Depends(get_contact_service),
) -> ContactRead:
    return await service.get_contact(contact_id)


@router.patch("/{contact_id}", response_model=ContactRead)
async def update_contact(
    contact_id: int,
    data: ContactUpdate,
    service: ContactService = Depends(get_contact_service),
) -> ContactRead:
    return await service.update_contact(contact_id, data)


@router.delete(
    "/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_contact(
    contact_id: int,
    service: ContactService = Depends(get_contact_service),
) -> Response:
    await service.delete_contact(contact_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

Контроллер теперь выполняет только три действия:

1. получает данные из HTTP-запроса;
2. вызывает нужный метод сервиса;
3. возвращает результат согласно `response_model`.

Маршруты объявлены через `async def`, поскольку они ожидают асинхронный сервис и обращения к PostgreSQL. Нельзя забывать `await`: без него вместо результата получится объект coroutine.

---

## 12. Шаг 9. Обработка ошибок

Прикладные исключения нужно преобразовать в HTTP-ответы в presentation-слое. Удобно зарегистрировать обработчики в `app/main.py`:

```python
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.controllers.contact_controller import router as contact_router
from app.exceptions.contact_exceptions import (
    ContactNotFoundError,
    NicknameAlreadyExistsError,
)


app = FastAPI(title="Contact Manager API")
app.include_router(contact_router)


@app.exception_handler(ContactNotFoundError)
async def contact_not_found_handler(
    request: Request,
    error: ContactNotFoundError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": "Contact not found"},
    )


@app.exception_handler(NicknameAlreadyExistsError)
async def nickname_conflict_handler(
    request: Request,
    error: NicknameAlreadyExistsError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "Contact nickname already exists"},
    )
```

Теперь сервис сообщает о смысле ошибки, а HTTP-слой решает, каким статусом её представить.

Запуск новой точки входа:

```bash
uvicorn app.main:app --reload
```

---

## 13. Шаг 10. Приведение API к REST

Текущие маршруты можно заменить следующими:

| Текущий маршрут | Новый маршрут | Назначение |
|---|---|---|
| `POST /contact_add` | `POST /contacts` | Создать контакт |
| `GET /contact_getAll` | `GET /contacts` | Получить список |
| `POST /contact_get` | `GET /contacts/{id}` | Получить контакт |
| `POST /contact_update` | `PATCH /contacts/{id}` | Частично обновить |
| `POST /contact_delete` | `DELETE /contacts/{id}` | Удалить контакт |

Рекомендуемые статусы:

- `201 Created` — контакт создан;
- `200 OK` — получение или изменение прошло успешно;
- `204 No Content` — контакт удалён;
- `404 Not Found` — контакт отсутствует;
- `409 Conflict` — nickname уже занят;
- `422 Unprocessable Content` — Pydantic отклонил входные данные.

Лучше использовать `id` в URL. Nickname может измениться и является пользовательским значением, а `id` остаётся стабильным.

Если совместимость со старым API важна, сначала оставьте старые маршруты как временные адаптеры, пометьте их `deprecated=True`, а удалите только после перехода клиентов.

---

## 14. Шаг 11. Alembic и PostgreSQL

Текущая миграция с названием `initial` только добавляет колонку `isActive` в таблицу `contacts`. Она не создаёт саму таблицу, поэтому на чистой PostgreSQL-базе такая цепочка миграций некорректна.

Перед исправлением определите, есть ли важные данные в существующей базе.

### Если данные не нужны

Для учебного проекта проще:

1. удалить Docker volume с учебной базой через `docker compose down -v`;
2. привести ORM-модель к финальному виду;
3. создать корректную начальную миграцию;
4. проверить её на пустой базе.

Команды Alembic:

```bash
alembic revision --autogenerate -m "create contacts table"
alembic upgrade head
```

Не удаляйте базу, пока не убедитесь, что в ней нет нужных данных.

### Если данные нужно сохранить

Создайте новую миграцию, которая отдельно:

- переименует `isActive` в `is_active`;
- преобразует `phone` в строковый тип;
- устранит повторяющиеся nickname;
- добавит уникальное ограничение;
- установит `nullable=False`.

PostgreSQL позволяет переименовать колонку напрямую:

```python
op.alter_column(
    "contacts",
    "isActive",
    new_column_name="is_active",
)
```

Автогенерацию миграции всегда нужно проверять вручную до запуска.

После переноса модели измените импорт metadata в `alembic/env.py`:

```python
from app.database.connection import Base
from app.models.contact_model import ContactModel

target_metadata = Base.metadata
```

Импорт модели нужен, чтобы таблица зарегистрировалась в `Base.metadata`.

Чтобы Alembic использовал тот же URL, что и приложение, в `alembic/env.py` перед созданием engine установите значение из настроек:

```python
from app.database.settings import get_settings

config.set_main_option(
    "sqlalchemy.url",
    get_settings().database_url.replace("%", "%%"),
)
```

После этого значение `sqlalchemy.url` в `alembic.ini` не должно содержать настоящий логин или пароль. Секреты остаются только в `.env`.

Так как URL использует `asyncpg`, стандартный синхронный `engine_from_config()` в `alembic/env.py` использовать нельзя. Онлайн-миграции настройте через async engine:

```python
import asyncio

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config


def run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online_async() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_migrations_online_async())
```

Нижняя часть `alembic/env.py` остаётся обычной:

```python
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

Сами функции миграций `upgrade()` и `downgrade()` остаются синхронными. Alembic выполняет их внутри соединения, переданного через `connection.run_sync()`.

Проверка миграций с нуля:

```bash
docker compose down -v
docker compose up -d postgres
alembic upgrade head
alembic current
```

После выполнения проверьте наличие таблицы:

```bash
docker compose exec postgres psql \
  -U contacts_user \
  -d contacts \
  -c "\\dt"
```

---

## 15. Шаг 12. Тестирование

Добавьте в зависимости разработки как минимум:

```text
pytest
pytest-asyncio
httpx
```

Тестировать стоит на двух уровнях.

### Unit-тесты сервиса

Замените настоящий репозиторий поддельной реализацией в памяти и проверьте:

- создание нового контакта;
- запрет повторяющегося nickname;
- получение отсутствующего контакта;
- частичное обновление;
- удаление контакта.

Главное преимущество слоистой архитектуры заключается в том, что эти тесты не требуют запуска FastAPI или PostgreSQL.

### Интеграционные тесты API

Через `httpx.AsyncClient` и `ASGITransport` проверьте:

- `POST /contacts` возвращает `201`;
- `GET /contacts/{id}` возвращает созданную запись;
- невалидное тело возвращает `422`;
- неизвестный ID возвращает `404`;
- повторяющийся nickname возвращает `409`;
- `DELETE` возвращает `204`.

Для интеграционных тестов используйте отдельную PostgreSQL-базу, например `contacts_test`, и переопределите зависимость `get_db`. Никогда не запускайте тесты на основной базе разработки. Перед каждым тестом данные можно откатывать транзакцией либо очищать таблицы в fixture.

Минимальная форма async-теста API:

```python
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_get_contacts() -> None:
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/contacts")

    assert response.status_code == 200
```

Поддельный репозиторий для unit-тестов сервиса также должен предоставлять `async def`-методы, чтобы контракт совпадал с настоящим репозиторием.

---

## 16. Безопасная последовательность переноса

Рекомендуемый порядок работы:

1. Создать `docker-compose.yml`, `.env.example` и поднять PostgreSQL.
2. Установить `asyncpg` и проверить подключение к контейнеру.
3. Создать пакет `app` и пустые каталоги слоёв.
4. Перенести настройки и подключение к БД.
5. Перенести ORM-модель без изменения поведения.
6. Разделить Pydantic-схемы на create, update и read.
7. Создать репозиторий и перенести туда SQLAlchemy-запросы.
8. Создать сервис и перенести туда проверки и транзакции.
9. Создать controller с `APIRouter`.
10. Подключить router в единственном `app/main.py`.
11. Добавить обработчики исключений.
12. Написать тесты на сохранённое поведение.
13. Только после этого менять URL, имена полей и структуру БД.
14. Исправить миграции и проверить создание чистой PostgreSQL-базы.
15. Обновить README и команды Docker.
16. После полной проверки удалить старые `main.py` и пакет `contact`.

Не переносите архитектуру, API и схему базы одним большим изменением. Небольшие отдельные коммиты значительно упростят поиск ошибок.

Пример последовательности коммитов:

```text
refactor: move database configuration
refactor: extract contact repository
refactor: extract contact service
refactor: move contact routes to controller
feat: add contact error handlers
test: add contact service tests
test: add contact API tests
refactor: replace legacy contact endpoints
fix: rebuild initial database migration
docs: update project structure and API examples
```

---

## 17. Правила зависимости между слоями

Используйте следующие ограничения как ориентир при написании кода:

### Controller может импортировать

- FastAPI;
- Pydantic-схемы;
- сервис;
- FastAPI-зависимости.

### Service может импортировать

- схемы или отдельные DTO;
- ORM-модель на первом этапе;
- репозиторий;
- прикладные исключения.

### Repository может импортировать

- SQLAlchemy;
- ORM-модель;
- сессию базы данных.

### Model может импортировать

- SQLAlchemy;
- общий `Base`.

### Запрещённые обратные зависимости

- repository не импортирует service или controller;
- service не импортирует controller или FastAPI;
- model не импортирует repository;
- database не импортирует controller.

Если нижний слой начинает импортировать верхний, граница архитектуры нарушена.

---

## 18. Чего пока не стоит добавлять

Для текущего проекта не нужны:

- generic repository для всех будущих моделей;
- отдельный интерфейс для каждого простого класса;
- dependency injection container;
- CQRS и отдельные command/query handlers;
- message bus;
- полноценный Unit of Work;
- смешивание синхронных и асинхронных SQLAlchemy-сессий;
- блокирующие библиотеки внутри `async def`-маршрутов.

Асинхронность полезна для операций ввода-вывода, таких как обращения к PostgreSQL. Она не ускоряет вычисления сама по себе. Если внутри `async def` вызвать долгую синхронную функцию, она заблокирует event loop.

---

## 19. Итоговый чек-лист

Рефакторинг можно считать завершённым, когда:

- [ ] существует одна точка входа FastAPI;
- [ ] PostgreSQL запускается через `docker compose up -d postgres`;
- [ ] пароль БД не хранится в Git;
- [ ] приложение читает настройки PostgreSQL из окружения;
- [ ] SQLAlchemy использует драйвер `postgresql+asyncpg`;
- [ ] engine создан через `create_async_engine()`;
- [ ] зависимости создают `AsyncSession`;
- [ ] repository, service и controller используют `async def` и `await`;
- [ ] Alembic запускает async engine через `connection.run_sync()`;
- [ ] маршруты вынесены в `contact_controller.py`;
- [ ] в controller нет SQLAlchemy-запросов;
- [ ] бизнес-проверки находятся в `contact_service.py`;
- [ ] запросы к БД находятся в `contact_repository.py`;
- [ ] ORM-модель отделена от Pydantic-схем;
- [ ] создание, обновление и ответ имеют разные схемы;
- [ ] отсутствующий контакт возвращает 404;
- [ ] повторяющийся nickname возвращает 409;
- [ ] транзакция откатывается при ошибке;
- [ ] `Base.metadata.create_all()` удалён из запуска приложения;
- [ ] Alembic создаёт всю схему на пустой PostgreSQL-базе;
- [ ] тесты используют отдельную базу;
- [ ] unit-тесты сервиса проходят без FastAPI;
- [ ] API-тесты покрывают успешные и ошибочные сценарии;
- [ ] README содержит новую структуру и команду запуска.

Главный критерий результата: изменение способа хранения контактов должно затрагивать преимущественно repository и model, изменение бизнес-правила — service, а изменение HTTP API — controller и schemas.
