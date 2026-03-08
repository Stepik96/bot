"""
Шаг 1 — Одноразовая авторизация через Google OAuth2.
Запускай ОДИН РАЗ на своём компьютере.
После успешного запуска создаётся token.json — его не нужно обновлять вручную,
бот сам обновляет access_token через refresh_token.

Установка зависимостей:
    pip install google-auth google-auth-oauthlib google-auth-httplib2

Перед запуском:
    1. Зайди на https://console.cloud.google.com
    2. Создай проект (или выбери существующий)
    3. APIs & Services → OAuth consent screen → External → заполни (название любое)
    4. APIs & Services → Credentials → Create Credentials → OAuth client ID
    5. Application type: Desktop app
    6. Скачай JSON → сохрани как credentials.json рядом с этим скриптом
    7. Запусти: python oauth2_setup.py
"""

import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import os

# Scope для доступа к Google Forms (отправка от имени пользователя)
SCOPES = [
    'https://www.googleapis.com/auth/forms.responses.readonly',
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]

TOKEN_FILE = 'token.json'
CREDENTIALS_FILE = 'credentials.json'


def setup_oauth():
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Обновляю токен...")
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                print(f"❌ Файл {CREDENTIALS_FILE} не найден!")
                print("Скачай его из Google Cloud Console:")
                print("  APIs & Services → Credentials → OAuth 2.0 Client IDs → Download JSON")
                print(f"  Сохрани как {CREDENTIALS_FILE} рядом с этим скриптом")
                return

            print("Открываю браузер для авторизации в Google...")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
        print(f"✅ Токен сохранён в {TOKEN_FILE}")

    print(f"\n✅ Авторизация успешна!")
    print(f"   Access token получен")
    print(f"   Refresh token: {'есть' if creds.refresh_token else 'НЕТ (проблема!)'}")
    print(f"\nТеперь скопируй token.json и credentials.json рядом с bot.py")
    print("И замени bot.py на новую версию из oauth2_bot.py")


if __name__ == '__main__':
    setup_oauth()
