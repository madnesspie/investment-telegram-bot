from datetime import datetime as dt, timedelta as td
from itertools import product

import matplotlib as mpl
import telegram
from telegram import Bot
mpl.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker

from core.decorators import log
from core import database as db


class ChartCreator:

    currency = [
        ['rub', 7, '₽', '1.0f'],
        ['usd', 5, '$', '1.0f'],
        ['btc', 6, 'Ƀ', '.3f']
    ]

    period = [
        ['month', '%d-%m', 30, 1, 55],
        ['all', '%m-%y', 0, 30, 0]
    ]

    @staticmethod
    @log
    def create_charts(bot: Bot, *args, **kwargs):
        hist = sorted(db.select('fund_hist'), key=lambda day: day[1])
        for currency, period in product(ChartCreator.currency,
                                        ChartCreator.period):
            ChartCreator.build(hist, *currency, *period)

    @staticmethod
    def build(hist, currency, column, sym, tick_fmt,
              period, date_fmt, count, step, turn):
        """
        Создание графика
        :param hist: история стоимости токена
        :param currency: название валюты
        :param column: номер поля в бд
        :param sym: unicode символ
        :param tick_fmt: формат подписей по оси Y
        :param period: название периода
        :param date_fmt: формат подписей по оси X
        :param count: отступ от конца (период графика)
        :param step: шаг (нужно чтобы строить длинные графики)
        :param turn: градус поворота подписей по оси X
        """
        points = hist[-count:]

        dates = [dt.strptime(point[1], '%Y-%m-%d').date()
                 for point in points
                 if point[column] != 0]
        values = [float(point[column])
                  for point in points
                  if point[column] != 0]

        mpl.rcParams.update({'font.size': 10})
        fig = plt.figure()
        plt.title(f'График SFI/{currency.upper()} {dt.now().strftime("%Y-%m-%d")}')

        ax = plt.axes()
        ax.yaxis.grid(True)
        ax.yaxis.set_major_formatter(ticker.FormatStrFormatter(f'{sym}%{tick_fmt}'))
        ax.xaxis.set_major_formatter(mdates.DateFormatter(date_fmt))
        ax.xaxis.set_major_locator(mdates.MonthLocator())

        for tick in ax.yaxis.get_major_ticks():
            tick.label1On = True
            tick.label2On = False
            tick.label1.set_color('green')

        plt.plot(dates, values, linestyle='solid', label='Цена токена BTC')
        plt.xticks(dates[::step], fontsize=7, rotation=turn)
        plt.subplots_adjust(bottom=0.1)

        fig.savefig(f'static/chart_sfi_{currency}_{period}.png')
        # todo проконтролировать по памяти
        plt.close(fig)
