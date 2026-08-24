# HORDE Auth Backend

Локальный каркас API для будущей авторизации сайта и лаунчера через MySQL Aiven.

Что уже заложено:

- регистрация ника Minecraft + пароль;
- вход по нику и паролю;
- токен сессии для сайта;
- отдельный токен для лаунчера;
- привязка существующего игрового аккаунта через одноразовый код `/linksite` в будущем;
- чтение активной донат-подписки по нику.

Важно: пароль MySQL нельзя хранить в GitHub Pages, лаунчере или публичном репозитории. Он должен лежать только в `.env` на сервере, где работает backend.

## Запуск локально

```powershell
cd tools\horde_auth_backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Потом заполнить `.env` настоящим паролем MySQL и положить CA-сертификат в `ca.pem`.

```powershell
uvicorn horde_auth.app:app --host 127.0.0.1 --port 8765
```

Проверка:

```powershell
Invoke-WebRequest http://127.0.0.1:8765/health
```

## Что нельзя делать

- Не коммитить `.env`, `ca.pem`, токены и пароли.
- Не подключать лаунчер напрямую к MySQL.
- Не заменять текущий LoginSystem до миграции: сначала привязка `/linksite`, потом переход.

## Следующий безопасный шаг

Сделать маленький серверный мод/команду `/linksite`, которая создаёт код в таблице `site_link_codes`. Тогда игрок сможет:

1. зайти на сервер старым способом;
2. написать `/linksite`;
3. ввести код на сайте;
4. задать пароль для сайта/лаунчера.

Так мы не потеряем инвентари, донаты и старые аккаунты.

## Бесплатный запуск через Render

1. Зайти на Render.
2. Создать `New` → `Web Service`.
3. Подключить GitHub-репозиторий `HordeMinecraft/HordeMinecraft`.
4. В `Root Directory` указать:

```text
backend/auth
```

5. Build command:

```text
pip install -r requirements.txt
```

6. Start command:

```text
uvicorn horde_auth.app:app --host 0.0.0.0 --port $PORT
```

7. Добавить переменные окружения:

```text
HORDE_AUTH_DB_HOST
HORDE_AUTH_DB_PORT
HORDE_AUTH_DB_NAME
HORDE_AUTH_DB_USER
HORDE_AUTH_DB_PASSWORD
HORDE_AUTH_DB_SSL_CA_TEXT
HORDE_AUTH_SERVER_SECRET
HORDE_AUTH_CORS_ORIGINS=https://hordeminecraft.ru
HORDE_AUTH_SESSION_DAYS=30
```

8. После запуска открыть:

```text
https://АДРЕС-RENDER/health
```

Если ответ `{"status":"ok"}`, backend работает.

9. Потом в DNS добавить поддомен:

```text
api.hordeminecraft.ru
```

и направить его на Render-сервис.
