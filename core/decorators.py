import logging
from functools import wraps
from time import time

from telegram import Bot, Update

from plugins import botan
from settings.config import ADMINS, DEBUG
from core import database as db

from sqlalchemy.exc import StatementError, InvalidRequestError, OperationalError


def create_db_user(tg_user, referrer_id=None):
    db_user = db.TelegramUsers(
        ts_add = int(time()),
        ts_update = int(time()),
        telegram_id=tg_user.id,
        referrer_id=referrer_id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name)

    db.session.add(db_user)
    db.commit()

    return db_user


def get_db_user(tg_user, logger):
    db_user = db.session.query(db.TelegramUsers).\
        filter_by(telegram_id=tg_user.id).first()

    if db_user:
        if (db_user.username != tg_user.username or
                db_user.first_name != tg_user.first_name or
                db_user.last_name != tg_user.last_name):

            db_user.ts_update = int(time())
            db_user.username = tg_user.username
            db_user.first_name = tg_user.first_name
            db_user.last_name = tg_user.last_name

            db.commit()

            logger.info(f"User updated: {db_user}")
    else:
        db_user = create_db_user(tg_user)
        logger.info(f"New user added: {db_user}")

    return db_user


def admin_access(func):
    @wraps(func)
    def wrapped(bot: Bot, update: Update, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in ADMINS:
            return

        return func(bot, update, *args, **kwargs)
    return wrapped


def pass_user(func):
    logger = logging.getLogger(func.__module__)

    @wraps(func)
    def wrapped(bot: Bot, update: Update, *args, **kwargs):
        tg_user = update.effective_user
        db_user = get_db_user(tg_user, logger)
        return func(bot, update, db_user, *args, **kwargs)
    return wrapped

#
# def pass_partner(func):
#
#     @wraps(func)
#     def wrapped(bot: Bot, update: Update, *args, **kwargs):
#         tg_user = update.effective_user
#         partner = db.session.query(db.Partners).\
#             filter_by(telegram_id=tg_user.id).first()
#         return func(bot, update, partner, *args, **kwargs)
#     return wrapped


def metrica(func):
    # TODO: это почему-то глючит. Надо разобраться
    @wraps(func)
    def wrapped(bot: Bot, update: Update, *args, **kwargs):
        # if not DEBUG:
        #     message = update.effective_message
        #     botan.track(message.chat_id, message.to_dict(),
        #                 name=func.__name__)

        return func(bot, update, *args, **kwargs)
    return wrapped


def sql_rollback(func):
    logger = logging.getLogger(func.__module__)

    @wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (StatementError, InvalidRequestError, OperationalError):
            db.session.rollback()
            logger.warning(f"Rollback!")
            return func(*args, **kwargs)
        finally:
            db.session.rollback()

    return wrapped


def handler_log(func):
    logger = logging.getLogger(func.__module__)

    @wraps(func)
    def wrapper(bot: Bot, update: Update, *args, **kwargs):
        tg_user = update.effective_user
        logger.debug(
            f"Called::{func.__name__}. By user "
            f"{'@' + tg_user.username if tg_user.username else tg_user.id}.")
        return func(bot, update, *args, **kwargs)
    return wrapper


def log(func):
    logger = logging.getLogger(func.__module__)

    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)

        if result is None:
            logger.debug(f"Called::{func.__name__}.")
        else:
            logger.debug(f"Called::{func.__name__}. Returned {result}")
        return result
    return wrapper
