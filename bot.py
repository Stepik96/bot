"""
Gym Auto-Registration Bot — версия с OAuth2 авторизацией Google
"""

import asyncio
import aiohttp
import logging
import re
import json
import os
import sys
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from config import (
    API_ID, API_HASH, CHANNEL_USERNAME,
    FORM_FIELDS, NOTIFY_USER_ID
)

DEVICE_PARAMS = dict(
    device_model='Desktop',
    system_version='11',
    app_version='4.16.30',
    system_lang_code='en-US',
    lang_code='en',
)

# Фикс кодировки Windows терминала (cp1251 не поддерживает эмодзи)
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger(__name__)

TOKEN_FILE = 'token.json'
CREDENTIALS_FILE = 'credentials.json'

SCOPES = [
    'https://www.googleapis.com/auth/forms.responses.readonly',
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]


def get_valid_credentials() -> Credentials | None:
    """Загружает и при необходимости обновляет OAuth2 токен."""
    if not os.path.exists(TOKEN_FILE):
        log.error(f"Файл {TOKEN_FILE} не найден! Запусти oauth2_setup.py")
        return None

    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            log.info("Обновляю OAuth2 токен...")
            creds.refresh(Request())
            # Сохраняем обновлённый токен
            with open(TOKEN_FILE, 'w') as f:
                f.write(creds.to_json())
            log.info("Токен обновлён и сохранён")
        else:
            log.error("Токен истёк и нет refresh_token. Запусти oauth2_setup.py заново")
            return None

    return creds


def extract_form_url(text: str) -> str | None:
    pattern = r'https://docs\.google\.com/forms/[^\s\)]+'
    match = re.search(pattern, text)
    return match.group(0) if match else None


def build_submit_url(form_url: str) -> str:
    base = re.match(r'(https://docs\.google\.com/forms/d/e/[^/]+)', form_url)
    if base:
        return base.group(1) + '/formResponse'
    base2 = re.match(r'(https://docs\.google\.com/forms/d/[^/]+)', form_url)
    if base2:
        return base2.group(1) + '/formResponse'
    return form_url.split('?')[0].replace('viewform', 'formResponse')


async def submit_google_form(form_url: str) -> bool:
    submit_url = build_submit_url(form_url)

    # Получаем валидный OAuth2 токен
    creds = get_valid_credentials()
    if not creds:
        return False

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Referer': form_url,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Origin': 'https://docs.google.com',
        # OAuth2 Bearer токен — это ключевое отличие от cookie-версии
        'Authorization': f'Bearer {creds.token}',
    }

    log.info(f"Отправляю на: {submit_url}")
    log.info(f"Поля: {FORM_FIELDS}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                submit_url,
                data=FORM_FIELDS,
                headers=headers,
                allow_redirects=True,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                final_url = str(response.url)
                log.info(f"Статус: {response.status}, URL: {final_url}")

                # Проверяем что форма реально принята
                # При успехе Google редиректит на .../formResponse (не на viewform)
                if 'viewform' in final_url and 'pli=1' in final_url:
                    log.error("Google вернул страницу формы снова — авторизация не прошла")
                    return False

                return response.status == 200

    except Exception as e:
        log.error(f"Ошибка при отправке: {e}")
        return False


async def main():
    log.info("Запуск бота (OAuth2 версия)...")

    # Проверяем токен при старте
    creds = get_valid_credentials()
    if not creds:
        log.error("Нет валидного OAuth2 токена. Запусти oauth2_setup.py")
        return

    log.info("OAuth2 токен валиден")

    client = TelegramClient(
        'gym_session', API_ID, API_HASH,
        **DEVICE_PARAMS,
    )

    try:
        await client.connect()
    except Exception as e:
        log.error("Не удалось подключиться к Telegram: %s", e)
        return

    if not await client.is_user_authorized():
        log.error("Сессия не авторизована. Запусти auth.py")
        await client.disconnect()
        return

    try:
        await client.start()
    except FloodWaitError as e:
        wait = getattr(e, 'seconds', None) or getattr(e, 'value', 60)
        log.error("FloodWait: подожди %s сек", wait)
        await client.disconnect()
        return

    log.info("Подключились к Telegram!")

    processed_messages = set()

    @client.on(events.NewMessage(chats=CHANNEL_USERNAME))
    async def handler(event):
        msg_id = event.message.id
        if msg_id in processed_messages:
            return
        processed_messages.add(msg_id)

        msg_text = event.message.message or ''
        log.info(f"Новое сообщение [{msg_id}]: {msg_text[:120]}")

        form_url = extract_form_url(msg_text)
        if not form_url:
            log.info("Ссылки на форму нет — пропускаем")
            return

        log.info(f"Форма найдена: {form_url}")
        success = await submit_google_form(form_url)

        if success:
            log.info("Форма заполнена!")
            if NOTIFY_USER_ID:
                await client.send_message(NOTIFY_USER_ID,
                    f"Записался в спортзал!\nФорма: {form_url}")
        else:
            log.error("Не удалось заполнить форму")
            if NOTIFY_USER_ID:
                await client.send_message(NOTIFY_USER_ID,
                    f"Ошибка! Заполни вручную:\n{form_url}")

    log.info(f"Мониторю канал: {CHANNEL_USERNAME}")
    await client.run_until_disconnected()


if __name__ == '__main__':
    asyncio.run(main())
