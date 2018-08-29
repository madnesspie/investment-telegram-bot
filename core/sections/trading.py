import pyqrcode
from telegram import Update, Bot, ParseMode, ChatAction
import jsonrpclib

import os
from datetime import datetime as dt, timedelta as td

from core import rates
from components import keyboards, texts
from core import database as db
from core.decorators import log, pass_user, metrica, sql_rollback, handler_log
from settings import config as cfg


# Трейдинг
def get_token_rates(days_to=0):
    """
    Получает из бд данные курсы токена SFI в формате
    {'rub': ..., 'usd': ..., 'btc': ...,}
    :param days_to: отступ в днях от текущего
    :return: данные о курсах
    :rtype: FundHist
    """
    day = dt.now() - td(days=days_to)
    row = db.session.query(db.FundHist).\
        filter_by(day=day.date()).first()
    if not row:
        prev = day - td(days=1)
        row = db.session.query(db.FundHist).\
            filter_by(day=prev.date()).first()

    rates = {
        'rub': row.token_rub,
        'usd': row.token_usd,
        'btc': row.token_btc
    } if row else {}

    return rates


def format_token_data(rates, week_rates):
    """
    Проверяет данные на валидность, если инвалидны - не выводит
    :param rates: курсы токена
    :param week_rates: курсы 7 дней назад
    :return: отформатированный словарь с данные по паре
    :rtype: dict
    """
    calc_percent = lambda x, y: round((x / y - 1) * 100, 2)
    arrow = lambda x: '🌲' if x > 0 else '🔻'
    data = {}

    for currency in ['rub', 'usd', 'btc']:
        if (rates and week_rates and
                rates[currency] > 0 and week_rates[currency] > 0):
            rate = round(rates[currency], cfg.CURRENCY_FMT[currency])
            percent = calc_percent(rates[currency], week_rates[currency])
            data[currency] = f"{rate} {arrow(percent)}{percent}%"
        else:
            data[currency] = f"<i>технические работы</i>"
    return data


def get_token_data(token):
    """
    Получает, форматирует, данные для Трейдинга
    :param token: пока что он тут прост
    :return: данные по валютам для Трейдинга
    :rtype: dict
    """
    rates = get_token_rates()
    week_rates = get_token_rates(7)
    return format_token_data(rates, week_rates)


def get_callback_data(upd):
    data = upd.callback_query.data
    return data


@sql_rollback
@metrica
@handler_log
def token(bot: Bot, update: Update, **kwargs):
    """
    Хендлер кнопки главной клавиатуры "Трейдинг"
    :param bot: telegram bot
    :param update: incoming update
    :param kwargs: others kwargs
    """
    token = 'sredafund:index'  # update.callback_query.data
    output = {
        'token': token,
        **get_token_data(token)
    }
    bot.send_message(
        chat_id=update.message.chat_id, parse_mode=ParseMode.HTML,
        text=texts.trading.format(**output), reply_markup=keyboards.trading('SFI')
    )


@sql_rollback
@handler_log
def back(bot: Bot, update: Update):
    """
    Изменение сообщения от которго пришел апдейт в "Трейдинг"
    :param bot: telegram bot
    :param update: incoming update
    :param kwargs: others kwargs
    """
    token = 'sredafund:index'  # update.callback_query.data
    output = {
        'token': token,
        **get_token_data(token)
    }
    bot.edit_message_text(
        chat_id=update.callback_query.message.chat_id, parse_mode=ParseMode.HTML,
        text=texts.trading.format(**output), reply_markup=keyboards.trading('SFI'),
        message_id=update.callback_query.message.message_id
    )


# График
def fmt_motion(currency, period, today_rate, rate):
    """"""
    eng_works = "<i>технические работы</i>"
    if not (today_rate and rate):
        return eng_works

    arrow = lambda x: '🌲' if x > 0 else '🔻'
    sign = lambda x: '+' + str(x) if x > 0 else x

    profit = round(today_rate - rate, cfg.CURRENCY_FMT[currency])
    percent = round((today_rate / rate - 1) * 100, 2)

    motion = (f"За {period}   {sign(profit)}{currency.upper()}"
              f" ️️ {arrow(profit)}{percent}%")
    return motion


def get_token_motion(period, currency):
    """
    Вычисляет и формирует строку для caption
    :param currency: базовая валюта
    :param period: период подсчета
    :return: строка с доходностью
    :rtype: str
    """
    if period == 'all':
        first_day = dt(2017, 6, 5).date()
        first = db.session.query(db.FundHist).\
            filter_by(day=first_day).first()
        start = {
            'rub': first.token_rub,
            'usd': first.token_usd,
            'btc': first.token_btc
        }
    else:
        start = get_token_rates(days_to=30)
    now = get_token_rates()

    if now and start:
        translate = {
            'all': 'все время',
            'month': 'месяц'
        }
        return fmt_motion(currency, translate[period],
                          now[currency], start[currency])
    else:
        return ''


@sql_rollback
@metrica
@handler_log
def chart(bot: Bot, update: Update):
    """
    График токена SFI
    :param bot: telegram bot
    :param update: incoming update
    :param kwargs: others kwargs
    """
    bot.send_chat_action(
        chat_id=update.callback_query.message.chat_id,
        action=ChatAction.UPLOAD_PHOTO
    )
    if update.callback_query.message.photo:
        bot.delete_message(chat_id=update.callback_query.message.chat_id,
                           message_id=update.callback_query.message.message_id)

    # callback_data example: 'chart_rub_month'
    callback_data = get_callback_data(update).split('_')[1:]
    base, period = callback_data

    img = '_'.join(['chart_sfi', base, period])
    with open(f'static/{img}.png', 'rb') as chart:
        bot.send_photo(chat_id=update.callback_query.message.chat_id,
                       photo=chart, reply_markup=keyboards.chart(base, period),
                       caption=get_token_motion(period, base))


