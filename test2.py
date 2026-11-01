import pandas as pd
import numpy as np
import os
from decimal import Decimal, getcontext

getcontext().prec = 10

# ------------- CONFIG (XAUUSD SPOT) -------------
csv_path = "XAUUSD_M5_candles.csv"          # your XAUUSD M5 OHLC data
initial_capital = Decimal("5000.0")

lot_size = Decimal("0.10")                  # fixed lot size
contract_oz_per_lot = Decimal("100")
charges_roundtrip = Decimal("0.0")

# Bollinger Band Parameters
bb_period = 20                               # Bollinger Band period
bb_std_dev = 2.0                            # Standard deviations
tp_points = Decimal("8.0")                  # Take profit in points
sl_points = Decimal("5.0")                  # Stop loss in points

# RSI Filter
rsi_len = 14
rsi_oversold = 30                           # RSI threshold for long entries
rsi_overbought = 70                         # RSI threshold for short entries

# Volatility Filter (ATR)
atr_len = 14
min_atr = Decimal("0.5")                    # minimum volatility
max_atr = Decimal("20.0")                   # maximum volatility

# Session Filter
session_start_hour = 7                      # inclusive (e.g., 7 AM)
session_end_hour = 20                       # inclusive (e.g., 8 PM)

TRADES_CSV = "xauusd_bollinger_trades.csv"
EQUITY_CSV = "xauusd_bollinger_equity.csv"
# -----------------------------------------------

if not os.path.exists(csv_path):
    raise FileNotFoundError(f"CSV not found: {csv_path}")

df = pd.read_csv(csv_path, dtype=str)
df["timestamp"] = pd.to_datetime(df["time"])

for c in ["open", "high", "low", "close"]:
    df[c] = df[c].apply(lambda x: Decimal(str(x)))

df = df.sort_values("timestamp").reset_index(drop=True)

# ---------- INDICATORS ----------
ind = pd.DataFrame({
    "timestamp": df["timestamp"],
    "close": df["close"].astype(float)
})

# Bollinger Bands
ind["bb_middle"] = ind["close"].rolling(bb_period).mean()
bb_std = ind["close"].rolling(bb_period).std()
ind["bb_upper"] = ind["bb_middle"] + (bb_std_dev * bb_std)
ind["bb_lower"] = ind["bb_middle"] - (bb_std_dev * bb_std)

# RSI
delta = ind["close"].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.rolling(rsi_len).mean()
avg_loss = loss.rolling(rsi_len).mean()
rs = avg_gain / avg_loss
ind["rsi"] = 100 - (100 / (1 + rs))

df = df.merge(
    ind[["timestamp", "bb_middle", "bb_upper", "bb_lower", "rsi"]],
    on="timestamp",
    how="left"
)

# ---------- ATR / VOLATILITY ----------
tr1 = (df["high"] - df["low"]).astype(float)
tr2 = (df["high"] - df["close"].shift(1)).abs().astype(float)
tr3 = (df["low"] - df["close"].shift(1)).abs().astype(float)
df["tr"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
df["atr"] = df["tr"].rolling(atr_len).mean()
df["atr_prev"] = df["atr"].shift(1)

# ---------- NO-LOOKAHEAD SHIFT ----------
df["close_prev"] = df["close"].shift(1).astype(float)
df["bb_upper_prev"] = df["bb_upper"].shift(1)
df["bb_lower_prev"] = df["bb_lower"].shift(1)
df["bb_middle_prev"] = df["bb_middle"].shift(1)
df["rsi_prev"] = df["rsi"].shift(1)

# ---------- SESSION FILTER ----------
df["hour"] = df["timestamp"].dt.hour
df["session_ok"] = (
    (df["hour"] >= session_start_hour) &
    (df["hour"] <= session_end_hour)
)

capital = initial_capital
equity = [capital]
equity_time = [df.loc[0, "timestamp"]]
position = None
trades = []

for i in range(1, len(df)):
    curr = df.loc[i]

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
    if (
        pd.isna(curr["bb_upper_prev"]) or pd.isna(curr["bb_lower_prev"]) or
        pd.isna(curr["rsi_prev"]) or pd.isna(curr["atr_prev"])
    ):
        equity.append(capital)
        equity_time.append(curr["timestamp"])
        continue

    close_prev = curr["close_prev"]
    bb_upper_prev = curr["bb_upper_prev"]
    bb_lower_prev = curr["bb_lower_prev"]
    bb_middle_prev = curr["bb_middle_prev"]
    rsi_prev = curr["rsi_prev"]
    atr_prev = curr["atr_prev"]
    session_ok = curr["session_ok"]

    # Volatility filter
    vol_ok = (
        Decimal(str(atr_prev)) >= min_atr and
        Decimal(str(atr_prev)) <= max_atr
    )

    # Bollinger Band mean reversion signals
    # Long: price touched lower band + RSI oversold
    long_signal = (
        session_ok and
        vol_ok and
        close_prev <= bb_lower_prev and
        rsi_prev < rsi_oversold
    )

    # Short: price touched upper band + RSI overbought
    short_signal = (
        session_ok and
        vol_ok and
        close_prev >= bb_upper_prev and
        rsi_prev > rsi_overbought
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

    print(f"\n{'='*60}")
    print(f"BOLLINGER BAND MEAN REVERSION BACKTEST - XAUUSD")
    print(f"{'='*60}")
    print(f"Initial capital: ${initial_capital}")
    print(f"Lot size: {lot_size} | Contract: {contract_oz_per_lot} oz/lot")
    print(f"BB Period: {bb_period} | Std Dev: {bb_std_dev}")
    print(f"RSI: Oversold < {rsi_oversold} | Overbought > {rsi_overbought}")
    print(f"TP: {tp_points} pts | SL: {sl_points} pts")
    print(f"Session: {session_start_hour}:00 - {session_end_hour}:00")
    print(f"ATR Filter: {min_atr} - {max_atr}")
    print(f"{'='*60}")
    print(f"Final capital:   ${capital}")
    print(f"Net P&L:         ${total_pnl:.2f}")
    print(f"Return:          {((float(capital) / float(initial_capital)) - 1) * 100:.2f}%")
    print(f"Trades:          {len(trades_df)}")
    print(f"Win rate:        {win_rate:.1f}%")
    print(f"Average P&L:     ${avg_pnl:.2f}")
    print(f"Max Drawdown:    ${max_dd:.2f}")
    print(f"{'='*60}\n")
    print("Exit Reasons:")
    print(trades_df["exit_reason"].value_counts())
    print("\nFirst 10 Trades:")
    print(trades_df.head(10).to_string(index=False))
    print("\nLast 10 Trades:")
    print(trades_df.tail(10).to_string(index=False))

    trades_df.to_csv(TRADES_CSV, index=False)
    equity_df.to_csv(EQUITY_CSV, index=False)
    print(f"\n✓ Saved trades to {TRADES_CSV}")
    print(f"✓ Saved equity curve to {EQUITY_CSV}")
else:
    print("No trades executed — check conditions or data.")