"""
4-Hour Range Breakout Scalping Backtest
=========================================
Strategy (from the source video):

1. Mark the first 4H candle of the day (New York time). Its high/low
   become the day's "range" (only valid after the candle fully closes).
2. On the 5-minute chart, wait for a candle to CLOSE outside the range
   (wicks don't count).
3. Wait for a later 5-minute candle to CLOSE back inside the range
   (this confirms the breakout-retest setup).
4. Enter on the NEXT 5-minute candle's open:
     - Broke above range high, then closed back inside -> SHORT
     - Broke below range low,  then closed back inside -> LONG
5. Stop loss = the breakout extreme (range high for shorts, range low
   for longs). Take profit = 2x the stop-loss distance (2R).
6. Only trade setups that occur on the same calendar day as the range
   candle. Multiple trades per day are allowed.

Input data required
--------------------
A 5-minute OHLC CSV with at least the columns: time, open, high, low, close
Timestamps should be timezone-aware or convertible to New York time (the
script assumes the input "time" column is in UTC unless you change
SOURCE_TZ below).

Output
------
- trades CSV (every trade with entry/exit/pnl)
- equity curve CSV
- daily / monthly PnL CSVs
- console summary + matplotlib charts
"""

import pandas as pd
import numpy as np
import os
from decimal import Decimal, getcontext
import matplotlib.pyplot as plt

getcontext().prec = 10

# ------------- CONFIG -------------
csv_path = "XAUUSD_M5_candles.csv"          # your 5-minute OHLC data (time, open, high, low, close)
initial_capital = Decimal("5000.0")

# Position sizing (kept simple / fixed size; adjust for your instrument)
units_per_trade = Decimal("1.0")     # e.g. lots, contracts, or coins depending on instrument
point_value = Decimal("1.0")         # $ value of 1 price unit move per unit_per_trade

# Trading costs
spread_points = Decimal("0.0")       # ask - bid in price units, set per instrument
commission_per_trade = Decimal("0.0")

# Strategy params
RANGE_CANDLE_HOURS = 4               # first 4H candle of the day
RR_MULTIPLE = Decimal("2.0")         # take profit = 2x stop-loss distance
SOURCE_TZ = "UTC"                    # timezone of the "time" column in your CSV
NY_TZ = "America/New_York"

TRADES_CSV = "range_breakout_trades.csv"
EQUITY_CSV = "range_breakout_equity.csv"
DAILY_PNL_CSV = "range_breakout_daily_pnl.csv"
MONTHLY_PNL_CSV = "range_breakout_monthly_pnl.csv"
# -----------------------------------------------

if not os.path.exists(csv_path):
    raise FileNotFoundError(f"CSV not found: {csv_path}")

df = pd.read_csv(csv_path, dtype=str)
df["timestamp"] = pd.to_datetime(df["time"])

# localize/convert to New York time so the "first 4H candle of the day" is correct
if df["timestamp"].dt.tz is None:
    df["timestamp"] = df["timestamp"].dt.tz_localize(SOURCE_TZ)
df["timestamp"] = df["timestamp"].dt.tz_convert(NY_TZ)

for c in ["open", "high", "low", "close"]:
    df[c] = df[c].apply(lambda x: Decimal(str(x)))

df = df.sort_values("timestamp").reset_index(drop=True)
df["ny_date"] = df["timestamp"].dt.date
df["ny_hour"] = df["timestamp"].dt.hour

# ---------- BUILD THE FIRST 4H RANGE PER DAY ----------
# The first 4H candle spans [00:00, 04:00) New York time.
range_rows = df[df["ny_hour"] < RANGE_CANDLE_HOURS]
day_ranges = (
    range_rows.groupby("ny_date")
    .agg(range_high=("high", "max"), range_low=("low", "min"))
    .reset_index()
)
day_ranges_map = day_ranges.set_index("ny_date")[["range_high", "range_low"]].to_dict("index")

