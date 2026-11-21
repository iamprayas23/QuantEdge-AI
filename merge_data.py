import pandas as pd
import glob
import os

path = "data/xauusd_raw/*.csv"
files = glob.glob(path)

if not files:
    print("No CSV files found.")
    exit()

print(f"Found {len(files)} files.")

df_list = []

for file in files:
    print(f"Processing: {file}")

    # READ AS COMMA SEPARATED
    df = pd.read_csv(file)

    # Rename columns properly
    df = df.rename(columns={
        "UTC": "timestamp",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume"
    })

    # Remove the " UTC" text from timestamp
    df["timestamp"] = df["timestamp"].str.replace(" UTC", "", regex=False)

    # Convert to datetime
    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        format="%d.%m.%Y %H:%M:%S.%f"
    )

    df_list.append(df)

# Merge all months
final_df = pd.concat(df_list)

# Remove duplicates
final_df.drop_duplicates(subset=["timestamp"], inplace=True)

# Sort chronologically
final_df.sort_values("timestamp", inplace=True)

# Reset index
final_df.reset_index(drop=True, inplace=True)

os.makedirs("data", exist_ok=True)

output_path = "data/XAUUSD_1H_merged.csv"
final_df.to_csv(output_path, index=False)

print("Merged successfully.")
print("Total rows:", len(final_df))
print("Saved to:", output_path)