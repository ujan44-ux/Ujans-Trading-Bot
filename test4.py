import pandas as pd
import numpy as np
import os
from decimal import Decimal, getcontext

getcontext().prec = 10

# ------------- CONFIG (XAUUSD SPOT) -------------
csv_path = "XAUUSD_M5_candles.csv"          # your XAUUSD M5 OHLC data
initial_capital = Decimal("5000.0")

lot_size = Decimal("0.15")          # fixed lot size
contract_oz_per_lot = Decimal("100")
charges_roundtrip = Decimal("0.0")

# Best parameters from grid
tp_points = Decimal("10.0")
sl_points = Decimal("0.25")
fast_ema = 8
slow_ema = 13
signal_ema = 5
rsi_len = 14
rsi_long_thresh = 52
rsi_short_thresh = 42

TRADES_CSV = "xauusd_momentum_best_trades.csv"
EQUITY_CSV = "xauusd_momentum_best_equity.csv"
# -----------------------------------------------

if not os.path.exists(csv_path):
    raise FileNotFoundError(f"CSV not found: {csv_path}")

df = pd.read_csv(csv_path, dtype=str)
df["timestamp"] = pd.to_datetime(df["datetime"])

for c in ["open", "high", "low", "close"]:
    df[c] = df[c].apply(lambda x: Decimal(str(x)))

df = df.sort_values("timestamp").reset_index(drop=True)

# ---------- INDICATORS ----------
ind = pd.DataFrame({
    "timestamp": df["timestamp"],
    "close": df["close"].astype(float)
})

ind["ema_fast"] = ind["close"].ewm(span=fast_ema, adjust=False).mean()
ind["ema_slow"] = ind["close"].ewm(span=slow_ema, adjust=False).mean()
ind["macd"] = ind["ema_fast"] - ind["ema_slow"]
ind["macd_signal"] = ind["macd"].ewm(span=signal_ema, adjust=False).mean()

delta = ind["close"].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.rolling(rsi_len).mean()
avg_loss = loss.rolling(rsi_len).mean()
rs = avg_gain / avg_loss
ind["rsi"] = 100 - (100 / (1 + rs))

df = df.merge(
    ind[["timestamp", "ema_fast", "ema_slow", "macd", "macd_signal", "rsi"]],
    on="timestamp",
    how="left"
)

# ---------- NO-LOOKAHEAD SHIFT ----------
df["macd_prev"] = df["macd"].shift(1)
df["macd_signal_prev"] = df["macd_signal"].shift(1)
df["rsi_prev"] = df["rsi"].shift(1)
df["ema_fast_prev"] = df["ema_fast"].shift(1)
df["ema_slow_prev"] = df["ema_slow"].shift(1)
df["close_prev"] = df["close"].shift(1)

capital = initial_capital
equity = [capital]
equity_time = [df.loc[0, "timestamp"]]
position = None
trades = []

