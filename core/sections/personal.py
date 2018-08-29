from datetime import datetime as dt
from time import time
import traceback
import logging

from telegram import Update, Bot, ParseMode
from telegram.ext import ConversationHandler
import requests
import jsonrpclib

from core import rates
from core.sections import trading
from core.decorators import log, pass_user, metrica, sql_rollback, handler_log
from components import keyboards, texts
from settings import config as cfg
from core import database as db

EMAIL, PASSWORD = range(2)
AMOUNT, ADDR, OK = range(3)
AMOUNT, QUOTED, ADDRESS, CONFIRMATION = range(4)
BUY_QUOTED, BUY_AMOUNT, BUY_CONFIRMATION = range(3)

logger = logging.getLogger(__name__)

rpc_servers = {
    'btc': jsonrpclib.Server(
        "http://sreda:{password}@127.0.0.1:{port}".format(**cfg.RPC['btc'])),
    'bch': jsonrpclib.Server(
        "http://sreda:{password}@127.0.0.1:{port}".format(**cfg.RPC['bch'])),
    'zec': jsonrpclib.Server(
        "http://sreda:{password}@127.0.0.1:{port}".format(**cfg.RPC['zec']))
}


@sql_rollback
@metrica
@pass_user
@handler_log
def area(bot: Bot, update: Update, user):
    """
    Хендлер кнопки главной клавиатуры "Личный кабинет"
    :param bot: telegram bot
    :param update: incoming update
    :param user: instance of the current bot user
    :param kwargs: others kwargs
    """
    # TODO: Убрать после доапдейта
    # if user.partner:
    #     user.partner_id = user.partner.id
    #     user.ts_update = int(time())
    #     db.commit()

    if not user.partner_id:
        bot.send_message(
            chat_id=user.telegram_id, parse_mode=ParseMode.HTML,
            text=texts.area_please_login,
            reply_markup=keyboards.authorization()
        )
        return
    elif not user.partner.email:
        bot.send_message(
            chat_id=user.telegram_id, parse_mode=ParseMode.HTML,
            text=texts.area_please_confirm_email,
            reply_markup=keyboards.main()
        )
        return

    wallet = get_wallet(user.partner.id, currency='sfi')
    if not wallet:
        wallet = create_token_wallet(user.partner.id, 'sfi')

    token_count = get_wallet_balance(wallet)

    rate = trading.get_token_rates()
    output = {
        # **calc_rigs_profit(user.rigs),
        'sfi': token_count,
        'in_currency': in_currency(token_count, rate),
        'f_name': user.partner.first_name,
        'l_name': user.partner.last_name
    }
    bot.send_message(
        chat_id=user.telegram_id, parse_mode=ParseMode.HTML,
        text=texts.area.format(**output),
        reply_markup=keyboards.personal()
    )


def get_currency(text):
    cmd = text.lstrip('/')
    currency = cmd.split('_')[0]
    return currency


@sql_rollback
@metrica
@pass_user
@handler_log
def deposit(bot: Bot, update: Update, user):
    if not user.partner:
        return

    currency = get_currency(update.message.text)
    wallet = db.session.query(db.PartnersWallet).\
        filter_by(partner_id=user.partner_id, currency=currency).first()

    if wallet:
        bot.send_message(
            chat_id=update.message.chat_id, parse_mode=ParseMode.HTML,
            text=texts.area_deposit.format(currency=currency.upper())
        )
        bot.send_message(
            chat_id=update.message.chat_id, parse_mode=ParseMode.HTML,
            text=f'<b>{wallet.addr}</b>'
        )
    # TODO: добавить QR


@metrica
@pass_user
@handler_log
def withdrawal(bot: Bot, update: Update, user, user_data):
    if not user.partner:
        return

    currency = get_currency(update.message.text)
    user_data['currency'] = currency

    bot.send_message(
        chat_id=update.message.chat_id,
        text=texts.area_withdrawal.format(currency=currency.upper()),
        reply_markup=keyboards.cancel(reply=True), parse_mode=ParseMode.HTML)

    return AMOUNT


def to_float(text):
    try:
        amount = float(text)
    except ValueError:
        text = text.replace(',', '.')
        return to_float(text)
    else:
        return amount


@log
def get_fee(currency):
    server = rpc_servers.get(currency)

    if currency in ['btc', 'bch']:
        fee = server.estimatesmartfee(2)['feerate']
    elif currency == 'zec':
        fee = 0.0001
    else:
        # WTF ?!
        return 0

    return float(fee)


@metrica
@pass_user
@handler_log
def withdrawal_amount(bot: Bot, update: Update, user, user_data):
    amount = to_float(update.message.text)
    currency = user_data['currency']

    wallet = get_wallet(partner_id=user.partner.id, currency=currency)
    balance = get_wallet_balance(wallet)

    if balance < amount:
        bot.send_message(
            chat_id=update.message.chat_id,
            text=texts.area_insufficient_balance.format(
                currency=currency.upper(),
                amount=amount, balance=balance
            ),
            reply_markup=keyboards.cancel(reply=True),
            parse_mode=ParseMode.HTML
        )
        return AMOUNT

    fee = get_fee(currency)
    user_data['amount'] = amount

    bot.send_message(
        chat_id=update.message.chat_id,
        text=texts.area_amount.format(
            currency=currency.upper(),
            amount=amount - fee,
            fee=fee
        ),
        reply_markup=keyboards.cancel(reply=True),
        parse_mode=ParseMode.HTML
    )
    return ADDR


