# MAVIN — Backend

[![CI](https://github.com/MAVIN-26/MAVIN-backend/actions/workflows/ci.yml/badge.svg)](https://github.com/MAVIN-26/MAVIN-backend/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Proprietary-red)](https://github.com/MAVIN-26/MAVIN/blob/main/LICENSE)

FastAPI-бэкенд платформы **MAVIN** — веб-сервиса предзаказа еды с самовывозом (Click & Collect) и персональным ИИ-ассистентом по питанию.

Основной репозиторий проекта: [MAVIN-26/MAVIN](https://github.com/MAVIN-26/MAVIN)

---

## Стек технологий

| Технология | Версия | Назначение |
|---|---|---|
| Python | 3.12 | Язык разработки |
| FastAPI | 0.115 | Веб-фреймворк |
| SQLAlchemy (async) | 2.0 | ORM |
| Alembic | 1.14 | Миграции БД |
| PostgreSQL | 16 | База данных |
| MinIO | — | Хранилище изображений (S3-совместимое) |
| python-jose + bcrypt | — | JWT-аутентификация |
| OpenRouter API | — | ИИ-ассистент (модель `openai/gpt-4o-mini`) |
| uvicorn | 0.32 | ASGI-сервер |

---

## Архитектура

Монолитный API с жёстким разделением слоёв:

```
routers → services → repositories → models
                                  ↘ schemas (Pydantic)
```

| Слой | Папка | Ответственность |
|---|---|---|
| Роутеры | `app/api/routers/` | Приём HTTP-запроса, вызов сервиса, возврат ответа |
| Сервисы | `app/services/` | Бизнес-логика, оркестрация репозиториев |
| Репозитории | `app/repositories/` | Все SQLAlchemy-запросы к БД |
| Модели | `app/models/` | Описание таблиц (SQLAlchemy ORM) |
| Схемы | `app/schemas/` | Pydantic-модели для валидации входа/выхода |
| Конфиг | `app/core/` | Настройки приложения, безопасность (JWT) |

---

## Структура проекта

```
MAVIN-backend/
├── app/
│   ├── api/
│   │   ├── routers/          # HTTP-эндпоинты
│   │   └── deps.py           # Зависимости FastAPI (текущий пользователь, сессия БД)
│   ├── services/             # Бизнес-логика
│   ├── repositories/         # Слой работы с БД
│   ├── models/               # SQLAlchemy-модели таблиц
│   ├── schemas/              # Pydantic-схемы
│   ├── core/
│   │   ├── config.py         # Настройки из .env
│   │   └── security.py       # JWT-токены, хэширование паролей
│   ├── db/
│   │   ├── session.py        # Асинхронная сессия SQLAlchemy
│   │   └── base.py           # Базовый класс моделей
│   └── cli/
│       └── create_site_admin.py  # CLI: создание администратора сайта
├── alembic/                  # Миграции БД
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── requirements.txt
```

---

## Быстрый старт

### Требования

- Docker и Docker Compose

### Запуск

```bash
git clone https://github.com/MAVIN-26/MAVIN-backend.git
cd MAVIN-backend

cp .env.example .env
# Обязательно укажи SECRET_KEY и OPENROUTER_API_KEY в .env

docker-compose up --build
```

После запуска:

| Адрес | Что |
|---|---|
| `http://localhost:8000` | REST API |
| `http://localhost:8000/docs` | Swagger UI |
| `http://localhost:9001` | Консоль MinIO (логин: `minioadmin` / `minioadmin`) |

### Применить миграции

```bash
docker-compose exec app alembic upgrade head
```

### Создать администратора сайта

```bash
docker-compose exec \
  -e SITE_ADMIN_EMAIL=admin@example.com \
  -e SITE_ADMIN_PASSWORD=secret \
  -e SITE_ADMIN_PHONE=+70000000000 \
  app python -m app.cli.create_site_admin
```

---

## Переменные окружения

Файл `.env` (пример в `.env.example`):

| Переменная | Описание | Обязательна |
|---|---|---|
| `DATABASE_URL` | Строка подключения к PostgreSQL | да |
| `SECRET_KEY` | Секрет для подписи JWT-токенов | да |
| `MINIO_ENDPOINT` | Адрес MinIO | да |
| `MINIO_ACCESS_KEY` | Логин MinIO | да |
| `MINIO_SECRET_KEY` | Пароль MinIO | да |
| `MINIO_BUCKET` | Имя бакета для изображений | нет (по умолчанию `mavin-images`) |
| `OPENROUTER_API_KEY` | API-ключ OpenRouter (ИИ-ассистент) | нет (ИИ не работает без него) |
| `OPENROUTER_BASE_URL` | Базовый URL OpenRouter | нет (по умолчанию `https://openrouter.ai/api/v1`) |
| `OPENROUTER_MODEL` | Модель OpenRouter | нет (по умолчанию `openai/gpt-4o-mini`) |
| `CORS_ORIGINS` | Разрешённые источники для CORS | нет (по умолчанию `["http://localhost:5173"]`) |

---

## API

Базовый URL: `/api/v1`  
Авторизация: `Authorization: Bearer <token>` (JWT)  
Формат: JSON

| Группа | Эндпоинты | Описание |
|---|---|---|
| Аутентификация | `/auth/register`, `/auth/login`, `/auth/logout`, `/auth/me` | Регистрация, вход, выход, текущий пользователь |
| Профиль | `/profile` | Просмотр и редактирование профиля |
| Рестораны | `/restaurants` | Каталог ресторанов |
| Категории | `/categories`, `/menu-categories` | Категории кухни и разделы меню |
| Меню | `/restaurants/{id}/menu` | Позиции меню ресторана |
| Аллергены | `/allergens` | Справочник аллергенов |
| Избранное | `/favorites` | Избранные рестораны |
| Корзина | `/cart` | Управление корзиной |
| Заказы | `/orders` | Оформление и история заказов (клиент) |
| Заказы (ресторан) | `/owner/orders` | Управление входящими заказами (владелец ресторана) |
| Подписка | `/subscriptions` | Оформление и проверка подписки |
| Промокоды | `/promo-codes` | Применение промокодов |
| Загрузка файлов | `/upload` | Загрузка изображений в MinIO |
| ИИ-ассистент | `/ai/recommend` | Персональные рекомендации блюд |
| WebSocket | `/ws/orders` | Уведомления об изменении статуса заказа |

Полная спецификация: [`docs/swagger.json`](https://github.com/MAVIN-26/MAVIN/blob/main/docs/swagger.json)

---

## Роли пользователей

| Роль | Возможности |
|---|---|
| `customer` | Просмотр ресторанов, оформление заказов, ИИ-ассистент, подписка |
| `restaurant_admin` | Управление своим рестораном: меню, заказы, акции, промокоды |
| `site_admin` | Полный доступ: все пользователи, рестораны, подписки |

---

## Git Workflow

- Основная ветка разработки: `develop`
- Ветки фич: `feature/be-X.X-<название>`
- Коммиты по [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `refactor:`, `docs:`

---

## Лицензия

Copyright © 2026 Команда MAVIN. Все права защищены.  
Подробнее: [LICENSE](https://github.com/MAVIN-26/MAVIN/blob/main/LICENSE)
