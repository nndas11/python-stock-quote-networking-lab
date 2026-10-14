"""Offline tests: synthetic fixtures, no API key or live market data required."""

import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import stock_quotes as app


def fixture(**changes):
    data = dict(symbol="ADBE", name="Example Company", close="109.24",
                change="0.60", percent_change="0.55", currency="USD",
                exchange="NASDAQ", timestamp=1476131028)
    data.update(changes)
    return data


class QuoteTests(unittest.TestCase):
    def setUp(self):
        self.client = app.TwelveDataClient("synthetic-test-key")

    def test_required_output_and_signs(self):
        for change, percent, expected in [
            ("0.60", "0.55", "109.24 +0.60 (+0.55%)"),
            ("-0.60", "-0.55", "109.24 -0.60 (-0.55%)"),
            ("0", "0", "109.24 +0.00 (+0.00%)"),
        ]:
            output = app.format_quote(app.parse_quote(fixture(change=change, percent_change=percent), "ADBE"))
            self.assertIn(expected, output)
            self.assertIn("Example Company (ADBE)", output)
            self.assertIn("Quote as of:", output)
            self.assertRegex(output.splitlines()[0], r"\w{3} \w{3} \d{2} \d{2}:\d{2}:\d{2}")

    def test_bad_symbols_never_make_network_requests(self):
        with patch.object(app, "urlopen") as request:
            for symbol in ("", " ", "AAPL&apikey=bad", "A" * 21):
                with self.assertRaises(app.QuoteError):
                    self.client.get_quote(symbol)
            request.assert_not_called()

    def test_response_validation(self):
        for data in ([], {}, fixture(close="NaN"), fixture(change="Infinity"),
                     fixture(symbol="AAPL"), fixture(name=""), fixture(timestamp="bad"),
                     fixture(close="-1"), fixture(name="bad\x1b[31m")):
            with self.subTest(data=data), self.assertRaises(app.QuoteError):
                app.parse_quote(data, "ADBE")

    def test_successful_request(self):
        with patch.object(app, "urlopen", return_value=io.BytesIO(json.dumps(fixture()).encode())) as request:
            quote = self.client.get_quote(" adbe ")
        self.assertEqual(quote.symbol, "ADBE")
        self.assertNotIn("synthetic-test-key", request.call_args.args[0].full_url)
        self.assertEqual(request.call_args.kwargs["timeout"], 10)

    def test_invalid_json(self):
        with patch.object(app, "urlopen", return_value=io.BytesIO(b"not json")):
            with self.assertRaisesRegex(app.QuoteError, "invalid JSON"):
                self.client.get_quote("ADBE")

    def test_network_failures_have_bounded_retries(self):
        for error in (URLError("offline"), TimeoutError("timed out")):
            with patch.object(app, "urlopen", side_effect=error) as request, patch.object(app.time, "sleep"):
                with self.assertRaisesRegex(app.QuoteError, "network"):
                    self.client.get_quote("ADBE")
                self.assertEqual(request.call_count, 3)

    def test_transient_failure_recovers(self):
        errors = [HTTPError("https://example.invalid", 503, "unavailable", {}, None),
                  io.BytesIO(json.dumps(fixture()).encode())]
        with patch.object(app, "urlopen", side_effect=errors) as request, patch.object(app.time, "sleep"):
            self.assertEqual(self.client.get_quote("ADBE").symbol, "ADBE")
            self.assertEqual(request.call_count, 2)

    def test_permanent_http_errors_are_not_retried(self):
        for code in (401, 403, 404, 429):
            error = HTTPError("https://example.invalid", code, "error", {}, None)
            with patch.object(app, "urlopen", side_effect=error) as request:
                with self.assertRaises(app.QuoteError):
                    self.client.get_quote("ADBE")
                self.assertEqual(request.call_count, 1)

    def test_json_provider_error(self):
        with self.assertRaisesRegex(app.QuoteError, "rate limit"):
            app.parse_quote({"status": "error", "code": 429}, "ADBE")

    def test_repeated_input_after_error(self):
        quote = app.parse_quote(fixture(), "ADBE")
        with patch.dict(app.os.environ, {"TWELVEDATA_API_KEY": "test"}), \
             patch("builtins.input", side_effect=["BAD", "ADBE", "quit"]), \
             patch.object(app.TwelveDataClient, "get_quote", side_effect=[app.QuoteError("Not found"), quote]), \
             patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(app.main(), 0)
            self.assertIn("Not found", output.getvalue())
            self.assertIn("Example Company", output.getvalue())

    def test_missing_key(self):
        with patch.dict(app.os.environ, {}, clear=True), patch("sys.stderr", new_callable=io.StringIO) as output:
            self.assertEqual(app.main(), 1)
            self.assertIn("TWELVEDATA_API_KEY", output.getvalue())

    def test_end_of_input(self):
        for error in (EOFError, KeyboardInterrupt):
            with patch.dict(app.os.environ, {"TWELVEDATA_API_KEY": "test"}), \
                 patch("builtins.input", side_effect=error), patch("sys.stdout", new_callable=io.StringIO):
                self.assertEqual(app.main(), 0)


if __name__ == "__main__":
    unittest.main()
