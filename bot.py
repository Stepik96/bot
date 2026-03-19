"""
Gym Auto-Registration Bot — версия с эмуляцией браузера через Playwright.

Бот:
- следит за Telegram-каналом;
- при появлении ссылки на Google Form открывает её в «виртуальном» браузере;
- заполняет форму через JavaScript (находит видимые поля рядом со скрытыми entry.ID);
- обрабатывает капчу / разлогин и уведомляет пользователя.
"""

import asyncio
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict

from playwright.async_api import Page, async_playwright
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError

from config import (
    API_ID,
    API_HASH,
    CHANNEL_USERNAME,
    PERSONAL_DATA,
    FORM_ENTRIES,
    NOTIFY_USER_ID,
    PREFERRED_TIME,
)

DEVICE_PARAMS = dict(
    device_model="Desktop",
    system_version="11",
    app_version="4.16.30",
    system_lang_code="en-US",
    lang_code="en",
)

PLAYWRIGHT_SESSION_FILE = "playwright_session.json"

CHROME_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("gym_bot")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    file_handler = logging.FileHandler("bot.log", encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


log = setup_logging()


def extract_form_url(text: str) -> str | None:
    """
    Извлекает нужную ссылку на Google Form из текста сообщения.

    Формат сообщения канала:
        18:00
        https://docs.google.com/forms/...

        19:15
        https://docs.google.com/forms/...

        20:30
        https://docs.google.com/forms/...

    Ссылка определяется по метке времени, написанной перед ней — не по порядку.
    Ссылки на Spreadsheets и Tasks игнорируются.
    Нужный слот задаётся в config.py через PREFERRED_TIME.
    """
    # Логируем ссылки которые игнорируем
    for pattern, label in [
        (r"https://docs\.google\.com/spreadsheets/[^\s]+", "Google Spreadsheets"),
        (r"https://tasks\.google\.com/[^\s]+", "Google Tasks"),
    ]:
        for url in re.findall(pattern, text):
            log.info("Найдена ссылка %s (информативная, пропускаем): %s", label, url[:60])

    # Ищем пары "время + ссылка на форму" — время написано на строке перед ссылкой
    # Паттерн: метка времени (HH:MM), затем любые символы до ссылки на форму
    pattern = r"(1[89]:\d{2}|20:30|21:\d{2})\s*\n\s*(https://docs\.google\.com/forms/[^\s]+)"
    matches = re.findall(pattern, text)

    slot_to_url: dict[str, str] = {}
    for time_label, url in matches:
        # Нормализуем метку: берём только HH:MM начала слота
        # Зал пишет "18:00", "19:15", "20:30" — берём как есть
        slot_to_url[time_label] = url

    if not slot_to_url:
        log.warning("Не удалось найти пары время+ссылка в сообщении. Текст: %s", text[:200])
        return None

    log.info(
        "Найдено %d слотов: %s",
        len(slot_to_url),
        {t: u[:55] + "..." for t, u in slot_to_url.items()},
    )

    if PREFERRED_TIME in slot_to_url:
        log.info("Выбран слот %s (PREFERRED_TIME из config.py)", PREFERRED_TIME)
        return slot_to_url[PREFERRED_TIME]

    log.warning(
        "Слот %s не найден среди доступных %s. Беру первый доступный.",
        PREFERRED_TIME,
        list(slot_to_url.keys()),
    )
    return next(iter(slot_to_url.values()))


async def _ensure_stealth(page: Page) -> None:
    """Stealth-режим: скрываем признаки автоматизации от Google."""
    await page.context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
    )


