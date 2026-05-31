"""
engine.py — ядро расчётов проекта KGST Monitor
Содержит логику получения курса KGS, расчёт средней цены из стакана
и расчёт профита для мульти-объёмов.
"""

import ccxt
import requests
from bs4 import BeautifulSoup

from config import (
    AKCHABAR_URL,
    DEFAULT_KGS_RATE,
    FEE_TRC20,
    FEE_BEP20,
    VOLUMES_KGS,
)


# ─── Парсинг курса USD (KGS) ─────────────────────────────────────────────────

def fetch_usd_rate():
    """
    Получает средний курс продажи доллара с akchabar.kg.
    Возвращает float или None при ошибке.
    """
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(AKCHABAR_URL, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Ищем значения курсов продажи на странице
        sell_values = []
        for tag in soup.find_all(string=True):
            text = tag.strip().replace(",", ".")
            try:
                value = float(text)
                # Отфильтровываем разумные значения курса USD (50–200 KGS)
                if 50 < value < 200:
                    sell_values.append(value)
            except (ValueError, TypeError):
                continue

        if not sell_values:
            return None

        avg_rate = sum(sell_values) / len(sell_values)
        return round(avg_rate, 2)

    except Exception as e:
        print(f"⚠️  Ошибка при получении курса USD: {e}")
        return None


# ─── Получение стакана ордеров ──────────────────────────────────────────────

def fetch_order_book(symbol="KGST/USDT"):
    """
    Получает стакан ордеров с биржи HTX.
    Возвращает словарь order_book (формат ccxt) или None при ошибке.
    """
    try:
        htx = ccxt.htx()
        order_book = htx.fetch_order_book(symbol)
        return order_book
    except Exception as e:
        print(f"❌ Ошибка получения стакана с HTX: {e}")
        return None


# ─── Средняя цена покупки по стакану ────────────────────────────────────────

def get_weighted_price(order_book, volume_kgs):
    """
    Считает среднюю цену покупки для заданного объёма KGS.

    order_book — словарь с ключами 'bids' и 'asks' (формат ccxt):
        [[price, amount], [price, amount], ...]
        asks — ордера на продажу (нас интересуют они)
    volume_kgs — объём в KGS, который нужно купить.

    Возвращает float — средняя взвешенная цена закупки (USDT за KGST).
    Если объём не закрыт полностью — возвращает частично закрытую цену.
    """
    asks = order_book.get("asks", [])
    remaining = volume_kgs
    total_cost = 0.0

    for price, amount in asks:
        if remaining <= 0:
            break
        filled = min(remaining, amount)
        total_cost += filled * price
        remaining -= filled

    return total_cost / (volume_kgs - remaining) if remaining < volume_kgs else 0.0


# ─── Расчёт профита ──────────────────────────────────────────────────────────

def calculate_kgs(price_usdt, kgs_rate):
    """Конвертирует цену из USDT в KGS."""
    return price_usdt * kgs_rate


def calculate_profit(price_kgst_usdt, kgs_rate, investment_kgs):
    """
    Рассчитывает профит арбитража для заданной суммы в KGS.

    Логика:
    1. Конвертируем KGS → USDT по текущему курсу обменника.
    2. Покупаем KGST на бирже за USDT.
    3. Продаём KGST за KGS (1 KGST = 1 KGS по номиналу).
    4. Вычитаем комиссию сети за вывод USDT.

    Возвращает dict с результатами для TRC-20 и BEP-20.
    """
    # Шаг 1: Конвертируем сомы в USDT
    investment_usdt = investment_kgs / kgs_rate

    # Шаг 2: Покупаем KGST за USDT на бирже
    kgst_amount = investment_usdt / price_kgst_usdt

    # Шаг 3: Продаём KGST за сомы (1 KGST ≈ 1 KGS по номиналу)
    received_kgs = kgst_amount  # 1 KGST = 1 KGS

    # Шаг 4: Вычитаем комиссию сети (конвертируем комиссию USDT → KGS)
    fee_trc20_kgs = FEE_TRC20 * kgs_rate
    fee_bep20_kgs = FEE_BEP20 * kgs_rate

    profit_trc20 = received_kgs - investment_kgs - fee_trc20_kgs
    profit_bep20 = received_kgs - investment_kgs - fee_bep20_kgs

    profit_pct_trc20 = (profit_trc20 / investment_kgs) * 100
    profit_pct_bep20 = (profit_bep20 / investment_kgs) * 100

    return {
        "investment_kgs": investment_kgs,
        "investment_usdt": round(investment_usdt, 2),
        "kgst_amount": round(kgst_amount, 2),
        "received_kgs": round(received_kgs, 2),
        "fee_trc20_kgs": round(fee_trc20_kgs, 2),
        "fee_bep20_kgs": round(fee_bep20_kgs, 2),
        "profit_trc20": round(profit_trc20, 2),
        "profit_bep20": round(profit_bep20, 2),
        "profit_pct_trc20": round(profit_pct_trc20, 2),
        "profit_pct_bep20": round(profit_pct_bep20, 2),
    }


# ─── Мульти-объёмный расчёт ──────────────────────────────────────────────────

def calculate_multi_profit(order_book, kgs_rate):
    """
    Рассчитывает профит для всех объёмов из VOLUMES_KGS.
    
    order_book — стакан ордеров (формат ccxt).
    kgs_rate — текущий курс USD → KGS.
    
    Возвращает dict: { volume_kgs: {
        "weighted_price": float,
        "price_kgs": float,
        "profit": dict (результат calculate_profit)
    }}
    """
    results = {}
    for vol in VOLUMES_KGS:
        weighted_price = get_weighted_price(order_book, vol)
        if weighted_price > 0:
            price_kgs = calculate_kgs(weighted_price, kgs_rate)
            profit = calculate_profit(weighted_price, kgs_rate, vol)
            results[vol] = {
                "weighted_price": weighted_price,
                "price_kgs": price_kgs,
                "profit": profit,
            }
    return results
