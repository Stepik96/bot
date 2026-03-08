"""
Вспомогательный скрипт для нахождения ID полей Google Form
Запусти его чтобы автоматически получить entry.XXXXXXXXX для каждого поля
"""

import re
import sys

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Устанавливаю зависимости...")
    import subprocess
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'requests', 'beautifulsoup4'])
    import requests
    from bs4 import BeautifulSoup


def get_form_fields(form_url: str):
    """Парсит форму и возвращает все поля с их entry ID"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    print(f"\n🔍 Загружаю форму: {form_url}\n")
    response = requests.get(form_url, headers=headers)

    if response.status_code != 200:
        print(f"❌ Ошибка загрузки формы: {response.status_code}")
        return

    # Ищем entry ID через регулярные выражения
    entry_ids = re.findall(r'entry\.(\d+)', response.text)
    entry_ids = list(dict.fromkeys(entry_ids))  # убираем дубли, сохраняем порядок

    # Пробуем найти названия полей через BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')

    # Google Forms хранит данные в JS — ищем паттерн с названиями полей
    fb_pattern = re.findall(r'\["([^"]+)",[^\]]*,(\d+),', response.text)

    print("=" * 50)
    print("📋 НАЙДЕННЫЕ ПОЛЯ ФОРМЫ")
    print("=" * 50)

    if fb_pattern:
        for name, eid in fb_pattern:
            if len(name) > 1 and not name.startswith('http'):
                print(f"  Поле: '{name}'")
                print(f"  entry ID: entry.{eid}")
                print(f"  В config.py: 'entry.{eid}': 'ТВОЁ_ЗНАЧЕНИЕ',")
                print()
    elif entry_ids:
        print("Нашёл entry ID (без названий полей):")
        for eid in entry_ids:
            print(f"  entry.{eid}")
        print("\nНазвания полей не удалось определить автоматически.")
        print("Используй метод с DevTools (F12) описанный в README.")
    else:
        print("❌ Не удалось найти поля. Возможно форма требует авторизации.")
        print("Используй метод с DevTools (F12) описанный в README.")

    print("=" * 50)
    print("\n✅ Скопируй нужные entry.ID в config.py")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        form_url = input("Введи ссылку на Google Form: ").strip()
    else:
        form_url = sys.argv[1]

    get_form_fields(form_url)