@metrica
@handler_log
def sell_tokens(bot: Bot, update: Update):
    """
    Формирует заявку на продажу токена
    :param bot: telegram bot
    :param update: incoming update
    :param kwargs: others kwargs
    """
    bot.send_message(
        chat_id=update.callback_query.message.chat_id,
        text=texts.trading_sell_token, parse_mode=ParseMode.HTML
    )


def get_personal_address(partner_id, type_):

    partner_addr = db.session.query(db.PartnersAddress).\
        filter_by(partner_id=partner_id, type=type_, testnet=False).first()

    if partner_addr:
        addr = partner_addr.addr
    else:

        server = jsonrpclib.Server(
            "http://sreda:{password}@127.0.0.1:{port}".format(**cfg.RPC[type_]))
        addr = server.getnewaddress()

        entry = db.PartnersAddress(
            partner_id=partner_id,
            type=type_,
            addr=addr,
            testnet=False)
        db.session.add(entry)
        db.commit()

    return addr


@sql_rollback
@metrica
@pass_user
@handler_log
def buy_token(bot: Bot, update: Update, user):
    """
    :param bot: telegram bot
    :param update: incoming update
    :param kwargs: others kwargs
    """
    if not user.partner_id:
        bot.answer_callback_query(
            callback_query_id=update.callback_query.id,
            text='Вам необходимо зарегистрироваться или войти. Нажмите '
                 'на кнопку "Личный кабинет"',
            show_alert=True
        )
        return

    bot.send_message(
        chat_id=update.callback_query.message.chat_id,
        parse_mode=ParseMode.HTML, text=texts.trading_invest,
        message_id=update.callback_query.message.message_id,
        reply_markup=keyboards.trading_invest()
    )


@metrica
@handler_log
def payment_method_btc(bot: Bot, update: Update):
    """
    :param bot: telegram bot
    :param update: incoming update
    :param kwargs: others kwargs
    """
    bot.edit_message_reply_markup(
        chat_id=update.callback_query.message.chat_id,
        message_id=update.callback_query.message.message_id,
        reply_markup=keyboards.trading_invest(btc=True)
    )


@metrica
@handler_log
def payment_method_bch(bot: Bot, update: Update):
    """
    :param bot: telegram bot
    :param update: incoming update
    :param kwargs: others kwargs
    """
    # bot.edit_message_reply_markup(
    #     chat_id=update.callback_query.message.chat_id,
    #     message_id=update.callback_query.message.message_id,
    #     reply_markup=keyboards.trading_invest(xem=True)
    # )
    bot.edit_message_reply_markup(
        chat_id=update.callback_query.message.chat_id,
        message_id=update.callback_query.message.message_id,
        reply_markup=keyboards.trading_invest(bch=True)
    )


@metrica
@handler_log
def payment_method_zec(bot: Bot, update: Update):
    """
    :param bot: telegram bot
    :param update: incoming update
    :param kwargs: others kwargs
    """
    # bot.edit_message_reply_markup(
    #     chat_id=update.callback_query.message.chat_id,
    #     message_id=update.callback_query.message.message_id,
    #     reply_markup=keyboards.trading_invest(xem=True)
    # )
    bot.edit_message_reply_markup(
        chat_id=update.callback_query.message.chat_id,
        message_id=update.callback_query.message.message_id,
        reply_markup=keyboards.trading_invest(zec=True)
    )


def send_qr(bot, chat_id, addr, type_):
    qr_path = 'static/qr-codes/'
    qr_name = f'{chat_id}_{type_}.png'
    if qr_name not in os.listdir(path=qr_path):
        pyqrcode.create(addr).png(qr_path + qr_name, scale=10)

    with open(qr_path + qr_name, 'rb') as qr_code:
        bot.send_photo(
            photo=qr_code, chat_id=chat_id,
            caption=texts.treading_qr_caption.format(currency=type_.upper()))


@sql_rollback
def send_requisites(bot, update_id, user, type_):
    token_price = {
        'btc': rates.get_SFIBTC,
        'bch': rates.get_SFIBCH,
        'zec': rates.get_SFIZEC
    }[type_]()
    addr = get_personal_address(user.partner.id, type_=type_)

    if not (token_price and addr):
        bot.answer_callback_query(
            callback_query_id=update_id,
            text='Эта функция сейчас недоступна', show_alert=True
        )
        return

    output = {
        'rate': token_price,
        'addr': addr,
        'currency': type_.upper()
    }
    bot.send_message(
        chat_id=user.telegram_id, parse_mode=ParseMode.HTML,
        text=texts.treading_buy.format(**output)
    )
    send_qr(bot, user.telegram_id, addr, type_)


@metrica
@pass_user
@handler_log
def pay_btc(bot: Bot, update: Update, user):
    """
    :param bot: telegram bot
    :param update: incoming update
    :param user: instance of the current bot user
    :param kwargs: others kwargs
    """
    send_requisites(bot, update.callback_query.id, user, 'btc')


@metrica
@pass_user
@handler_log
def pay_bch(bot: Bot, update: Update, user):
    """
    :param bot: telegram bot
    :param update: incoming update
    :param user: instance of the current bot user
    :param kwargs: others kwargs
    """
    send_requisites(bot, update.callback_query.id, user, 'bch')


@metrica
@pass_user
@handler_log
def pay_zec(bot: Bot, update: Update, user):
    """
    :param bot: telegram bot
    :param update: incoming update
    :param user: instance of the current bot user
    :param kwargs: others kwargs
        """
    send_requisites(bot, update.callback_query.id, user, 'zec')