@metrica
@handler_log
def withdrawal_invalid_amount(bot: Bot, update: Update, user_data):
    bot.send_message(
        chat_id=update.message.chat_id,
        text=texts.area_withdrawal_invalid_amount.format(
            currency=user_data['currency'].upper()),
        reply_markup=keyboards.cancel(reply=True)
    )
    return AMOUNT


@metrica
@handler_log
def token_invalid_amount(bot: Bot, update: Update):
    bot.send_message(
        chat_id=update.message.chat_id,
        text=texts.area_token_invalid_amount,
        reply_markup=keyboards.cancel(reply=True)
    )
    return AMOUNT


@metrica
@handler_log
def buy_token_invalid_amount(bot: Bot, update: Update):
    bot.send_message(
        chat_id=update.message.chat_id,
        text=texts.area_token_invalid_amount,
        reply_markup=keyboards.cancel(reply=True)
    )
    return BUY_AMOUNT


@log
def validate_address(addr, currency):
    server = rpc_servers.get(currency)
    result = server.validateaddress(addr)
    return result.get("isvalid", False)


@metrica
@handler_log
def withdrawal_addr(bot: Bot, update: Update, user_data):
    addr = update.message.text

    if not validate_address(addr, user_data['currency']):
        bot.send_message(
            chat_id=update.message.chat_id,
            text=texts.area_invalid_addr.format(
                currency=user_data['currency'].upper()),
            reply_markup=keyboards.cancel(reply=True))

        return ADDR

    user_data['addr'] = addr

    fee = get_fee(user_data['currency'])

    bot.send_message(
        chat_id=update.message.chat_id,
        text=texts.area_addr.format(
            currency=user_data['currency'].upper(),
            amount=user_data['amount'] - fee, addr=addr,
            fee=fee),
        reply_markup=keyboards.confirmation(),
        parse_mode=ParseMode.HTML)

    return OK


def send_to_admin(bot, text):
    for admin in cfg.ADMINS:
        bot.send_message(
            chat_id=admin, text=text, parse_mode=ParseMode.HTML)


@log
def add_wallet_event(partner_id, wallet_id, amount,
                     status='done', source_name='gateway', source_id=None):
    event = db.WalletsEvent(
        partner_id=partner_id,
        wallet_id=wallet_id,
        amount=amount,
        status=status,
        source_name=source_name,
        source_id=source_id,
        ts_add=int(time())
    )
    db.session.add(event)
    db.commit()

    return event


@log
def add_gateway_event(currency, amount, address,
                      event_name='out', txid=None, confirmed=None):
    event = db.GatewayEvents(
        currency=currency,
        event_name=event_name,
        amount=amount,
        address=address,
        txid=txid,
        confirmed=confirmed,
        ts_add=int(time())
    )
    db.session.add(event)
    db.commit()

    return event


@metrica
@pass_user
@handler_log
def withdrawal_confirmation(bot: Bot, update: Update, user, user_data):
    currency = user_data['currency']
    amount = user_data['amount']
    address = user_data['addr']

    server = rpc_servers.get(currency)

    wallet = get_wallet(partner_id=user.partner.id, currency=currency)
    wallet_balance = get_wallet_balance(wallet)
    blockchain_balance = server.getbalance()

    if blockchain_balance < amount:
        # Нам недостаточно средств на ноде, сообщение об этом
        # придет админу, а эвент запишется в gateway_events,
        # без id транзакции и подтверждения.
        bot.send_message(
            chat_id=update.message.chat_id,
            text=texts.area_withdrawal_error,
            reply_markup=keyboards.main(),
            parse_mode=ParseMode.HTML
        )

        gateway_event = add_gateway_event(
            currency=currency, amount=amount, address=address)

        add_wallet_event(
            partner_id=user.partner.id, wallet_id=wallet.id,
            amount=-amount, source_id=gateway_event.id, status='moderation')

        error_msg = texts.area_withdrawal_error_admin.format(
            id=user.partner.id, amount=amount, currency=currency.upper(),
            balance=blockchain_balance, event_id=gateway_event.id, addr=address
        )
        send_to_admin(bot, error_msg)
        user_data.clear()

        return ConversationHandler.END

    if wallet_balance < amount:
        bot.send_message(
            chat_id=update.message.chat_id,
            text=texts.area_insufficient_balance.format(
                currency=currency.upper(),
                amount=amount, balance=wallet_balance
            ),
            reply_markup=keyboards.cancel(reply=True),
            parse_mode=ParseMode.HTML
        )
        return AMOUNT

    txid = server.sendtoaddress(
        address, amount, "bot withdrawal", "", True)

    logger.debug(f"txid: {txid}")
    txinfo = server.gettransaction(txid)
    logger.debug(f"txinfo: {txinfo}")

    gateway_event = add_gateway_event(
        currency=currency, amount=amount, address=address,
        txid=txid, confirmed=True)

    add_wallet_event(
        partner_id=user.partner.id, wallet_id=wallet.id,
        amount=-amount, source_id=gateway_event.id)

    text = texts.area_withdrawal_info.format(
        id=txid, currency=currency.upper(),
        amount=abs(txinfo['amount']), fee=abs(txinfo['fee'])
    )

    user_data.clear()
    bot.send_message(
        chat_id=update.message.chat_id,
        text=text, reply_markup=keyboards.main(),
        parse_mode=ParseMode.HTML
    )
    return ConversationHandler.END