# The range is only "valid" (known) once the clock reaches 04:00 NY time on that day.
range_ready_time = {
    d: pd.Timestamp(d, tz=NY_TZ) + pd.Timedelta(hours=RANGE_CANDLE_HOURS)
    for d in day_ranges_map.keys()
}

# ---------- BACKTEST LOOP ----------
capital = initial_capital
equity = [capital]
equity_time = [df.loc[0, "timestamp"]]

position = None          # open trade dict
day_state = {}            # per-day breakout state machine
trades = []

def get_day_state(d):
    if d not in day_state:
        day_state[d] = {"phase": "waiting_breakout", "breakout_side": None}
    return day_state[d]

for i in range(1, len(df)):
    curr = df.loc[i]
    d = curr["ny_date"]

    # ---------- Manage open position first ----------
    if position is not None:
        side = position["side"]
        entry_price = position["entry_price"]
        tp = position["tp"]
        sl = position["sl"]

        hit_target = (side == "long" and curr["high"] >= tp) or (side == "short" and curr["low"] <= tp)
        hit_stop   = (side == "long" and curr["low"] <= sl) or (side == "short" and curr["high"] >= sl)

        if hit_stop and hit_target:
            exit_price, reason = sl, "stop_loss (both hit)"
        elif hit_target:
            exit_price, reason = tp, "target"
        elif hit_stop:
            exit_price, reason = sl, "stop_loss"
        elif d != position["entry_date"]:
            # strategy trades only within the day of the range candle -> force flat at day change
            exit_price, reason = curr["open"], "day_end_close"
        else:
            equity.append(capital)
            equity_time.append(curr["timestamp"])
            continue

        if side == "long":
            eff_entry = entry_price + spread_points / 2
            eff_exit = exit_price - spread_points / 2
        else:
            eff_entry = entry_price - spread_points / 2
            eff_exit = exit_price + spread_points / 2

        price_move = (eff_exit - eff_entry) if side == "long" else (eff_entry - eff_exit)
        gross_pnl = price_move * units_per_trade * point_value
        pnl = gross_pnl - commission_per_trade
        capital += pnl

        trades.append({
            "entry_time": position["entry_time"],
            "exit_time": curr["timestamp"],
            "side": side,
            "entry_price": float(entry_price),
            "exit_price": float(exit_price),
            "sl": float(sl),
            "tp": float(tp),
            "gross_pnl": float(gross_pnl),
            "commission": float(commission_per_trade),
            "pnl": float(pnl),
            "exit_reason": reason,
            "capital_after": float(capital),
        })
        position = None
        equity.append(capital)
        equity_time.append(curr["timestamp"])
        continue

    # ---------- No open position: run the breakout/re-entry state machine ----------
    if d not in day_ranges_map:
        equity.append(capital)
        equity_time.append(curr["timestamp"])
        continue

    # range not established yet (still inside/before the first 4H candle)
    if curr["timestamp"] < range_ready_time[d]:
        equity.append(capital)
        equity_time.append(curr["timestamp"])
        continue

    r = day_ranges_map[d]
    range_high = r["range_high"]
    range_low = r["range_low"]
    state = get_day_state(d)

    if state["phase"] == "waiting_breakout":
        if curr["close"] > range_high:
            state["phase"] = "waiting_reentry"
            state["breakout_side"] = "up"
        elif curr["close"] < range_low:
            state["phase"] = "waiting_reentry"
            state["breakout_side"] = "down"

    elif state["phase"] == "waiting_reentry":
        reentered = range_low <= curr["close"] <= range_high
        if reentered:
            state["phase"] = "armed"  # enter on the NEXT candle's open
        else:
            # if price closes even further away, or flips to the other side,
            # just keep waiting for a valid re-entry close back inside the range
            if state["breakout_side"] == "up" and curr["close"] < range_low:
                state["breakout_side"] = "down"
            elif state["breakout_side"] == "down" and curr["close"] > range_high:
                state["breakout_side"] = "up"

    elif state["phase"] == "armed":
        side = "short" if state["breakout_side"] == "up" else "long"
        entry_price = curr["open"]
        sl = range_high if side == "short" else range_low
        risk = abs(entry_price - sl)
        tp = entry_price - risk * RR_MULTIPLE if side == "short" else entry_price + risk * RR_MULTIPLE

        position = {
            "side": side,
            "entry_price": entry_price,
            "entry_time": curr["timestamp"],
            "entry_date": d,
            "sl": sl,
            "tp": tp,
        }
        # reset state so another setup can form later the same day
        day_state[d] = {"phase": "waiting_breakout", "breakout_side": None}

    equity.append(capital)
    equity_time.append(curr["timestamp"])