async def submit_form_playwright(form_url: str, selected_time: str) -> Dict[str, Any]:
    """
    Открывает форму через Playwright и заполняет её.

    Порядок полей в форме (сверху вниз):
      1. Электронная почта — чекбокс div[role='checkbox']
      2. ФИО             — видимый input, индекс 0
      3. Группа          — видимый input, индекс 1
      4. Telegram        — видимый input, индекс 2

    entry.ID для каждого времени берутся из FORM_ENTRIES[selected_time].
    Личные данные берутся из PERSONAL_DATA — одно место для всех форм.
    """
    result: Dict[str, Any] = {
        "success": False,
        "captcha": False,
        "login_required": False,
        "screenshot": None,
    }

    # Собираем поля: entry.ID из FORM_ENTRIES + значения из PERSONAL_DATA
    entries = FORM_ENTRIES.get(selected_time, {})
    form_fields = {
        entries['entry_fio']:      PERSONAL_DATA['name'],
        entries['entry_group']:    PERSONAL_DATA['group'],
        entries['entry_telegram']: PERSONAL_DATA['telegram'],
        'emailAddress':            PERSONAL_DATA['email'],
    }
    log.info("Поля для слота %s: %s", selected_time, form_fields)

    session_path = Path(PLAYWRIGHT_SESSION_FILE)

    async with async_playwright() as p:
        headless = session_path.exists()

        browser = await p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=CHROME_USER_AGENT,
            storage_state=str(session_path) if session_path.exists() else None,
        )

        page = await context.new_page()
        await _ensure_stealth(page)

        try:
            log.info("Открываю форму через Playwright: %s", form_url)
            # domcontentloaded быстрее чем networkidle
            await page.goto(form_url, wait_until="domcontentloaded")

            # Ждём загрузки DOM формы
            await asyncio.sleep(2.0)

            # Если Google просит логин — сессия истекла
            if "accounts.google.com" in page.url:
                log.warning("Перенаправление на страницу логина Google. Нужна повторная авторизация.")
                result["login_required"] = True
                shot = "playwright_login_required.png"
                await page.screenshot(path=shot, full_page=True)
                result["screenshot"] = shot
                return result

            # Заполнение полей через Playwright locator().fill() по порядку появления на странице.
            # Текстовые поля (entry.XXXXX) заполняем по индексу среди видимых input/textarea.
            # emailAddress — это кастомный чекбокс Google Forms (div[role='checkbox']), не input.

            # Текстовые поля: ФИО (0), Группа (1), Telegram (2)
            text_fields = [(name, value) for name, value in form_fields.items() if name != 'emailAddress']

            # Ждём пока хотя бы одно текстовое поле станет видимым
            visible_input_selector = (
                'input:not([type="hidden"]):not([type="submit"]):not([type="checkbox"]):not([type="radio"]), textarea'
            )
            try:
                await page.wait_for_selector(visible_input_selector, timeout=10000)
            except Exception:
                log.warning("Видимые поля ввода не найдены за 10 сек.")

            for field_index, (name, value) in enumerate(text_fields):
                log.info("Заполняю поле '%s' (индекс %d)...", name, field_index)
                try:
                    locator = page.locator(visible_input_selector).nth(field_index)
                    await locator.wait_for(state="visible", timeout=5000)
                    await locator.click()
                    await locator.fill(str(value))
                    # Триггерим blur чтобы Google Forms зафиксировал значение
                    await locator.evaluate("el => el.blur()")
                    log.info("Результат заполнения поля '%s': ok", name)
                except Exception as e:
                    log.error("Не удалось заполнить поле '%s': %s", name, e)

            # Специальная обработка emailAddress — Google Forms рендерит его как div[role='checkbox']
            if 'emailAddress' in form_fields:
                log.info("Заполняю поле 'emailAddress'...")
                checked = await page.evaluate("""
                    () => {
                        // Google Forms рендерит чекбокс email как div с role='checkbox'
                        const selectors = [
                            'div[role="checkbox"]',
                            'div[jsname][role="checkbox"]',
                            'div.isRequired div[role="checkbox"]',
                        ];
                        for (const sel of selectors) {
                            const cb = document.querySelector(sel);
                            if (cb) {
                                const isChecked = cb.getAttribute('aria-checked') === 'true';
                                if (!isChecked) {
                                    cb.click();
                                }
                                return 'ok';
                            }
                        }
                        // Запасной вариант: стандартный input[type=checkbox]
                        const input = document.querySelector('input[type="checkbox"]');
                        if (input) {
                            if (!input.checked) {
                                input.click();
                                input.dispatchEvent(new Event('change', {bubbles: true}));
                            }
                            return 'ok_input';
                        }
                        return 'not_found';
                    }
                """)
                log.info("Чекбокс emailAddress: %s", checked)

            # Небольшая пауза после заполнения всех полей
            await asyncio.sleep(0.5)

            # Скриншот перед отправкой — для диагностики заполнения
            await page.screenshot(path="playwright_before_submit.png", full_page=True)
            log.info("Скриншот до отправки сохранён: playwright_before_submit.png")

            # Поиск и нажатие кнопки Submit
            log.info("Ищу кнопку отправки формы...")
            submit_selectors = [
                "div[role='button'][jsname='M2UYVd']",
                "div[role='button'] span[jsname='V67aGc']",
                "div[role='button']:has(span:text('Отправить'))",
                "div[role='button']:has(span:text('Submit'))",
                "div[role='button'][data-idom-class*='quantumWizButtonPaperbuttonLabel']",
            ]

            submit_button = None
            for sel in submit_selectors:
                try:
                    submit_button = await page.wait_for_selector(sel, timeout=3000)
                    if submit_button:
                        log.info("Кнопка Submit найдена по селектору: %s", sel)
                        break
                except Exception:
                    continue

            if not submit_button:
                log.error("Кнопка Submit не найдена ни одним из селекторов")
                shot_path = "playwright_no_submit.png"
                await page.screenshot(path=shot_path, full_page=True)
                result["screenshot"] = shot_path
                result["success"] = False
                return result

            await page.evaluate("el => el.click()", submit_button)
            log.info("Кнопка отправки нажата (JS click), жду ответ...")

            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(2.0)

            # Скриншот результата
            shot_path = "playwright_result.png"
            await page.screenshot(path=shot_path, full_page=True)
            result["screenshot"] = shot_path

            content = (await page.content()).lower()
            url_after = page.url
            log.info("URL после отправки: %s", url_after)

            # Обнаружение капчи
            if "капча" in content or "recaptcha" in content or "робот" in content:
                log.warning("Похоже, Google показал капчу.")
                result["captcha"] = True
                result["success"] = False
                return result

            # Проверка успешной отправки по тексту страницы
            success_markers = [
                "ответ записан",
                "форма отправлена",
                "your response has been recorded",
                "thanks",
                "спасибо",
            ]
            if any(marker in content for marker in success_markers):
                result["success"] = True
                log.info("Форма успешно отправлена (по тексту страницы).")
                return result

            # Если вернули на страницу формы — скорее всего ошибка
            if "viewform" in url_after and "pli=1" in url_after:
                log.error("Google вернул страницу формы снова — отправка не прошла.")
                result["success"] = False
                return result

            # Нет явных признаков ошибки — считаем успехом
            log.info("Нет явных признаков ошибки, считаем отправку успешной.")
            result["success"] = True
            return result

        finally:
            await context.close()
            await browser.close()


