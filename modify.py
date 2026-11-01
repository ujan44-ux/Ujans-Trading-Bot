import MetaTrader5 as mt5
import time
import pandas as pd  # For your analysis workflows

# Initialize MT5 connection
if not mt5.initialize():
    print("MT5 initialize failed")
    quit()

# Configuration - adjust as needed
SYMBOL = "XAUUSD"  # Your trading symbol
TARGET_PROFIT = 5.0  # Trigger threshold
NEW_SL_OFFSET = 2.0  # SL at entry +2 (in account currency? Wait, typically points/pips)
PROFIT_CHECK_INTERVAL = 5  # Seconds between checks
POSITION_TICKET = None  # Set to specific ticket or None for first position

def get_positions(symbol=None, ticket=None):
    """Get positions filtered by symbol or ticket."""
    if ticket:
        return mt5.positions_get(ticket=ticket)
    elif symbol:
        return mt5.positions_get(symbol=symbol)
    return mt5.positions_get()

def modify_sl_to_profit(ticket, profit_level):
    """Modify SL to breakeven + profit_level."""
    position = mt5.positions_get(ticket=ticket)[0]
    if not position:
        print(f"Position {ticket} not found")
        return False
    
    # Calculate new SL: current price - some distance? But per request: "switch stoploss to +2"
    # Assuming +2 means breakeven +2 units profit, but SL is price level.
    # Common: move SL to entry + 2 pips/points for lock-in.
    # Adjust point value
    symbol_info = mt5.symbol_info(SYMBOL)
    if not symbol_info:
        print("Symbol info failed")
        return False
    point = symbol_info.point
    new_sl = position.price_open + (NEW_SL_OFFSET * point)  # +2 points/pips above open
    
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": SYMBOL,
        "position": ticket,
        "sl": new_sl,
        "tp": position.tp  # Keep existing TP
    }
    result = mt5.order_send(request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"SL moved to {new_sl} for ticket {ticket}, profit was {position.profit}")
        return True
    else:
        print(f"Modify failed: {result.retcode} {result.comment}")
        return False

# Main loop
print("Monitoring open P&L...")
modified_tickets = set()  # Track modified to avoid repeats

while True:
    positions = get_positions(symbol=SYMBOL)  # Or use ticket=POSITION_TICKET
    if not positions:
        print("No open positions, waiting...")
        time.sleep(PROFIT_CHECK_INTERVAL)
        continue
    
    for pos in positions:
        if pos.ticket in modified_tickets:
            continue  # Already handled
        
        pnl = pos.profit  # Open P&L
        print(f"Ticket {pos.ticket}: P&L = {pnl:.2f}")
        
        if pnl > TARGET_PROFIT:
            if modify_sl_to_profit(pos.ticket, NEW_SL_OFFSET):
                modified_tickets.add(pos.ticket)
    
    time.sleep(PROFIT_CHECK_INTERVAL)

# Shutdown on exit (Ctrl+C)
mt5.shutdown()
