import sys
import os
import pandas as pd
from datetime import datetime

# Add 1_core to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
core_dir = os.path.join(parent_dir, '1_core')
sys.path.insert(0, core_dir)

from smart_preprocessor import JSWEnergyPreprocessor

def test_strict_date_parsing():
    preprocessor = JSWEnergyPreprocessor()
    test_cases = [
        ("2024-07-01", "2024-07-01"),
        ("01-07-2024", "2024-07-01"),
        ("15", "15"), # Numeric day
        ("Difference.14", None), # Should be REJECTED now
        ("SL NO", None), # Should be REJECTED now
        ("45474", "2024-07-01"), # Excel serial
        ("32", None), # Invalid day
    ]
    
    print("="*60)
    print("STRICT DATE PARSING VERIFICATION")
    print("="*60)
    
    for input_val, expected in test_cases:
        actual = preprocessor.attempt_date_parse(input_val, {"month": "07", "year": "2024"})
        status = "PASS" if actual == expected else "FAIL"
        print(f"Input: '{input_val:15}' | Expected: {str(expected):12} | Actual: {str(actual):12} | {status}")

if __name__ == "__main__":
    test_strict_date_parsing()
