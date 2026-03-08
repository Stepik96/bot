"""
Gym Auto-Registration Bot — версия с Cookie авторизацией
"""

import asyncio
import aiohttp
import logging
import re
import json
import os
from telethon import TelegramClient, events
from config import (
    API_ID, API_HASH, CHANNEL_USERNAME,
    FORM_FIELDS, NOTIFY_USER_ID
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

COOKIES_FILE = 'google_cookies.json'


def load_cookies() -> dict:
    if not os.path.exists(COOKIES_FILE):
        log.error(f"Файл {COOKIES_FILE} не найден! Запусти get_cookies.py")
        return {}
    with open(COOKIES_FILE, 'r') as f:
        cookies_list = json.load(f)
    # Конвертируем из формата браузера в dict
    return {c['name']: c['value'] for c in cookies_list}


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
    cookies = load_cookies()

    if not cookies:
        log.error("Cookies не загружены!")
        return False

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Referer': form_url,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Origin': 'https://docs.google.com',
    }

    log.info(f"Отправляю на: {submit_url}")
    log.info(f"Поля: {FORM_FIELDS}")

    try:
        async with aiohttp.ClientSession(cookies=cookies) as session:
            async with session.post(
                submit_url,
                data=FORM_FIELDS,
                headers=headers,
                allow_redirects=True,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                log.info(f"Статус ответа: {response.status}, URL: {response.url}")
                return response.status == 200
    except Exception as e:
        log.error(f"Ошибка при отправке: {e}")
        return False


async def main():
    log.info("Запуск бота...")

    client = TelegramClient('gym_session', API_ID, API_HASH)
    await client.start()
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

        log.info(f"🎯 Форма найдена: {form_url}")
        success = await submit_google_form(form_url)

        if success:
            log.info("✅ Форма заполнена!")
            if NOTIFY_USER_ID:
                await client.send_message(NOTIFY_USER_ID,
                    f"✅ Записался в спортзал!\nФорма: {form_url}")
        else:
            log.error("❌ Не удалось заполнить форму")
            if NOTIFY_USER_ID:
                await client.send_message(NOTIFY_USER_ID,
                    f"❌ Ошибка! Заполни вручную:\n{form_url}")

    log.info(f"👀 Мониторю канал: {CHANNEL_USERNAME}")
    await client.run_until_disconnected()


if __name__ == '__main__':
    asyncio.run(main())
