import logging
import os
import sys
import time
from http import HTTPStatus
import settings

from typing import Optional
import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN: Optional[str] = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN: Optional[str] = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID: Optional[str] = os.getenv('TELEGRAM_CHAT_ID')

HEADERS: dict = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)


def send_message(bot: telegram.bot.Bot, message: str) -> None:
    """Отправка сообщения в Telegram."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.info(f'Сообщение успешно отправлено в Telegram: {message}')
    except telegram.error.TelegramError as error:
        logging.error('Сообщение не отправлено в Telegram:'
                      f' {message}, ошибка {error}')


def get_api_answer(current_timestamp: int) -> dict:
    """Запрос к эндпоинту API-сервиса."""
    timestamp: int = current_timestamp or int(time.time())
    params: dict = {'from_date': timestamp}
    try:
        response: requests.Response = requests.get(
            settings.ENDPOINT, headers=HEADERS, params=params)
    except requests.exceptions.RequestException:
        message = (
            f'Эндпоинт {settings.ENDPOINT} недоступен'
            f'Код ответа API {response.status_code}'
        )
        logging.error(message)
        raise Exception(message)
    if response.status_code != HTTPStatus.OK:
        message = (
            f'Эндпоинт {settings.ENDPOINT} недоступен'
            f'Код ответа API {response.status_code}'
        )
        logging.error(message)
        raise requests.HTTPError(message)
    return response.json()


def check_response(response: dict) -> list:
    """Проверка корректности ответа API."""
    if not isinstance(response, dict):
        message = 'Ответ API не является словарём'
        logging.error(message)
        raise TypeError(message)
    if 'homeworks' not in response:
        message = 'В ответе API нет ключа homeworks'
        logging.error(message)
        raise KeyError(message)
    if not isinstance(response['homeworks'], list):
        message = 'Значение ключа homeworks не является списком'
        logging.error(message)
        raise TypeError(message)
    return response['homeworks']


def parse_status(homework: dict) -> str:
    """Извлечение статуса домашней работы."""
    if 'homework_name' not in homework:
        message = 'В словаре homework нет ключа "homework_name"'
        logging.error(message)
        raise KeyError(message)
    homework_name: str = homework['homework_name']
    if 'status' not in homework:
        message = 'В словаре homework нет ключа "status"'
        logging.error(message)
        raise KeyError(message)
    homework_status: str = homework['status']
    if homework_status not in settings.HOMEWORK_STATUSES:
        message = f'Недокументированный статус ДЗ {homework_status}'
        logging.error(message)
        raise Exception(message)
    verdict: str = settings.HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Проверка доступности переменных окружения."""
    token_list = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    if not all(token_list):
        for token in token_list:
            if token is None:
                logging.critical(
                    f'Отсутствует обязательная переменная окружения: {token}')
        return False
    return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        log_message = 'Отсутствуют переменные окружения'
        logging.critical(log_message)
        raise Exception(log_message)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    error_message = ''
    while True:
        try:
            response: dict = get_api_answer(current_timestamp)
            homeworks: list = check_response(response)
            if homeworks:
                for homework in homeworks:
                    parse_homework: str = parse_status(homework)
                    send_message(bot, parse_homework)
            time.sleep(settings.RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            if error_message != message:
                send_message(bot, message)
                error_message: str = message
        finally:
            time.sleep(settings.RETRY_TIME)


if __name__ == '__main__':
    main()
