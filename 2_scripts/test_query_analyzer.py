import sys
import os

# Add 1_core to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
core_dir = os.path.join(parent_dir, '1_core')
sys.path.insert(0, core_dir)

from query_rewriter import query_analyzer

def test_query_analysis():
    test_queries = [
        "What is the location L21 stands for?",
        "Show me the details for the peak day in July 24",
        "How is Boiler 1 performing compared to main pump?",
        "Where is the I/C-1 panel located?",
        "What was the total consumption of the plant last week?"
    ]

    print("="*60)
    print("QUERY ANALYSIS VERIFICATION")
    print("="*60)

    for q in test_queries:
        print(f"Query: '{q}'")
        result = query_analyzer.analyze_query(q)
        print(f"  Entities: {result['primary_entities']}")
        print(f"  Intent:   {result['intent']}")
        print(f"  Technical Code: {result['has_technical_code']}")
        print("-" * 30)

if __name__ == "__main__":
    test_query_analysis()
