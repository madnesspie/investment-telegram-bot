import unicodedata

from telegram.ext import BaseFilter


def check_latin(uchr):
    return 'LATIN' in unicodedata.name(uchr)


class FilterCurrencyValue(BaseFilter):
    def filter(self, message):
        return (message.text.replace(',', '').isdigit() or
                message.text.replace('.', '').isdigit())


class FilterAddr(BaseFilter):
    def filter(self, message):
        addr = message.text
        if len(addr) < 20:
            return
        else:
            return all(check_latin(uchr) for uchr in addr
                       if uchr.isalpha())


class FilterQuotedCurrency(BaseFilter):
    def filter(self, message):
        quoted = message.text
        return True if quoted in ['BTC', 'BCH', 'ZEC'] else False


class FilterSellTokenAddress(BaseFilter):
    def filter(self, message):
        addr = message.text
        if '💰  На кошелек в боте' == addr:
            return True
        elif len(addr) < 20:
            return False
        else:
            return all(check_latin(uchr) for uchr in addr
                       if uchr.isalpha())


class FilterСonfirmation(BaseFilter):
    def filter(self, message):
        return True if 'Отправить' in message.text else False


class FilterEmail(BaseFilter):
    def filter(self, message):
        email = message.text
        if ('@' in email and '.' in email):
            return True
        else:
            return False


class FilterPassword(BaseFilter):
    def filter(self, message):
        password = message.text
        if len(password) < 8:
            return
        else:
            return all(check_latin(uchr) for uchr in password
                       if uchr.isalpha())


class FilterInvalidValue(BaseFilter):
    def filter(self, message):
        return False if 'Отмена' in message.text else True
