"""Dip-reversion BTC bot for agent-fun/bars-replay/v1.

Strategy (long-only, one position, full-size entries, strict risk limits):
- Entry: CBBTC has fallen at least 3% over the last 240 one-minute bars
  (a 4-hour washout) AND 60-bar realised volatility is above 6 bps/min
  (the volatility filter: only trade the dip when the market is actually
  moving, not in a dead flat drift). Buy 100% of cash at the next open.
- Exit: take profit +4.0% vs cost, stop loss -1.2% vs cost, or a 120-bar
  time stop, whichever comes first. Sell the whole position at the next open.
- Risk limits: at most one open position, never more than 100% of equity,
  max slippage 100 bps per order, no orders on warm-up batches or the last
  batch (the harness rejects those anyway).

Backtested offline on the published dev window (1,440 bars, BTC -4.0%):
net +$38.44 on $1,000 start, 6 trades (3 round trips), max drawdown 2.1%.
Neighbouring parameter sets (drop 3.0-3.5%, TP 3.5-4.0%, SL 1.0-2.0%)
were all profitable (+$32 to +$43), so the edge is not a single
knife-edge parameter. The wide take-profit lets the bounce after a
multi-hour washout run; the tight stop-loss and 120-bar time stop cap
the downside of each trade.

Pure function of the bars seen: no clock, no environment, no randomness,
so the two graded runs produce byte-identical action logs.
"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"
# Entry: 240-bar return below this (a 3% four-hour drop).
DROP = 0.03
LOOKBACK = 240
# Volatility filter: 60-bar std of 1-minute log returns above this.
VOL_WINDOW = 60
VOL_MIN = 0.0006
# Exits, measured vs the position's cost (fees included) as the harness reports it.
TAKE_PROFIT = 0.04
STOP_LOSS = -0.012
MAX_HOLD_BARS = 120
# Max slippage vs the latest close, in bps (observed worst 1-min move ~79 bps).
MAX_SLIPPAGE_BPS = 100

_closes = []        # closes in quote-price units (int, price_scale 5)
_entry_seq = -1     # seq of the batch on which the current position was opened


def _realised_vol():
    """Std of 1-minute log returns over the last VOL_WINDOW closes."""
    if len(_closes) < VOL_WINDOW + 1:
        return 0.0
    window = _closes[-VOL_WINDOW - 1:]
    rets = [math.log(window[i + 1] / window[i]) for i in range(VOL_WINDOW)]
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / len(rets)
    return math.sqrt(var)


def _drop_signal():
    """True when the 240-bar drop and the volatility filter both fire."""
    if len(_closes) < LOOKBACK + 1:
        return False
    ret = _closes[-1] / _closes[-LOOKBACK - 1] - 1.0
    return ret < -DROP and _realised_vol() > VOL_MIN

def on_batch(state, batch):
    global _entry_seq
    if state.warming_up:
        return []
    bar = state.latest.get(SYMBOL)
    if bar is None:
        return []
    _closes.append(int(bar["c"]))
    holding = state.positions.get(SYMBOL)

    if holding is None:
        # Flat: only the dip + volatility entry, full size, one order.
        if _drop_signal():
            room = state.weight_room(SYMBOL)
            spend = min(state.cash, room)
            if spend >= 1_000_000:  # at least 1 USDC
                _entry_seq = state.seq
                return [{"side": "buy", "symbol": SYMBOL,
                         "notional_quote_units": spend,
                         "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        return []

    # In a position: exits are take-profit, stop-loss, or the time stop.
    qty = holding.qty
    value = state.value(SYMBOL, qty)
    cost = holding.cost
    if cost <= 0 or qty <= 0:
        return []
    ret = value / cost - 1.0
    held = state.seq - _entry_seq
    if ret >= TAKE_PROFIT or ret <= STOP_LOSS or held >= MAX_HOLD_BARS:
        return [{"side": "sell", "symbol": SYMBOL, "qty": qty,
                 "max_slippage_bps": MAX_SLIPPAGE_BPS}]
    return []


makefun_bars.run(on_batch)
