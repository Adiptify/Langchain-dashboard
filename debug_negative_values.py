import pandas as pd

file_path = "4_data/Energy Consumption Daily Report MHS Ele - Copy.xlsx"
sheet_name = "JULY24"

print(f"--- Scanning {sheet_name} for negative values ---")
df = pd.read_excel(file_path, sheet_name=sheet_name, header=0)

# Identify difference columns
diff_cols = [col for col in df.columns if "diff" in str(col).lower()]
print(f"Difference columns found: {diff_cols}")

for col in diff_cols:
    neg_vals = df[df[col] < 0]
    if not neg_vals.empty:
        print(f"\nNegative values in {col}:")
        print(neg_vals[[df.columns[0], col]].head())
    else:
        print(f"No negative values in {col}")
