"""
database.py — работа с SQLite-базой данных history.db
Все функции, связанные с хранением и получением метрик арбитража.
"""

import aiosqlite
from datetime import datetime

from config import DB_PATH

# ─── Глобальное состояние модуля ──────────────────────────────────────────────
_db_initialized = False


# ─── Инициализация базы данных ────────────────────────────────────────────────

async def init_db():
    """
    Создаёт файл history.db и таблицу metrics при старте.
    Использует DB_PATH из config.py (относительный путь — база в корне проекта).
    """
    global _db_initialized
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                kgs_rate REAL NOT NULL,
                price_usdt REAL NOT NULL,
                weighted_price REAL NOT NULL,
                profit_pct_bep20 REAL NOT NULL
            )
        """)
        await db.commit()
    _db_initialized = True
    print(f"✅ База данных {DB_PATH} инициализирована")


def is_db_initialized():
    """Возвращает True, если база данных уже инициализирована."""
    return _db_initialized


# ─── Запись метрик ─────────────────────────────────────────────────────────────

async def save_metric(price_usdt, kgs_rate, weighted_price, profit_pct_bep20):
    """
    Сохраняет одну строку метрик в базу данных.

    Параметры:
        price_usdt       — текущая цена KGST в USDT
        kgs_rate         — курс USD → KGS
        weighted_price   — средняя взвешенная цена покупки (USDT)
        profit_pct_bep20 — профит в % (BEP-20)
    """
    timestamp = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO metrics (timestamp, kgs_rate, price_usdt, weighted_price, profit_pct_bep20) VALUES (?, ?, ?, ?, ?)",
            (timestamp, kgs_rate, price_usdt, weighted_price, profit_pct_bep20)
        )
        await db.commit()


# ─── Получение статистики ─────────────────────────────────────────────────────

async def get_max_profit():
    """
    Возвращает кортеж (timestamp, profit_pct_bep20) с максимальным профитом за всё время.
    Если данных нет — возвращает None.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT timestamp, profit_pct_bep20 FROM metrics ORDER BY profit_pct_bep20 DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            return row  # (timestamp, profit_pct_bep20) или None


async def get_recent_rows(limit=100):
    """
    Возвращает список последних записей в хронологическом порядке.
    Каждая запись — кортеж (timestamp, profit_pct_bep20).
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT timestamp, profit_pct_bep20 FROM metrics ORDER BY timestamp DESC LIMIT ?"
        ) as cursor:
            rows = await cursor.fetchall()
    rows.reverse()  # хронологический порядок
    return rows