@metrica
@handler_log
def withdrawal_invalid_addr(bot: Bot, update: Update, user_data):
    bot.send_message(
        chat_id=update.message.chat_id,
        text=texts.area_invalid_addr.format(
            currency=user_data['currency'].upper()),
        reply_markup=keyboards.cancel(reply=True))

    return ADDR


@handler_log
def login(bot: Bot, update: Update):
    bot.send_message(
        chat_id=update.message.chat_id, parse_mode=ParseMode.HTML,
        text=texts.area_request_email,
        reply_markup=keyboards.cancel(reply=True)
    )
    return EMAIL


@handler_log
def registration(bot: Bot, update: Update):
    bot.send_message(
        chat_id=update.message.chat_id, parse_mode=ParseMode.HTML,
        text=texts.area_request_email,
        reply_markup=keyboards.cancel(reply=True)
    )
    return EMAIL


@handler_log
def login_email(bot: Bot, update: Update, user_data):
    email = user_data['email'] = update.message.text

    partner = db.session.query(db.Partners).filter_by(
        email=email).first()

    if not partner:
        bot.send_message(
            chat_id=update.message.chat_id, parse_mode=ParseMode.HTML,
            text=texts.area_email_doesnt_exist.format(email=email),
            reply_markup=keyboards.authorization()
        )
        user_data.clear()
        return ConversationHandler.END
    else:
        bot.send_message(
            chat_id=update.message.chat_id, parse_mode=ParseMode.HTML,
            text=texts.area_request_password,
            reply_markup=keyboards.restore_password()
        )
        return PASSWORD


@handler_log
def registration_email(bot: Bot, update: Update, user_data):
    email = user_data['email'] = update.message.text

    partner = db.session.query(db.Partners).filter_by(
        email=email).first()

    if partner:
        bot.send_message(
            chat_id=update.message.chat_id, parse_mode=ParseMode.HTML,
            text=texts.area_email_already_exists.format(email=email),
            reply_markup=keyboards.authorization(registration=False)
        )
        user_data.clear()
        return ConversationHandler.END
    else:
        # TODO: Delete this after updating all accounts
        # TODO: Then delete 'telegram_id' from table 'partners'
        # Check out old account created by bot
        partner = db.session.query(db.Partners).filter_by(
            telegram_id=update.effective_user.id).first()
        if partner:
            if not partner.email and not partner.password:
                user_data['based_on'] = partner.id
                logger.debug("An old account was found. "
                             "Additional registration.")

        bot.send_message(
            chat_id=update.message.chat_id, parse_mode=ParseMode.HTML,
            text=texts.area_request_password,
            reply_markup=keyboards.cancel(reply=True)
        )
        return PASSWORD


@handler_log
def invalid_email(bot: Bot, update: Update):
    bot.send_message(
        chat_id=update.message.chat_id, parse_mode=ParseMode.HTML,
        text=texts.area_invalid_email,
        reply_markup=keyboards.cancel(reply=True)
    )
    return EMAIL


@pass_user
@handler_log
def login_password(bot: Bot, update: Update, user, user_data):
    password = update.message.text
    email = user_data['email']

    partner = db.session.query(db.Partners).filter_by(
        email=email, password=password).first()

    if not partner:
        bot.send_message(
            chat_id=update.message.chat_id, parse_mode=ParseMode.HTML,
            text=texts.area_unsuitable_password,
            reply_markup=keyboards.cancel(reply=True)
        )
        return PASSWORD
    else:
        user.partner_id = partner.id
        user.ts_update = int(time())
        db.commit()

        bot.send_message(
            chat_id=update.message.chat_id, parse_mode=ParseMode.HTML,
            text=texts.area_success_login,
            reply_markup=keyboards.main()
        )
        user_data.clear()
        return ConversationHandler.END


@pass_user
@handler_log
def registration_password(bot: Bot, update: Update, user, user_data):
    user_data['password'] = update.message.text
    user_data['referrer'] = user.referrer_id

    response = requests.post(
        "http://localhost:6000/v1/user/signup",
        data=user_data
    ).json()

    output = {
        'email': user_data['email']
    }
    user_data.clear()

    if response['success']:
        logger.debug(f"Api registration response: {response}")

        user.partner_id = response['data']['id']
        user.ts_update = int(time())
        db.commit()

        bot.send_message(
            chat_id=update.message.chat_id, parse_mode=ParseMode.HTML,
            text=texts.area_success_registration.format(**output),
            reply_markup=keyboards.main()
        )
    else:
        logger.warning(f'Invalid response: {response}')
        bot.send_message(
            chat_id=update.message.chat_id, parse_mode=ParseMode.HTML,
            text=texts.area_email_already_exists.format(**output),
            reply_markup=keyboards.authorization(registration=False)
        )

    return ConversationHandler.END