for i in range(1, len(df)):
    curr = df.loc[i]
    time = curr["timestamp"].time()

    # Trading hours
    if not (pd.to_datetime("09:00").time() <= time <= pd.to_datetime("23:00").time()):
        equity.append(capital)
        equity_time.append(curr["timestamp"])
        continue

    # ---------- Manage open position ----------
    if position is not None:
        side = position["side"]
        entry_price = position["entry_price"]

        tp = entry_price + tp_points if side == "long" else entry_price - tp_points
        sl = entry_price - sl_points if side == "long" else entry_price + sl_points

        hit_target = (side == "long" and curr["high"] >= tp) or (side == "short" and curr["low"] <= tp)
        hit_stop   = (side == "long" and curr["low"] <= sl) or (side == "short" and curr["high"] >= sl)

        if hit_stop and hit_target:
            exit_price, reason = sl, "stop_loss (both hit)"
        elif hit_target:
            exit_price, reason = tp, "target"
        elif hit_stop:
            exit_price, reason = sl, "stop_loss"
        else:
            equity.append(capital)
            equity_time.append(curr["timestamp"])
            continue

        price_move = (exit_price - entry_price) if side == "long" else (entry_price - exit_price)
        pnl = price_move * lot_size * contract_oz_per_lot
        pnl -= charges_roundtrip
        capital += pnl

        trades.append({
            "entry_time": position["entry_time"],
            "exit_time": curr["timestamp"],
            "side": side,
            "entry_price": float(entry_price),
            "exit_price": float(exit_price),
            "pnl": float(pnl),
            "exit_reason": reason,
            "capital_after": float(capital)
        })
        position = None
        equity.append(capital)
        equity_time.append(curr["timestamp"])
        continue

    # ---------- Entry signals using previous bar only ----------
    if pd.isna(curr["macd_prev"]) or pd.isna(curr["macd_signal_prev"]) or pd.isna(curr["rsi_prev"]):
        equity.append(capital)
        equity_time.append(curr["timestamp"])
        continue

    macd_prev = curr["macd_prev"]
    macd_signal_prev = curr["macd_signal_prev"]
    rsi_prev = curr["rsi_prev"]
    ema_fast_prev = curr["ema_fast_prev"]
    close_prev = curr["close_prev"]

    macd_bullish_prev = macd_prev > macd_signal_prev
    macd_bearish_prev = macd_prev < macd_signal_prev

    macd_long_ok = macd_bullish_prev
    macd_short_ok = macd_bearish_prev

    long_trend_ok = float(close_prev) > ema_fast_prev
    short_trend_ok = float(close_prev) < ema_fast_prev

    long_signal = (
        macd_long_ok and
        (rsi_prev >= rsi_long_thresh) and
        long_trend_ok
    )

    short_signal = (
        macd_short_ok and
        (rsi_prev <= rsi_short_thresh) and
        short_trend_ok
    )

    if long_signal:
        position = {
            "side": "long",
            "entry_price": curr["open"],
            "entry_time": curr["timestamp"]
        }
    elif short_signal:
        position = {
            "side": "short",
            "entry_price": curr["open"],
            "entry_time": curr["timestamp"]
        }

    equity.append(capital)
    equity_time.append(curr["timestamp"])

# ---------- End-of-data close ----------
if position is not None:
    last_price = df.iloc[-1]["close"]
    side = position["side"]
    entry_price = position["entry_price"]
    price_move = (last_price - entry_price) if side == "long" else (entry_price - last_price)
    pnl = price_move * lot_size * contract_oz_per_lot - charges_roundtrip
    capital += pnl
    trades.append({
        "entry_time": position["entry_time"],
        "exit_time": df.iloc[-1]["timestamp"],
        "side": side,
        "entry_price": float(entry_price),
        "exit_price": float(last_price),
        "pnl": float(pnl),
        "exit_reason": "eod_close",
        "capital_after": float(capital)
    })

# ------------- SUMMARY & CSV OUTPUT -------------
trades_df = pd.DataFrame(trades)
equity_df = pd.DataFrame({
    "timestamp": equity_time,
    "equity": [float(x) for x in equity]
})

if not trades_df.empty:
    total_pnl = trades_df["pnl"].sum()
    win_rate = 100 * (trades_df["pnl"] > 0).sum() / len(trades_df)
    avg_pnl = trades_df["pnl"].mean()
    dd = pd.Series(equity) - pd.Series(equity).cummax()
    max_dd = dd.min()

    print(f"Initial capital: ${initial_capital}")
    print(f"Lot size: {lot_size} | Contract: {contract_oz_per_lot} oz/lot")
    print(f"Final capital:   ${capital}")
    print(f"Net P&L:         ${total_pnl:.2f}")
    print(f"Trades:          {len(trades_df)}")
    print(f"Win rate:        {win_rate:.1f}%")
    print(f"Average P&L:     ${avg_pnl:.2f}")
    print(f"Max Drawdown:    ${max_dd}\n")
    print("Exit Reasons:\n", trades_df["exit_reason"].value_counts())
    print("\nSample Trades:\n", trades_df.head(10))

    trades_df.to_csv(TRADES_CSV, index=False)
    equity_df.to_csv(EQUITY_CSV, index=False)
    print(f"\nSaved trades to {TRADES_CSV}")
    print(f"Saved equity curve to {EQUITY_CSV}")
else:
    print("No trades executed — check conditions or data / hours.")
