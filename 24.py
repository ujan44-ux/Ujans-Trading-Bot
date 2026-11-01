import pandas as pd

# Full path to your file (update filename if needed, e.g., XAU_5m.csv)

# Load with SEMICOLON separator
df = pd.read_csv("XAU_5m_data.csv", sep=';')

print("Columns:", df.columns.tolist())
print("\nFirst few rows:")
print(df.head())

# Parse datetime column (handles 2004.06.11 07:15 format)
df['datetime'] = pd.to_datetime(df['datetime'], format='%Y.%m.%d %H:%M')

# Filter 2015-2025
df_filtered = df[(df['datetime'].dt.year >= 2015) & (df['datetime'].dt.year <= 2025)].reset_index(drop=True)

# Save filtered
df_filtered.to_csv("xau.csv", index=False)

print(f"\nOriginal rows: {len(df):,}")
print(f"Filtered rows: {len(df_filtered):,}")
print("\nFiltered head:")
print(df_filtered.head())
