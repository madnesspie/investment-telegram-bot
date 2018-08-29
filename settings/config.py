from settings.logger import set_up_logging, logging

DEBUG = True

# setup loggers
set_up_logging(level=logging.DEBUG)

# bot
PRODUCTION_TOKEN = '428370285:AAEfjY1o6DyLp1ysrz-OQBtgFYBwlmS-d1g'
TEST_TOKEN = '428474365:AAGhkCJc3_mhKALgMX-4my45w53yRpxwAk8'
API_TOKEN = TEST_TOKEN if DEBUG else PRODUCTION_TOKEN
BOT = 'mycryptotestobot' if DEBUG else 'cryptosreda_bot'

# botan
BOTAN_KEY = 'ca6f01fd-8b9f-40f5-a8bc-1551cf93ee6b'

# webhook
WEBHOOK_HOST = '54.37.233.220'  # old '95.172.133.74'
WEBHOOK_PORT = 8443  # 443, 80, 88 or 8443 (port need to be 'open')
WEBHOOK_LISTEN = '0.0.0.0'  # In some VPS you may need to put here the IP addr

WEBHOOK_SSL_CERT = 'cert/cert.pem'  # Path to the ssl certificate
WEBHOOK_SSL_PRIV = 'cert/private.key'  # Path to the ssl private key

WEBHOOK_URL_PATH = f"{API_TOKEN}/"
WEBHOOK_URL_BASE = f"https://{WEBHOOK_HOST}:{WEBHOOK_PORT}/{WEBHOOK_URL_PATH}"

WEBHOOK = {
    'listen': WEBHOOK_HOST,
    'port': WEBHOOK_PORT,
    'url_path': WEBHOOK_URL_PATH,
    'key': WEBHOOK_SSL_PRIV,
    'cert': WEBHOOK_SSL_CERT,
}

# database
DATABASE_NAME = 'myfund' if DEBUG else 'myfund'
DATABASE_USER = 'myfund'
DATABASE_HOST = 'localhost'
DATABASE_PASSWORD = 'SFM09WfZjuRM8UhrH0PzXiUmwNIiMiNM'

# groups
ADMINS = [202628185, 272418334]

# nodes
# TODO: сменить порты!!!!!!!!!!!!!
RPC = {
    'btc': {'port': 18332, 'password': 'TuZ0GQ69C8wW'},
    'bch': {'port': 18432, 'password': 'txbZ3YI653PtVbulWZXZoFSbyXuJBrq5'},
    'zec': {'port': 18232, 'password': 'myhkwsH707qObV1592beEv6LvXXvancM'}
}

# formats
CURRENCY_FMT = {
    'rub': 0,
    'usd': 2,
    'btc': 8
}
