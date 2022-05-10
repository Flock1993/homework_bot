import os
import logging

from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = '639168619'


def check_tokens():
    """Проверка доступности переменных окружения."""
    if PRACTICUM_TOKEN is None:
        logging.critical(f'Переменная PRACTICUM_TOKEN отсутствует')
        return False
    else:
        return True


print(check_tokens())
print(globals())
print(PRACTICUM_TOKEN)