async def process_message(client, msg_id: int, msg_text: str, processed_messages: set, processed_urls: set) -> None:
    """Обработка нового сообщения из канала."""
    if msg_id in processed_messages:
        log.debug("Сообщение [%s] уже обработано — пропускаем", msg_id)
        return
    processed_messages.add(msg_id)

    log.info("Новое сообщение [%s]: %s", msg_id, msg_text[:120])

    form_url = extract_form_url(msg_text)
    if not form_url:
        log.info("Ссылок на форму нет — пропускаем")
        return

    # Защита от дублирования: Telethon иногда доставляет одно сообщение дважды
    if form_url in processed_urls:
        log.warning("Форма %s уже отправлялась — пропускаем дубль", form_url)
        return
    processed_urls.add(form_url)

    log.info("Форма найдена: %s", form_url)

    # Определяем время слота по метке перед ссылкой
    pattern = r"(1[89]:\d{2}|20:30|21:\d{2})\s*\n\s*(https://docs\.google\.com/forms/[^\s]+)"
    matches = re.findall(pattern, msg_text)
    selected_time = next(
        (t for t, u in matches if u == form_url),
        PREFERRED_TIME
    )
    log.info("Время слота: %s", selected_time)

    result = await submit_form_playwright(form_url, selected_time)

    success = bool(result.get("success"))
    captcha = bool(result.get("captcha"))
    login_required = bool(result.get("login_required"))
    screenshot = result.get("screenshot")

    if NOTIFY_USER_ID:
        if login_required:
            text = (
                "⚠️ Нужна повторная авторизация в Google.\n"
                "Запусти playwright_setup.py, выполни вход и попробуй снова."
            )
        elif captcha:
            text = (
                "⚠️ Google показал капчу при отправке формы.\n"
                "Заполни форму вручную."
            )
        elif success:
            text = f"✅ Записался в спортзал на {selected_time}!\nФорма: {form_url}"
        else:
            text = (
                "❌ Не удалось автоматически отправить форму.\n"
                f"Заполни вручную:\n{form_url}"
            )

        if screenshot and os.path.exists(screenshot):
            await client.send_file(NOTIFY_USER_ID, screenshot, caption=text)
        else:
            await client.send_message(NOTIFY_USER_ID, text)

    if success:
        log.info("Форма отправлена успешно.")
    elif captcha:
        log.warning("Отправка не удалась из-за капчи.")
    elif login_required:
        log.warning("Отправка не удалась из-за просроченной сессии Google.")
    else:
        log.error("Отправка завершилась с ошибкой.")


async def main() -> None:
    log.info("Запуск бота (Playwright версия)...")

    client = TelegramClient(
        "gym_session",
        API_ID,
        API_HASH,
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
        wait = getattr(e, "seconds", None) or getattr(e, "value", 60)
        log.error("FloodWait: подожди %s сек", wait)
        await client.disconnect()
        return

    log.info("Подключились к Telegram!")

    processed_messages: set[int] = set()
    processed_urls: set[str] = set()  # защита от дублей: одна форма — одна отправка

    @client.on(events.NewMessage(chats=CHANNEL_USERNAME))
    async def handler(event) -> None:
        msg_text = event.message.message or ""
        await process_message(client, event.message.id, msg_text, processed_messages, processed_urls)

    log.info("Жду новое сообщение с формами в канале: %s", CHANNEL_USERNAME)
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
