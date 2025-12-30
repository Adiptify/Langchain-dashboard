import sys
import os

# Add 1_core to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
core_dir = os.path.join(parent_dir, '1_core')
sys.path.insert(0, core_dir)

from date_utils import date_extractor
from datetime import datetime

def test_date_extraction():
    test_queries = [
        "What was the consumption in July 2024?",
        "Show me readings from last 7 days",
        "How is the pump doing last month?",
        "Compare data between 2024-01-01 and 2024-01-15",
        "Who is the top feeder today?"
    ]

    print("="*60)
    print("DATE EXTRACTION VERIFICATION")
    print("="*60)
    print(f"Current Date: {datetime.now().strftime('%Y-%m-%d')}\n")

    for q in test_queries:
        print(f"Query: '{q}'")
        result = date_extractor.extract_date_range(q)
        if result:
            print(f"  Result: {result['start_date']} to {result['end_date']}")
        else:
            print("  Result: No date detected")
        print("-" * 30)

if __name__ == "__main__":
    test_date_extraction()
