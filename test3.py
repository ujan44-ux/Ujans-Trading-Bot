import pandas as pd
import numpy as np
import os
from decimal import Decimal, getcontext

getcontext().prec = 10

# ------------- CONFIG (XAUUSD SPOT) -------------
csv_path = "XAUUSD_M1_candles.csv"          # your XAUUSD M5 OHLC data
initial_capital = Decimal("5000.0")

lot_size = Decimal("0.01")                  # fixed lot size
contract_oz_per_lot = Decimal("100")
charges_roundtrip = Decimal("0.0")

# Support/Resistance Zone Parameters
zone_lookback = 50                          # bars to look back for S/R levels
zone_tolerance = Decimal("2.0")             # how close price must be to level (in points)
touch_count_min = 2                         # minimum touches to validate a level
zone_strength_period = 20                   # recent bars to check for level strength

tp_points = Decimal("8.0")                  # Take profit in points
sl_points = Decimal("5.0")                  # Stop loss in points

# Round number levels (psychological levels)
use_round_numbers = True
round_number_interval = 10                  # e.g., 2650, 2660, 2670

# RSI Filter (optional confluence)
use_rsi_filter = True
rsi_len = 14
rsi_oversold = 35
rsi_overbought = 65

# Volatility Filter (ATR)
atr_len = 14
min_atr = Decimal("0.5")                    # minimum volatility
max_atr = Decimal("20.0")                   # maximum volatility

# Session Filter
use_session_filter = True
session_start_hour = 7                      # inclusive
session_end_hour = 20                       # inclusive

TRADES_CSV = "xauusd_support_resistance_trades.csv"
EQUITY_CSV = "xauusd_support_resistance_equity.csv"
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
    "close": df["close"].astype(float),
    "high": df["high"].astype(float),
    "low": df["low"].astype(float)
})

