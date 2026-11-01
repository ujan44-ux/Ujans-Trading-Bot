import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime
import time
import os


# === CONFIG ===
LOGIN = 101424503
SERVER = "MetaQuotes-Demo"
SYMBOL = "GBPUSD"  # Changed to GBPUSD
TIMEFRAME = mt5.TIMEFRAME_M5
INIT_CANDLES = 200


CANDLE_CSV = f"{SYMBOL}_M5_candles.csv"  # Will now be GBPUSD_M5_candles.csv
TRADES_CSV = "trades_log.csv"


# indicators / risk config (from backtest)
short_ema_period = 9
long_ema_period = 21
rsi_period = 14
bb_period = 20
bb_std = 2


# fraction of account equity to allocate per trade
allocation_fraction = 0.330  # 1.0 = 100%, 0.5 = 50%, etc.


# For GBPUSD: 1 lot = 100,000 GBP (standard forex contract size)
CONTRACT_SIZE = 100000.0  # Standard forex contract size


FILL_MODES_TRY = [
    mt5.ORDER_FILLING_RETURN,
    mt5.ORDER_FILLING_FOK,
    mt5.ORDER_FILLING_IOC,
]


# === INIT & LOGIN ===
if not mt5.initialize():
    print("MT5 init failed:", mt5.last_error())
    quit()


if not mt5.login(LOGIN, server=SERVER):
    print("Login failed:", mt5.last_error())
    mt5.shutdown()
    quit()


if not mt5.symbol_select(SYMBOL, True):
    print(f"Symbol select failed: {SYMBOL}")
    mt5.shutdown()
    quit()


info = mt5.symbol_info(SYMBOL)
if info is None:
    print("symbol_info failed:", mt5.last_error())
    mt5.shutdown()
    quit()


print("Connected to MT5")
print("Account:", mt5.account_info().login)
print("Server :", mt5.account_info().server)
print("Symbol :", SYMBOL)
print("Broker filling_mode flag:", info.filling_mode)


# === CANDLES: INITIAL 100 + CSV ===
print(f"Fetching last {INIT_CANDLES} M5 candles for {SYMBOL}...")
rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, INIT_CANDLES)
if rates is None or len(rates) == 0:
    print("Failed to fetch initial candles:", mt5.last_error())
    mt5.shutdown()
    quit()


candles_df = pd.DataFrame(rates)
candles_df["time"] = pd.to_datetime(candles_df["time"], unit="s")
candles_df.set_index("time", inplace=True)
candles_df.to_csv(CANDLE_CSV)
print(f"Saved {len(candles_df)} candles to {CANDLE_CSV}")


# === TRADE LOG HELPERS ===
def append_trade_log(row: dict):
    row_df = pd.DataFrame([row])
    if os.path.exists(TRADES_CSV):
        existing = pd.read_csv(TRADES_CSV)
        all_df = pd.concat([existing, row_df], ignore_index=True)
    else:
        all_df = row_df
    all_df.to_csv(TRADES_CSV, index=False)


# === ORDER SEND WITH FILLING FALLBACK ===
def send_order_with_fill(request_base):
    for fm in FILL_MODES_TRY:
        req = dict(request_base)
        req["type_filling"] = fm
        result = mt5.order_send(req)
        print(f"Try filling_mode={fm} -> retcode {result.retcode}, {result.comment}")
        if result.retcode != mt5.TRADE_RETCODE_INVALID_FILL:
            return result, fm
    return result, None


# === GET CURRENT OPEN POSITION STATE FOR SYMBOL ===
def get_position_state():
    """
    Returns (position_side, volume):
     0  = flat
     1  = net long
     -1 = net short
    Uses positions_get(symbol=SYMBOL).
    """
    positions = mt5.positions_get(symbol=SYMBOL)
    if positions is None or len(positions) == 0:
        return 0, 0.0

    net_volume = 0.0
    for pos in positions:
        if pos.type == mt5.POSITION_TYPE_BUY:
            net_volume += pos.volume
        elif pos.type == mt5.POSITION_TYPE_SELL:
            net_volume -= pos.volume

    if net_volume > 0:
        return 1, net_volume
    elif net_volume < 0:
        return -1, net_volume
    else:
        return 0, 0.0


# === COMPUTE INDICATORS ON CURRENT CSV DF ===
def compute_indicators(df):
    df = df.copy()
    df["ema_fast"] = df["close"].ewm(span=short_ema_period, adjust=False).mean()
    df["ema_slow"] = df["close"].ewm(span=long_ema_period, adjust=False).mean()

    delta = df["close"].diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    roll_up = up.rolling(rsi_period).mean()
    roll_down = down.rolling(rsi_period).mean()
    rs = roll_up / roll_down
    df["rsi"] = 100.0 - (100.0 / (1.0 + rs))

    ma = df["close"].rolling(window=bb_period).mean()
    std = df["close"].rolling(window=bb_period).std()
    df["bb_mid"] = ma
    df["bb_upper"] = ma + bb_std * std
    df["bb_lower"] = ma - bb_std * std

    return df


