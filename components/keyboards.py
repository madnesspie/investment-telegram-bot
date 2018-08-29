from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup,
                      InlineKeyboardButton, KeyboardButton)


def main():
    keyboard = [['💳  Обменник', '📈  Трейдинг'],
                ['❓  О крипто-фонде'],
                ['👨🏻‍💻  Личный кабинет']]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def authorization(login=True, registration=True):
    top_line = []

    if login:
        top_line.append('🔑  Вход')
    if registration:
        top_line.append('📝  Регистрация')

    keyboard = [top_line, ['⌨️  Главное меню']]

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def confirmation():
    keyboard = [
        [KeyboardButton(text='➡️  Отправить')],
        [KeyboardButton(text='🚫  Отмена')]
    ]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    return markup


def restore_password():
    keyboard = [
        [InlineKeyboardButton(
            "↩️  Восстановить пароль",
            url='https://my.sreda.fund/site/restore')]
    ]
    return InlineKeyboardMarkup(keyboard)


def token_quoted():
    keyboard = [
        [KeyboardButton(text='BTC')],
        [KeyboardButton(text='BCH')],
        [KeyboardButton(text='ZEC')],
        [KeyboardButton(text='🚫  Отмена')]
    ]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    return markup


def sell_token_address():
    keyboard = [
        [KeyboardButton(text='💰  На кошелек в боте')],
        [KeyboardButton(text='🚫  Отмена')]
    ]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    return markup


def personal():
    keyboard = [
        [InlineKeyboardButton(
            "💰  Кошелек", callback_data='personal_wallet'),
         InlineKeyboardButton(
            "🔐  Выйти", callback_data='personal_logout')],

        [InlineKeyboardButton(
            "🍫  Реферальная программа", callback_data='personal_referral')],

        [InlineKeyboardButton(
            "🌐  Личный кабинет на сайте", url='https://my.sreda.fund/')]
    ]
    return InlineKeyboardMarkup(keyboard)


def wallet():
    keyboard = [
        [InlineKeyboardButton(
            "♻️  Автоплатеж", callback_data='personal_wallet_autopay')],

        [InlineKeyboardButton(
            '➕  Добавить', callback_data='personal_wallet_add'),
         InlineKeyboardButton(
            "📃  История", callback_data='personal_wallet_history')],

        [InlineKeyboardButton(
            '⬅️  Назад', callback_data='personal_back')]
    ]
    return InlineKeyboardMarkup(keyboard)


def autopay(buttons):
    keyboard = [
        [
            InlineKeyboardButton(
                f'{currency.upper()} -> {token.upper()}',
                callback_data=f'personal_wallet_autopay_{currency}_{token}')
        ] for currency, token in buttons
    ]
    return InlineKeyboardMarkup(keyboard)


def wallet_add(available):
    keyboard = []
    keyboard.append(
        [InlineKeyboardButton(
            currency.upper(),
            callback_data=f'personal_wallet_make_{currency}'
        ) for currency in available]
    )
    keyboard.append(
        [InlineKeyboardButton(
            '⬅️  Назад', callback_data='personal_wallet_back')]
    )
    return InlineKeyboardMarkup(keyboard)


def about():
    keyboard = [
        [InlineKeyboardButton("🚀  О Боте", callback_data='about_bot'),
         InlineKeyboardButton("⚙️  Разработка", callback_data='about_dev')],

        [InlineKeyboardButton("👨🏻‍🏫  КриптоСреда", callback_data='about_meetup')],
    ]
    return InlineKeyboardMarkup(keyboard)


def trading(token):
    keyboard = [
        [InlineKeyboardButton(text=f"📈  График {token}", callback_data='chart_usd_all')]
    ]
    return InlineKeyboardMarkup(keyboard)


def chart(base, period):
    enable, disable = '🔘', '⚪️'
    state = {
        'rub': enable if base == 'rub' else disable,
        'usd': enable if base == 'usd' else disable,
        'btc': enable if base == 'btc' else disable,

        'month': enable if period == 'month' else disable,
        'all': enable if period == 'all' else disable
    }

    keyboard = [
        [InlineKeyboardButton(text=state['rub'] + ' SFI/RUB',
                              callback_data=f'chart_rub_{period}'),
         InlineKeyboardButton(text=state['usd'] + ' SFI/USD',
                              callback_data=f'chart_usd_{period}'),
         InlineKeyboardButton(text=state['btc'] + ' SFI/BTC',
                              callback_data=f'chart_btc_{period}')],

        [InlineKeyboardButton(text=state['month'] + ' Месяц',
                              callback_data=f'chart_{base}_month'),
         InlineKeyboardButton(text=state['all'] + ' Все',
                              callback_data=f'chart_{base}_all')]
    ]
    return InlineKeyboardMarkup(keyboard)


def mining():
    keyboard = [
        [InlineKeyboardButton(text="🛒  Купить ферму", callback_data='mining_buy'),
         InlineKeyboardButton(text="🗳  Разместить ферму", callback_data='mining_place')],

        [InlineKeyboardButton(text="💡  Мониторинг", callback_data='mining_monitoring')]
    ]
    return InlineKeyboardMarkup(keyboard)


def admin():
    keyboard = [
        [InlineKeyboardButton(text="✉️  Рассылка", callback_data='admin_dispatch')]
    ]
    return InlineKeyboardMarkup(keyboard)


def admin_dispatch():
    keyboard = [
        [InlineKeyboardButton(text='📩 Отправить', callback_data='admin_dispatch_send'),
         InlineKeyboardButton(text='🚫 Отмена', callback_data='admin_cancel')]
    ]
    return InlineKeyboardMarkup(keyboard)


def trading_invest(btc=False, bch=False, zec=False):
    enable, disable = '🔘', '⚪️'
    keyboard = [
        [InlineKeyboardButton(text=(enable if btc else disable) + ' BTC',
                              callback_data='btc_payment'),
         InlineKeyboardButton(text=(enable if bch else disable) + ' BCH',
                              callback_data='bch_payment'),
         InlineKeyboardButton(text=(enable if zec else disable) + ' ZEC',
                              callback_data='zec_payment')]
    ]
    if btc:
        keyboard.append([InlineKeyboardButton(text="💳  Оплатить",
                                              callback_data='buy_token_btc')])
    elif bch:
        keyboard.append([InlineKeyboardButton(text="💳  Оплатить",
                                              callback_data='buy_token_bch')])
    elif zec:
        keyboard.append([InlineKeyboardButton(text="💳  Оплатить",
                                              callback_data='buy_token_zec')])

    return InlineKeyboardMarkup(keyboard)


def back(type_):
    back_button = InlineKeyboardButton(
        text='⬅️  Назад', callback_data=type_ + '_back')
    return InlineKeyboardMarkup([[back_button]])


def cancel(reply=False):
    if reply:
        keyboard = [[KeyboardButton(text='🚫  Отмена')]]
        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    else:
        keyboard = [[InlineKeyboardButton(text='🚫  Отмена', callback_data='cancel')]]
        markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True)
    return markup


def remove():
    return ReplyKeyboardRemove()
