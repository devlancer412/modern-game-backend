import unittest
from .client import api_wrapper

_TEST_API_KEY = "0a6d67c58b40a35f949329157a99e96753e64c06aa252d574fd32aa26631f5c2"


class TestApiMethods(unittest.TestCase):
    def setUp(self):
        self.api_wrapper = api_wrapper

    def test_get_currencies(self):
        currencies = self.api_wrapper("CURRENCIES", active=True, fixed_rate=True)
        self.assertIsNotNone(currencies)
        self.assertIsNot(len(currencies), 0)

    def test_get_currency_info(self):
        currency = self.api_wrapper("CURRENCY_INFO", ticker="btc")
        self.assertIsNotNone(currency)
        self.assertEqual(currency["ticker"], "btc")

    def test_get_currencies_to(self):
        currencies = self.api_wrapper("CURRENCIES_TO", ticker="btc")
        currencies_fixed_rate = self.api_wrapper(
            "CURRENCIES_TO", ticker="btc", fixed_rate=True
        )
        self.assertIsNotNone(currencies)
        self.assertIsNotNone(currencies_fixed_rate)
        self.assertIsNot(len(currencies), 0)
        self.assertIsNot(len(currencies_fixed_rate), 0)
        self.assertTrue(len(currencies) > len(currencies_fixed_rate))

    def test_get_transactions_list(self):
        from_currency = "btc"
        to_currency = "eth"
        status = "waiting"
        limit = 10
        txes = self.api_wrapper(
            "LIST_OF_TRANSACTIONS",
            api_key=_TEST_API_KEY,
            from_ticker=from_currency,
            to_ticker=to_currency,
            status=status,
            limit=limit,
        )
        self.assertIsNotNone(txes)
        self.assertIsNot(len(txes), 0)
        self.assertEqual(txes[0]["fromCurrency"], from_currency)
        self.assertEqual(txes[0]["toCurrency"], to_currency)
        self.assertEqual(txes[0]["status"], status)
        self.assertTrue(len(txes) <= limit)

    def test_get_transaction_status(self):
        tx_id = "74cc0255c2a130"
        tx = self.api_wrapper("TX_STATUS", api_key=_TEST_API_KEY, id=tx_id)
        self.assertIsNotNone(tx)
        self.assertEqual(tx["id"], tx_id)

    def test_get_available_pairs(self):
        pairs = self.api_wrapper("PAIRS")
        self.assertIsNotNone(pairs)
        self.assertIsNot(len(pairs), 0)

    def test_get_fixed_rate_available_pairs(self):
        pairs = self.api_wrapper("FIXED_RATE_PAIRS", api_key=_TEST_API_KEY)
        self.assertIsNotNone(pairs)
        self.assertIsNot(len(pairs), 0)

    def test_get_exchange_amount(self):
        estimate = self.api_wrapper(
            "ESTIMATED",
            api_key=_TEST_API_KEY,
            amount=1,
            from_ticker="btc",
            to_ticker="eth",
        )
        fixed_rate_estimate = self.api_wrapper(
            "ESTIMATED",
            api_key=_TEST_API_KEY,
            amount=1,
            from_ticker="btc",
            to_ticker="eth",
            fixed_rate=True,
        )
        self.assertIsNotNone(estimate)
        self.assertIsNotNone(fixed_rate_estimate)
        self.assertTrue(estimate["estimatedAmount"])
        self.assertTrue(estimate["estimatedAmount"])

    def test_get_minimal_exchange_amount(self):
        res = self.api_wrapper("MIN_AMOUNT", from_ticker="btc", to_ticker="eth")
        self.assertIsNotNone(res)
        self.assertTrue(res["minAmount"])

    def test_create_exchange(self):
        from_ticker = "btc"
        to_ticker = "eth"
        address = "0xdddddddddddddddddddddddddddddddddddddddd"
        amount = 1
        extra_id = ("111111",)
        user_id = "123"
        contact_email = "exmaple@mail.ru"
        tx = self.api_wrapper(
            "CREATE_TX",
            api_key=_TEST_API_KEY,
            from_ticker=from_ticker,
            to_ticker=to_ticker,
            address=address,
            amount=amount,
            extra_id=extra_id,
            user_id=user_id,
            contact_email=contact_email,
        )

        self.assertIsNotNone(tx)
        self.assertEqual(tx["fromCurrency"], from_ticker)
        self.assertEqual(tx["toCurrency"], to_ticker)
        self.assertTrue(tx["payinAddress"])

    def test_fixed_rate_create_exchange(self):
        from_ticker = "btc"
        to_ticker = "eth"
        address = "0xdddddddddddddddddddddddddddddddddddddddd"
        amount = 1
        extra_id = ("111111",)
        user_id = "123"
        contact_email = "exmaple@mail.ru"
        tx = self.api_wrapper(
            "CREATE_TX",
            api_key=_TEST_API_KEY,
            from_ticker=from_ticker,
            to_ticker=to_ticker,
            address=address,
            amount=amount,
            fixed_rate=True,
            extra_id=extra_id,
            user_id=user_id,
            contact_email=contact_email,
        )

        self.assertIsNotNone(tx)
        self.assertEqual(tx["fromCurrency"], from_ticker)
        self.assertEqual(tx["toCurrency"], to_ticker)
        self.assertTrue(tx["payinAddress"])
        self.assertTrue(tx["validUntil"])


if __name__ == "__main__":
    unittest.main()