# === ENTRY LOGIC (NO EXITS) ===
def maybe_open_trade_from_signals():
    # read full candle history from CSV and recompute indicators
    df = pd.read_csv(CANDLE_CSV, index_col="time", parse_dates=True)
    df = compute_indicators(df)

    if len(df) < 2:
        return  # need at least 2 rows for cross detection

    row_prev = df.iloc[-2]
    row = df.iloc[-1]

    # skip if indicators not ready
    if (
        np.isnan(row_prev["ema_fast"]) or np.isnan(row_prev["ema_slow"])
        or np.isnan(row_prev["rsi"]) or np.isnan(row_prev["bb_lower"])
        or np.isnan(row_prev["bb_upper"])
    ):
        return

    crossed_up = (row_prev["ema_fast"] <= row_prev["ema_slow"]) and (row["ema_fast"] > row["ema_slow"])
    crossed_down = (row_prev["ema_fast"] >= row_prev["ema_slow"]) and (row["ema_fast"] < row["ema_slow"])

    price_near_lower = row["close"] <= row["bb_lower"] * 1.005
    price_near_upper = row["close"] >= row["bb_upper"] * 0.995
    rsi_ok = (row["rsi"] > 30) and (row["rsi"] < 70)

    position_side, _ = get_position_state()
    if position_side != 0:
        # already in net position; do nothing (no pyramiding)
        return

    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        print("No tick data for entry")
        return

    # determine side
    side = None
    price = None

    if crossed_up and rsi_ok and price_near_lower:
        side = "BUY"
        price = tick.ask
    elif crossed_down and rsi_ok and price_near_upper:
        side = "SELL"
        price = tick.bid

    if side is None or price is None:
        return  # no signal this bar

    # position sizing: equity * allocation_fraction / price -> units -> lots
    acc = mt5.account_info()
    if acc is None:
        print("Could not fetch account_info for sizing")
        return

    equity = acc.equity  # current equity
    capital_for_trade = equity * allocation_fraction
    units = capital_for_trade / price if price > 0 else 0.0
    lots = 0.5  # Standard forex sizing

    # respect broker min/step volume
    symbol_info = mt5.symbol_info(SYMBOL)
    if symbol_info is None:
        print("symbol_info is None during sizing")
        return

    min_lot = symbol_info.volume_min
    max_lot = symbol_info.volume_max
    step_lot = symbol_info.volume_step

    # round down to nearest step
    lots = max(min_lot, min(max_lot, lots))
    step_count = int(lots / step_lot)
    lots = 0.5

    if lots <= 0:
        print("Calculated lot size <= 0, skipping order")
        return

    order_type = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL

    base_request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": lots,
        "type": order_type,
        "price": price,
        "deviation": 50,
        "magic": 123456,
        "comment": "ema_rsi_bb_bot",
        "type_time": mt5.ORDER_TIME_GTC,
    }

    result, used_fill = send_order_with_fill(base_request)
    print(f"{side} final result:", result.retcode, result.comment, "| used fill:", used_fill)

    if result.retcode == mt5.TRADE_RETCODE_DONE:
        append_trade_log({
            "time": datetime.now(),
            "action": "OPEN",
            "ticket": result.order,
            "deal": result.deal,
            "type": side,
            "symbol": SYMBOL,
            "volume": lots,
            "price": result.price,
            "comment": f"entry_fill_{used_fill}",
            "profit": 0.0,
        })


# === MAIN LOOP: NEW M5 BAR HANDLING ===
last_bar_time = candles_df.index[-1]

print("Bot running on", SYMBOL, "Ctrl+C to stop.")
try:
    while True:
        latest = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, 1)
        if latest is not None and len(latest) > 0:
            bar = latest[0]
            bar_time = datetime.fromtimestamp(bar["time"])

            if bar_time > last_bar_time:
                last_bar_time = bar_time
                print("New M5 bar:", bar_time)

                # --- update candles CSV ---
                new_candle = {
                    "time": bar_time,
                    "open": bar["open"],
                    "high": bar["high"],
                    "low": bar["low"],
                    "close": bar["close"],
                    "tick_volume": bar["tick_volume"],
                    "spread": bar["spread"],
                    "real_volume": bar["real_volume"],
                }
                new_row_df = pd.DataFrame([new_candle]).set_index("time")

                existing_candles = pd.read_csv(CANDLE_CSV, index_col="time", parse_dates=True)
                updated_candles = pd.concat([existing_candles, new_row_df])
                updated_candles.to_csv(CANDLE_CSV)
                print(f"Appended candle, total rows: {len(updated_candles)}")

                # --- trading logic: ONLY entries based on EMA/RSI/BB, NO exits ---
                maybe_open_trade_from_signals()

        time.sleep(5)
except KeyboardInterrupt:
    print("Stopping bot...")

mt5.shutdown()
print("Disconnected.")
