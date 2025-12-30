import pandas as pd
import sys
import os

# Add core to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../1_core')))
from smart_preprocessor import JSWEnergyPreprocessor

def test_aggregation():
    p = JSWEnergyPreprocessor()
    
    # Mock data with Incomers and Feeders
    data = {
        'Description': ['MAIN I/C', 'FEEDER 1', 'FEEDER 2', 'PLANT TOTAL'],
        'SWB No': ['MAIN', 'SUB1', 'SUB1', 'TOTAL'],
        '30-06-2024': [0, 0, 0, 0],   # Baseline for delta
        '01-07-2024': [100, 40, 60, 100], 
        '02-07-2024': [250, 110, 140, None], # (250-100=150)
        '03-07-2024': [None, 160, 200, None], # (160-110=50, 200-140=60 => sum 110)
    }
    df = pd.DataFrame(data)
    
    # We can't easily run process_file because it needs an Excel file
    # But we can test the logic if we extract it or run a mini-mock
    print("Testing JSWEnergyPreprocessor logic manually...")
    
    # This is a bit complex as process_file does a lot of heavy lifting.
    # Instead, let's create a temporary Excel file to test.
    test_excel = "test_mock_data.xlsx"
    with pd.ExcelWriter(test_excel) as writer:
        df.to_excel(writer, sheet_name='JUL-24', index=False)
    
    try:
        docs = p.process_file(test_excel)
        
        daily_totals = {}
        for doc in docs:
            if doc.doc_type == 'daily_total':
                daily_totals[doc.metadata['date']] = doc.metadata['total']
        
        print("\nResults:")
        expected = {
            '2024-07-01': 100.0,
            '2024-07-02': 150.0,
            '2024-07-03': 110.0
        }
        
        passed = True
        for date, val in expected.items():
            actual = daily_totals.get(date)
            status = "✅" if actual == val else f"❌ (Expected {val}, got {actual})"
            print(f"Date {date}: {status}")
            if actual != val:
                passed = False
        
        if passed:
            print("\nSUCCESS: Hierarchical aggregation works correctly!")
        else:
            print("\nFAILED: Aggregation logic error.")
            
    finally:
        if os.path.exists(test_excel):
            os.remove(test_excel)

if __name__ == "__main__":
    test_aggregation()
