"""
Проверка конфигурации перед запуском бота.
Запусти: python validate_config.py
"""

import sys

def check_config():
    errors = []
    warnings = []

    try:
        import config
        API_ID = config.API_ID
        API_HASH = config.API_HASH
        CHANNEL_USERNAME = config.CHANNEL_USERNAME
        FORM_FIELDS = config.FORM_FIELDS
        NOTIFY_USER_ID = config.NOTIFY_USER_ID
        FORM_URL = getattr(config, 'FORM_URL', None)
    except ImportError as e:
        print("[X] Ошибка импорта config.py:", e)
        return False

    # API credentials
    if not isinstance(API_ID, int) or API_ID in (0, 12345678):
        errors.append("API_ID: укажи свой api_id с https://my.telegram.org/apps (число)")

    if not isinstance(API_HASH, str) or API_HASH in ('', 'your_api_hash'):
        errors.append("API_HASH: укажи свой api_hash с https://my.telegram.org/apps")

    # Channel
    if not CHANNEL_USERNAME or CHANNEL_USERNAME == '@your_gym_channel':
        errors.append("CHANNEL_USERNAME: укажи username канала (напр. @gym_channel)")

    # Notify user
    if not NOTIFY_USER_ID or NOTIFY_USER_ID == 123456789:
        warnings.append("NOTIFY_USER_ID: укажи свой Telegram ID (узнай у @userinfobot) для уведомлений")

    # Form fields
    if not FORM_FIELDS or any(k.startswith('entry.111') or k.startswith('entry.222') for k in FORM_FIELDS):
        errors.append(
            "FORM_FIELDS: замени entry.1111111111 и entry.2222222222 на реальные ID.\n"
            "  Запусти: python find_fields.py <ссылка_на_форму>"
        )

    # Form URL (optional - used for find_fields.py)
    if FORM_URL and 'FORM_ID' in str(FORM_URL):
        warnings.append("FORM_URL: заполни для удобства (используется find_fields.py), бот берёт ссылку из канала")

    # Report
    print("=" * 50)
    print("ПРОВЕРКА КОНФИГУРАЦИИ")
    print("=" * 50)

    if errors:
        print("\n[!] ОБЯЗАТЕЛЬНО ИСПРАВИТЬ:")
        for e in errors:
            print(f"  - {e}")
    else:
        print("\n[OK] Обязательные поля заполнены")

    if warnings:
        print("\n[?] РЕКОМЕНДУЕТСЯ:")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("\n[OK] Рекомендуемые поля заполнены")

    print("=" * 50)

    if errors:
        print("\nПосле правок запусти снова: python validate_config.py")
        return False

    print("\n[OK] Конфиг готов! Запускай: python bot.py")
    return True


if __name__ == '__main__':
    ok = check_config()
    sys.exit(0 if ok else 1)
