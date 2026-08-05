# Nifty 500 1-Hour Swing Screener

Scans all Nifty 500 stocks on the 1-hour timeframe every evening and sends
matches to Telegram based on this strategy:

1. **EMA9 > EMA20** (crossover already active on the latest candle)
2. **RSI(14) > 60**
3. **Close > EMA9** and the candle is green (close > open)
4. **Volume > 20-period average volume** on that candle

---

## 1. Setup (one-time)

### Install Python packages
```
pip install -r requirements.txt
```

### Get your Nifty 500 stock list
```
python fetch_nifty500.py
```
This creates `stocks.csv`. Re-run this monthly or so — Nifty 500 constituents
change periodically. If NSE blocks the automated fetch (they sometimes do),
the script will tell you where to manually download the list instead.

### Create a Telegram bot
1. Open Telegram, search for **@BotFather**, start a chat.
2. Send `/newbot`, follow the prompts (choose a name and username).
3. BotFather gives you a token like `123456789:AAExamplexxxxxxxxxxxxxxxxxxxxx`.
4. Send your new bot **any message** (e.g. "hi") so it can see your chat.
5. In a browser, visit:
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```
6. In the JSON response, find `"chat":{"id": 123456789, ...}` — that number
   is your chat ID.

### Fill in `config.py`
```python
TELEGRAM_BOT_TOKEN = "123456789:AAExample..."
TELEGRAM_CHAT_ID = "123456789"
```

### Test it manually
```
python screener.py
```
Check `screener.log` for progress and errors, and check Telegram for the message.
A full Nifty 500 scan takes a while (500 stocks × ~0.3s delay + fetch time —
expect roughly 10-20 minutes depending on your connection). This is intentional:
scanning too fast can get you rate-limited by Yahoo Finance.

---

## 2. Alternative: Run on GitHub Actions (no PC required)

This runs the screener on GitHub's servers on a schedule — your machine
doesn't need to be on at all.

### Setup
1. Push this project to a GitHub repo (private is fine and recommended,
   since it's your personal trading tool — but even public repos work since
   credentials are stored as secrets, not in code).
2. In the repo: **Settings → Secrets and variables → Actions → New repository secret**
   - Add `TELEGRAM_BOT_TOKEN` = your bot token
   - Add `TELEGRAM_CHAT_ID` = your chat ID
3. The workflow file is already included at `.github/workflows/screener.yml`.
   It's scheduled to run **hourly, 10:00 AM to 4:00 PM IST, Monday–Friday**
   (7 runs/day, aligned to NSE trading hours).
4. Commit `stocks.csv` to the repo too (run `fetch_nifty500.py` locally once
   and commit the output) — the Actions runner needs it since it starts
   from a clean checkout each time.
5. To test immediately without waiting for the schedule: go to the
   **Actions** tab → select "Nifty 500 Evening Screener" → **Run workflow**.

### Things to know about this approach
- **GitHub's cron scheduler is not exact** — it can be delayed by several
  minutes during high load on GitHub's infrastructure, especially right at
  common trigger times like the top of the hour. Not a problem for an
  evening screener, but don't expect second-precision.
- **Free minutes**: public repos get unlimited Actions minutes; private
  repos get a free monthly quota (verify current limits in GitHub's docs
  since these change). At 7 runs/day × ~15-20 min each × ~22 trading
  days/month, that's roughly **2,300-3,100 minutes (~40-50 hours)/month**
  — check this against your plan's quota if using a private repo, since
  it's a meaningful jump from a single daily run. If this pushes past your
  quota, a public repo avoids the limit entirely (credentials stay safe
  either way, since they're in secrets, not code).
- **Scheduled workflows auto-disable after 60 days of repo inactivity**
  (no commits). If you don't touch the repo for two months, GitHub pauses
  the schedule — just re-enable it from the Actions tab, or push any commit
  to reset the clock.
- **Logs**: since there's no persistent machine, `screener.log` doesn't
  accumulate across runs. The workflow uploads it as a run artifact instead
  — download it from the specific run's page under the Actions tab if you
  need to debug a failure.
- **stocks.csv gets stale**: since Actions checks out a fresh copy of your
  repo each run, remember to periodically re-run `fetch_nifty500.py`
  locally and push the updated `stocks.csv`, or add a separate monthly
  workflow for that (ask if you'd like this automated too).

---

## 3. Schedule it to run hourly, 10 AM–4 PM IST (Windows Task Scheduler)

1. Open **Task Scheduler** (search in Start menu).
2. Click **Create Task** (not "Basic Task" — we want more control).
3. **General tab**: Name it "Nifty 500 Screener". Select "Run whether user is
   logged on or not" if you want it to run even if you're not actively at
   the PC (you'll need to enter your Windows password).
4. **Triggers tab** → New:
   - Begin the task: **On a schedule**
   - Daily, repeat every 1 day
   - Start time: **10:00 AM**
   - Check **"Repeat task every"** → set to **1 hour**, **for a duration of**
     **6 hours** (this gives you runs at 10, 11, 12, 1, 2, 3, and 4 — the
     6-hour window covers 10 AM through 4 PM)
5. **Actions tab** → New:
   - Action: **Start a program**
   - Program/script: full path to `run_screener.bat`
     (e.g. `C:\Users\YourName\nifty500_screener\run_screener.bat`)
   - Start in: the folder containing the script
     (e.g. `C:\Users\YourName\nifty500_screener\`)
6. **Conditions tab**: uncheck "Start the task only if the computer is on AC
   power" if this is a laptop, otherwise it may skip runs on battery.
7. Save. Right-click the task → **Run** to test it fires correctly.

**Important**: Your PC must be on and awake at the scheduled time (Task
Scheduler can wake a sleeping PC if you check "Wake the computer to run this
task" under the Conditions tab, but it can't start from fully powered off).

---

## 4. Alternative: WSL Ubuntu (cron or Task Scheduler → wsl.exe)

**Cron inside WSL** works, but only fires if the WSL instance is actually
running at trigger time — WSL2 shuts down shortly after you close all
terminals, so a bare `crontab -e` schedule is unreliable unless something
keeps WSL alive all day.

```bash
crontab -e
```
Add (runs hourly, 10 AM–4 PM IST, weekdays):
```
0 10-16 * * 1-5 cd ~/nifty500_screener && /usr/bin/python3 screener.py >> cron.log 2>&1
```
Also make sure cron itself is running (WSL doesn't start it automatically):
```bash
sudo service cron start
```

**More reliable: let Windows Task Scheduler launch WSL** for each run, so
you don't depend on WSL already being open. Follow the same Task Scheduler
steps as Section 3 above (10 AM start, repeat every 1 hour for 6 hours), but
in the **Actions tab**, instead of the `.bat` file use:
- Program/script: `wsl.exe`
- Add arguments:
  ```
  -d Ubuntu -e bash -c "cd ~/nifty500_screener && python3 screener.py >> cron.log 2>&1"
  ```
  (replace `Ubuntu` with your exact distro name from `wsl -l -v` in PowerShell)

---

## 5. Files in this project

| File | Purpose |
|---|---|
| `screener.py` | Main script — fetches data, applies strategy, sends Telegram alert |
| `config.py` | Your Telegram credentials and settings |
| `fetch_nifty500.py` | Pulls the current Nifty 500 symbol list from NSE |
| `stocks.csv` | Generated symbol list (edit manually if you want a custom universe) |
| `run_screener.bat` | Windows launcher for Task Scheduler |
| `screener.log` | Run log — check here if something goes wrong |

---

## 6. Known limitations & things to watch

- **Yahoo Finance 1h data history is limited** (~60 days via `yfinance`).
  Fine for this strategy since we only need the last ~25-30 candles to warm
  up the indicators, but don't expect to backtest years of 1h data this way.
- **"Crossover already active"** means EMA9 > EMA20 on the latest candle,
  regardless of when the actual cross happened. If you instead want to
  restrict to the day/week the cross occurred, that's a one-line change in
  `check_strategy()` — just ask.
- **Free data can lag or occasionally have gaps/errors** — this is not
  broker-grade data. For real trading decisions, cross-check flagged stocks
  on your broker terminal before acting.
- **Rate limiting**: if Yahoo starts blocking requests mid-run, increase
  `REQUEST_DELAY_SECONDS` in `config.py`.
- **This is a screener, not a trading bot** — it only sends you a list. No
  orders are placed. You still make the trade decisions.
