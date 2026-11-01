import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
import time
import os

import winsound

SOUND_FILE = "sound.wav"  # keep this in the same folder as your script

def play_order_sound():
    winsound.PlaySound(SOUND_FILE, winsound.SND_FILENAME)  # no ASYNC


# === CONFIG ===
LOGIN = 5045120579
SERVER = "MetaQuotes-Demo"
SYMBOL = "EURUSD"
VOLUME = 0.1
TIMEFRAME = mt5.TIMEFRAME_M5
INIT_CANDLES = 100

CANDLE_CSV = f"{SYMBOL}_M5_candles.csv"
TRADES_CSV = "trades_log.csv"

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
    """
    Try different filling modes until one works.
    """
    for fm in FILL_MODES_TRY:
        req = dict(request_base)
        req["type_filling"] = fm
        result = mt5.order_send(req)
        print(f"Try filling_mode={fm} -> retcode {result.retcode}, {result.comment}")
        if result.retcode != mt5.TRADE_RETCODE_INVALID_FILL:
            # any retcode other than invalid fill means this fill mode is accepted or another issue
            return result, fm
    return result, None  # all failed with invalid fill

# === ORDER HELPERS ===
def send_buy():
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        print("No tick data")
        return

    base_request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": VOLUME,
        "type": mt5.ORDER_TYPE_SELL,
        "price": tick.ask,
        "deviation": 50,
        "magic": 123456,
        "comment": "5m_buy_bot",
        "type_time": mt5.ORDER_TIME_GTC,
    }

    result, used_fill = send_order_with_fill(base_request)
    print("BUY final result:", result.retcode, result.comment, "| used fill:", used_fill)

    if result.retcode == mt5.TRADE_RETCODE_DONE:
        append_trade_log({
            "time": datetime.now(),
            "action": "OPEN",
            "ticket": result.order,
            "deal": result.deal,
            "type": "BUY",
            "symbol": SYMBOL,
            "volume": VOLUME,
            "price": result.price,
            "comment": f"entry_fill_{used_fill}",
            "profit": 0.0,
        })

def close_old_positions():
    now = datetime.now()
    positions = mt5.positions_get(symbol=SYMBOL)
    if positions is None:
        return
    for pos in positions:
        open_time = datetime.fromtimestamp(pos.time)
        if now - open_time >= timedelta(minutes=10):
            tick = mt5.symbol_info_tick(SYMBOL)
            if tick is None:
                continue
            price = tick.bid if pos.type == mt5.POSITION_TYPE_BUY else tick.ask

            base_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": pos.ticket,
                "symbol": SYMBOL,
                "volume": pos.volume,
                "type": mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                "price": price,
                "deviation": 50,
                "magic": 123456,
                "comment": "close_after_10m",
                "type_time": mt5.ORDER_TIME_GTC,
            }

            res, used_fill = send_order_with_fill(base_request)
            print(f"Close final result for {pos.ticket}:", res.retcode, res.comment, "| used fill:", used_fill)

            if res.retcode == mt5.TRADE_RETCODE_DONE:
                try:
                 play_order_sound()
                except RuntimeError as e:
                  print("Sound play failed:", e)

                append_trade_log({
                    "time": datetime.now(),
                    "action": "CLOSE",
                    "ticket": pos.ticket,
                    "deal": res.deal,
                    "type": "BUY" if pos.type == mt5.POSITION_TYPE_BUY else "SELL",
                    "symbol": SYMBOL,
                    "volume": pos.volume,
                    "price": res.price,
                    "comment": f"exit_10m_fill_{used_fill}",
                    "profit": pos.profit,
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

                # --- trading logic ---
                close_old_positions()
                send_buy()

        time.sleep(5)
except KeyboardInterrupt:
    print("Stopping bot...")

mt5.shutdown()
print("Disconnected.")