# ---------- Force-close any position left open at end of data ----------
if position is not None:
    last = df.iloc[-1]
    side = position["side"]
    entry_price = position["entry_price"]
    exit_price = last["close"]

    if side == "long":
        eff_entry = entry_price + spread_points / 2
        eff_exit = exit_price - spread_points / 2
    else:
        eff_entry = entry_price - spread_points / 2
        eff_exit = exit_price + spread_points / 2

    price_move = (eff_exit - eff_entry) if side == "long" else (eff_entry - eff_exit)
    gross_pnl = price_move * units_per_trade * point_value
    pnl = gross_pnl - commission_per_trade
    capital += pnl

    trades.append({
        "entry_time": position["entry_time"],
        "exit_time": last["timestamp"],
        "side": side,
        "entry_price": float(entry_price),
        "exit_price": float(exit_price),
        "sl": float(position["sl"]),
        "tp": float(position["tp"]),
        "gross_pnl": float(gross_pnl),
        "commission": float(commission_per_trade),
        "pnl": float(pnl),
        "exit_reason": "eod_close",
        "capital_after": float(capital),
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

    trades_df["entry_time"] = pd.to_datetime(trades_df["entry_time"])
    trades_df["exit_time"] = pd.to_datetime(trades_df["exit_time"])
    trades_df["date"] = trades_df["exit_time"].dt.date
    trades_df["month"] = trades_df["exit_time"].dt.to_period("M")

    daily_pnl = trades_df.groupby("date")["pnl"].sum().reset_index()
    monthly_pnl = trades_df.groupby("month")["pnl"].sum().reset_index()
    monthly_pnl["month"] = monthly_pnl["month"].astype(str)

    daily_pnl["cum_pnl"] = daily_pnl["pnl"].cumsum()
    monthly_pnl["cum_pnl"] = monthly_pnl["pnl"].cumsum()

    print(f"Initial capital: ${initial_capital}")
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
    daily_pnl.to_csv(DAILY_PNL_CSV, index=False)
    monthly_pnl.to_csv(MONTHLY_PNL_CSV, index=False)

    print(f"\nSaved trades to {TRADES_CSV}")
    print(f"Saved equity curve to {EQUITY_CSV}")
    print(f"Saved daily PnL to {DAILY_PNL_CSV}")
    print(f"Saved monthly PnL to {MONTHLY_PNL_CSV}")

    # ---------- Charts ----------
    plt.figure(figsize=(10, 4))
    plt.plot(equity_df["timestamp"], equity_df["equity"])
    plt.title("Equity Curve")
    plt.xlabel("Time")
    plt.ylabel("Equity (USD)")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    plt.figure(figsize=(10, 4))
    plt.bar(daily_pnl["date"].astype(str), daily_pnl["pnl"])
    plt.title("Daily PnL")
    plt.xlabel("Date")
    plt.ylabel("PnL (USD)")
    plt.xticks(rotation=45)
    plt.grid(True, axis="y")
    plt.tight_layout()
    plt.show()

    plt.figure(figsize=(8, 4))
    plt.bar(monthly_pnl["month"], monthly_pnl["pnl"])
    plt.title("Monthly PnL")
    plt.xlabel("Month")
    plt.ylabel("PnL (USD)")
    plt.xticks(rotation=45)
    plt.grid(True, axis="y")
    plt.tight_layout()
    plt.show()

else:
    print("No trades executed — check your data range/timezone or the CSV path.")