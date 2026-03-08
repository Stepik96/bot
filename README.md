# 🏋️ Gym Auto-Registration Bot v2 (Cookie Auth)

---

## 📁 Файлы

```
gym_bot/
├── bot.py                # Основной скрипт
├── config.py             # Настройки (заполнить!)
├── get_cookies.py        # Извлечение cookies (запускать на компьютере)
├── requirements.txt      # Зависимости
└── gym_bot.service       # Автозапуск systemd
```

---

## 🚀 Пошаговая инструкция

### Шаг 1 — Найди entry.ID полей формы (через DevTools)

1. Открой форму в браузере (войди в Google аккаунт)
2. Нажми **F12** → вкладка **Network**
3. Заполни форму тестовыми данными → нажми **Отправить**
4. В Network найди запрос **formResponse** → нажми на него → **Payload**
5. Увидишь что-то вроде:
   ```
   entry.123456789: Иванов Иван Иванович
   entry.987654321: @username
   ```
6. Скопируй эти ID в config.py

### Шаг 2 — Заполни config.py

```python
CHANNEL_USERNAME = 'my_gym_test'   # тест, потом поменяй на NVKGYM
FORM_FIELDS = {
    'entry.123456789': 'Твоё ФИО полностью',
    'entry.987654321': '@твой_telegram',
}
```

### Шаг 3 — Получи Google cookies (на своём компьютере)

**Автоматически:**
```bash
pip install browser-cookie3
python get_cookies.py
```

**Вручную (если автоматически не сработало):**
1. Открой форму в браузере, убедись что авторизован в Google
2. F12 → Application → Cookies → https://accounts.google.com
3. Найди cookie с именем **SSID**, **SID**, **HSID**, **APISID**, **SAPISID**, **__Secure-1PSID**
4. Создай файл `google_cookies.json` вручную:
```json
[
  {"name": "SID", "value": "значение"},
  {"name": "HSID", "value": "значение"},
  {"name": "SSID", "value": "значение"},
  {"name": "APISID", "value": "значение"},
  {"name": "SAPISID", "value": "значение"},
  {"name": "__Secure-1PSID", "value": "значение"}
]
```

**Скопируй на сервер:**
```bash
scp google_cookies.json user@server-ip:~/gym_bot/
```

### Шаг 4 — Установка на сервере

```bash
cd ~/gym_bot
pip3 install -r requirements.txt
python3 bot.py   # первый запуск — авторизация Telegram
```

### Шаг 5 — Автозапуск

```bash
sudo cp gym_bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable gym_bot
sudo systemctl start gym_bot
sudo systemctl status gym_bot
```

---

## 🔄 Обновление cookies (раз в 2-3 недели)

```bash
# На своём компьютере:
python get_cookies.py
scp google_cookies.json user@server-ip:~/gym_bot/

# На сервере:
sudo systemctl restart gym_bot
```

---

## 🧪 Тестирование

1. Запусти бота: `python3 bot.py`
2. Скинь ссылку на форму в тестовый канал @my_gym_test
3. Бот должен среагировать и заполнить форму
4. Проверь таблицу ответов формы — там должна появиться твоя запись
5. Ты получишь уведомление в Telegram

---

## ❓ Частые проблемы

**"Cookies не загружены"**
→ Запусти get_cookies.py и скопируй файл на сервер

**Форма не заполняется (401/403)**
→ Cookies протухли — обнови их через get_cookies.py

**Бот не видит сообщения**
→ Убедись что подписан на канал
→ Проверь CHANNEL_USERNAME в config.py (без @)
