import sys
import logging

from settings import config as cfg
from core.manager import Manager

logger = logging.getLogger('bot')

if __name__ == '__main__':
    # DEBUG = True if '-debug' in sys.argv else False

    manager = Manager(token=cfg.API_TOKEN)

    if cfg.DEBUG:
        logging.info("SetUp Polling")
        manager.start_polling()
    else:
        logging.info("SetUp Webhook")
        manager.start_webhook(cfg.WEBHOOK)
