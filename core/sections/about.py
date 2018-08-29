from telegram import Update, Bot, ParseMode

from core.decorators import handler_log, metrica
from components import texts, keyboards


@metrica
@handler_log
def fund(bot: Bot, update: Update, **kwargs):
    bot.send_message(
        chat_id=update.message.chat_id, parse_mode=ParseMode.HTML,
        text=texts.about_fund, reply_markup=keyboards.about()
    )


@metrica
@handler_log
def bot(bot: Bot, update: Update, **kwargs):
    bot.edit_message_text(
        chat_id=update.callback_query.message.chat_id,
        parse_mode=ParseMode.HTML, text=texts.about_bot,
        message_id=update.callback_query.message.message_id,
        reply_markup=keyboards.back('about')
    )


@metrica
@handler_log
def meetup(bot: Bot, update: Update, **kwargs):
    bot.edit_message_text(
        chat_id=update.callback_query.message.chat_id,
        message_id=update.callback_query.message.message_id,
        parse_mode=ParseMode.HTML, text=texts.about_meetup,
        reply_markup=keyboards.back('about')
    )


@metrica
@handler_log
def development(bot: Bot, update: Update, **kwargs):
    bot.edit_message_text(
        chat_id=update.callback_query.message.chat_id,
        parse_mode=ParseMode.HTML, text=texts.about_development,
        message_id=update.callback_query.message.message_id,
        reply_markup=keyboards.back('about')
    )


@handler_log
def back(bot: Bot, update: Update, **kwargs):
    """
    Инлайн-кнопка для возврата в "О Крипто-Фонде"
    :param bot: telegram bot
    :param update: incoming update
    :param kwargs: others kwargs
    """
    bot.edit_message_text(
        chat_id=update.callback_query.message.chat_id,
        parse_mode=ParseMode.HTML, text=texts.about_fund,
        message_id=update.callback_query.message.message_id,
        reply_markup=keyboards.about()
    )
