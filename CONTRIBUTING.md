# 🛠️ Contributing Guide

Инструкция для разработчиков — как развернуть проект локально, настроить и запустить.

---

## 🚀 Быстрый старт

### Шаг 1 — Установка зависимостей

```bash
pip install -r requirements.txt
playwright install chromium
```

### Шаг 2 — Заполни config.py

```python
API_ID = 12345678            # С https://my.telegram.org/apps
API_HASH = 'your_api_hash'   # С https://my.telegram.org/apps
CHANNEL_USERNAME = 'nvkgym'  # Username канала без @
NOTIFY_USER_ID = 123456789   # Твой Telegram ID (узнай у @userinfobot)

FORM_FIELDS = {
    'entry.14248722':   'Иванов Иван Иванович',  # ФИО
    'entry.1479772708': '@твой_telegram',         # Telegram username
    'emailAddress':     'your@gmail.com',         # Email (для чекбокса)
}
```

Проверь конфиг:
```bash
python validate_config.py
```

Если не знаешь entry.ID полей формы — найди их:
```bash
python find_fields.py https://docs.google.com/forms/d/e/FORM_ID/viewform
```
Или через DevTools: открой форму → F12 → Network → заполни и отправь → найди запрос `formResponse` → вкладка Payload.

### Шаг 3 — Авторизация Telethon (один раз)

```bash
python auth.py
```

Введи номер телефона и код из Telegram. Создаётся `gym_session.session`.

### Шаг 4 — Создание Google-сессии (один раз)

```bash
python playwright_setup.py
```

Откроется видимый браузер — войди в нужный Google-аккаунт, затем нажми Enter в терминале. Создаётся `playwright_session.json`.

### Шаг 5 — Запуск

```bash
python bot.py
```

Бот подключится к Telegram и начнёт мониторить канал. Когда появится ссылка на форму — заполнит автоматически.

---

## 🖥️ Автозапуск на сервере (Linux / systemd)

```bash
sudo cp gym_bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable gym_bot
sudo systemctl start gym_bot
sudo systemctl status gym_bot
```

Логи:
```bash
journalctl -u gym_bot -f
# или
tail -f bot.log
```

---

## 🔄 Обновление Google-сессии

Сессия браузера живёт несколько недель. Когда бот начнёт получать уведомление "Нужна повторная авторизация в Google" — обнови её:

```bash
python playwright_setup.py
```

---

## 🧪 Тестирование

1. Задай тестовый канал в config.py: `CHANNEL_USERNAME = 'my_gym_test'`
2. Запусти бота: `python bot.py`
3. Опубликуй ссылку на форму в тестовом канале
4. Бот должен среагировать, заполнить форму и прислать уведомление
5. Проверь таблицу ответов формы — там должна появиться запись
