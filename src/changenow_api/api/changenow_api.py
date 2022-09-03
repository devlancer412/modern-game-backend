from . import requests_client


class ChangeNowAPi:
    __api_url = "https://changenow.io/api/v1/"

    def get_currencies(self, active=False, fixed_rate=False):
        payload = {}
        if active:
            payload["active"] = "true"

        if fixed_rate:
            payload["fixedRate"] = "true"

        url = self.__api_url + "currencies"
        response = requests_client.get(url, params=payload)
        return response

    def get_currencies_to(self, ticker="", fixed_rate=False):
        payload = {}
        if fixed_rate:
            payload["fixedRate"] = "true"

        url = self.__api_url + "{}/{}".format("currencies-to", ticker)
        response = requests_client.get(url, params=payload)
        return response

    def get_currency_info(self, ticker=""):
        url = self.__api_url + "{}/{}".format("currencies", ticker)
        response = requests_client.get(url)
        return response

    def get_transactions_list(
        self,
        api_key="",
        from_ticker="",
        to_ticker="",
        status="",
        limit=10,
        offset=0,
        date_from="",
        date_to="",
    ):
        payload = {
            "from": from_ticker,
            "to": to_ticker,
            "status": status,
            "limit": limit,
            "offset": offset,
            "dateFrom": date_from,
            "dateTo": date_to,
        }
        url = self.__api_url + "{}/{}".format("transactions", api_key)
        response = requests_client.get(url, params=payload)
        return response

    def get_transaction_status(self, id="", api_key=""):
        url = self.__api_url + "{}/{}/{}".format("transactions", id, api_key)
        response = requests_client.get(url)
        return response

    def get_available_pairs(self, include_partners=False):
        payload = {"includePartners": str(include_partners).lower()}
        url = self.__api_url + "market-info/available-pairs"
        response = requests_client.get(url, params=payload)
        return response

    def get_minimal_exchange_amount(self, from_ticker="", to_ticker=""):
        from_to = "{}_{}".format(from_ticker.lower(), to_ticker.lower())
        url = self.__api_url + "{}/{}".format("min-amount", from_to)
        response = requests_client.get(url)
        return response

    def get_fixed_rate_available_pairs(self, api_key=""):
        url = self.__api_url + "{}/{}".format("market-info/fixed-rate", api_key)
        response = requests_client.get(url)
        return response

    def get_exchange_amount(
        self, api_key="", amount=None, from_ticker="", to_ticker="", fixed_rate=False
    ):
        payload = {"api_key": api_key}
        method_name = "exchange-amount"
        if fixed_rate:
            method_name += "/fixed-rate"

        from_to = "{}_{}".format(from_ticker.lower(), to_ticker.lower())
        url = self.__api_url + "{}/{}/{}".format(method_name, amount, from_to)
        response = requests_client.get(url, params=payload)
        return response

    def create_exchange(
        self,
        api_key="",
        from_ticker="",
        to_ticker="",
        address="",
        amount=None,
        fixed_rate=False,
        extra_id="",
        refund_address="",
        refund_extra_id="",
        user_id="",
        payload=None,
        contact_email="",
    ):
        if payload is None:
            payload = {}

        transaction_data = {
            "from": from_ticker,
            "to": to_ticker,
            "address": address,
            "amount": amount,
            "extraId": extra_id,
            "refundAddress": refund_address,
            "refundExtraId": refund_extra_id,
            "userId": user_id,
            "payload": payload,
            "contactEmail": contact_email,
        }

        method_name = "transactions"
        if fixed_rate:
            method_name += "/fixed-rate"

        url = self.__api_url + "{}/{}".format(method_name, api_key)
        response = requests_client.post(url, body=transaction_data)
        return response
