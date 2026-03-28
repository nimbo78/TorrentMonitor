# 🤖 TorrentMonitor Bot

Управляй своим [TorrentMonitor](https://github.com/nimbo78/TorrentMonitor) прямо из Telegram — никакого веб-интерфейса, всё в чате. Добавляй раздачи, следи за сериалами, получай уведомления с постерами как в Sonarr/Radarr.

## ✨ Фичи

- 📋 **Список раздач** с пагинацией и сортировкой по дате или имени
- ⏸ **Пауза / возобновление / удаление** прямо из инлайн-меню
- 🔗 **Добавление по URL** — кидаешь ссылку с rutracker, получаешь подтверждение
- 📺 **Добавление сериалов** — по названию для lostfilm и аналогов
- 🔔 **Авто-уведомления** о новых обновлениях с постером из TMDB
- 🔑 **Редактирование учётных данных** трекеров без входа в веб
- ⚙️ **Настройки TM** — прокси, торрент-клиент и прочее прямо из бота
- ⚠️ **Лог ошибок** — смотришь что сломалось, не заходя на сервер
- 🔄 **Два адаптера** — HTTP (по сети) или DB (прямой доступ к базе)

---

## 📱 Как это выглядит

### /list — список раздач

```
📋 Раздачи (24) — 📅 по дате

▶️ Severance [S04E04]
   lostfilm.tv · 2026-03-28 22:36

⏸ Ubuntu 24.04
   rutracker.org · 2026-03-20 10:00

▶️ The Last of Us [S02E01]
   lostfilm.tv · 2026-03-16 18:00

[ Severance [S04E04]      ]
[ Ubuntu 24.04             ]
[ The Last of Us [S02E01] ]
[ ◀️    2/3    ▶️          ]
[ Сортировать 🔤 по имени  ]
```

Нажимаешь на раздачу — открывается карточка:

```
Severance [S04E04]
🔗 lostfilm.tv
📅 2026-03-28 22:36
Статус: ▶️ активна

[ ⏸ Пауза ]  [ 🗑 Удалить ]
[       ◀️ Назад        ]
```

### 🔔 Уведомление о новой раздаче

Когда TM обновил что-то новое, бот пришлёт (с постером если настроен TMDB):

```
[🖼 постер сериала]

🆕 Severance [S04E04]
🔗 lostfilm.tv
📅 2026-03-28 22:36
```

### /addurl — добавить раздачу

```
ты:  /addurl
бот: Отправь URL темы с трекера:
ты:  https://rutracker.org/forum/viewtopic.php?t=6456789
бот: ✅ Тема добавлена для мониторинга.
```

### /errors — что сломалось

```
⚠️ Ошибки (2)

• rutracker.org — cookie_expired
  2026-03-28 12:00
• lostfilm.tv — login_failed
  2026-03-27 08:15
```

---

## 🚀 Быстрый старт

```bash
# 1. Скопировать конфиг
cp bot/.env.example bot/.env

# 2. Заполнить обязательное в bot/.env:
#    TELEGRAM_BOT_TOKEN=...
#    TELEGRAM_ALLOWED_IDS=123456789
#    TM_HTTP_URL=http://localhost:8080
#    TM_HTTP_PASSWORD=admin

# 3. Зависимости
pip install -r bot/requirements.txt

# 4. Поехали
python -m bot.main
```

---

## ⚙️ Конфигурация

Все настройки через `bot/.env` (шаблон — `bot/.env.example`).

### Обязательные

| Переменная | Описание |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Токен от [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_ALLOWED_IDS` | Telegram ID через запятую — только эти юзеры получат доступ |

### HTTP-адаптер (по умолчанию, рекомендуется)

| Переменная | По умолчанию | Описание |
|---|---|---|
| `TM_ADAPTER` | `http` | Режим подключения |
| `TM_HTTP_URL` | `http://localhost:80` | URL TorrentMonitor |
| `TM_HTTP_PASSWORD` | `admin` | Пароль (открытый текст, MD5 делает сам TM) |

### DB-адаптер (прямо в базу)

| Переменная | По умолчанию | Описание |
|---|---|---|
| `TM_ADAPTER` | — | Поставь `db` |
| `TM_DB_TYPE` | `sqlite` | `sqlite` / `mysql` / `pgsql` |
| `TM_DB_PATH` | `/data/htdocs/db/tm.sqlite` | Путь к SQLite файлу |
| `TM_DB_HOST` | `localhost` | Хост (MySQL/PostgreSQL) |
| `TM_DB_PORT` | `3306` | Порт (MySQL/PostgreSQL) |
| `TM_DB_NAME` | `torrentmonitor` | Имя базы |
| `TM_DB_USER` | `torrentmonitor` | Юзер БД |
| `TM_DB_PASSWORD` | *(пусто)* | Пароль БД |

### Прочее

| Переменная | По умолчанию | Описание |
|---|---|---|
| `TM_PAGE_SIZE` | `10` | Раздач на странице в /list |
| `TM_POLL_INTERVAL` | `300` | Как часто проверять обновления (секунды) |
| `TMDB_API_KEY` | *(пусто)* | Ключ для постеров. Без него — только текст |

---

## 🎮 Команды

| Команда | Что делает |
|---|---|
| `/list` | Все раздачи — листаешь, сортируешь, тыкаешь |
| `/addurl` | Добавить раздачу по ссылке с трекера |
| `/addserial` | Добавить сериал по названию (lostfilm и тп) |
| `/credentials` | Учётные данные трекеров — логин/пароль/passkey |
| `/settings` | Настройки TM — прокси, торрент-клиент |
| `/errors` | Лог ошибок — cookie_expired и всё такое |

---

## 🔄 Адаптеры: HTTP vs DB

### 🌐 HTTP (рекомендуется)

Бот общается с TM через HTTP API. Работает откуда угодно, хоть с другого сервера.

- ✅ Все команды работают включая `/addurl` и `/addserial`
- ✅ Авторизация через сессию (бот сам логинится)
- ✅ Идеально для Docker

```env
TM_ADAPTER=http
TM_HTTP_URL=http://torrentmonitor:80
TM_HTTP_PASSWORD=mypassword
```

### 🗄️ DB (прямой доступ)

Бот лезет в базу данных напрямую. Нужно когда TM и бот на одном сервере.

- ⚠️ `/addurl` и `/addserial` недоступны — нет PHP-валидации трекера
- ✅ Работает даже если веб-сервер TM лежит
- ✅ SQLite / MySQL / PostgreSQL

```env
TM_ADAPTER=db
TM_DB_TYPE=sqlite
TM_DB_PATH=/var/www/html/torrentmonitor.sqlite
```

---

## 🔔 Уведомления с постерами

Бот в фоне проверяет новые раздачи каждые `TM_POLL_INTERVAL` секунд. Нашёл — шлёт всем из `TELEGRAM_ALLOWED_IDS`.

С ключом TMDB подгружает постер сериала/фильма (бесплатно):

> **Получить ключ:** [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api) — регистрация бесплатная

Без ключа уведомления всё равно приходят, просто без картинки.

Прогресс сохраняется в `bot/data/state.json` — при рестарте не задвоит.

---

## 🐳 Docker

### Только TorrentMonitor

```bash
docker compose up -d
```

### TorrentMonitor + бот

```bash
# bot/.env должен быть заполнен
docker compose --profile bot up -d
```

Бот крутится в отдельном контейнере, `state.json` живёт в volume `bot_data`.

### Готовые образы

При пуше в `master` или теге `v*` GitHub Actions собирает multi-arch образы (`amd64` / `arm64` / `arm/v7`) и пушит в GHCR:

```bash
docker pull ghcr.io/nimbo78/torrentmonitor:latest
docker pull ghcr.io/nimbo78/torrentmonitor-bot:latest
```

---

## 🖥️ Без Docker

```bash
pip install -r bot/requirements.txt
cp bot/.env.example bot/.env
# заполнить bot/.env
python -m bot.main
```

Для автозапуска через systemd:

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
