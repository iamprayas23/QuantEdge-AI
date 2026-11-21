import pandas as pd
import numpy as np

# =========================
# Load Data
# =========================
df = pd.read_csv("data/XAUUSD_1H_merged.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])
df.sort_values("timestamp", inplace=True)
df.reset_index(drop=True, inplace=True)

# =========================
# RSI
# =========================
def calculate_rsi(df, period=14):
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    df["rsi"] = 100 - (100 / (1 + rs))
    return df

df = calculate_rsi(df)

# =========================
# Swing Detection
# =========================
window = 5

df["swing_low"] = df["low"][
    df["low"] == df["low"].rolling(window*2+1, center=True).min()
]

df["swing_high"] = df["high"][
    df["high"] == df["high"].rolling(window*2+1, center=True).max()
]

# =========================
# Candle Pattern Functions
# =========================
def bullish_marubozu(i):
    o = df.iloc[i]["open"]
    c = df.iloc[i]["close"]
    h = df.iloc[i]["high"]
    l = df.iloc[i]["low"]

    body = abs(c - o)
    range_ = h - l

    return (c > o) and (body > 0.7 * range_)


def bearish_marubozu(i):
    o = df.iloc[i]["open"]
    c = df.iloc[i]["close"]
    h = df.iloc[i]["high"]
    l = df.iloc[i]["low"]

    body = abs(c - o)
    range_ = h - l

    return (c < o) and (body > 0.7 * range_)


def bullish_engulfing(i):
    if i < 1:
        return False

    o1 = df.iloc[i-1]["open"]
    c1 = df.iloc[i-1]["close"]
    o2 = df.iloc[i]["open"]
    c2 = df.iloc[i]["close"]

    return (c2 > o2) and (c2 > o1) and (o2 < c1)


def bearish_engulfing(i):
    if i < 1:
        return False

    o1 = df.iloc[i-1]["open"]
    c1 = df.iloc[i-1]["close"]
    o2 = df.iloc[i]["open"]
    c2 = df.iloc[i]["close"]

    return (c2 < o2) and (c2 < o1) and (o2 > c1)

# =========================
# Backtest
# =========================
capital = 10000
risk_per_trade = 0.01
rr = 2

equity = capital
trades = []
position = None

for i in range(50, len(df)-1):

    if position is None:

        # ---- LONG SETUP ----
        lows = df.iloc[:i].dropna(subset=["swing_low"])
        if len(lows) >= 2:

            L1 = lows.iloc[-2]
            L2 = lows.iloc[-1]

            if (
                L2["low"] < L1["low"] and
                L2["rsi"] > L1["rsi"] and
                L1["rsi"] < 30
            ):

                if bullish_marubozu(i) or bullish_engulfing(i):

                    entry = df.iloc[i]["close"]
                    sl = L2["low"]
                    risk = entry - sl

                    if risk > 0:

                        tp = entry + rr * risk
                        risk_amount = equity * risk_per_trade
                        lot_size = risk_amount / risk

                        position = {
                            "type": "long",
                            "entry": entry,
                            "sl": sl,
                            "tp": tp,
                            "lot": lot_size
                        }

        # ---- SHORT SETUP ----
        highs = df.iloc[:i].dropna(subset=["swing_high"])
        if position is None and len(highs) >= 2:

            H1 = highs.iloc[-2]
            H2 = highs.iloc[-1]

            if (
                H2["high"] > H1["high"] and
                H2["rsi"] < H1["rsi"] and
                H1["rsi"] > 70
            ):

                if bearish_marubozu(i) or bearish_engulfing(i):

                    entry = df.iloc[i]["close"]
                    sl = H2["high"]
                    risk = sl - entry

                    if risk > 0:

                        tp = entry - rr * risk
                        risk_amount = equity * risk_per_trade
                        lot_size = risk_amount / risk

                        position = {
                            "type": "short",
                            "entry": entry,
                            "sl": sl,
                            "tp": tp,
                            "lot": lot_size
                        }

    # =========================
    # Manage Trade
    # =========================
    if position is not None:

        high = df.iloc[i]["high"]
        low = df.iloc[i]["low"]

        if position["type"] == "long":

            if low <= position["sl"]:
                loss = (position["entry"] - position["sl"]) * position["lot"]
                equity -= loss
                trades.append(-1)
                position = None

            elif high >= position["tp"]:
                profit = (position["tp"] - position["entry"]) * position["lot"]
                equity += profit
                trades.append(1)
                position = None

        elif position["type"] == "short":

            if high >= position["sl"]:
                loss = (position["sl"] - position["entry"]) * position["lot"]
                equity -= loss
                trades.append(-1)
                position = None

            elif low <= position["tp"]:
                profit = (position["entry"] - position["tp"]) * position["lot"]
                equity += profit
                trades.append(1)
                position = None

# =========================
# Results
# =========================
total_return = (equity - capital) / capital * 100
win_rate = trades.count(1) / len(trades) * 100 if trades else 0

print("========== Early Divergence Strategy ==========")
print(f"Final Equity: {equity:.2f}")
print(f"Total Return: {total_return:.2f}%")
print(f"Total Trades: {len(trades)}")
print(f"Win Rate: {win_rate:.2f}%")

# =========================
# Advanced Metrics
# =========================
returns = []

equity_curve = [capital]
equity_running = capital

for result in trades:
    if result == 1:
        equity_running *= (1 + 0.02)
    else:
        equity_running *= (1 - 0.01)
    equity_curve.append(equity_running)

equity_series = pd.Series(equity_curve)

drawdown = (equity_series / equity_series.cummax() - 1)
max_dd = drawdown.min() * 100

wins = trades.count(1)
losses = trades.count(-1)

profit_factor = (wins * 2) / (losses * 1) if losses > 0 else 0

print("\n========== Advanced Metrics ==========")
print(f"Max Drawdown: {max_dd:.2f}%")
print(f"Profit Factor: {profit_factor:.2f}")