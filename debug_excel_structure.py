import pandas as pd

file_path = "4_data/Energy Consumption Daily Report MHS Ele - Copy.xlsx"
sheet_name = "JULY24"  # Check one of the monthly sheets

print(f"--- Inspecting {sheet_name} ---")
df = pd.read_excel(file_path, sheet_name=sheet_name, header=0)

# Print columns
print("Columns:", list(df.columns)[:10])

# Print first 5 rows
print("\nFirst 5 rows:")
print(df.iloc[:5, :10])

# Check specifically for I/C Panel
print("\nSearching for I/C Panel:")
ic_panel = df[df.iloc[:, 0].astype(str).str.contains("I/C Panel", case=False, na=False)]
if not ic_panel.empty:
    print(ic_panel.iloc[:, :10])
else:
    print("I/C Panel not found in first 10 columns/rows")