# RSI (optional)
if use_rsi_filter:
    delta = ind["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(rsi_len).mean()
    avg_loss = loss.rolling(rsi_len).mean()
    rs = avg_gain / avg_loss
    ind["rsi"] = 100 - (100 / (1 + rs))
else:
    ind["rsi"] = 50  # neutral value

df = df.merge(
    ind[["timestamp", "rsi"]],
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
df["high_prev"] = df["high"].shift(1).astype(float)
df["low_prev"] = df["low"].shift(1).astype(float)
df["rsi_prev"] = df["rsi"].shift(1)

# ---------- SESSION FILTER ----------
df["hour"] = df["timestamp"].dt.hour
if use_session_filter:
    df["session_ok"] = (
        (df["hour"] >= session_start_hour) &
        (df["hour"] <= session_end_hour)
    )
else:
    df["session_ok"] = True

# ---------- SUPPORT/RESISTANCE DETECTION ----------
def find_support_resistance_levels(df_window, tolerance):
    """
    Identify S/R levels from swing highs/lows
    """
    levels = []
    
    highs = df_window["high"].astype(float).values
    lows = df_window["low"].astype(float).values
    
    # Find local swing highs (resistance)
    for i in range(2, len(highs) - 2):
        if (highs[i] > highs[i-1] and highs[i] > highs[i-2] and 
            highs[i] > highs[i+1] and highs[i] > highs[i+2]):
            levels.append(("resistance", float(highs[i])))
    
    # Find local swing lows (support)
    for i in range(2, len(lows) - 2):
        if (lows[i] < lows[i-1] and lows[i] < lows[i-2] and 
            lows[i] < lows[i+1] and lows[i] < lows[i+2]):
            levels.append(("support", float(lows[i])))
    
    return levels

def get_round_number_levels(current_price, interval, range_points=50):
    """
    Generate round number levels around current price
    """
    levels = []
    price_float = float(current_price)
    
    # Find nearest round number
    base = int(price_float / interval) * interval
    
    # Generate levels above and below
    for offset in range(-range_points, range_points + 1, interval):
        level = base + offset
        if abs(level - price_float) <= range_points:
            levels.append(level)
    
    return levels

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
            "capital_after": float(capital),
            "level_type": position.get("level_type", "unknown")
        })
        position = None
        equity.append(capital)
        equity_time.append(curr["timestamp"])
        continue

    # ---------- Entry signals using previous bar only ----------
    if pd.isna(curr["atr_prev"]) or i < zone_lookback:
        equity.append(capital)
        equity_time.append(curr["timestamp"])
        continue

    close_prev = curr["close_prev"]
    high_prev = curr["high_prev"]
    low_prev = curr["low_prev"]
    rsi_prev = curr["rsi_prev"]
    atr_prev = curr["atr_prev"]
    session_ok = curr["session_ok"]

    # Get historical data for S/R detection (no lookahead)
    lookback_data = df.iloc[max(0, i - zone_lookback):i].copy()
    
    # Find S/R levels
    sr_levels = find_support_resistance_levels(lookback_data, float(zone_tolerance))
    
    # Add round number levels if enabled
    all_levels = []
    if use_round_numbers:
        round_levels = get_round_number_levels(close_prev, round_number_interval)
        for level in round_levels:
            all_levels.append(("round_support", level))
            all_levels.append(("round_resistance", level))
    
    all_levels.extend(sr_levels)

    # Volatility filter
    vol_ok = (
        Decimal(str(atr_prev)) >= min_atr and
        Decimal(str(atr_prev)) <= max_atr
    )

    # RSI filter
    if use_rsi_filter:
        rsi_long_ok = rsi_prev < rsi_oversold
        rsi_short_ok = rsi_prev > rsi_overbought
    else:
        rsi_long_ok = True
        rsi_short_ok = True

    # Check if price is near any support/resistance level
    long_signal = False
    short_signal = False
    triggered_level_type = None

    for level_type, level_price in all_levels:
        price_diff = abs(float(close_prev) - level_price)
        
        # Near support - potential bounce (long)
        if ("support" in level_type and 
            price_diff <= float(zone_tolerance) and
            float(close_prev) >= level_price - float(zone_tolerance) and
            session_ok and vol_ok and rsi_long_ok):
            long_signal = True
            triggered_level_type = f"{level_type}@{level_price:.1f}"
            break
        
        # Near resistance - potential rejection (short)
        if ("resistance" in level_type and 
            price_diff <= float(zone_tolerance) and
            float(close_prev) <= level_price + float(zone_tolerance) and
            session_ok and vol_ok and rsi_short_ok):
            short_signal = True
            triggered_level_type = f"{level_type}@{level_price:.1f}"
            break

    if long_signal:
        position = {
            "side": "long",
            "entry_price": curr["open"],
            "entry_time": curr["timestamp"],
            "level_type": triggered_level_type
        }
    elif short_signal:
        position = {
            "side": "short",
            "entry_price": curr["open"],
            "entry_time": curr["timestamp"],
            "level_type": triggered_level_type
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
        "capital_after": float(capital),
        "level_type": position.get("level_type", "unknown")
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
    print(f"SUPPORT/RESISTANCE ZONE TRADING BACKTEST - XAUUSD")
    print(f"{'='*60}")
    print(f"Initial capital: ${initial_capital}")
    print(f"Lot size: {lot_size} | Contract: {contract_oz_per_lot} oz/lot")
    print(f"Zone lookback: {zone_lookback} bars | Tolerance: {zone_tolerance} pts")
    if use_round_numbers:
        print(f"Round numbers: Every {round_number_interval} pts")
    if use_rsi_filter:
        print(f"RSI: Oversold < {rsi_oversold} | Overbought > {rsi_overbought}")
    print(f"TP: {tp_points} pts | SL: {sl_points} pts")
    if use_session_filter:
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
    print("\nLevel Types Traded:")
    if "level_type" in trades_df.columns:
        print(trades_df["level_type"].value_counts())
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