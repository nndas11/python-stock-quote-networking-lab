"""Interactive stock quotes using Twelve Data's HTTPS JSON API (Python 3.10+)."""

import json
import os
import re
import ssl
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class QuoteError(Exception):
    """An expected input, network, or provider failure safe to show to users."""


@dataclass(frozen=True)
class Quote:
    symbol: str
    name: str
    price: Decimal
    change: Decimal
    percent_change: Decimal
    currency: str
    exchange: str
    as_of: datetime


def normalize_symbol(value):
    symbol = value.strip().upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9.-]{0,19}", symbol):
        raise QuoteError("Enter a stock symbol such as ADBE, AAPL, or BRK.B.")
    return symbol


def provider_error(code):
    messages = {
        400: "The provider rejected this symbol or request.",
        401: "Invalid API key. Check TWELVEDATA_API_KEY.",
        403: "Your API plan does not permit access to this data.",
        404: "Symbol not found, or no quote is available.",
        429: "API rate limit reached. Wait for your quota to reset before retrying.",
    }
    return QuoteError(messages.get(code, "The data provider is unavailable. Try again later."))


def parse_quote(data, symbol):
    """Validate untrusted provider data before creating an application record."""
    try:
        if not isinstance(data, dict):
            raise ValueError
        if data.get("status") == "error":
            raise provider_error(int(data.get("code", 0)))
        for key in ("symbol", "name", "currency", "exchange"):
            value = data[key]
            if not isinstance(value, str) or not value.strip() or len(value) > 300:
                raise ValueError
            if any(not character.isprintable() for character in value):
                raise ValueError
        if data["symbol"].upper() != symbol:
            raise ValueError
        values = [Decimal(str(data[key])) for key in ("close", "change", "percent_change")]
        if any(not value.is_finite() or abs(value) > Decimal("1e15") for value in values):
            raise ValueError
        if values[0] <= 0:
            raise ValueError
        timestamp = data.get("last_quote_at") or data["timestamp"]
        if isinstance(timestamp, bool) or int(timestamp) <= 0:
            raise ValueError
        as_of = datetime.fromtimestamp(int(timestamp), timezone.utc)
        return Quote(symbol, data["name"], *values, data["currency"], data["exchange"], as_of)
    except (KeyError, TypeError, ValueError, InvalidOperation, OverflowError, OSError):
        raise QuoteError("The provider returned an incomplete or invalid quote.") from None


class TwelveDataClient:
    """Provider adapter: bounded retries, HTTPS verification, no credential logging."""

    def __init__(self, api_key):
        self.api_key = api_key.strip()
        if not self.api_key or not self.api_key.isascii() or not self.api_key.isprintable():
            raise QuoteError("Set TWELVEDATA_API_KEY to your Twelve Data API key.")

    def get_quote(self, raw_symbol):
        symbol = normalize_symbol(raw_symbol)
        url = "https://api.twelvedata.com/quote?" + urlencode({"symbol": symbol})
        request = Request(url, headers={
            "Authorization": "apikey " + self.api_key,
            "Accept": "application/json",
            "User-Agent": "StockQuoteNetworkingLab/1.0",
        })
        # Three attempts; 10-second socket timeout; 1 then 2 seconds backoff.
        for attempt in range(3):
            try:
                with urlopen(request, timeout=10) as response:
                    payload = response.read(1_000_001)
                if len(payload) > 1_000_000:
                    raise QuoteError("The provider response is unexpectedly large.")
                try:
                    data = json.loads(payload)
                except (ValueError, UnicodeError, RecursionError):
                    raise QuoteError("The provider returned invalid JSON.") from None
                if isinstance(data, dict) and str(data.get("code")) in {"500", "502", "503", "504"}:
                    if attempt < 2:
                        time.sleep(2 ** attempt)
                        continue
                return parse_quote(data, symbol)
            except HTTPError as error:
                code = error.code
                error.close()
                if code not in {500, 502, 503, 504} or attempt == 2:
                    raise provider_error(code) from None
            except (URLError, OSError, HTTPException) as error:
                reason = error.reason if isinstance(error, URLError) else error
                if isinstance(reason, ssl.SSLCertVerificationError):
                    raise QuoteError("TLS certificate verification failed. Check your system certificates.") from None
                if attempt == 2:
                    raise QuoteError("Unable to reach the provider. Check your network and try again.") from None
            time.sleep(2 ** attempt)
        raise QuoteError("No quote could be retrieved.")


def format_quote(quote):
    return "\n".join([
        datetime.now().astimezone().strftime("%a %b %d %H:%M:%S %Z %Y"),
        f"{quote.name} ({quote.symbol})",
        f"{quote.price:.2f} {quote.change:+.2f} ({quote.percent_change:+.2f}%)",
        f"Currency: {quote.currency} | Exchange: {quote.exchange}",
        f"Quote as of: {quote.as_of.isoformat()} | Source: Twelve Data",
        "Latest available quote; freshness depends on market hours and API plan.",
    ])


def main():
    try:
        client = TwelveDataClient(os.environ.get("TWELVEDATA_API_KEY", ""))
    except QuoteError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print("Stock Quotes — enter a symbol, or 'quit' to exit.")
    while True:
        try:
            symbol = input("\nPlease enter a symbol: ")
            if symbol.strip().lower() in {"quit", "exit"}:
                return 0
            print(format_quote(client.get_quote(symbol)))
        except QuoteError as error:
            print(f"Error: {error}")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            return 0


if __name__ == "__main__":
    sys.exit(main())
