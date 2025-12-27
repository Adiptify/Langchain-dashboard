import sys
import os

# Add core to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '1_core')))

from suggestion_engine import suggestion_engine

try:
    print("Generating query suggestions...")
    suggestions = suggestion_engine.get_query_suggestions("test_user")
    print(f"Suggestions: {suggestions}")
    
    print("Generating daily briefing...")
    briefing = suggestion_engine.generate_daily_briefing("test_user")
    print(f"Briefing: {briefing}")
except Exception as e:
    print(f"Error: {e}")
