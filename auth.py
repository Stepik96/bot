"""
Первичная авторизация Telethon: пошаговый ввод с подробным логированием.
Запускай этот скрипт, если при bot.py код подтверждения не приходит.

После успешного входа создаётся gym_session.session — затем можно запускать bot.py.

Почему код может не прийти (часто на стороне Telegram):
- Код приходит в чат "Telegram" в приложении (не SMS) — проверь вкладку "Устройства" или чат с Telegram.
- Временные сбои доставки (помогает подождать 8–12 ч или попробовать позже).
- FloodWait — слишком частые запросы; скрипт сам ждёт и повторяет.
- Попробуй QR-логин в веб-версии Telegram или другой клиент для создания сессии.
"""

import asyncio
import logging
import sys
from getpass import getpass

from telethon import TelegramClient, functions
from telethon.errors import (
    FloodWaitError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    SessionPasswordNeededError,
    PhoneNumberInvalidError,
)

from config import API_ID, API_HASH

SESSION_NAME = 'gym_session'
CODE_WAIT_SECONDS = 60
RESEND_AFTER_SECONDS = 60

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('auth.log'),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger('auth')


def _sent_code_type_hint(sent):
    """По типу SentCode подсказываем, куда смотреть код."""
    try:
        t = sent.type
        name = type(t).__name__
        if 'App' in name:
            return 'Код отправлен в приложение Telegram (чаты или уведомление). Проверь чат "Telegram" или вкладку "Устройства".'
        if 'Sms' in name or 'SMS' in name:
            return 'Код отправлен по SMS на твой номер.'
        if 'Call' in name or 'FlashCall' in name:
            return 'Код может прийти звонком (последние цифры номера).'
        return 'Код отправлен Telegram. Проверь приложение и SMS.'
    except Exception:
        return 'Код отправлен Telegram. Проверь приложение Telegram и SMS.'


async def send_code_with_retry(client, phone: str):
    """Отправка кода с обработкой FloodWait. Возвращает (sent_code, phone_code_hash)."""
    while True:
        try:
            log.info('Отправляю запрос кода на номер %s...', phone)
            sent = await client.send_code_request(phone)
            log.info('Ответ от Telegram получен.')
            hash_val = sent.phone_code_hash
            log.info('phone_code_hash получен (нужен для sign_in и повторной отправки).')
            hint = _sent_code_type_hint(sent)
            log.info('Подсказка: %s', hint)
            return sent, hash_val
        except FloodWaitError as e:
            wait = getattr(e, 'seconds', None) or getattr(e, 'value', 60)
            log.warning('FloodWait: ждём %s сек перед повторной отправкой.', wait)
            await asyncio.sleep(wait)
        except PhoneNumberInvalidError:
            log.error('Номер телефона неверный. Введи в формате +79001234567')
            raise
        except Exception as e:
            log.exception('Ошибка при отправке кода: %s', e)
            raise


async def resend_code(client, phone: str, phone_code_hash: str):
    """Повторная отправка кода."""
    try:
        log.info('Запрашиваю повторную отправку кода...')
        result = await client(functions.auth.ResendCodeRequest(
            phone_number=phone,
            phone_code_hash=phone_code_hash,
        ))
        hint = _sent_code_type_hint(result)
        log.info('Код отправлен снова. %s', hint)
        return True
    except FloodWaitError as e:
        wait = getattr(e, 'seconds', None) or getattr(e, 'value', 60)
        log.warning('FloodWait при повторной отправке: ждём %s сек.', wait)
        await asyncio.sleep(wait)
        return await resend_code(client, phone, phone_code_hash)
    except Exception as e:
        log.error('Не удалось отправить код повторно: %s', e)
        return False


async def wait_for_code_input(phone: str, phone_code_hash: str, client: TelegramClient) -> str:
    """Ждём ввод кода; через 60 сек без ввода — предлагаем отправить код повторно."""
    loop = asyncio.get_event_loop()

    while True:
        print()
        print('Введи код из Telegram или SMS (без пробелов). Если не пришёл — через 60 сек можно запросить снова.')
        print()

        def read_code():
            return input('Код: ').strip().replace(' ', '')

        try:
            code = await asyncio.wait_for(
                loop.run_in_executor(None, read_code),
                timeout=RESEND_AFTER_SECONDS,
            )
        except asyncio.TimeoutError:
            log.info('Прошло %s сек. Код не введён.', RESEND_AFTER_SECONDS)
            again = input('Запросить код повторно? (да/нет): ').strip().lower()
            if again in ('да', 'yes', 'y', 'д'):
                await resend_code(client, phone, phone_code_hash)
                continue
            raise SystemExit('Выход. Запусти auth.py снова, когда будешь готов ввести код.')

        if code:
            return code
        print('Введи непустой код.')


async def do_auth():
    log.info('=== Авторизация Telethon ===')
    log.info('Сессия: %s.session', SESSION_NAME)
    log.info('API_ID: %s', API_ID)

    # Параметры устройства — у некоторых пользователей помогают получить код (см. GitHub #4730)
    client = TelegramClient(
        SESSION_NAME,
        API_ID,
        API_HASH,
        device_model='Desktop',
        system_version='11',
        app_version='4.16.30',
        system_lang_code='en-US',
        lang_code='en',
    )

    try:
        await client.connect()
        log.info('Подключение к Telegram установлено.')

        if not await client.is_user_authorized():
            phone = input('Номер телефона (формат +79001234567): ').strip()
            if not phone:
                log.error('Номер не введён.')
                return

            sent, phone_code_hash = await send_code_with_retry(client, phone)
            code = await wait_for_code_input(phone, phone_code_hash, client)

            try:
                await client.sign_in(phone, code=code, phone_code_hash=phone_code_hash)
            except SessionPasswordNeededError:
                log.info('Включена двухфакторная аутентификация (2FA).')
                password = getpass('Пароль 2FA: ')
                await client.sign_in(password=password)
            except PhoneCodeInvalidError:
                log.error('Неверный код. Запусти auth.py заново.')
                return
            except PhoneCodeExpiredError:
                log.error('Код истёк. Запусти auth.py заново и запроси новый код.')
                return

            log.info('Вход выполнен успешно.')
        else:
            log.info('Сессия уже авторизована.')

        me = await client.get_me()
        log.info('Ты вошёл как: %s (%s)', me.first_name or me.username or me.phone, me.phone)
        log.info('Файл сессии: %s.session — можно запускать bot.py', SESSION_NAME)

    except FloodWaitError as e:
        wait = getattr(e, 'seconds', None) or getattr(e, 'value', 60)
        log.error('FloodWait: Telegram просит подождать %s сек. Попробуй позже.', wait)
    except Exception as e:
        log.exception('Ошибка: %s', e)
    finally:
        await client.disconnect()
        log.info('Отключено.')


if __name__ == '__main__':
    asyncio.run(do_auth())
