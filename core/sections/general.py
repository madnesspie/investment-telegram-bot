import os
import logging
import subprocess
from time import time

from telegram import Update, Bot, ParseMode
from telegram.error import (TelegramError, Unauthorized, BadRequest,
                            TimedOut, ChatMigrated, NetworkError)
from sqlalchemy.exc import (StatementError, InvalidRequestError,
                            OperationalError)
from telegram.ext import ConversationHandler

from components import texts
from components import keyboards
from core.decorators import (log, admin_access, pass_user, handler_log,
                             create_db_user)
from settings.config import ADMINS
from core import database as db

logger = logging.getLogger(__name__)


def check_link(text):
    if text != '/start':
        try:
            referrer_id = int(text.split()[1])
        except (TypeError, IndexError):
            return
        else:
            referrer = db.session.query(db.Partners).\
                filter_by(id=referrer_id).first()

            if referrer:
                return referrer_id
            else:
                logger.warning(
                    f'invalid referral link. '
                    f'Partner with {referrer_id} does not exist')


@handler_log
def start(bot: Bot, update: Update):
    tg_user = update.effective_user
    user = db.session.query(db.TelegramUsers).\
        filter_by(telegram_id=tg_user.id).first()

    if not user:
        referrer_id = check_link(update.message.text)
        user = create_db_user(tg_user, referrer_id)

    bot.send_message(
        chat_id=user.telegram_id, parse_mode=ParseMode.HTML,
        text=texts.welcome.format(user.first_name),
        reply_markup=keyboards.main()
    )


@handler_log
def menu(bot: Bot, update: Update):
    bot.send_message(
        chat_id=update.effective_user.id, parse_mode=ParseMode.HTML,
        text="<b>Главное меню</b>", reply_markup=keyboards.main()
    )


@admin_access
@pass_user
@handler_log
def test(bot: Bot, update: Update, user, **kwargs):
    lol = bot.get_updates()
    out = '\n\n'.join(map(str, lol))
    bot.send_message(202628185, out if out else 'empty')


def author(bot: Bot, update: Update):
    bot.send_message(
        chat_id=update.message.chat_id, parse_mode=ParseMode.HTML,
        text=texts.author, reply_markup=keyboards.main()
    )


@admin_access
@handler_log
def restart(bot: Bot, update: Update, **kwargs):
    bot.send_message(
        update.message.chat_id, parse_mode=ParseMode.HTML,
        text=f"<i>Процесс {os.getpid()} убит. Перезагрузка...</i>",
        reply_markup=keyboards.main()
    )
    subprocess.call(['kill', str(os.getpid())])


@log
def error(bot: Bot, update: Update, error, **kwargs):
    try:
        raise error
    except (Unauthorized, BadRequest, NetworkError):
        for admin_id in ADMINS:
            bot.send_message(admin_id, 'Ошибка:\n' + str(error))
    finally:
        logger.warning(f"Update {update} caused error {error}")


@handler_log
def cancel(bot: Bot, update: Update, user_data):
    user_data.clear()
    bot.send_message(
        chat_id=update.message.chat_id, parse_mode=ParseMode.HTML,
        text='<b>Главное меню</b>', reply_markup=keyboards.main())
    return ConversationHandler.END
