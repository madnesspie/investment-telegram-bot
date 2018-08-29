import logging

from telegram.ext import (
    Updater, Filters, CommandHandler, CallbackQueryHandler, MessageHandler,
    RegexHandler, ConversationHandler)

from core.decorators import log
from core.scheduler import Scheduler
from core.sections import (personal, trading, tasks, about,
                           general, exchanger, admin)
from core.filters import (
    FilterEmail, FilterPassword, FilterInvalidValue, FilterCurrencyValue,
    FilterAddr, FilterСonfirmation, FilterQuotedCurrency,
    FilterSellTokenAddress)

TEXT, SEND = range(2)
EMAIL, PASSWORD = range(2)
AMOUNT, ADDR, OK = range(3)
AMOUNT, QUOTED, ADDRESS, CONFIRMATION = range(4)
BUY_QUOTED, BUY_AMOUNT, BUY_CONFIRMATION = range(3)


class Manager(object):

    def __init__(self, token: str):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.token = token
        self.updater = Updater(token)
        self.scheduler = Scheduler(self.updater.job_queue)
        self.dispatcher = self.updater.dispatcher

    @log
    def activate(self):
        self.set_up_commands()
        self.set_up_strings()
        self.set_up_query()
        self.set_up_conversation()

        self.set_up_scheduler()

    def start_polling(self):
        self.activate()

        self.updater.start_polling()
        # Run the bot until the user presses Ctrl-C
        # or the process receives SIGINT,
        # SIGTERM or SIGABRT
        self.updater.idle()

    def start_webhook(self, webhook_setting):
        self.activate()

        self.updater.start_webhook(**webhook_setting)
        self.updater.idle()

    def set_up_scheduler(self):
        self.scheduler.run_repeating(
            tasks.ChartCreator.create_charts,
            interval=3600, first=1)

    def set_up_commands(self):
        callback_cmd = {
            'start': general.start,
            'help': about.fund,
            'admin': admin.panel,
            'test': general.test,
            'restart': general.restart,
            'menu': general.menu,
            'author': general.author,
            ('btc_deposit', 'bch_deposit', 'zec_deposit'):
                personal.deposit,
        }

        for name, callback_func in callback_cmd.items():
            self.dispatcher.add_handler(
                CommandHandler(
                    name, callback_func),
            )
        self.dispatcher.add_error_handler(general.error)

    def set_up_strings(self):
        callback_str = {
            '❓  О крипто-фонде': about.fund,
            '📈  Трейдинг': trading.token,
            '💳  Обменник': exchanger.beta,
            '👨🏻‍💻  Личный кабинет': personal.area,
            '⌨️  Главное меню': general.menu
        }
        for name, callback_func in callback_str.items():
            self.dispatcher.add_handler(
                RegexHandler(f'^{name}$', callback_func))

    def set_up_query(self):
        callback_query = {
            # personal area
            'personal_wallet': personal.wallet,
            'personal_wallet_add': personal.wallet_add,
            'personal_wallet_make_\w+': personal.wallet_make,
            'personal_wallet_history': personal.wallet_history,
            'personal_wallet_autopay': personal.wallet_autopay,
            'personal_wallet_autopay_\w+': personal.wallet_autopay_addr,
            'personal_wallet_invoice': personal.wallet_invoice,
            'personal_wallet_back': personal.wallet,
            'personal_referral': personal.referral,
            'personal_portfolio': personal.portfolio,
            'personal_settings': personal.settings,
            'personal_logout': personal.logout,
            'personal_back': personal.back,
            # 'area_profit': personal.profit,

            # about
            'about_bot': about.bot,
            'about_dev': about.development,
            'about_meetup': about.meetup,
            'about_back': about.back,

            # trading
            'buy_sfi': trading.buy_token,
            'sell_tokens': trading.sell_tokens,
            'chart_\w+': trading.chart,
            'btc_payment': trading.payment_method_btc,
            'bch_payment': trading.payment_method_bch,
            'zec_payment': trading.payment_method_zec,
            'buy_token_btc': trading.pay_btc,
            'buy_token_bch': trading.pay_bch,
            'buy_token_zec': trading.pay_zec,
            'trading_back': trading.back

            # tools & plugins
        }

        for name, callback_func in callback_query.items():
            self.dispatcher.add_handler(
                CallbackQueryHandler(
                    callback_func, pattern=f'^{name}$')
            )

    def set_up_conversation(self):
        # admin dispatch
        self.dispatcher.add_handler(
            # TODO: Здесь не работает "отмена" и эдит
            ConversationHandler(
                entry_points=[
                    CallbackQueryHandler(
                        admin.dispatch, pattern='^admin_dispatch')
                ],
                states={
                    TEXT: [
                        MessageHandler(
                            Filters.text, admin.dispatch_text,
                            pass_user_data=True)
                    ],
                    SEND: [
                        CallbackQueryHandler(
                            admin.dispatch_send, pass_user_data=True,
                            pattern='^admin_dispatch_send')
                    ]
                },
                fallbacks=[
                    MessageHandler(
                        Filters.text, admin.edit_dispatch_text,
                        edited_updates=True, pass_user_data=True),
                    CallbackQueryHandler(
                        admin.back, pattern='^back_admin')
                ]
            )
        )
        # login
        self.dispatcher.add_handler(
            ConversationHandler(
                entry_points=[
                    RegexHandler(
                        f'^🔑  Вход$', personal.login)
                ],
                states={
                    EMAIL: [
                        MessageHandler(
                            FilterEmail(), personal.login_email,
                            pass_user_data=True),
                        MessageHandler(
                            FilterInvalidValue(), personal.invalid_email)
                    ],
                    PASSWORD: [
                        MessageHandler(
                            FilterPassword(), personal.login_password,
                            pass_user_data=True),
                        MessageHandler(
                            FilterInvalidValue(),
                            personal.invalid_password)
                    ]
                },
                fallbacks=[
                    RegexHandler(
                        f'^🚫  Отмена$', general.cancel,
                        pass_user_data=True)
                ]
            )
        )
        # registration
        self.dispatcher.add_handler(
            ConversationHandler(
                entry_points=[
                    RegexHandler(
                        f'^📝  Регистрация$', personal.registration)
                ],
                states={
                    EMAIL: [
                        MessageHandler(
                            FilterEmail(), personal.registration_email,
                            pass_user_data=True),
                        MessageHandler(
                            FilterInvalidValue(), personal.invalid_email)
                    ],
                    PASSWORD: [
                        MessageHandler(
                            FilterPassword(), personal.registration_password,
                            pass_user_data=True),
                        MessageHandler(
                            FilterInvalidValue(),
                            personal.invalid_password)
                    ]
                },
                fallbacks=[
                    RegexHandler(
                        f'^🚫  Отмена$', general.cancel,
                        pass_user_data=True)
                ]
            )
        )
        # withdrawal
        self.dispatcher.add_handler(
            ConversationHandler(
                entry_points=[
                    CommandHandler(
                        ('btc_withdrawal', 'bch_withdrawal', 'zec_withdrawal'),
                        personal.withdrawal, pass_user_data=True)
                ],
                states={
                    AMOUNT: [
                        MessageHandler(
                            FilterCurrencyValue(),
                            personal.withdrawal_amount,
                            pass_user_data=True),
                        MessageHandler(
                            FilterInvalidValue(),
                            personal.withdrawal_invalid_amount,
                            pass_user_data=True),
                    ],
                    ADDR: [
                        MessageHandler(
                            FilterAddr(), personal.withdrawal_addr,
                            pass_user_data=True),
                        MessageHandler(
                            FilterInvalidValue(),
                            personal.withdrawal_invalid_addr,
                            pass_user_data=True)
                    ],
                    OK: [
                        MessageHandler(
                            FilterСonfirmation(),
                            personal.withdrawal_confirmation,
                            pass_user_data=True),
                    ]
                },
                fallbacks=[
                    RegexHandler(
                        f'^🚫  Отмена$', general.cancel,
                        pass_user_data=True)
                ]
            )
        )
        # sell token
        self.dispatcher.add_handler(
            ConversationHandler(
                entry_points=[
                    CommandHandler(
                        ('sfi_sell', 'sft_sell'),
                        personal.sell_token, pass_user_data=True)
                ],
                states={
                    AMOUNT: [
                        MessageHandler(
                            FilterCurrencyValue(),
                            personal.sell_token_amount,
                            pass_user_data=True),
                        MessageHandler(
                            FilterInvalidValue(),
                            personal.token_invalid_amount)
                    ],
                    QUOTED: [
                        MessageHandler(
                            FilterQuotedCurrency(),
                            personal.sell_token_quoted,
                            pass_user_data=True),
                        MessageHandler(
                            FilterInvalidValue(),
                            personal.sell_token_invalid_quoted)
                    ],
                    ADDRESS: [
                        MessageHandler(
                            FilterSellTokenAddress(),
                            personal.sell_token_address,
                            pass_user_data=True),
                        MessageHandler(
                            FilterInvalidValue(),
                            personal.sell_token_invalid_address,
                            pass_user_data=True)
                    ],
                    CONFIRMATION: [
                        MessageHandler(
                            FilterСonfirmation(),
                            personal.sell_token_confirmation,
                            pass_user_data=True),
                    ]
                },
                fallbacks=[
                    RegexHandler(
                        f'^🚫  Отмена$', general.cancel,
                        pass_user_data=True)
                ]
            )
        )
        # buy token
        self.dispatcher.add_handler(
            ConversationHandler(
                entry_points=[
                    CommandHandler(
                        ('sfi_buy', 'sft_buy'),
                        personal.buy_token, pass_user_data=True)
                ],
                states={
                    BUY_QUOTED: [
                        MessageHandler(
                            FilterQuotedCurrency(),
                            personal.buy_token_quoted,
                            pass_user_data=True),
                        MessageHandler(
                            FilterInvalidValue(),
                            personal.buy_token_invalid_quoted)
                    ],
                    BUY_AMOUNT: [
                        MessageHandler(
                            FilterCurrencyValue(),
                            personal.buy_token_amount,
                            pass_user_data=True),
                        MessageHandler(
                            FilterInvalidValue(),
                            personal.buy_token_invalid_amount)
                    ],
                    BUY_CONFIRMATION: [
                        MessageHandler(
                            FilterСonfirmation(),
                            personal.buy_token_confirmation,
                            pass_user_data=True),
                    ]
                },
                fallbacks=[
                    RegexHandler(
                        f'^🚫  Отмена$', general.cancel,
                        pass_user_data=True)
                ]
            )
        )
