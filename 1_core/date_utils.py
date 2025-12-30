import json
import requests
from datetime import datetime
from typing import Optional, Dict, Any
from config import SLM_PARSE_MODEL, OLLAMA_BASE_URL
from utils import logger

class DateExtractor:
    """
    Uses SLM to extract structured date ranges from natural language queries.
    """
    def __init__(self):
        self.model = SLM_PARSE_MODEL

    def extract_date_range(self, query: str) -> Optional[Dict[str, str]]:
        """
        Extracts start_date and end_date from a query.
        Returns e.g., {"start_date": "2024-07-01", "end_date": "2024-07-31"}
        """
        today = datetime.now().strftime("%Y-%m-%d")
        
        prompt = f"""Extract the date range (start and end) mentioned or implied in the query.
If relative terms are used (e.g., 'last month', '7 days ago'), use Today's Date to resolve them.
If a specific month is mentioned, return the full range of that month.
If no date is mentioned, return null.

Today's Date: {today}
Query: "{query}"

Respond ONLY with a JSON object: {{"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}} or null.
JSON:"""

        try:
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.0},
                    "format": "json"
                },
                timeout=30
            )
            response.raise_for_status()
            result_raw = response.json().get("response", "").strip()
            
            if not result_raw or result_raw.lower() == 'null':
                return None
                
            data = json.loads(result_raw)
            if data and "start_date" in data and "end_date" in data:
                return data
            return None
        except Exception as e:
            logger.error(f"Error extracting date range: {e}")
            return None

# Singleton instance
date_extractor = DateExtractor()
