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
        API_ID            = config.API_ID
        API_HASH          = config.API_HASH
        CHANNEL_USERNAME  = config.CHANNEL_USERNAME
        NOTIFY_USER_ID    = config.NOTIFY_USER_ID
        PREFERRED_TIME    = config.PREFERRED_TIME
        PERSONAL_DATA     = config.PERSONAL_DATA
        FORM_ENTRIES      = config.FORM_ENTRIES
    except ImportError as e:
        print("[X] Ошибка импорта config.py:", e)
        return False
    except AttributeError as e:
        print("[X] В config.py отсутствует переменная:", e)
        print("    Убедись что используешь актуальный config.py")
        return False

    # --- API credentials ---
    if not isinstance(API_ID, int) or API_ID == 0:
        errors.append("API_ID: должен быть числом с https://my.telegram.org/apps")

    if not isinstance(API_HASH, str) or len(API_HASH) < 10:
        errors.append("API_HASH: укажи свой api_hash с https://my.telegram.org/apps")

    # --- Канал ---
    if not CHANNEL_USERNAME:
        errors.append("CHANNEL_USERNAME: укажи username канала (например: NVKGYM)")

    # --- Уведомления ---
    if not NOTIFY_USER_ID or NOTIFY_USER_ID == 123456789:
        warnings.append("NOTIFY_USER_ID: укажи свой Telegram ID (узнай у @userinfobot)")

    # --- Время ---
    valid_times = ['18:00', '19:15', '20:30']
    if PREFERRED_TIME not in valid_times:
        errors.append(f"PREFERRED_TIME: должно быть одним из {valid_times}, сейчас: '{PREFERRED_TIME}'")

    # --- Личные данные ---
    required_keys = ['name', 'group', 'telegram', 'email']
    for key in required_keys:
        if key not in PERSONAL_DATA or not PERSONAL_DATA[key]:
            errors.append(f"PERSONAL_DATA['{key}']: поле не заполнено")

    # --- Entry ID ---
    entry_keys = ['entry_fio', 'entry_group', 'entry_telegram']
    for time_slot in valid_times:
        if time_slot not in FORM_ENTRIES:
            errors.append(f"FORM_ENTRIES: отсутствует слот '{time_slot}'")
            continue
        for key in entry_keys:
            val = FORM_ENTRIES[time_slot].get(key, '')
            if not val or 'XXXXXXX' in val:
                errors.append(f"FORM_ENTRIES['{time_slot}']['{key}']: не заполнен реальный entry.ID")

    # --- Отчёт ---
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

    # --- Итог по личным данным и entry.ID ---
    print("\n--- Текущие настройки ---")
    print(f"  Канал:          {CHANNEL_USERNAME}")
    print(f"  Время записи:   {PREFERRED_TIME}")
    print(f"  ФИО:            {PERSONAL_DATA.get('name', '?')}")
    print(f"  Группа:         {PERSONAL_DATA.get('group', '?')}")
    print(f"  Telegram:       {PERSONAL_DATA.get('telegram', '?')}")
    print(f"  Email:          {PERSONAL_DATA.get('email', '?')}")
    print()
    for slot in valid_times:
        if slot in FORM_ENTRIES:
            e = FORM_ENTRIES[slot]
            print(f"  {slot}: fio={e.get('entry_fio','?')}  group={e.get('entry_group','?')}  tg={e.get('entry_telegram','?')}")

    print("=" * 50)

    if errors:
        print("\nПосле правок запусти снова: python validate_config.py")
        return False

    print("\n[OK] Конфиг готов! Запускай: python bot.py")
    return True


if __name__ == '__main__':
    ok = check_config()
    sys.exit(0 if ok else 1)
