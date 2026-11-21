import pandas as pd
import numpy as np

# ---------------------------
# Load Data
# ---------------------------

df = pd.read_csv("data/XAUUSD_1H_merged.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])
df.set_index("timestamp", inplace=True)

# ---------------------------
# RSI Calculation
# ---------------------------

window = 14

delta = df["close"].diff()

gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()

rs = gain / loss
df["rsi"] = 100 - (100 / (1 + rs))

# ---------------------------
# Strategy Logic
# ---------------------------

df["signal"] = 0
df.loc[df["rsi"] < 30, "signal"] = 1     # Buy
df.loc[df["rsi"] > 70, "signal"] = -1    # Sell

df["position"] = df["signal"].shift()

# ---------------------------
# Returns
# ---------------------------

df["returns"] = df["close"].pct_change()
df["strategy_returns"] = df["position"] * df["returns"]

# ---------------------------
# Performance Metrics
# ---------------------------

df["equity_curve"] = (1 + df["strategy_returns"]).cumprod()

total_return = df["equity_curve"].iloc[-1] - 1

# Sharpe ratio
sharpe = (
    df["strategy_returns"].mean() /
    df["strategy_returns"].std()
) * np.sqrt(252 * 24)

# Max Drawdown
rolling_max = df["equity_curve"].cummax()
drawdown = df["equity_curve"] / rolling_max - 1
max_drawdown = drawdown.min()

win_rate = (df["strategy_returns"] > 0).sum() / len(df)

print("========== RSI Strategy Results ==========")
print(f"Total Return: {total_return:.2%}")
print(f"Sharpe Ratio: {sharpe:.2f}")
print(f"Max Drawdown: {max_drawdown:.2%}")
print(f"Win Rate: {win_rate:.2%}")