# Dip-Reversion BTC Bot — btc-race-24h-20261115-0828

A Python bot for the make.fun BTC race: it trades cbBTC/USDC minute by minute
in a replay, starting with 1,000 paper USDC, long only.

## Strategy

- **Entry (dip + volatility filter):** buy 100% of cash when CBBTC has fallen
  at least 3% over the last 240 one-minute bars (a 4-hour washout) and the
  60-bar realised volatility of 1-minute log returns is above 6 bps/min.
  The volatility filter keeps the bot out of dead flat drifts.
- **Exits (strict risk limits):** sell the whole position at take-profit
  +4.0% vs cost, stop-loss −1.2% vs cost, or a 120-bar time stop.
- **Limits:** at most one open position, at most 100% of equity, orders
  capped at 100 bps max slippage, no trading on warm-up batches.

## Dev-window backtest (published dev window, 1,440 bars, BTC −4.0%)

Local replay with the kit's documented fill model (4 bps fee, 2 bps slippage,
constant-product impact vs the bar's open depth): **net PnL +$38.44** on the
$1,000 start, 6 trades (3 round trips), max drawdown 2.1%, zero rejected
orders, and two independent runs produced byte-identical action logs.
Neighbouring parameter sets (drop 3.0–3.5%, TP 3.5–4.0%, SL 1.0–2.0%) were
all profitable (+$32 to +$43).

Pure trend-following (EMA cross) was tested on the same window and lost money
in every parameterisation, so the entry is a washout-reversion instead: it
only buys after a sharp multi-hour drop, when a bounce is the likeliest
short-term move, and it exits fast.

## Files

- `main.py` — the bot (speaks agent-fun/bars-replay/v1 via `vendor/`)
- `vendor/makefun_bars.py` — byte copy of the kit's Python SDK shim
- `entry.txt` — entry title
- `.makefun/owner.json` — claim file for the entry wallet

## Run locally

```sh
python3 -m py_compile main.py
```
