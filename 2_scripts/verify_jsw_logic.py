import sys
import os
import pandas as pd
import numpy as np

# Add 1_core to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
core_dir = os.path.join(parent_dir, '1_core')
sys.path.insert(0, core_dir)

from smart_preprocessor import JSWEnergyPreprocessor
import json

def run_logic_verification():
    preprocessor = JSWEnergyPreprocessor()
    
    # Create a mock JSW energy report style dataframe
    data = {
        'Description': [
            'TOTAL PLANT',          # Total Row
            'Panel I/C 1',          # Incomer 1
            'Panel I/C 2',          # Incomer 2
            'Feeder A',             # Regular Feeder
            'Feeder B',             # Regular Feeder
            'Feeder C (Difference)'  # Malformed row? No, just a regular feeder
        ],
        'Reading 15-01-2024': [10000, 5000, 5000, 2000, 2000, 1000],
        'Reading 26-01-2024': [12458, 6229, 6229, 2500, 2500, 1229],
        'Difference': [2458, 1229, 1229, 500, 500, 229] 
    }
    
    df = pd.DataFrame(data)
    
    print("="*60)
    print("LOGIC VERIFICATION: JSW AGGREGATION")
    print("="*60)
    print("Input Data Structure:")
    print(df)
    print("-" * 30)

    # We need to simulate the multi-column "Difference" renaming by pandas
    # Let's say we have two dates, so pandas renmes the 'Difference' columns
    df.columns = ['Description', 'R 15-01-24', 'R 26-01-24', 'Difference'] 
    
    # In reality, JSW files often have:
    # Reading 15, Reading 16, Difference, Difference
    # Pandas makes them: Reading 15, Reading 16, Difference, Difference.1
    
    complex_data = {
        'Description': ['TOTAL PLANT', 'I/C 1', 'Feeder 1'],
        '15-01-24': [1000, 500, 500],
        '26-01-24': [2458, 1229, 1229],
        'Diff': [1000, 500, 500],   # This matches 15-01-24
        'Diff.1': [2458, 1229, 1229] # This matches 26-01-24
    }
    df_complex = pd.DataFrame(complex_data)
    
    # Run the preprocessor logic
    # We'll mock the internal calls since we don't want to write to disk
    docs = preprocessor.process_file_object(df_complex, "TestFile", "JAN-24")
    
    print("\nExtraction Results:")
    found_dates = set()
    total_consumption = 0
    
    for doc in docs:
        if doc.doc_type == "industrial_data":
            # Check period in content
            content = doc.content
            print(f"  Doc: {content}")
            if "Total:" in content:
                try:
                    val = float(content.split("Total: ")[1].split(" KWH")[0])
                    # Avoid double counting by only looking at specific doc markers if we had them
                    pass 
                except: pass

    # The real verification is in the internal state which we can check by looking at the summary docs if created
    summary_docs = [d for d in docs if d.doc_type == "plant_summary"]
    for s in summary_docs:
        print(f"  Summary: {s.content}")

    print("\nLogic Check:")
    print("1. Did 'Diff.1' map to 26-01-2024? (Check if 2458 is the peak)")
    print("2. Is the total exactly 2458 (from Total row) or 1229+? (No double counting)")
    
if __name__ == "__main__":
    # We need to add a method to preprocessor to handle direct DF for testing
    # Or just run it through a temp file. Let's use a temp excel.
    
    temp_excel = "jsw_test_logic.xlsx"
    with pd.ExcelWriter(temp_excel) as writer:
        # Create a JSW style sheet
        mock_jsw = pd.DataFrame([
            ['', '', '', '', ''],
            ['', '', '', '', ''],
            ['', '', '', '', ''],
            ['Description', '15-01-2024', '26-01-2024', 'Diff', 'Diff'], # Header at row 4
            ['TOTAL PLANT', 1000, 3458, 1000, 2458],
            ['I/C 1', 1000, 3458, 1000, 2458], # This is an incomer
            ['Feeder A', 500, 1500, 500, 1000],
            ['Feeder B', 500, 1958, 500, 1458],
        ])
        mock_jsw.to_excel(writer, sheet_name='JAN-24', index=False, header=False)
        
    print("="*60)
    print("PHASE 2: EXCEL LOGIC VERIFICATION")
    print("="*60)
    
    preprocessor = JSWEnergyPreprocessor()
    docs = preprocessor.process_file(temp_excel)
    
    print("\nDocument Inspection:")
    doc_types = {}
    for doc in docs:
        dtype = doc.doc_type
        doc_types[dtype] = doc_types.get(dtype, 0) + 1
        
        # Verify metadata
        if 'created_at' not in doc.metadata:
            print(f"  🚨 MISSING created_at: {doc.doc_id} ({dtype})")
            
        if doc.doc_type == "plant_summary":
            print(f"  Summary Doc: {doc.content}")
        elif "TOTAL" in doc.content.upper() and doc.doc_type == "daily_total":
             print(f"  Total Info: {doc.content}")
    
    print("\nDocument Statistics:")
    for dtype, count in doc_types.items():
        print(f"  - {dtype}: {count}")
    
    # Logic Checks
    print("\nLogic Verification:")
    if doc_types.get('industrial_data', 0) == 3: # 3 feeders
        print("  ✅ Duplication: Resolved (Exactly 3 feeder docs created)")
    else:
        print(f"  ❌ Duplication: {doc_types.get('industrial_data', 0)} docs found (!= 3)")
            
    # Clean up
    try:
        os.remove(temp_excel)
    except: pass
