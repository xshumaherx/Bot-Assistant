import json
import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO)


def check_tokens():
    """Проверяет доступность переменных окружения."""
    item_list = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    return all(item_list)


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp},
        )
    except requests.exceptions.Timeout as errTime:
        message = 'Время запроса истекла'
        logger.error(message, errTime)
        raise TimeoutError(message)
    except requests.exceptions.ConnectionError as errCon:
        message = 'Ошибка подключения'
        logger.error(message, errCon)
        raise ConnectionError(message)
    except Exception as error:
        message = 'Ошибка'
        logger.error(message, error)
        raise SystemExit(error)
    if response.status_code != HTTPStatus.OK:
        message = 'Ошибка запроса к API'
        logger.error(message)
        raise Exception(message)
    try:
        return response.json()
    except json.decoder.JSONDecodeError:
        logger.error("Это не JSON")


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if type(response) is not dict:
        message = 'Данные приходят не в виде словаря'
        logging.error(message)
        raise TypeError(message)
    if type(response.get('homeworks')) is not list:
        message = ('В ответе API домашки под ключом `homeworks`\n'
                   'данные приходят не в виде списка')
        logging.error(message)
        raise TypeError(message)
    if 'homeworks' not in response:
        message = 'В ответе API домашки нет ключа'
        logging.error(message)
        raise KeyError(message)
    return response.get('homeworks')


def parse_status(homework):
    """Извлекает из информации статус этой работы."""
    if 'status' not in homework:
        raise KeyError('В ответе API нет ключа "status"')
    else:
        homework_status = homework['status']
    if 'homework_name' not in homework:
        raise KeyError('В ответе API нет ключа "homework_name"')
    else:
        homework_name = homework['homework_name']
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if homework_status not in HOMEWORK_VERDICTS:
        message = 'Проект еще не открыли.'
        logging.error(message)
        raise KeyError(message)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(
            TELEGRAM_CHAT_ID,
            message,
        )
        logging.debug(f'Бот отправил сообщение {message}')
    except Exception as error:
        logging.error(f'Ошибка при отправки сообщения в Telegram: {error}')


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            if check_tokens():
                response = get_api_answer(timestamp)
                homeworks = check_response(response)
                if homeworks:
                    send_message(bot, parse_status(homeworks[0]))
            else:
                logging.critical(
                    'Отсутствует обязательная переменная окружения\n')
                break
        except Exception as error:
            logging.error(f'Сбой в работе программы: {error}')
            break
        timestamp = int(time.time())
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
