from telegram import Update, Bot, ParseMode
from telegram.ext import ConversationHandler
from telegram.error import Unauthorized

import logging
import traceback

from components import texts, keyboards
from core import database as db
from core.decorators import admin_access, pass_user, log, handler_log

logger = logging.getLogger(__name__)
TEXT, SEND = 0, 1


@admin_access
@handler_log
def panel(bot: Bot, update: Update):
    bot.send_message(
        chat_id=update.message.chat_id,
        parse_mode=ParseMode.HTML, text=texts.admin,
        reply_markup=keyboards.admin()
    )


@handler_log
def dispatch(bot: Bot, update: Update):
    bot.edit_message_text(
        chat_id=update.callback_query.message.chat_id,
        parse_mode=ParseMode.HTML, text=texts.admin_dispatch,
        message_id=update.callback_query.message.message_id,
        reply_markup=keyboards.back('admin')
    )
    return TEXT


@handler_log
def dispatch_text(bot: Bot, update: Update, user_data):
    user_data['dispatch'] = update.message.text
    user_data['preview_id'] = bot.send_message(
        chat_id=update.message.chat_id, parse_mode=ParseMode.MARKDOWN,
        text=texts.admin_dispatch_preview.format(user_data['dispatch']),
        reply_markup=keyboards.admin_dispatch()
    ).message_id
    logger.debug(f'dispatch_text: {user_data}')
    return SEND


@handler_log
def edit_dispatch_text(bot: Bot, update: Update, user_data):
    logger.debug(f'edit_dispatch_text: {user_data}\n{update.edited_message}')
    msg = bot.edit_message_text(
        chat_id=update.edited_message.chat_id,
        message_id=user_data['preview_id'], parse_mode=ParseMode.MARKDOWN,
        text=texts.admin_dispatch_preview.format(user_data['dispatch']),
        reply_markup=keyboards.admin_dispatch()
    )
    logger.debug(f'edit_dispatch_text: {msg}')
    return SEND


@handler_log
def dispatch_send(bot: Bot, update: Update, user_data):
    partners_id = db.session.query(db.Partners.telegram_id).\
        filter(db.Partners.telegram_id.isnot(None)).all()

    for partner_id in partners_id:
        # TODO: Проверить как работает и допилить искл.
        try:
            bot.send_message(
                chat_id=partner_id, text=user_data['dispatch'],
                parse_mode=ParseMode.MARKDOWN)
        except Unauthorized:
            logger.warning(f"Unauthorized user: id={partner_id}")
        except:
            logger.warning(f"dispatch - {traceback.format_exc()}")

    logger.info(f'Admin: {update.callback_query.message.chat_id} '
                f'send notification')
    user_data.clear()

    return ConversationHandler.END


@handler_log
def back(bot: Bot, update: Update):
    bot.edit_message_text(
        chat_id=update.callback_query.message.chat_id,
        parse_mode=ParseMode.HTML, text=texts.admin,
        message_id=update.callback_query.message.message_id,
        reply_markup=keyboards.admin())
    return ConversationHandler.END
