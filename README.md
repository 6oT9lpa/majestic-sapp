# AppealFlow Backend

`AppealFlow Backend` — FastAPI-сервис для обработки пользовательских обращений: помощь, жалобы, амнистии, статусы, роли, уведомления и отчёты модераторов.

Проект оформлен как портфолио-пример backend-разработки: маршруты FastAPI, роли и уровни доступа, PostgreSQL, Redis, Docker Compose, уведомления и административные сценарии.

## Назначение

Система решает задачу централизованной обработки обращений:

1. Пользователь создаёт обращение.
2. Обращение попадает в систему.
3. Модератор или администратор берёт его в работу.
4. Статус обращения меняется по workflow.
5. Действие логируется.
6. Пользователь получает ответ или уведомление.
7. Администратор видит отчёты и статистику.

## Основные возможности

| Модуль | Назначение |
|---|---|
| Appeals | создание обращений: помощь, жалоба, амнистия |
| Dashboard | рабочее пространство модератора / администратора |
| Admin | управление пользователями, ролями и служебными данными |
| Reports | отчёты по активности и обработке обращений |
| Messenger | сообщения и realtime-сценарии |
| Auth | авторизация и проверка текущего пользователя |
| Logging | журналирование действий пользователей и модераторов |

## Стек

| Зона | Технологии |
|---|---|
| Backend | `Python`, `FastAPI`, `Uvicorn` |
| Database | `PostgreSQL`, async DB access |
| Cache / PubSub | `Redis` |
| Infrastructure | `Docker`, `Docker Compose`, `.env` |
| Frontend delivery | `StaticFiles`, HTML/CSS/JS assets |
| Access control | role-level checks, protected routes |

## Архитектура

```text
majestic-sapp/
├── src/
│   ├── api/
│   │   ├── main_routes.py
│   │   ├── auth_route.py
│   │   ├── appeal_route.py
│   │   ├── dashboard_route.py
│   │   ├── admin_route.py
│   │   ├── messanger_route.py
│   │   └── reports_route.py
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── scripts/
│   ├── database.py
│   └── main.py
├── static/
├── storage/
├── docker-compose.yml
├── Dockerfile
└── README.md
```

Главная точка входа — `src/main.py`. Приложение подключает роутеры для `auth`, `appeal`, `dashboard`, `admin`, `messanger` и `reports`, монтирует `/static` и `/storage`, а при старте инициализирует базу данных и роли.

## Основные маршруты

| Prefix | Назначение |
|---|---|
| `/` | основные страницы приложения |
| `/auth` | авторизация |
| `/appeal` | создание обращений |
| `/dashboard` | рабочая панель |
| `/dashboard/admin` | административная часть |
| `/messanger` | сообщения / realtime-логика |
| `/dashboard/admin/reports` | отчёты |

## Appeals workflow

В проекте выделены три типа обращений:

- `help` — помощь;
- `complaint` — жалоба;
- `amnesty` — обжалование наказания / амнистия.

Типовой поток:

```text
request -> Pydantic schema -> AppealService -> database -> log_action -> response
```

## Доступ и роли

Защищённые операции используют проверку уровня роли через `RoleLevelChecker` и `PermissionLevel`.

Базовая модель:

- пользователь создаёт обращения;
- модератор обрабатывает обращения;
- администратор управляет системой и отчётами;
- действия пользователей и модераторов логируются.

## Запуск через Docker Compose

```bash
git clone https://github.com/6oT9lpa/majestic-sapp.git
cd majestic-sapp
cp .env.example .env
```

Минимальные переменные окружения:

```env
DATABASE_URL=<postgresql_async_url>
REDIS_URL=<redis_url>
SECRET_KEY=<secret_key>
```

Запуск:

```bash
docker compose up --build
```

После запуска backend доступен на `http://localhost:8000`.

## Локальный запуск без Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

Для локального запуска должны быть доступны PostgreSQL и Redis.

## Полезные команды

```bash
docker compose logs -f web
docker compose logs -f db
docker compose down
docker compose build --no-cache
```

## Что проект показывает работодателю

- Умение строить backend на FastAPI.
- Разделение маршрутов, схем, сервисов и моделей.
- Работа с PostgreSQL и Redis в Docker Compose.
- Реализация защищённых маршрутов и role-level access control.
- Обработка пользовательских обращений через сервисный слой.
- Логирование действий и подготовка административной отчётности.
- Проектирование workflow для заявок и статусов.

## Production-ready доработки

Перед реальным запуском нужно дополнительно:

- вынести чувствительные значения в `.env` или отдельное хранилище;
- ограничить CORS и TrustedHost;
- добавить миграции БД, если они не используются;
- добавить unit и integration tests;
- настроить structured logging;
- добавить healthcheck endpoints;
- настроить мониторинг и резервное копирование БД.

## Статус проекта

Пет-проект / портфолио-проект. Основной фокус — backend-логика обращений, роли, административные сценарии и инфраструктурный запуск через Docker Compose.