@handler_log
def invalid_password(bot: Bot, update: Update):
    bot.send_message(
        chat_id=update.message.chat_id, parse_mode=ParseMode.HTML,
        text=texts.area_invalid_password,
        reply_markup=keyboards.cancel(reply=True)
    )
    return PASSWORD


@log
def format_events(events):
    in_token, out_token = [], []
    for event in events:
        lst = in_token if event.event_param > 0 else out_token
        lst.append(
            f"{event.day}  {event.event_param} SFI"
        )

    if not out_token:
        out_token.append("<i>Нет выводов средств</i>")

    fmt_events = {
        'in_token': '\n'.join(in_token),
        'out_token': '\n'.join(out_token)}

    return fmt_events


@sql_rollback
@metrica
@pass_user
@handler_log
def wallet_history(bot: Bot, update: Update, user):
    """
    Хендлер кнопки инлайн-клавиатуры "История" в личном кабинете
    :param bot: telegram bot
    :param update: incoming update
    :param user: instance of the current bot user
    """
    partners_events = db.session.query(db.PartnerEvents).\
        filter_by(partner_id=user.partner.id).all()

    if partners_events:
        output = {**format_events(partners_events)}
        bot.edit_message_text(
            chat_id=user.telegram_id, parse_mode=ParseMode.HTML,
            message_id=update.callback_query.message.message_id,
            text=texts.area_hist.format(**output),
            reply_markup=keyboards.back('personal')
        )
    else:
        bot.answer_callback_query(
            callback_query_id=update.callback_query.id,
            text='Вы еще не совершили ни одного пополнения',
            show_alert=True
        )


@sql_rollback
@pass_user
@handler_log
def back(bot: Bot, update: Update, user):
    """
    Инлайн-кнопка для возврата в личный кабинет
    :param bot: telegram bot
    :param update: incoming update
    :param user: instance of the current bot user
    """
    token_count = user.partner.token_count
    rate = trading.get_token_rates()
    output = {
        # **calc_rigs_profit(user.rigs),
        'sfi': token_count,
        'in_currency': in_currency(token_count, rate),
        'f_name': user.partner.first_name,
        'l_name': user.partner.last_name
    }
    bot.edit_message_text(
        chat_id=update.callback_query.message.chat_id,
        parse_mode=ParseMode.HTML, text=texts.area.format(**output),
        message_id=update.callback_query.message.message_id,
        reply_markup=keyboards.personal()
    )


# Мониторинг
@metrica
@handler_log
def monitoring(bot: Bot, update: Update):
    """
    Хендлер инлайн-кнопки "мониторинг" в личном кабинете
    :param bot: telegram bot
    :param update: incoming update
    """
    bot.answer_callback_query(
        callback_query_id=update.callback_query.id,
        text='Технические работы, приносим свои извенения за неудобства. '
             'Дата-центр переходит на EthOS',
        show_alert=True
    )


def get_wallet_balance(wallet):
    balance = .0
    for event in wallet.events:
        balance += event.amount
    return balance


def format_wallets(wallets):
    wallets_data = []
    tokens_data = []

    template = (
        "<pre>{currency}</pre>"
        "{token}"
        "Баланс: {balance}\n"
        "Примерно: {rates}\n"
        "{cmds}"
    )
    tokens = {
        'sfi': '<i>sredafund:index</i>\n',
        # 'sft': '<i>sredafund:trade</i>\n'
        # TODO: add new token
    }

    for wallet in wallets:

        if wallet.autopay:
            continue

        currency = wallet.currency
        balance = get_wallet_balance(wallet)

        if currency in tokens:
            cmds = f"/{currency}_buy  /{currency}_sell"

            # TODO Здесь нужно добавить фиатные курсы для SFT
            token_rates = trading.get_token_rates()
            rates_tmp = f"{token_rates['usd'] * balance:.0f}$ или " \
                        f"{token_rates['rub'] * balance:.0f}₽"

            tokens_data.append(template.format(
                currency=currency.upper(),
                token=tokens[currency],
                cmds=cmds,
                rates=rates_tmp,
                balance=balance))

            tokens.pop(currency)
            logger.debug(f"remove token: {currency}, dct: {tokens}")

        elif currency in ['zec', 'btc', 'bch']:

            usd_rates = {
                'btc': rates.get_BTCUSD(),
                'bch': rates.get_BCHUSD(),
                'zec': rates.get_ZECUSD()
            }.get(currency)

            cmds = f"/{currency}_deposit  /{currency}_withdrawal"
            wallets_data.append(template.format(
                currency=currency.upper(),
                token="",
                cmds=cmds,
                rates=f"{usd_rates * balance:.0f}$",
                balance=balance))

    for token, full_name in tokens.items():
        cmds = f"/{token}_buy  /{token}_sell"
        tokens_data.append(template.format(
            currency=token.upper(),
            token=full_name,
            cmds=cmds,
            # TODO: add rates
            rub_balance=1,
            usd_balance=1,
            balance=.0))

    if wallets_data:
        wallets_output = '\n\n'.join(wallets_data)
    else:
        wallets_output = texts.area_wallets_doesnt_exist

    output = {
        'tokens': '\n\n'.join(tokens_data),
        'wallet': wallets_output
    }

    return output


