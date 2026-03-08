"""
Скрипт для извлечения Google cookies из браузера Chrome/Edge.
Запускай на своём КОМПЬЮТЕРЕ (не на сервере), потом копируй google_cookies.json на сервер.

Установка: pip install browser-cookie3
"""

import json
import sys

def get_cookies_chrome():
    try:
        import browser_cookie3
        cookies = browser_cookie3.chrome(domain_name='.google.com')
        result = []
        for c in cookies:
            result.append({
                'name': c.name,
                'value': c.value,
                'domain': c.domain,
            })
        return result
    except Exception as e:
        print(f"Chrome не сработал: {e}")
        return None

def get_cookies_edge():
    try:
        import browser_cookie3
        cookies = browser_cookie3.edge(domain_name='.google.com')
        result = []
        for c in cookies:
            result.append({
                'name': c.name,
                'value': c.value,
                'domain': c.domain,
            })
        return result
    except Exception as e:
        print(f"Edge не сработал: {e}")
        return None

def get_cookies_firefox():
    try:
        import browser_cookie3
        cookies = browser_cookie3.firefox(domain_name='.google.com')
        result = []
        for c in cookies:
            result.append({
                'name': c.name,
                'value': c.value,
                'domain': c.domain,
            })
        return result
    except Exception as e:
        print(f"Firefox не сработал: {e}")
        return None

if __name__ == '__main__':
    print("Извлекаю Google cookies из браузера...")
    print("ВАЖНО: перед запуском открой Google Forms в браузере и убедись что ты авторизован!\n")

    # Пробуем браузеры по очереди
    cookies = get_cookies_chrome() or get_cookies_edge() or get_cookies_firefox()

    if not cookies:
        print("\n❌ Не удалось извлечь cookies автоматически.")
        print("Используй ручной способ (инструкция в README).")
        sys.exit(1)

    with open('google_cookies.json', 'w') as f:
        json.dump(cookies, f, indent=2)

    print(f"✅ Сохранено {len(cookies)} cookies в google_cookies.json")
    print("\nТеперь скопируй google_cookies.json на сервер:")
    print("  scp google_cookies.json user@your-server:/home/user/gym_bot/")
