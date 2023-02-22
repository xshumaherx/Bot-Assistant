import logging
import os
import time

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
        if response.status_code != 200:
            message = 'Ошибка запроса к API'
            logging.error(message)
            raise Exception(message)
        return response.json()
    except requests.RequestException('Неполадки') as error:
        logging.error(error)


def check_response(response):
    """Проверяет ответ API на соответствие документации"""
    if type(response) is not dict:
        message = 'Данные приходят не в виде словаря'
        logging.error(message)
        raise TypeError(message)
    if type(response.get('homeworks')) is not list:
        message = ('В ответе API домашки под ключом `homeworks`\n'
                   'данные приходят не в виде списка')
        logging.error(message)
        raise TypeError(message)
    if str('homeworks') not in response:
        message = 'В ответе API домашки нет ключа'
        logging.error(message)
        raise KeyError(message)
    return response.get('homeworks')


def parse_status(homework):
    """Извлекает из информации о конкретной
        домашней работе статус этой работы"""
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
    else:
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат,
    определяемый переменной окружения TELEGRAM_CHAT_ID."""
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
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
