# TorrentMonitor Bot

Telegram-бот для управления [TorrentMonitor](https://github.com/nimbo78/TorrentMonitor).
Позволяет просматривать раздачи, добавлять новые, управлять паузой/удалением и получать уведомления о новых обновлениях — без веб-интерфейса.

## Содержание

- [Требования](#требования)
- [Быстрый старт](#быстрый-старт)
- [Конфигурация](#конфигурация)
- [Команды](#команды)
- [Адаптеры](#адаптеры)
- [Уведомления и постеры TMDB](#уведомления-и-постеры-tmdb)
- [Запуск через Docker](#запуск-через-docker)
- [Запуск без Docker](#запуск-без-docker)

---

## Требования

- Python 3.12+
- Работающий экземпляр TorrentMonitor (v2.2.4+)
- Telegram Bot Token ([получить у @BotFather](https://t.me/BotFather))
- *(опционально)* TMDB API Key для постеров в уведомлениях

---

## Быстрый старт

```bash
# 1. Создать .env из примера
cp bot/.env.example bot/.env

# 2. Заполнить обязательные поля в bot/.env
#    TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_IDS, TM_HTTP_URL, TM_HTTP_PASSWORD

# 3. Установить зависимости
pip install -r bot/requirements.txt

# 4. Запустить
python -m bot.main
```

---

## Конфигурация

Все настройки задаются через файл `bot/.env` (шаблон — `bot/.env.example`).

### Обязательные

| Переменная | Описание |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Токен бота от @BotFather |
| `TELEGRAM_ALLOWED_IDS` | Telegram ID пользователей через запятую (бот отвечает только им) |

### Адаптер подключения к TM

| Переменная | По умолчанию | Описание |
|---|---|---|
| `TM_ADAPTER` | `http` | Способ подключения: `http` или `db` |

**HTTP-адаптер** (рекомендуется):

| Переменная | По умолчанию | Описание |
|---|---|---|
| `TM_HTTP_URL` | `http://localhost:80` | URL TorrentMonitor |
| `TM_HTTP_PASSWORD` | `admin` | Пароль для входа (открытый текст, MD5 делает сам TM) |

**DB-адаптер** (прямой доступ к базе данных):

| Переменная | По умолчанию | Описание |
|---|---|---|
| `TM_DB_TYPE` | `sqlite` | Тип БД: `sqlite`, `mysql`, `pgsql` |
| `TM_DB_PATH` | `/data/htdocs/db/tm.sqlite` | Путь к файлу SQLite |
| `TM_DB_HOST` | `localhost` | Хост (только для MySQL/PostgreSQL) |
| `TM_DB_PORT` | `3306` | Порт (только для MySQL/PostgreSQL) |
| `TM_DB_NAME` | `torrentmonitor` | Имя базы данных |
| `TM_DB_USER` | `torrentmonitor` | Пользователь БД |
| `TM_DB_PASSWORD` | *(пусто)* | Пароль БД |

### Дополнительные

| Переменная | По умолчанию | Описание |
|---|---|---|
| `TM_PAGE_SIZE` | `10` | Количество раздач на одной странице `/list` |
| `TM_POLL_INTERVAL` | `300` | Интервал проверки новых раздач в секундах |
| `TMDB_API_KEY` | *(пусто)* | API-ключ TMDB для постеров в уведомлениях |

---

## Команды

| Команда | Описание |
|---|---|
| `/list` | Список всех отслеживаемых раздач с пагинацией и сортировкой |
| `/addurl` | Добавить раздачу по URL с трекера |
| `/addserial` | Добавить сериал по названию (для lostfilm.tv и аналогов) |
| `/credentials` | Просмотр и редактирование учётных данных трекеров |
| `/settings` | Просмотр и редактирование настроек TorrentMonitor |
| `/errors` | Просмотр последних ошибок и предупреждений |

### Как работает /list

- Раздачи отображаются постранично (по `TM_PAGE_SIZE` на странице)
- Сортировка: по дате обновления или по названию — переключается кнопкой
- Эпизод серии отображается в формате `[S04E04]` рядом с названием
- Нажатие на раздачу открывает карточку с кнопками **Пауза / Возобновить** и **Удалить**

---

## Адаптеры

Бот поддерживает два способа работы с TorrentMonitor:

### HTTP-адаптер (по умолчанию)

Работает через HTTP API (`action.php` + `api.php`). TM должен быть доступен по сети.

- Поддерживает все операции, включая добавление раздач
- Авторизация через сессионные cookie (автоматически)
- Рекомендуется для Docker и удалённого доступа

### DB-адаптер

Прямое подключение к базе данных TM. Используется когда бот запущен на том же сервере, что и TM.

- Не поддерживает `/addurl` и `/addserial` (нет валидации трекера без PHP)
- Работает без запущенного веб-сервера TM
- Подходит для резервного доступа

Выбор адаптера: `TM_ADAPTER=http` или `TM_ADAPTER=db` в `.env`.

---

## Уведомления и постеры TMDB

Бот автоматически проверяет новые обновления раздач каждые `TM_POLL_INTERVAL` секунд и отправляет уведомления всем пользователям из `TELEGRAM_ALLOWED_IDS`.

Если задан `TMDB_API_KEY`, бот ищет постер сериала/фильма в TMDB и отправляет его вместе с уведомлением (как `sendPhoto`). Без ключа — просто текстовое сообщение.

**Получить ключ TMDB:** [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api) (бесплатно)

Состояние последней проверки сохраняется в `bot/data/state.json`.

---

## Запуск через Docker

### Только TorrentMonitor (без бота)

```bash
docker compose up -d
```

### С ботом

```bash
# Убедитесь, что bot/.env заполнен
docker compose --profile bot up -d
```

Бот запустится как отдельный контейнер `bot`, данные `state.json` сохраняются в volume `bot_data`.

### Сборка образов вручную

```bash
# TorrentMonitor
docker build -t torrentmonitor:latest .

# Бот
docker build -f bot/Dockerfile -t torrentmonitor-bot:latest .
```

### Готовые образы (GitHub Actions)

При пуше в `master` или теге `v*` автоматически собираются multi-arch образы (`amd64`, `arm64`, `arm/v7`) и публикуются в GHCR:

```bash
docker pull ghcr.io/nimbo78/torrentmonitor:latest
docker pull ghcr.io/nimbo78/torrentmonitor-bot:latest
```

---

## Запуск без Docker

```bash
# Установить зависимости
pip install -r bot/requirements.txt

# Создать и заполнить .env
cp bot/.env.example bot/.env
nano bot/.env

# Запустить из корня проекта
python -m bot.main
```

Для автозапуска можно использовать systemd:

```ini
[Unit]
Description=TorrentMonitor Bot
After=network.target

[Service]
WorkingDirectory=/path/to/TorrentMonitor
ExecStart=/usr/bin/python3 -m bot.main
Restart=on-failure
EnvironmentFile=/path/to/TorrentMonitor/bot/.env

[Install]
WantedBy=multi-user.target
```
