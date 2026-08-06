"""
Standalone Telegram delivery test — run this on its own to confirm your
bot token and chat ID are correct, independent of the screener_logic
"""

import requests
import config

def main():
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    print(f"Using token: {config.TELEGRAM_BOT_TOKEN[:10]}... (truncated)")
    print(f"Using chat_id: {config.TELEGRAM_CHAT_ID}")

    resp = requests.post(
        url,
        data={
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": "Test message from screener project — if you see this, Telegram delivery works.",
        },
        timeout=15,
    )

    print(f"HTTP status: {resp.status_code}")
    print(f"Response body: {resp.text}")

if __name__ == "__main__":
    main()
