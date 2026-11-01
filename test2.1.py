import pandas as pd
import numpy as np
import os
from decimal import Decimal, getcontext

getcontext().prec = 10

# ------------- CONFIG (XAUUSD SPOT) -------------
csv_path = "XAUUSD_M1_candles.csv"          # M1 data for high frequency
initial_capital = Decimal("5000.0")

lot_size = Decimal("0.01")                  # SMALL fixed lot (no martingale)
contract_oz_per_lot = Decimal("100")
charges_roundtrip = Decimal("0.0")

# GRID PARAMETERS (OPTIMIZED)
grid_spacing = 6                            # Wider spacing to avoid instant fills
num_levels_each_side = 6                    # Fewer levels, more selective
tp_points = Decimal("4.0")                  # Slightly wider TP
sl_points = Decimal("3.0")                  # Slightly wider SL (better R:R for grid)

# GRID RESET/RECALCULATION
recalc_grid_every_n_bars = 30               # Recenter less frequently
max_total_positions = 2                     # Reduced max positions

# TREND FILTER (CRITICAL)
use_trend_filter = True
trend_ema_period = 50                       # Trend reference
only_trade_with_trend = True                # Only BUY above EMA, SELL below EMA
trend_strength_lookback = 10                # Check if trend is strong

# RANGE DETECTION (ADX-like simple version)
use_range_filter = True
range_detection_period = 14
max_trend_strength = 15.0                   # Max ATR/price ratio for "ranging" (in basis points)

# VOLATILITY FILTER (ATR)
use_atr_filter = True
atr_len = 14
min_atr = Decimal("1.0")                    # Minimum volatility to trade
max_atr = Decimal("15.0")                   # Maximum volatility (avoid extreme moves)

# PAUSE TRADING CONDITIONS
pause_after_consecutive_losses = 5          # Pause after X losing trades in a row
pause_duration_bars = 20                    # How many bars to pause

# SESSION FILTER
use_session_filter = False                  # Trade 24/5 for max frequency
session_start_hour = 0
session_end_hour = 23

TRADES_CSV = "xauusd_grid_v2_trades.csv"
EQUITY_CSV = "xauusd_grid_v2_equity.csv"
# -----------------------------------------------

if not os.path.exists(csv_path):
    raise FileNotFoundError(f"CSV not found: {csv_path}")

df = pd.read_csv(csv_path, dtype=str)
df["timestamp"] = pd.to_datetime(df["time"])

for c in ["open", "high", "low", "close"]:
    df[c] = df[c].apply(lambda x: Decimal(str(x)))

df = df.sort_values("timestamp").reset_index(drop=True)

# ---------- INDICATORS ----------
df_float = df.copy()
for c in ["open", "high", "low", "close"]:
    df_float[c] = df_float[c].astype(float)

# Trend EMA
if use_trend_filter:
    df_float["ema_trend"] = df_float["close"].ewm(span=trend_ema_period, adjust=False).mean()
    df["ema_trend"] = df_float["ema_trend"]
    df["ema_trend_prev"] = df["ema_trend"].shift(1)
else:
    df["ema_trend_prev"] = df["close"]

