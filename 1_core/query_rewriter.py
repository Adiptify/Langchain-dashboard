import json
import requests
from typing import Dict, Any, List, Optional
from config import SLM_PARSE_MODEL, OLLAMA_BASE_URL
from utils import logger

class QueryAnalyzer:
    """
    Decomposes user queries into searchable entities and intent using SLM.
    Used to bridge the gap between semantic search and technical specificity.
    """
    def __init__(self):
        self.model = SLM_PARSE_MODEL

    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyzes a query to extract:
        - primary_entities: List of technical IDs or equipment names (e.g., L21, I/C-1)
        - intent: The "searchable essence" of the query for RAG (e.g., "location of L21")
        - has_technical_code: Boolean indicating if a specific device/location ID was found
        """
        prompt = f"""Decompose the following industrial user query into its core searchable components for a RAG system.

Your goal is to "fetch the real query" by stripping away conversational filler and identifying specific technical entities that MUST be found.

Technical entities are specific machine codes (e.g., L21, I/C-1), equipment names (e.g., Boiler, Pump), or locations.
The intent should be a concise, searchable string that captures what exactly is being asked about those entities.

Query: "{query}"

Respond ONLY with a JSON object:
{{
  "primary_entities": ["L21"], 
  "intent": "location of L21",
  "has_technical_code": true
}}
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
            
            data = json.loads(result_raw)
            return {
                "primary_entities": data.get("primary_entities", []),
                "intent": data.get("intent", query),
                "has_technical_code": data.get("has_technical_code", False)
            }
        except Exception as e:
            logger.error(f"Error analyzing query: {e}")
            return {
                "primary_entities": [],
                "intent": query,
                "has_technical_code": False
            }

# Singleton instance
query_analyzer = QueryAnalyzer()
