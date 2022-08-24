from .api import changenow_api
from urllib.error import HTTPError, URLError
from .exceptions import ChangeNowApiError

_CLIENT = changenow_api.ChangeNowAPi()

_METHODS = {
    'CURRENCIES': _CLIENT.get_currencies,
    'CURRENCIES_TO': _CLIENT.get_currencies_to,
    'CURRENCY_INFO': _CLIENT.get_currency_info,
    'LIST_OF_TRANSACTIONS': _CLIENT.get_transactions_list,
    'TX_STATUS': _CLIENT.get_transaction_status,
    'ESTIMATED': _CLIENT.get_exchange_amount,
    'MIN_AMOUNT': _CLIENT.get_minimal_exchange_amount,
    'PAIRS': _CLIENT.get_available_pairs,
    'FIXED_RATE_PAIRS': _CLIENT.get_fixed_rate_available_pairs,
    'CREATE_TX': _CLIENT.create_exchange
}


def api_wrapper(call_name, **kwargs):
    try:
        response = _METHODS[call_name](**kwargs)
        return response
    except KeyError as err:
        raise ValueError('Undefined api method: {}'.format(err.args[0]))
    except HTTPError as err:
        raise ChangeNowApiError(err.reason, err.code, err.read())
    except URLError as err:
        raise ChangeNowApiError(err.reason)
