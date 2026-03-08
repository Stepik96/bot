"""
Первичная настройка Playwright-сессии для Google Forms.

Сценарий:
- открывает настоящий браузер (headless=False);
- даёт тебе возможность войти в нужный Google-аккаунт;
- сохраняет состояние в playwright_session.json;
- дальше bot.py сможет работать в headless-режиме, используя эту сессию.
"""

import asyncio
import logging
from pathlib import Path

from playwright.async_api import async_playwright

from bot import CHROME_USER_AGENT, PLAYWRIGHT_SESSION_FILE, _ensure_stealth


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("playwright_setup")


async def main() -> None:
    session_path = Path(PLAYWRIGHT_SESSION_FILE)
    log.info("Файл сессии: %s", session_path.resolve())

    async with async_playwright() as p:
        # Открываем видимый браузер, чтобы ты мог залогиниться вручную.
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=CHROME_USER_AGENT,
        )

        page = await context.new_page()
        await _ensure_stealth(page)

        log.info(
            "Открыл браузер. Войди в Google (тот же аккаунт, что использует форму), "
            "затем нажми Enter в терминале."
        )
        await page.goto("https://accounts.google.com/", wait_until="networkidle")

        # Ждём, пока пользователь закончит логин в браузере.
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: input("Когда закончишь вход, нажми Enter здесь...\n")
        )

        # Сохраняем состояние сессии в файл — bot.py будет его подхватывать.
        await context.storage_state(path=str(session_path))
        log.info("Состояние сессии сохранено в %s", session_path.resolve())

        await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())

