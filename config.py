"""
Configuration file.

Credentials are read from environment variables first (this is what GitHub
Actions secrets populate). If not running in that environment, it falls back
to the placeholder values below — fill those in for local/WSL/Windows use.

Do NOT commit this file with real credentials filled in to a public repo.
If your repo is public, rely on the environment-variable path only (i.e.
leave the fallbacks below as placeholders) and set secrets in GitHub instead.
"""

import os

# --- Telegram ---
# 1. Message @BotFather on Telegram, send /newbot, follow prompts -> get a token like
#    "123456789:AAExampleTokenxxxxxxxxxxxxxxxxxxxxx"
# 2. Message your new bot once (anything), then visit in a browser:
#    https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
#    Find "chat":{"id": 123456789, ...} in the JSON response -> that's your chat ID.

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "PUT_YOUR_BOT_TOKEN_HERE")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "PUT_YOUR_CHAT_ID_HERE")

if TELEGRAM_BOT_TOKEN == "PUT_YOUR_BOT_TOKEN_HERE" or TELEGRAM_CHAT_ID == "PUT_YOUR_CHAT_ID_HERE":
    import sys
    print(
        "WARNING: Telegram credentials not set. Set TELEGRAM_BOT_TOKEN and "
        "TELEGRAM_CHAT_ID as environment variables (GitHub Actions secrets) "
        "or fill in config.py directly for local runs.",
        file=sys.stderr,
    )

# --- Screener behaviour ---
# Delay between each stock fetch to avoid Yahoo Finance rate-limiting (seconds)
REQUEST_DELAY_SECONDS = 0.3
