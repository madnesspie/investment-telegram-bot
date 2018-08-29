from datetime import datetime as dt, timedelta as td

from . import database as db
from core.decorators import log


class RatesError(Exception): pass
class GetRateError(RatesError): pass


@log
def get_SFIBTC():
    """
    Получает из бд курс токена к BTC
    :return: курс SFI/BTC
    :rtype: float
    """
    today = dt.now()
    rates = db.session.query(db.FundHist).\
        filter_by(day=today.date()).first()

    if not rates:
        yesterday = today - td(days=1)
        rates = db.session.query(db.FundHist).\
            filter_by(day=yesterday.date()).first()

    if not rates:
        # logger.warning(f"Called::get_SFIBTC_rate. GetRateError")
        # raise GetRateError("Can't get rate SFI/BTC")
        return

    return rates.token_btc


@log
def get_SFIBCH():
    """
    Получает из бд курс токена к BCH
    :return: курс SFI/BCH
    :rtype: float
    """
    today = dt.now()
    price = db.session.query(db.CostPriceHist).\
        filter_by(day=today.date(), src='BCH', dst='BTC').first()

    if not price:
        yesterday = today - td(days=1)
        price = db.session.query(db.CostPriceHist). \
            filter_by(day=yesterday.date(), src='BCH', dst='BTC').first()

    if not price:
        # logger.warning(f"Called::get_SFIBCH_rate. GetRateError")
        # raise GetRateError("Can't get rate SFI/BCH")
        return

    bch_btc = price.cost
    sfi_btc = get_SFIBTC()
    sfi_bch = sfi_btc / bch_btc

    return sfi_bch


@log
def get_SFIZEC():
    """
    Получает из бд курс токена к ZEC
    :return: курс SFI/ZEC
    :rtype: float
    """
    today = dt.now()
    price = db.session.query(db.CostPriceHist).\
        filter_by(day=today.date(), src='ZEC', dst='BTC').first()

    if not price:
        yesterday = today - td(days=1)
        price = db.session.query(db.CostPriceHist). \
            filter_by(day=yesterday.date(), src='ZEC', dst='BTC').first()

    if not price:
        # logger.warning(f"Called::get_SFIZEC_rate. GetRateError")
        # raise GetRateError("Can't get rate SFI/ZEC")
        return

    zec_btc = price.cost
    sfi_btc = get_SFIBTC()
    sfi_zec = sfi_btc / zec_btc

    return sfi_zec


@log
def get_BTCUSD():
    today = dt.now()
    price = db.session.query(db.CostPriceHist). \
        filter_by(day=today.date(), src='BTC', dst='USD').first()

    if not price:
        yesterday = today - td(days=1)
        price = db.session.query(db.CostPriceHist). \
            filter_by(day=yesterday.date(), src='BTC', dst='USD').first()

    if not price:
        # logger.warning(f"Called::get_SFIZEC_rate. GetRateError")
        # raise GetRateError("Can't get rate SFI/ZEC")
        return

    return price.cost


@log
def get_ZECUSD():
    today = dt.now()
    price = db.session.query(db.CostPriceHist).\
        filter_by(day=today.date(), src='ZEC', dst='BTC').first()

    if not price:
        yesterday = today - td(days=1)
        price = db.session.query(db.CostPriceHist). \
            filter_by(day=yesterday.date(), src='ZEC', dst='BTC').first()

    if not price:
        # logger.warning(f"Called::get_SFIZEC_rate. GetRateError")
        # raise GetRateError("Can't get rate SFI/ZEC")
        return

    zec_btc = price.cost
    btc_usd = get_BTCUSD()
    zec_usd = zec_btc * btc_usd

    return zec_usd


@log
def get_BCHUSD():
    today = dt.now()
    price = db.session.query(db.CostPriceHist). \
        filter_by(day=today.date(), src='BCH', dst='BTC').first()

    if not price:
        yesterday = today - td(days=1)
        price = db.session.query(db.CostPriceHist). \
            filter_by(day=yesterday.date(), src='BCH', dst='BTC').first()

    if not price:
        # logger.warning(f"Called::get_SFIZEC_rate. GetRateError")
        # raise GetRateError("Can't get rate SFI/ZEC")
        return

    bch_btc = price.cost
    btc_usd = get_BTCUSD()
    bch_usd = bch_btc * btc_usd

    return bch_usd