@sql_rollback
@metrica
@pass_user
@handler_log
def wallet(bot: Bot, update: Update, user):
    """
    """
    wallets = user.partner.wallets
    # logger.debug(f'walletdebug: {user.partner.addresses}')
    output = {
        **format_wallets(wallets)
    }
    bot.edit_message_text(
        chat_id=user.telegram_id, parse_mode=ParseMode.HTML,
        message_id=update.callback_query.message.message_id,
        text=texts.area_wallet.format(**output),
        reply_markup=keyboards.wallet()
    )


def get_available(wallets):
    available = ['btc', 'bch', 'zec']
    for wallet in wallets:
        if wallet.currency in ['sfi', 'sft'] or wallet.autopay:
            continue
        available.remove(wallet.currency)
    return available


@sql_rollback
@metrica
@pass_user
@handler_log
def wallet_autopay(bot: Bot, update: Update, user):
    tokens = ['sfi']  # , 'sft'] TODO: add new token
    currencies = ['zec', 'btc', 'bch']

    buttons = [(currency, token)
               for currency in currencies
               for token in tokens]

    bot.edit_message_text(
        chat_id=user.telegram_id, parse_mode=ParseMode.HTML,
        message_id=update.callback_query.message.message_id,
        text=texts.area_wallet_autopay,
        reply_markup=keyboards.autopay(buttons)
    )


@log
def get_wallet(partner_id, currency, autopay=None):
    wallet = db.session.query(db.PartnersWallet).\
        filter_by(
            partner_id=partner_id, currency=currency, autopay=autopay
        ).first()
    return wallet


@sql_rollback
@metrica
@pass_user
@handler_log
def wallet_autopay_addr(bot: Bot, update: Update, user):
    callback_data = update.callback_query.data
    src, dst = callback_data.split('_')[-2:]

    wallet = get_wallet(partner_id=user.partner.id, currency=src, autopay=dst)
    if not wallet:
        wallet = create_wallet(
            partner_id=user.partner.id, currency=src, autopay=dst)

    bot.send_message(
        chat_id=user.telegram_id, parse_mode=ParseMode.HTML,
        text=texts.area_wallet_autopay_addr.format(currency=src.upper())
    )
    bot.send_message(
        chat_id=user.telegram_id, parse_mode=ParseMode.HTML,
        text=f"<b>{wallet.addr}</b>"
    )


@sql_rollback
@metrica
@pass_user
@handler_log
def wallet_add(bot: Bot, update: Update, user):
    """
    """
    wallets = user.partner.wallets
    available = get_available(wallets)

    if not available:
        bot.answer_callback_query(
            callback_query_id=update.callback_query.id,
            text='Все доступные валюты уже добавленны!'
        )
        return

    bot.edit_message_text(
        chat_id=user.telegram_id, parse_mode=ParseMode.HTML,
        message_id=update.callback_query.message.message_id,
        reply_markup=keyboards.wallet_add(available),
        text=texts.area_wallet_add
    )


@log
def create_wallet(partner_id, currency, autopay=None):
    server = jsonrpclib.Server(
        "http://sreda:{password}@127.0.0.1:{port}".format(**cfg.RPC[currency]))
    addr = server.getnewaddress()

    wallet = db.PartnersWallet(
        partner_id=partner_id,
        currency=currency,
        addr=addr,
        autopay=autopay,
        ts_add=int(time())
    )
    logger.info(f'Create new {currency}-address for partner {partner_id}: '
                f'{addr}. Autopay = {autopay}.')

    db.session.add(wallet)
    db.commit()

    return wallet


@log
def create_token_wallet(partner_id, currency):
    wallet = db.PartnersWallet(
        partner_id=partner_id,
        currency=currency,
        ts_add=int(time())
    )
    db.session.add(wallet)
    db.commit()

    return wallet


@sql_rollback
@metrica
@pass_user
@handler_log
def wallet_make(bot: Bot, update: Update, user):
    callback_data = update.callback_query.data
    currency = callback_data.split("_")[-1]

    create_wallet(user.partner.id, currency)
    bot.answer_callback_query(
        callback_query_id=update.callback_query.id,
        text=f'Новый {currency}-адрес добавлен в кошелек.'
    )

    wallets = user.partner.wallets
    available = get_available(wallets)

    if available:
        text = texts.area_wallet_add
    else:
        text = texts.area_wallet_all_added

    bot.edit_message_text(
        chat_id=user.telegram_id, parse_mode=ParseMode.HTML,
        message_id=update.callback_query.message.message_id,
        reply_markup=keyboards.wallet_add(available), text=text
    )


def to_dt(ts):
    return str(dt.fromtimestamp(ts))


