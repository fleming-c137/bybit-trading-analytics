"""Minimal, read-only Bybit V5 REST client.

Only GET endpoints are implemented on purpose: this project never places orders
or moves funds. Use a read-only API key.

Docs: https://bybit-exchange.github.io/docs/v5/intro
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Iterator
from urllib.parse import urlencode

import requests

log = logging.getLogger(__name__)

SEVEN_DAYS_MS = 7 * 24 * 60 * 60 * 1000
# Bybit keeps transaction log / closed PnL history for up to 2 years.
MAX_HISTORY_DAYS = 730

RATE_LIMIT_CODES = {10006, 10018}
TIMESTAMP_ERROR_CODE = 10002


class BybitAPIError(RuntimeError):
    def __init__(self, code: int, message: str, endpoint: str):
        super().__init__(f"Bybit API error {code} on {endpoint}: {message}")
        self.code = code
        self.endpoint = endpoint


def sign(secret: str, timestamp: str, api_key: str, recv_window: str, query: str) -> str:
    """HMAC-SHA256 signature for a V5 GET request."""
    payload = f"{timestamp}{api_key}{recv_window}{query}"
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def to_ms(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def time_windows(start_ms: int, end_ms: int, size_ms: int = SEVEN_DAYS_MS) -> Iterator[tuple[int, int]]:
    """Split [start, end] into consecutive windows no larger than ``size_ms``.

    Bybit rejects history queries whose endTime - startTime exceeds 7 days.
    """
    cursor = start_ms
    while cursor < end_ms:
        upper = min(cursor + size_ms - 1, end_ms)
        yield cursor, upper
        cursor = upper + 1


class BybitClient:
    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        base_url: str = "https://api.bybit.com",
        recv_window: int = 10_000,
        timeout: int = 20,
        max_retries: int = 5,
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.recv_window = str(recv_window)
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self._time_offset_ms = 0

    # ------------------------------------------------------------------ core
    def _sync_time(self) -> None:
        data = self._get("/v5/market/time", {}, auth=False)
        server_ms = int(data["timeNano"]) // 1_000_000 if "timeNano" in data else int(data["timeSecond"]) * 1000
        self._time_offset_ms = server_ms - int(time.time() * 1000)
        log.info("Synced clock with Bybit (offset %d ms)", self._time_offset_ms)

    def _get(self, endpoint: str, params: dict[str, Any], auth: bool = True) -> dict[str, Any]:
        params = {k: v for k, v in params.items() if v is not None and v != ""}
        query = urlencode(sorted(params.items()))
        url = f"{self.base_url}{endpoint}"

        for attempt in range(1, self.max_retries + 1):
            headers = {}
            if auth:
                if not (self.api_key and self.api_secret):
                    raise RuntimeError("BYBIT_API_KEY / BYBIT_API_SECRET are not set (see .env.example)")
                ts = str(int(time.time() * 1000) + self._time_offset_ms)
                headers = {
                    "X-BAPI-API-KEY": self.api_key,
                    "X-BAPI-TIMESTAMP": ts,
                    "X-BAPI-RECV-WINDOW": self.recv_window,
                    "X-BAPI-SIGN": sign(self.api_secret, ts, self.api_key, self.recv_window, query),
                }
            try:
                resp = self.session.get(f"{url}?{query}" if query else url, headers=headers, timeout=self.timeout)
            except requests.RequestException as exc:
                if attempt == self.max_retries:
                    raise
                wait = 2**attempt
                log.warning("Network error on %s (%s), retrying in %ss", endpoint, exc, wait)
                time.sleep(wait)
                continue

            if resp.status_code == 429:
                time.sleep(2**attempt)
                continue
            resp.raise_for_status()
            body = resp.json()
            code = int(body.get("retCode", -1))
            if code == 0:
                return body.get("result", {})
            if code in RATE_LIMIT_CODES and attempt < self.max_retries:
                log.warning("Rate limited on %s, backing off", endpoint)
                time.sleep(2**attempt)
                continue
            if code == TIMESTAMP_ERROR_CODE and auth and attempt < self.max_retries:
                self._sync_time()
                continue
            raise BybitAPIError(code, body.get("retMsg", ""), endpoint)
        raise BybitAPIError(-1, "max retries exceeded", endpoint)

    def _paginate(self, endpoint: str, params: dict[str, Any], auth: bool = True) -> Iterator[dict[str, Any]]:
        cursor = None
        while True:
            result = self._get(endpoint, {**params, "cursor": cursor}, auth=auth)
            yield from result.get("list", [])
            cursor = result.get("nextPageCursor")
            if not cursor:
                break

    def _windowed(self, endpoint: str, params: dict[str, Any], start: datetime, end: datetime) -> Iterator[dict[str, Any]]:
        earliest = datetime.now(timezone.utc) - timedelta(days=MAX_HISTORY_DAYS - 1)
        start = max(start if start.tzinfo else start.replace(tzinfo=timezone.utc), earliest)
        for lo, hi in time_windows(to_ms(start), to_ms(end)):
            log.debug("%s %s -> %s", endpoint, lo, hi)
            yield from self._paginate(endpoint, {**params, "startTime": lo, "endTime": hi})

    # --------------------------------------------------------------- private
    def transaction_log(
        self, start: datetime, end: datetime, category: str | None = None, currency: str | None = None
    ) -> Iterator[dict[str, Any]]:
        """UTA transaction log -- the same data as the 'Asset Change Details' CSV export.

        https://bybit-exchange.github.io/docs/v5/account/transaction-log
        """
        params = {"accountType": "UNIFIED", "category": category, "currency": currency, "limit": 50}
        yield from self._windowed("/v5/account/transaction-log", params, start, end)

    def closed_pnl(self, start: datetime, end: datetime, category: str = "linear") -> Iterator[dict[str, Any]]:
        """Closed position PnL records (include leverage, avg entry/exit).

        https://bybit-exchange.github.io/docs/v5/position/close-pnl
        """
        yield from self._windowed("/v5/position/closed-pnl", {"category": category, "limit": 100}, start, end)

    def wallet_balance(self) -> dict[str, Any]:
        result = self._get("/v5/account/wallet-balance", {"accountType": "UNIFIED"})
        rows = result.get("list", [])
        return rows[0] if rows else {}

    # ---------------------------------------------------------------- public
    def klines(
        self, symbol: str, start: datetime, end: datetime, interval: str = "D", category: str = "linear"
    ) -> list[list[str]]:
        """Public OHLCV candles, used for market context (e.g. BTC)."""
        out: list[list[str]] = []
        end_ms = to_ms(end)
        start_ms = to_ms(start)
        while end_ms > start_ms:
            result = self._get(
                "/v5/market/kline",
                {"category": category, "symbol": symbol, "interval": interval,
                 "start": start_ms, "end": end_ms, "limit": 1000},
                auth=False,
            )
            batch = result.get("list", [])  # newest first
            if not batch:
                break
            out.extend(batch)
            oldest = int(batch[-1][0])
            if oldest <= start_ms or len(batch) < 1000:
                break
            end_ms = oldest - 1
        return out
