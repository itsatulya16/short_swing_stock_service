"""
Nifty 500 1-Hour Swing Screener
--------------------------------
Strategy:
  1. EMA9 > EMA20 now, AND the crossover happened within the last 1-2 candles (fresh cross)
  2. RSI(14) > 60
  3. Close > EMA9 AND candle is green (close > open)
  4. Volume on latest candle > 20-period average volume

Sends matching stocks to Telegram every evening.

Author: generated for personal use
"""

import time
import logging
import sys
from datetime import datetime

import pandas as pd
import numpy as np
import yfinance as yf
import requests

import config

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("screener.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Indicator calculations
# ---------------------------------------------------------------------------
def compute_ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    # Where avg_loss is 0, RSI should be 100
    rsi = rsi.where(avg_loss != 0, 100)
    return rsi


# ---------------------------------------------------------------------------
# Data fetch
# ---------------------------------------------------------------------------
def fetch_1h_data(ticker: str, period: str = "1mo") -> pd.DataFrame | None:
    """Fetch 1-hour candles for a single ticker. Returns None on failure/empty."""
    try:
        df = yf.download(
            ticker,
            period=period,
            interval="1h",
            progress=False,
            auto_adjust=False,
            multi_level_index=False,
        )
        if df is None or df.empty or len(df) < 25:
            return None
        return df
    except Exception as e:
        log.warning(f"Failed to fetch {ticker}: {e}")
        return None


# ---------------------------------------------------------------------------
# Strategy check
# ---------------------------------------------------------------------------
def check_strategy(df: pd.DataFrame) -> dict | None:
    """
    Evaluate the 4-step strategy on the latest COMPLETED candle.
    Returns a dict of signal details if matched, else None.
    """
    df = df.copy()
    df["EMA9"] = compute_ema(df["Close"], 9)
    df["EMA20"] = compute_ema(df["Close"], 20)
    df["RSI"] = compute_rsi(df["Close"], 14)
    df["VolAvg20"] = df["Volume"].rolling(window=20).mean()

    if len(df) < 27:
        return None

    latest = df.iloc[-1]
    prev1 = df.iloc[-2]
    prev2 = df.iloc[-3]

    # Guard against NaNs in freshly-warmed-up indicators
    check_cols = ["EMA9", "EMA20", "RSI", "VolAvg20"]
    if df.iloc[-3:][check_cols].isna().any().any():
        return None

    ema_cross_now = latest["EMA9"] > latest["EMA20"]
    # Crossover must have happened ON the latest candle, or 1-2 candles ago
    # (i.e. EMA9 was still <= EMA20 at some point within the last 2 candles).
    crossed_recently = (
        (prev1["EMA9"] <= prev1["EMA20"]) or (prev2["EMA9"] <= prev2["EMA20"])
    )
    rsi_burst = latest["RSI"] > 60
    green_candle = latest["Close"] > latest["Open"]
    price_above_ema9 = latest["Close"] > latest["EMA9"]
    volume_confirm = latest["Volume"] > latest["VolAvg20"]

    if ema_cross_now and crossed_recently and rsi_burst and green_candle and price_above_ema9 and volume_confirm:
        return {
            "close": round(float(latest["Close"]), 2),
            "ema9": round(float(latest["EMA9"]), 2),
            "ema20": round(float(latest["EMA20"]), 2),
            "rsi": round(float(latest["RSI"]), 2),
            "volume": int(latest["Volume"]),
            "vol_avg20": int(latest["VolAvg20"]),
            "candle_time": df.index[-1],
        }
    return None


# ---------------------------------------------------------------------------
# Telegram delivery
# ---------------------------------------------------------------------------
def send_telegram_message(text: str):
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    # Telegram caps messages at 4096 chars; chunk if needed
    chunks = [text[i:i + 4000] for i in range(0, len(text), 4000)] or [text]
    for chunk in chunks:
        resp = requests.post(
            url,
            data={
                "chat_id": config.TELEGRAM_CHAT_ID,
                "text": chunk,
                "parse_mode": "HTML",
            },
            timeout=15,
        )
        if resp.status_code != 200:
            log.error(f"Telegram send failed: {resp.status_code} {resp.text}")
        time.sleep(0.5)


def format_results(results: list[dict]) -> str:
    today = datetime.now().strftime("%d-%b-%Y %H:%M")
    if not results:
        return f"📊 <b>Nifty 500 Screener — {today}</b>\n\nNo stocks matched the strategy today."

    lines = [f"📊 <b>Nifty 500 Screener — {today}</b>", f"Matches: {len(results)}\n"]
    for r in results:
        lines.append(
            f"• <b>{r['symbol']}</b>  |  ₹{r['close']}  |  RSI {r['rsi']}  "
            f"|  EMA9 {r['ema9']} / EMA20 {r['ema20']}  "
            f"|  Vol {r['volume']:,} (avg {r['vol_avg20']:,})"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main run
# ---------------------------------------------------------------------------
def load_universe() -> list[str]:
    """Load the stock universe from stocks.csv (one NSE symbol per line, no .NS suffix)."""
    try:
        with open("stocks.csv", "r", encoding="utf-8") as f:
            symbols = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        return symbols
    except FileNotFoundError:
        log.error("stocks.csv not found. Run fetch_nifty500.py first, or supply your own list.")
        sys.exit(1)


def run():
    log.info("Starting Nifty 500 screener run")
    symbols = load_universe()
    log.info(f"Loaded {len(symbols)} symbols")

    matches = []
    failed = []

    for i, symbol in enumerate(symbols, 1):
        ticker = f"{symbol}.NS"
        df = fetch_1h_data(ticker)
        if df is None:
            failed.append(symbol)
            continue

        result = check_strategy(df)
        if result:
            result["symbol"] = symbol
            matches.append(result)
            log.info(f"MATCH: {symbol} | RSI {result['rsi']} | Close {result['close']}")

        if i % 50 == 0:
            log.info(f"Progress: {i}/{len(symbols)} scanned, {len(matches)} matches so far")

        # Be polite to Yahoo's endpoint — avoid getting rate-limited/blocked
        time.sleep(config.REQUEST_DELAY_SECONDS)

    log.info(f"Scan complete. {len(matches)} matches, {len(failed)} failed fetches out of {len(symbols)}")
    if failed:
        log.warning(f"Failed symbols (sample): {failed[:20]}")

    message = format_results(matches)
    send_telegram_message(message)
    log.info("Telegram message sent. Done.")


if __name__ == "__main__":
    run()
