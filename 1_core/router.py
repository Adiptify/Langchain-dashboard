import json
import requests
from typing import Dict, Any, List

from config import SLM_PARSE_MODEL, LLM_REASON_MODEL, LLM_EXPLAIN_MODEL, OLLAMA_BASE_URL
from utils import logger

class QueryRouter:
    """
    Dynamically routes incoming queries using SLM-based intent classification and entity extraction.
    Uses llama3.2:3b for parsing queries and extracting equipment names, dates, and operations.
    """
    def __init__(self):
        logger.info("QueryRouter initialized.")

    def _call_slm_parser(self, query: str) -> Dict[str, Any]:
        """Call SLM to parse query and extract entities"""
        prompt = f"""
You are a strict parser for industrial plant data queries. Given a user's question, output a single JSON object with schema:
{{ 
  "intent": "EXACT_FETCH|FILTER_LIST|AGGREGATE|COMPARE|EXPLAIN|OPINION|UNKNOWN",
  "operation": "sum|avg|max|min|count|list|filter",
  "metric": "energy|consumption|power|temperature|pressure",
  "equipment": ["SCP M/C FDR-2", "SVP machine -3", "isolator room"],
  "dates": ["2025-09-22", "2025-10-22"],
  "filters": [{{"column":"", "op":"equals|contains|greater_than", "value":""}}],
  "group_by": [],
  "limit": 100,
  "confidence": 0.95
}}

Examples:
User: "Show me SCP M/C FDR-2 consumption data"
Output: {{"intent":"EXACT_FETCH","equipment":["SCP M/C FDR-2"],"filters":[{{"column":"equipment","op":"contains","value":"SCP M/C FDR-2"}}],"confidence":0.98}}

User: "Total energy consumption for SVP machine -3 to isolator room from 2025-09-22 to 2025-10-22"
Output: {{"intent":"AGGREGATE","operation":"sum","metric":"energy","equipment":["SVP machine -3","isolator room"],"dates":["2025-09-22","2025-10-22"],"filters":[{{"column":"equipment","op":"contains","value":"SVP machine -3"}},{{"column":"equipment","op":"contains","value":"isolator room"}}],"confidence":0.95}}

User: "Average consumption of SVP machine -3 to isolator room"
Output: {{"intent":"AGGREGATE","operation":"avg","metric":"consumption","equipment":["SVP machine -3","isolator room"],"filters":[{{"column":"equipment","op":"contains","value":"SVP machine -3"}},{{"column":"equipment","op":"contains","value":"isolator room"}}],"confidence":0.9}}

Now parse this query:
"{query}"

Only output JSON. Extract equipment names, dates, and operations accurately.
"""
        
        try:
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": SLM_PARSE_MODEL,
                    "prompt": prompt,
                    "max_tokens": 512,
                    "temperature": 0.0,
                    "stream": False  # Disable streaming for cleaner JSON parsing
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            raw_text = data.get("response", "") or data.get("text", "")
            
            # Extract JSON from response - simplified since SLM returns clean JSON
            raw_text = raw_text.strip()
            
            # Try to parse the response directly as JSON
            try:
                result = json.loads(raw_text)
                logger.info(f"SLM parsed query: {result}")
                return result
            except json.JSONDecodeError:
                # If direct parsing fails, try to extract JSON from the text
                start = raw_text.find('{')
                end = raw_text.rfind('}')
                if start != -1 and end != -1:
                    json_str = raw_text[start:end+1]
                    try:
                        result = json.loads(json_str)
                        logger.info(f"SLM parsed query (extracted): {result}")
                        return result
                    except json.JSONDecodeError as e:
                        logger.warning(f"SLM JSON extraction failed: {e}")
                        logger.warning(f"Raw response: {raw_text}")
                        return {"intent": "UNKNOWN", "equipment": [], "dates": [], "filters": [], "confidence": 0.5}
                else:
                    logger.warning(f"SLM returned non-JSON response: {raw_text}")
                    return {"intent": "UNKNOWN", "equipment": [], "dates": [], "filters": [], "confidence": 0.5}
                
        except Exception as e:
            logger.error(f"SLM parsing failed: {e}")
            return {"intent": "UNKNOWN", "equipment": [], "dates": [], "filters": [], "confidence": 0.5}

    def route_query(self, query: str) -> Dict[str, Any]:
        """Route query using SLM-based parsing"""
        # Parse query with SLM
        parsed = self._call_slm_parser(query)
        
        intent = parsed.get('intent', 'UNKNOWN')
        equipment = parsed.get('equipment', [])
        operation = parsed.get('operation', '')
        
        # Determine route based on intent and operation
        if 'EXACT_FETCH' in intent:
            route = "agent"
            logger.info(f"Routing query '{query}' to Agent (exact fetch)")
        elif 'AGGREGATE' in intent and operation in ['sum', 'avg', 'mean', 'max', 'min', 'count']:
            route = "agent"
            logger.info(f"Routing query '{query}' to Agent (aggregation)")
        elif 'EXPLAIN' in intent or 'explain' in query.lower():
            route = "llm_explain"
            logger.info(f"Routing query '{query}' to LLM (explanation)")
        elif 'COMPARE' in intent or 'analyze' in query.lower() or 'reasoning' in query.lower():
            route = "llm_reason"
            logger.info(f"Routing query '{query}' to LLM (reasoning)")
        else:
            route = "llm_explain"
            logger.info(f"Routing query '{query}' to LLM (default explanation)")
        
        # Handle metric as list or string
        metric = parsed.get('metric', '')
        if isinstance(metric, list):
            metric = metric[0] if metric else ''
        
        # Handle dates - filter out None values
        dates = parsed.get('dates', [])
        if isinstance(dates, list):
            dates = [d for d in dates if d is not None]
        
        return {
            "route": route,
            "model": SLM_PARSE_MODEL if route == "slm_parse" else (LLM_REASON_MODEL if route == "llm_reason" else LLM_EXPLAIN_MODEL),
            "tool": "pandas_calculator" if route == "agent" else None,
            "parsed": parsed,
            "equipment": equipment,
            "dates": dates,
            "operation": operation,
            "metric": metric,
            "filters": parsed.get('filters', [])
        }

# Example Usage (for testing/demonstration)
if __name__ == "__main__":
    router = QueryRouter()

    queries = [
        "Give me the avg consumption of SVP machine -3 to isolator room",
        "Show me SCP M/C FDR-2 energy data",
        "Total energy consumption from 2025-09-22 to 2025-10-22",
        "Explain why energy consumption increased",
        "Compare energy usage between different machines"
    ]

    for q in queries:
        route = router.route_query(q)
        print(f"Query: \"{q}\" -> Route: {route['route']}, Equipment: {route['equipment']}, Operation: {route['operation']}")