@log
def format_events(wallets):
    pending = []
    done = []

    for wallet in wallets:
        for event in wallet.events:

            lst = done if event.status == 'done' else pending
            lst.append(
                f"<i>{to_dt(event.ts_add)}</i>    {event.amount}"
                f"<b>{wallet.currency.upper()}</b>")

    output = {
        'pending': '\n'.join(pending) if len(pending) else '<i>Пусто</i>',
        'done': '\n'.join(done) if len(done) else '<i>Пусто</i>'
    }
    return output


@sql_rollback
@metrica
@pass_user
@handler_log
def wallet_history(bot: Bot, update: Update, user):
    """
    """
    wallets = user.partner.wallets
    output = format_events(wallets)

    bot.edit_message_text(
        chat_id=user.telegram_id, parse_mode=ParseMode.HTML,
        message_id=update.callback_query.message.message_id,
        reply_markup=keyboards.back('personal_wallet'),
        text=texts.area_wallet_history.format(**output)
    )


@sql_rollback
@metrica
@pass_user
@handler_log
def wallet_invoice(bot: Bot, update: Update, user):
    """
    """
    pass


@sql_rollback
@metrica
@pass_user
@handler_log
def buy_token(bot: Bot, update: Update, user, user_data):
    if not user.partner:
        return

    base = get_currency(update.message.text)
    user_data['base'] = base

    bot.send_message(
        chat_id=user.telegram_id, parse_mode=ParseMode.HTML,
        text=texts.area_token_buy.format(token=base.upper()),
        reply_markup=keyboards.token_quoted()
    )
    return BUY_QUOTED


@sql_rollback
@metrica
@pass_user
@handler_log
def buy_token_quoted(bot: Bot, update: Update, user, user_data):
    quoted = update.message.text.lower()
    base = user_data['base']

    user_data['quoted'] = quoted
    rate = get_rate(base, quoted)

    bot.send_message(
        chat_id=user.telegram_id, parse_mode=ParseMode.HTML,
        text=texts.area_token_buy_quoted.format(
            base=base.upper(), quoted=quoted.upper(),
            rate=rate),
        reply_markup=keyboards.cancel(reply=True)
    )
    return BUY_AMOUNT


@sql_rollback
@metrica
@pass_user
@handler_log
def buy_token_amount(bot: Bot, update: Update, user, user_data):
    amount = to_float(update.message.text)
    base = user_data['base']
    quoted = user_data['quoted']

    wallet = get_wallet(partner_id=user.partner.id, currency=base)
    balance = get_wallet_balance(wallet)

    if balance < amount:
        bot.send_message(
            chat_id=update.message.chat_id,
            text=texts.area_insufficient_balance.format(
                currency=quoted.upper(),
                amount=amount, balance=balance
            ),
            reply_markup=keyboards.cancel(reply=True),
            parse_mode=ParseMode.HTML
        )
        return BUY_AMOUNT

    user_data['amount'] = amount
    rate = get_rate(base, quoted)

    if not rate:
        bot.send_message(
            chat_id=update.message.chat_id,
            text=texts.area_maintenance,
            reply_markup=keyboards.main(),
            parse_mode=ParseMode.HTML)

        user_data.clear()
        return ConversationHandler.END

    amount_received = round(amount / rate, 8)
    fee = round(amount_received * 0.05, 8)
    amount_received *= 0.95

    bot.send_message(
        chat_id=update.message.chat_id,
        text=texts.area_token_buy_amount.format(
            base=base.upper(), quoted=quoted.upper(), fee=fee,
            amount=amount, amount_received=amount_received, rate=rate
        ),
        reply_markup=keyboards.confirmation(),
        parse_mode=ParseMode.HTML
    )
    return BUY_CONFIRMATION


@sql_rollback
@metrica
@pass_user
@handler_log
def buy_token_confirmation(bot: Bot, update: Update, user, user_data):
    amount = user_data['amount']
    base = user_data['base']
    quoted = user_data['quoted']

    wallet = get_wallet(partner_id=user.partner.id, currency=quoted)
    balance = get_wallet_balance(wallet)

    if balance < amount:
        bot.send_message(
            chat_id=update.message.chat_id,
            text=texts.area_insufficient_balance.format(
                currency=quoted.upper(),
                amount=amount, balance=balance
            ),
            reply_markup=keyboards.cancel(reply=True),
            parse_mode=ParseMode.HTML
        )
        return BUY_AMOUNT

    rate = get_rate(base, quoted)
    if not rate:
        bot.send_message(
            chat_id=update.message.chat_id,
            text=texts.area_maintenance,
            reply_markup=keyboards.main(),
            parse_mode=ParseMode.HTML)

        user_data.clear()
        return ConversationHandler.END

    amount_received = round(amount / rate, 8)
    fee = round(amount_received * 0.05, 8)
    amount_received *= 0.95

    exchange_event = add_exchange_event(
        partner_id=user.partner.id,
        src=quoted, dst=base,
        amount=amount, status='pending')

    # fee
    add_wallet_event(
        partner_id=32, wallet_id=1,
        amount=fee, status='done',
        source_name='exchange', source_id=exchange_event.id)

    add_wallet_event(
        partner_id=user.partner.id, wallet_id=wallet.id,
        amount=-amount, status='done', source_name='exchange',
        source_id=exchange_event.id)

    bot.send_message(
        chat_id=update.message.chat_id,
        text=texts.area_token_buy_confirmation.format(
            base=base.upper(), quoted=quoted.upper(), fee=fee,
            amount=amount, amount_received=amount_received, rate=rate
        ),
        reply_markup=keyboards.main(),
        parse_mode=ParseMode.HTML
    )
    user_data.clear()
    return ConversationHandler.END


