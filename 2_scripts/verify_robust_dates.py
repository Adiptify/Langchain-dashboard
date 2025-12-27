import sys
import os
import pandas as pd
from datetime import datetime

# Add core to path
sys.path.append(os.path.join(os.getcwd(), '1_core'))

from smart_preprocessor import JSWEnergyPreprocessor

def test_robust_date_parsing():
    p = JSWEnergyPreprocessor()
    
    print("="*60)
    print("ROBUST DATE PARSING VERIFICATION")
    print("="*60)
    
    test_cases = [
        # (input_value, sheet_name, expected_output)
        ("2024-12-01", "DEC-24", "2024-12-01"),
        (45620, "DEC-24", "2024-11-24"), # Excel serial date
        ("12", "DEC-24", "2024-12-12"),  # Numeric day with context
        ("1", "AUG-24", "2024-08-01"),   # Numeric day with context
        ("246885", "JULY24", None),      # Random large number (should be rejected)
        ("103.1", "JULY24", None),       # Floating point (should be rejected)
        ("100", "Sheet1", None),         # Out of range for day, no context
        ("SL NO", "DEC-24", "SL NO")      # Non-numeric string (passes through as is, filtered later)
    ]
    
    all_passed = True
    for val, sheet, expected in test_cases:
        context = p._parse_sheet_context(sheet)
        result = p.attempt_date_parse(val, context)
        
        status = "✅ PASS" if result == expected else "❌ FAIL"
        if result != expected:
            all_passed = False
            
        print(f"Input: {val:<10} | Sheet: {sheet:<10} | Result: {str(result):<12} | Expected: {str(expected):<12} | {status}")
    
    print("\n" + "="*60)
    if all_passed:
        print("VERIFICATION SUCCESSFUL: All date edge cases handled correctly.")
    else:
        print("VERIFICATION FAILED: Some cases did not match expected output.")
    print("="*60)

if __name__ == "__main__":
    test_robust_date_parsing()
