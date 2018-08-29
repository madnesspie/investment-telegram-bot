import requests

import logging

API = 'https://api.telegram.org/bot'
TOKEN = '533035104:AAFbwljq76fLd8gbOLJfan16DZIqSr7j8Zw'
GROUP_ID = -286567703

DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR


def send_log(text):
    requests.post(
        url=API + TOKEN + '/sendMessage',
        data={
            'chat_id': GROUP_ID,
            'text': f"<code>{text}</code>",
            'parse_mode': 'HTML'
        }
    )


def set_up_logging(level):
    logging.basicConfig(
        format='%(asctime)s ~ %(levelname)-10s %(name)-25s %(message)s',
        datefmt='%Y-%m-%d %H:%M', level=level, filename='bot.log')

    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('JobQueue').setLevel(logging.WARNING)
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('jsonrpclib').setLevel(logging.WARNING)

    logging.addLevelName(DEBUG, '🐛 DEBUG')
    logging.addLevelName(INFO, '📑 INFO')
    logging.addLevelName(WARNING, '🤔 WARNING')
    logging.addLevelName(ERROR, '🚨 ERROR')