@sql_rollback
@metrica
@pass_user
@handler_log
def sell_token(bot: Bot, update: Update, user, user_data):
    if not user.partner:
        return

    base = get_currency(update.message.text)
    user_data['base'] = base

    bot.send_message(
        chat_id=user.telegram_id, parse_mode=ParseMode.HTML,
        text=texts.area_sell_token.format(currency=base.upper()),
        reply_markup=keyboards.cancel(reply=True)
    )
    return AMOUNT


@sql_rollback
@metrica
@pass_user
@handler_log
def sell_token_amount(bot: Bot, update: Update, user, user_data):
    amount = to_float(update.message.text)
    base = user_data['base']

    wallet = get_wallet(partner_id=user.partner.id, currency=base)
    balance = get_wallet_balance(wallet)

    if balance < amount:
        bot.send_message(
            chat_id=update.message.chat_id,
            text=texts.area_insufficient_balance.format(
                currency=base.upper(),
                amount=amount, balance=balance
            ),
            reply_markup=keyboards.cancel(reply=True),
            parse_mode=ParseMode.HTML
        )
        return AMOUNT

    user_data['amount'] = amount

    bot.send_message(
        chat_id=update.message.chat_id,
        text=texts.area_sell_token_amount.format(
            currency=base.upper(),
            amount=amount
        ),
        reply_markup=keyboards.token_quoted(),
        parse_mode=ParseMode.HTML
    )
    return QUOTED


@log
def get_rate(base, quoted):
    def return1():
        return 1

    rate = {
        'sfi': {
            'btc': rates.get_SFIBTC,
            'bch': rates.get_SFIBCH,
            'zec': rates.get_SFIZEC,
        },
        'sft': {
            'btc': return1,
            'bch': return1,
            'zec': return1
        }
    }[base][quoted]()
    # TODO: add new token rates
    return round(rate, 8)


@sql_rollback
@metrica
@handler_log
def sell_token_quoted(bot: Bot, update: Update, user_data):
    quoted = update.message.text.lower()
    base, amount = user_data['base'], user_data['amount']

    user_data['quoted'] = quoted

    rate = get_rate(base, quoted)
    if not rate:
        bot.send_message(
            chat_id=update.message.chat_id,
            text=texts.area_maintenance,
            reply_markup=keyboards.main(),
            parse_mode=ParseMode.HTML)

        user_data.clear()
        return ConversationHandler.END

    amount_received = round(amount / rate, 8)
    logger.debug(f"usr_dt: {user_data}, rate: {rate}, "
                 f"amount_r: {amount_received}")

    bot.send_message(
        chat_id=update.message.chat_id,
        text=texts.area_sell_token_quoted.format(
            base=base.upper(), quoted=quoted.upper(),
            amount=amount, rate=rate,
            amount_received=amount_received
        ),
        reply_markup=keyboards.sell_token_address(),
        parse_mode=ParseMode.HTML
    )
    return ADDRESS


@sql_rollback
@metrica
@handler_log
def sell_token_invalid_quoted(bot: Bot, update: Update):
    bot.send_message(
        chat_id=update.message.chat_id,
        text=texts.area_invalid_sell_quoted.format(
            currency=update.message.text),
        reply_markup=keyboards.token_quoted(),
        parse_mode=ParseMode.HTML
    )
    return QUOTED


@sql_rollback
@metrica
@handler_log
def buy_token_invalid_quoted(bot: Bot, update: Update):
    bot.send_message(
        chat_id=update.message.chat_id,
        text=texts.area_invalid_buy_quoted.format(
            currency=update.message.text),
        reply_markup=keyboards.token_quoted(),
        parse_mode=ParseMode.HTML
    )
    return BUY_QUOTED


@sql_rollback
@metrica
@pass_user
@handler_log
def sell_token_address(bot: Bot, update: Update, user, user_data):
    addr = update.message.text
    quoted = user_data['quoted']
    base = user_data['base']
    amount = user_data['amount']

    rate = get_rate(base, quoted)
    amount_received = round(amount / rate, 8)

    if '💰  На кошелек в боте' == addr:
        wallet = db.session.query(db.PartnersWallet).filter_by(
            partner_id=user.partner.id, currency=quoted,
            autopay=None
        ).first()
        if not wallet:
            wallet = create_wallet(
                partner_id=user.partner.id, currency=quoted,
                autopay=base)
        addr = wallet.addr

    user_data['addr'] = addr
    fee = 0  # TODO: добавить вычисление комиссии

    bot.send_message(
        chat_id=update.message.chat_id,
        text=texts.area_sell_token_address.format(
            base=base.upper(), quoted=quoted.upper(),
            amount=amount, rate=rate, address=addr,
            amount_received=amount_received, fee=fee
        ),
        reply_markup=keyboards.confirmation(),
        parse_mode=ParseMode.HTML
    )
    return CONFIRMATION