# ATR / Volatility
tr1 = (df_float["high"] - df_float["low"])
tr2 = (df_float["high"] - df_float["close"].shift(1)).abs()
tr3 = (df_float["low"] - df_float["close"].shift(1)).abs()
df_float["tr"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
df_float["atr"] = df_float["tr"].rolling(atr_len).mean()

df["atr"] = df_float["atr"]
df["atr_prev"] = df["atr"].shift(1)

# Range Detection (simple momentum measure)
if use_range_filter:
    # Calculate price momentum over lookback period
    df_float["price_change"] = df_float["close"].diff(range_detection_period).abs()
    df_float["avg_price"] = df_float["close"].rolling(range_detection_period).mean()
    df_float["trend_strength"] = (df_float["price_change"] / df_float["avg_price"]) * 10000  # basis points
    df["trend_strength"] = df_float["trend_strength"]
    df["trend_strength_prev"] = df["trend_strength"].shift(1)
else:
    df["trend_strength_prev"] = 0

# SESSION FILTER
df["hour"] = df["timestamp"].dt.hour
if use_session_filter:
    df["session_ok"] = (
        (df["hour"] >= session_start_hour) &
        (df["hour"] <= session_end_hour)
    )
else:
    df["session_ok"] = True

# ---------- GRID SYSTEM STATE ----------
capital = initial_capital
equity = [capital]
equity_time = [df.loc[0, "timestamp"]]
open_positions = []
pending_orders = []
trades = []
last_grid_calc_bar = 0
consecutive_losses = 0
pause_until_bar = 0

def calculate_grid_levels(current_price, current_ema, spacing, num_levels, only_with_trend):
    """
    Calculate grid levels with trend filter
    """
    levels = []
    base_price = float(current_price)
    ema_price = float(current_ema)
    
    if only_with_trend:
        # Only place BUY orders if price is above EMA (uptrend)
        if base_price > ema_price:
            for i in range(1, num_levels + 1):
                buy_price = base_price - (spacing * i)
                if buy_price > ema_price - (spacing * 2):  # Don't go too far below EMA
                    levels.append((buy_price, "long"))
        
        # Only place SELL orders if price is below EMA (downtrend)
        if base_price < ema_price:
            for i in range(1, num_levels + 1):
                sell_price = base_price + (spacing * i)
                if sell_price < ema_price + (spacing * 2):  # Don't go too far above EMA
                    levels.append((sell_price, "short"))
    else:
        # Traditional grid (both sides)
        for i in range(1, num_levels + 1):
            buy_price = base_price - (spacing * i)
            levels.append((buy_price, "long"))
        
        for i in range(1, num_levels + 1):
            sell_price = base_price + (spacing * i)
            levels.append((sell_price, "short"))
    
    return levels

def check_pending_order_trigger(bar, order):
    """Check if pending order should be filled"""
    order_price = order["price"]
    side = order["side"]
    
    if side == "long":
        if float(bar["low"]) <= order_price <= float(bar["high"]):
            return True
    
    if side == "short":
        if float(bar["low"]) <= order_price <= float(bar["high"]):
            return True
    
    return False

def manage_position(position, bar):
    """Check if position hits TP or SL"""
    side = position["side"]
    entry_price = position["entry_price"]
    
    tp = entry_price + tp_points if side == "long" else entry_price - tp_points
    sl = entry_price - sl_points if side == "long" else entry_price + sl_points
    
    hit_target = (side == "long" and bar["high"] >= tp) or (side == "short" and bar["low"] <= tp)
    hit_stop = (side == "long" and bar["low"] <= sl) or (side == "short" and bar["high"] >= sl)
    
    if hit_stop and hit_target:
        return True, sl, "stop_loss (both hit)"
    elif hit_target:
        return True, tp, "target"
    elif hit_stop:
        return True, sl, "stop_loss"
    
    return False, None, None

# ---------- MAIN BACKTEST LOOP ----------
for i in range(1, len(df)):
    curr = df.loc[i]
    
    # Check if we're in pause mode
    if i < pause_until_bar:
        equity.append(capital)
        equity_time.append(curr["timestamp"])
        continue
    
    # Volatility filter
    if pd.notna(curr["atr_prev"]) and use_atr_filter:
        atr_prev = curr["atr_prev"]
        vol_ok = (
            Decimal(str(atr_prev)) >= min_atr and
            Decimal(str(atr_prev)) <= max_atr
        )
    else:
        vol_ok = True
    
    # Range filter (only trade when NOT trending strongly)
    if use_range_filter and pd.notna(curr["trend_strength_prev"]):
        trend_strength = curr["trend_strength_prev"]
        range_ok = trend_strength < max_trend_strength
    else:
        range_ok = True
    
    session_ok = curr["session_ok"]
    
    # Get trend direction
    if use_trend_filter and pd.notna(curr["ema_trend_prev"]):
        ema_prev = curr["ema_trend_prev"]
        close_prev = float(df.loc[i-1]["close"])
        in_uptrend = close_prev > float(ema_prev)
        in_downtrend = close_prev < float(ema_prev)
    else:
        ema_prev = curr["close"]
        in_uptrend = True
        in_downtrend = True
    
    # ---------- MANAGE OPEN POSITIONS ----------
    positions_to_remove = []
    for idx, pos in enumerate(open_positions):
        hit, exit_price, reason = manage_position(pos, curr)
        
        if hit:
            side = pos["side"]
            entry_price = pos["entry_price"]
            
            price_move = (exit_price - entry_price) if side == "long" else (entry_price - exit_price)
            pnl = price_move * lot_size * contract_oz_per_lot
            pnl -= charges_roundtrip
            capital += pnl
            
            trades.append({
                "entry_time": pos["entry_time"],
                "exit_time": curr["timestamp"],
                "side": side,
                "entry_price": float(entry_price),
                "exit_price": float(exit_price),
                "pnl": float(pnl),
                "exit_reason": reason,
                "capital_after": float(capital),
                "grid_level": pos["grid_level"]
            })
            
            # Track consecutive losses
            if pnl < 0:
                consecutive_losses += 1
            else:
                consecutive_losses = 0
            
            positions_to_remove.append(idx)
    
    # Remove closed positions
    for idx in reversed(positions_to_remove):
        open_positions.pop(idx)
    
    # Check if we should pause trading
    if consecutive_losses >= pause_after_consecutive_losses:
        pause_until_bar = i + pause_duration_bars
        consecutive_losses = 0
        pending_orders = []  # Clear pending orders during pause
    
    # ---------- CHECK PENDING ORDERS ----------
    orders_to_remove = []
    for idx, order in enumerate(pending_orders):
        if check_pending_order_trigger(curr, order):
            # Validate trend direction before filling
            side = order["side"]
            allow_fill = True
            
            if only_trade_with_trend:
                if side == "long" and not in_uptrend:
                    allow_fill = False
                if side == "short" and not in_downtrend:
                    allow_fill = False
            
            # Fill order if conditions met
            if allow_fill and len(open_positions) < max_total_positions and session_ok and vol_ok and range_ok:
                open_positions.append({
                    "side": order["side"],
                    "entry_price": Decimal(str(order["price"])),
                    "entry_time": curr["timestamp"],
                    "grid_level": order["price"]
                })
                orders_to_remove.append(idx)
    
    # Remove filled orders
    for idx in reversed(orders_to_remove):
        pending_orders.pop(idx)
    
    # ---------- RECALCULATE GRID ----------
    if i - last_grid_calc_bar >= recalc_grid_every_n_bars and vol_ok and range_ok:
        # Clear old pending orders
        pending_orders = []
        
        # Calculate new grid
        current_price = curr["close"]
        current_ema = ema_prev if use_trend_filter else current_price
        
        grid_levels = calculate_grid_levels(
            current_price, 
            current_ema, 
            grid_spacing, 
            num_levels_each_side,
            only_trade_with_trend
        )
        
        # Create pending orders
        for price, side in grid_levels:
            pending_orders.append({
                "price": price,
                "side": side
            })
        
        last_grid_calc_bar = i
    
    equity.append(capital)
    equity_time.append(curr["timestamp"])

# ---------- CLOSE ALL OPEN POSITIONS AT END ----------
if open_positions:
    last_bar = df.iloc[-1]
    last_price = last_bar["close"]
    
    for pos in open_positions:
        side = pos["side"]
        entry_price = pos["entry_price"]
        price_move = (last_price - entry_price) if side == "long" else (entry_price - last_price)
        pnl = price_move * lot_size * contract_oz_per_lot - charges_roundtrip
        capital += pnl
        
        trades.append({
            "entry_time": pos["entry_time"],
            "exit_time": last_bar["timestamp"],
            "side": side,
            "entry_price": float(entry_price),
            "exit_price": float(last_price),
            "pnl": float(pnl),
            "exit_reason": "eod_close",
            "capital_after": float(capital),
            "grid_level": pos["grid_level"]
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
    avg_win = trades_df[trades_df["pnl"] > 0]["pnl"].mean() if (trades_df["pnl"] > 0).any() else 0
    avg_loss = trades_df[trades_df["pnl"] < 0]["pnl"].mean() if (trades_df["pnl"] < 0).any() else 0
    
    dd = pd.Series(equity) - pd.Series(equity).cummax()
    max_dd = dd.min()
    
    # Calculate profit factor
    gross_profit = trades_df[trades_df["pnl"] > 0]["pnl"].sum()
    gross_loss = abs(trades_df[trades_df["pnl"] < 0]["pnl"].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

    print(f"\n{'='*70}")
    print(f"TREND-AWARE GRID TRADING SYSTEM V2 - XAUUSD")
    print(f"{'='*70}")
    print(f"Initial capital: ${initial_capital}")
    print(f"Lot size: {lot_size} (FIXED) | Contract: {contract_oz_per_lot} oz/lot")
    print(f"Grid spacing: {grid_spacing} pts | Levels each side: {num_levels_each_side}")
    print(f"TP: {tp_points} pts | SL: {sl_points} pts")
    print(f"Max simultaneous positions: {max_total_positions}")
    print(f"Grid recalc: Every {recalc_grid_every_n_bars} bars")
    if use_trend_filter:
        print(f"Trend filter: {trend_ema_period}-EMA | Trade with trend: {only_trade_with_trend}")
    if use_range_filter:
        print(f"Range filter: Max trend strength {max_trend_strength} bps")
    if use_atr_filter:
        print(f"ATR Filter: {min_atr} - {max_atr}")
    print(f"Pause after {pause_after_consecutive_losses} losses for {pause_duration_bars} bars")
    print(f"{'='*70}")
    print(f"Final capital:   ${capital:.2f}")
    print(f"Net P&L:         ${total_pnl:.2f}")
    print(f"Return:          {((float(capital) / float(initial_capital)) - 1) * 100:.2f}%")
    print(f"{'='*70}")
    print(f"Total Trades:    {len(trades_df)}")
    print(f"Win rate:        {win_rate:.1f}%")
    print(f"Profit Factor:   {profit_factor:.2f}")
    print(f"Average P&L:     ${avg_pnl:.2f}")
    print(f"Average Win:     ${avg_win:.2f}")
    print(f"Average Loss:    ${avg_loss:.2f}")
    print(f"Max Drawdown:    ${max_dd:.2f}")
    print(f"{'='*70}\n")
    
    print("Exit Reasons:")
    print(trades_df["exit_reason"].value_counts())
    
    # Side distribution
    print("\nTrade Direction:")
    print(trades_df["side"].value_counts())
    
    print("\n" + "="*70)
    print("FIRST 15 TRADES:")
    print("="*70)
    print(trades_df.head(15).to_string(index=False))
    
    print("\n" + "="*70)
    print("LAST 15 TRADES:")
    print("="*70)
    print(trades_df.tail(15).to_string(index=False))
    
    # Trades per day analysis
    trades_df["date"] = pd.to_datetime(trades_df["entry_time"]).dt.date
    trades_per_day = trades_df.groupby("date").size()
    print("\n" + "="*70)
    print("TRADES PER DAY:")
    print("="*70)
    print(f"Average: {trades_per_day.mean():.1f} trades/day")
    print(f"Min: {trades_per_day.min()} | Max: {trades_per_day.max()}")
    print(f"\nDaily breakdown:\n{trades_per_day}")

    trades_df.to_csv(TRADES_CSV, index=False)
    equity_df.to_csv(EQUITY_CSV, index=False)
    print(f"\n✓ Saved trades to {TRADES_CSV}")
    print(f"✓ Saved equity curve to {EQUITY_CSV}")
else:
    print("No trades executed — check conditions or data.")