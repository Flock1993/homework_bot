import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)


def send_message(bot, message):
    """Отправка сообщения в Telegram"""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.info(f'Сообщение успешно отправлено в Telegram: {message}')
    except telegram.error.TelegramError as error:
        logging.error('Сообщение не отправлено в Telegram:'
                      f' {message}, ошибка {error}')


def get_api_answer(current_timestamp):
    """Запрос к эндпоинту API-сервиса"""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.exceptions.RequestException:
        message = (
            f'Эндпоинт {ENDPOINT} недоступен'
            f'Код ответа API {response.status_code}'
        )
        logging.error(message)
        raise Exception(message)
    if response.status_code != HTTPStatus.OK:
        message = (
            f'Эндпоинт {ENDPOINT} недоступен'
            f'Код ответа API {response.status_code}'
        )
        logging.error(message)
        raise requests.HTTPError(message)
    return response.json()


def check_response(response):
    """Проверка корректности ответа API"""
    if not isinstance(response, dict):
        message = 'Ответ API не является словарём'
        logging.error(message)
        raise TypeError(message)
    if "homeworks" not in response:
        message = 'В ответе API нет ключа homeworks'
        logging.error(message)
        raise Exception(message)
    if not isinstance(response['homeworks'], list):
        message = 'Значение ключа homeworks не является списком'
        logging.error(message)
        raise TypeError(message)
    else:
        return response['homeworks']


def parse_status(homework):
    """Извлечение статуса домашней работы"""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        message = f'Недокументированный статус ДЗ {homework_status}'
        logging.error(message)
        raise Exception(message)
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности переменных окружения."""
    flag = True
    if PRACTICUM_TOKEN is None:
        logging.critical(
            'Отсутствует обязательная переменная окружения: PRACTICUM_TOKEN')
        flag = False
    if TELEGRAM_TOKEN is None:
        logging.critical(
            'Отсутствует обязательная переменная окружения: TELEGRAM_TOKEN')
        flag = False
    if TELEGRAM_CHAT_ID is None:
        logging.critical(
            'Отсутствует обязательная переменная окружения: TELEGRAM_CHAT_ID')
        flag = False
    return flag


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise Exception('Отсутствуют переменные окружения')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    # current_timestamp = int(time.time())
    current_timestamp = 1652161970
    error_message = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                for homework in homeworks:
                    parse_homework = parse_status(homework)
                    send_message(bot, parse_homework)
            # current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            if error_message != message:
                try:
                    send_message(bot, message)
                    error_message = message
                except Exception as send_error:
                    message_err = f'Сбой в работе программы: {send_error}'
                    logging.error(message_err)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