@sql_rollback
@metrica
@handler_log
def sell_token_invalid_address(bot: Bot, update: Update, user_data):
    bot.send_message(
        chat_id=update.message.chat_id,
        text=texts.area_invalid_sell_address.format(
            currency=user_data['quoted'].upper()
        ),
        reply_markup=keyboards.sell_token_address(),
        parse_mode=ParseMode.HTML
    )
    return ADDRESS


@log
def add_exchange_event(partner_id, src, dst, amount, status):
    event = db.ExchangeEvents(
        partner_id=partner_id,
        src=src,
        dst=dst,
        amount=amount,
        status=status,
        ts_add=int(time())
    )
    db.session.add(event)
    db.commit()

    return event


@sql_rollback
@metrica
@pass_user
@handler_log
def sell_token_confirmation(bot: Bot, update: Update, user, user_data):
    addr = user_data['addr']
    quoted = user_data['quoted']
    base = user_data['base']
    amount = user_data['amount']

    rate = get_rate(base, quoted)
    wallet = get_wallet(user.partner.id, base)
    amount_received = round(amount / rate, 8)

    fee = 0 # TODO: добавить вычисление комиссии

    exchange_event = add_exchange_event(
        partner_id=user.partner.id,
        src=base,
        dst=quoted,
        amount=amount,
        status='done')

    # fee
    add_wallet_event(
        partner_id=32, wallet_id=1,
        amount=fee, status='done',
        source_name='exchange', source_id=exchange_event.id)

    add_wallet_event(
        partner_id=user.partner.id, wallet_id=wallet.id,
        amount=-amount, status='done',
        source_name='exchange', source_id=exchange_event.id)

    ticket = db.WithdrawalTicket(
        partner_id=user.partner.id,
        src=base,
        dst=quoted,
        src_count=amount,
        dst_count=amount_received,
        rate=rate,
        address=addr,
        status='pending',
        ts_create=int(time()),
        ts_update=int(time())
    )
    db.session.add(ticket)
    db.commit()

    bot.send_message(
        chat_id=update.message.chat_id,
        text=texts.area_sell_token_confirmation.format(
            amount=amount, base=base.upper(), quoted=quoted.upper(),
            amount_received=amount_received, address=addr, rate=rate,
            fee=fee
        ),
        reply_markup=keyboards.main(),
        parse_mode=ParseMode.HTML
    )

    user_data.clear()
    return ConversationHandler.END


@sql_rollback
@metrica
@pass_user
@handler_log
def settings(bot: Bot, update: Update, user):
    """
    Здесь выводим доступные для редактирования данные о партнере,
    Настройку кошелька
    """
    output = {}
    bot.edit_message_text(
        chat_id=user.telegram_id, parse_mode=ParseMode.HTML,
        message_id=update.callback_query.message.message_id,
        text=''.format(**output),
        reply_markup=keyboards.back('personal')
    )


@sql_rollback
@metrica
@pass_user
@handler_log
def portfolio(bot: Bot, update: Update, user):
    """
    """
    pass


@sql_rollback
@metrica
@pass_user
@handler_log
def logout(bot: Bot, update: Update, user):
    """
    """
    user.partner_id = None
    db.commit()

    bot.edit_message_text(
        chat_id=user.telegram_id, parse_mode=ParseMode.HTML,
        message_id=update.callback_query.message.message_id,
        text='Вы вышли из аккаунта!'
    )


# Баунти
@sql_rollback
@metrica
@pass_user
@handler_log
def referral(bot: Bot, update: Update, user):
    """
    Хендлер инлайн-кнопки "Реферальная программа" в личном кабинете
    :param bot: telegram bot
    :param update: incoming update
    :param user: instance of the current bot user
    """
    output = {
        'ref_code': user.partner.id,
        'bot_name': cfg.BOT}
    bot.edit_message_text(
        chat_id=user.telegram_id, parse_mode=ParseMode.HTML,
        message_id=update.callback_query.message.message_id,
        text=texts.area_bounty.format(**output),
        reply_markup=keyboards.back('personal')
    )


# Доходность портфеля в личном кабинете !!! Нужно лучше продумать !!!
def in_currency(token_count, rates):
    """


    :param token_count: количество токенов пользователя
    :return: баланс токена в валюте
    :rtype: str
    """
    blcs = {}
    fmt = ('<code>{btc}</code>BTC / '
           '<code>{usd}</code>USD / <code>{rub}</code>RUB')
    try:
        if not (token_count and rates):
            raise KeyError
        for currency in rates:
            blcs[currency] = round(rates[currency] * token_count,
                                   cfg.CURRENCY_FMT[currency])
    except (KeyError, TypeError):
        error = '<i>недоступно</i>'
        return error
    else:
        return fmt.format(**blcs)
