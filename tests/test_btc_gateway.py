from subprocess import CalledProcessError

import pytest

from core.database import select_partner
from core.gateways.bitcoin import bitcoin_cli, set_partner


@pytest.yield_fixture(scope='function')
def chat_id(request):
    yield 189882448


@pytest.yield_fixture(scope='function')
def tel_num(request):
    yield '+79994405487'


# python3.6 -m pytest -v tests/test_btc_gateway.py


# 1) Cli отвечает отвечает без CalledProcessError
def test_bitcoin_cli_returned_valid():
    try:
        responce = bitcoin_cli('getbestblockhash')
    except CalledProcessError:
        pytest.fail('Unexpected CalledProcessError!')


# 2) Верно ли записывается в бд юзер
def test_set_partner_records_validly(chat_id):
    partner_id = set_partner(chat_id)
    partner = select_partner(chat_id)
    assert partner[0] == partner_id and partner[11] == chat_id


# 3)
