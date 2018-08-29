import requests

import json
import logging

from settings.config import BOTAN_KEY

TRACK_URL = 'https://api.botan.io/track'
SHORTENER_URL = 'https://api.botan.io/s/'

logger = logging.getLogger(__name__)


def track(uid, message, name='Message'):
    try:
        r = requests.post(
            TRACK_URL,
            params={"token": BOTAN_KEY, "uid": uid, "name": name},
            data=json.dumps(message),
            headers={'Content-type': 'application/json'},
        )
        return r.json()
    except requests.exceptions.Timeout:
        # set up for a retry, or continue in a retry loop
        return False
    except (requests.exceptions.RequestException, ValueError) as e:
        # catastrophic error
        logger.error(e)
        return False


def shorten_url(url, user_id):
    """
    Shorten URL for specified user of a bot
    """
    try:
        return requests.get(SHORTENER_URL, params={
            'token': BOTAN_KEY,
            'url': url,
            'user_ids': str(user_id),
        }).text
    except:
        return url