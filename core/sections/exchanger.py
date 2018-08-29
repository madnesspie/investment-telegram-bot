from telegram import Update, Bot, ParseMode

from core.decorators import handler_log, metrica
from components import texts


@metrica
@handler_log
def beta(bot: Bot, update: Update, **kwargs):
    bot.send_message(
        chat_id=update.message.chat_id, parse_mode=ParseMode.HTML,
        text=texts.exchanger_beta
    )
