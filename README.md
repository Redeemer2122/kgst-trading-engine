# KGST Arbitrage Monitor

> A modular, async Python engine for real-time KGST/USDT arbitrage monitoring on HTX Exchange — with Telegram alerts, multi-volume profit analysis, and persistent SQLite history.

---

## Overview

**KGST Arbitrage Monitor** tracks the price of KGST/USDT on [HTX Exchange](https://www.htx.com/) and calculates real-time arbitrage profitability against the Kyrgyzstani Som (KGS). It fetches live USD/KGS exchange rates, reads the live order book, computes weighted-average purchase prices across multiple capital volumes, and fires Telegram alerts the moment a profit threshold is crossed.

Designed for reliability: fully async, gracefully handles API failures, logs everything to disk, and stores a complete profit history in SQLite for charting and statistical review.

---

## Key Features

| Feature | Details |
|---|---|
| **Real-time order book** | Reads live `KGST/USDT` asks from HTX via `ccxt` |
| **Live USD/KGS rate** | Scraped from [akchabar.kg](https://www.akchabar.kg) every 5 minutes |
| **Multi-volume analysis** | Computes weighted prices for 2,000 / 15,000 / 50,000 KGS simultaneously |
| **Network fee modelling** | Deducts TRC-20 (1.0 USDT) and BEP-20 (0.3 USDT) fees from profit |
| **Telegram bot** | Commands for status, stats, chart, logs, and ping |
| **Smart alerts** | Fires when BEP-20 profit ≥ threshold; 10-minute cooldown prevents spam |
| **SQLite history** | Every tick saved to `history.db` for trend analysis |
| **Profit chart** | `/graph` command renders a matplotlib chart of the last 100 data points |
| **Structured logging** | Dual output: console + `bot.log` (UTF-8, timestamped) |

---

## Architecture

The project is intentionally split into four focused modules with zero circular dependencies.

```
monitor.py      ← Entry point: async event loop, Telegram bot, console display
    │
    ├── config.py    ← All constants and environment variables (single source of truth)
    ├── engine.py    ← Data fetching and profit calculation logic (pure functions)
    └── database.py  ← SQLite read/write layer (aiosqlite, async)
```

### Module Responsibilities

| File | Role |
|---|---|
| `monitor.py` | Boots the `asyncio` event loop, runs the polling loop, handles Telegram command routing and chart generation |
| `config.py` | Centralises every tunable constant — thresholds, intervals, fees, volumes, paths |
| `engine.py` | Stateless calculation core: fetches the order book, parses USD rates, computes weighted prices and multi-volume profit |
| `database.py` | Async SQLite interface: schema init, metric persistence, `get_max_profit`, `get_recent_rows` |

---

## Profit Calculation Logic

For each configured volume (in KGS):

```
1. Convert KGS → USDT  (using live USD/KGS rate)
2. Buy KGST on HTX     (weighted-average price from order book)
3. Redeem KGST → KGS   (1 KGST = 1 KGS at nominal value)
4. Subtract network fee (TRC-20 or BEP-20, converted to KGS)
5. Profit % = (received_KGS − invested_KGS − fee_KGS) / invested_KGS × 100
```

---

## Telegram Bot Commands

| Command | Description |
|---|---|
| `/start` | Welcome message and feature overview |
| `/status` | Live snapshot: current price, rate, and multi-volume profit table |
| `/stats` | Historical maximum profit and timestamp |
| `/graph` | PNG chart of profit % for the last 100 recorded ticks |
| `/logs` | Last 20 lines from `bot.log` |
| `/ping` | Health check — confirms the bot is alive |
| `/help` | Full command reference |

---

## Quick Start

### 1. Clone & set up the virtual environment

```bash
git clone https://github.com/your-username/kgst-monitor.git
cd kgst-monitor

python -m venv venv

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# macOS / Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

<details>
<summary>Expected dependencies</summary>

```
aiogram
ccxt
requests
beautifulsoup4
aiosqlite
python-dotenv
python-telegram-bot>=20.0
matplotlib
```

</details>

### 3. Configure secrets via `.env`

Create a `.env` file in the project root (never commit this file):

```bash
cp .env.example .env
```

Edit `.env`:

```env
TELEGRAM_TOKEN=your_bot_token_from_BotFather
TELEGRAM_CHAT_ID=your_chat_id
```

> **Getting your Chat ID:** Send any message to your bot, then open  
> `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` and look for `"chat":{"id": ...}`.

### 4. (Optional) Tune constants in `config.py`

| Constant | Default | Description |
|---|---|---|
| `PROFIT_ALERT_THRESHOLD_PCT` | `1.0` | Minimum BEP-20 profit % to trigger an alert |
| `ALERT_COOLDOWN` | `600` s | Minimum gap between consecutive alerts |
| `PRICE_UPDATE_INTERVAL` | `30` s | Order book polling frequency |
| `RATE_UPDATE_INTERVAL` | `300` s | USD/KGS rate refresh frequency |
| `VOLUMES_KGS` | `[2000, 15000, 50000]` | Capital amounts to analyse simultaneously |
| `FEE_TRC20` | `1.0` USDT | TRC-20 withdrawal fee |
| `FEE_BEP20` | `0.3` USDT | BEP-20 withdrawal fee |
| `DEFAULT_KGS_RATE` | `89.5` | Fallback rate used if scraping fails on first boot |

### 5. Run

```bash
python monitor.py
```

The bot will initialise the database, fetch the current USD/KGS rate, and begin polling HTX every 30 seconds. All activity is logged to the console and `bot.log`.

---

## File Structure

```
kgst-monitor/
│
├── monitor.py          # Application entry point & Telegram bot
├── engine.py           # Order book fetching & profit calculation
├── database.py         # SQLite schema, writes, and reads
├── config.py           # All configuration constants
│
├── .env                # Secrets (not committed — see .env.example)
├── .env.example        # Template for environment variables
├── requirements.txt    # Python dependencies
│
├── history.db          # Auto-created SQLite database (runtime)
└── bot.log             # Auto-created rotating log file (runtime)
```

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_TOKEN` | Yes | Bot token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | Yes | Target chat ID for alerts and commands |

Both variables must be set in `.env`. The bot runs in console-only mode (no Telegram) if either is missing.

---

## Development Notes

- **Python:** 3.13.5+
- **Concurrency:** Fully `asyncio`-based; blocking I/O (ccxt, requests) is offloaded via `run_in_executor`
- **Encoding:** Strict UTF-8 throughout — stdout, stderr, and `bot.log`
- **Security:** No credentials in source code; all secrets loaded exclusively from `.env`
- **Database:** `aiosqlite` ensures the SQLite layer never blocks the event loop
- **Resilience:** All external calls (`fetch_order_book`, `fetch_usd_rate`) are wrapped in `try/except` with logged fallbacks

---

## License

MIT — see `LICENSE` for details.
