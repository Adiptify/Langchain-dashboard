import json
from typing import Dict, Any, List
from datetime import datetime

from config import LLM_REASON_MODEL, LLM_EXPLAIN_MODEL, OLLAMA_BASE_URL, CLOUD_API_KEY, USE_CLOUD_ENDPOINT
from utils import logger
import requests

class LLMReasoning:
    """
    Handles complex reasoning and explanation tasks using larger LLMs.
    This component will take retrieved context and a query, and generate
    a comprehensive response.
    """
    def __init__(self):
        self.reasoning_model = LLM_REASON_MODEL  # Use actual model name
        self.explanation_model = LLM_EXPLAIN_MODEL  # Use actual model name
        logger.info(f"LLMReasoning initialized with reasoning model: {self.reasoning_model} and explanation model: {self.explanation_model}")

    def _call_ollama_llm(self, prompt: str, model: str, temperature: float = 0.2) -> str:
        """Helper to call LLM (Ollama or Cloud) with retry logic."""
        max_retries = 3
        url = f"{OLLAMA_BASE_URL}/api/generate"
        headers = {}
        
        if USE_CLOUD_ENDPOINT:
            # Assume OpenAI-compatible endpoint for cloud OSS models if needed
            # For now, we still use the /api/generate format but add headers
            if CLOUD_API_KEY:
                headers["Authorization"] = f"Bearer {CLOUD_API_KEY}"
        
        for attempt in range(max_retries):
            try:
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": temperature, "num_gpu": 1}
                }
                response = requests.post(url, json=payload, headers=headers, timeout=180)
                response.raise_for_status()
                response_data = response.json()
                return response_data.get("response", "").strip()
            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed for model {model}: {e}")
                if attempt == max_retries - 1:
                    logger.error(f"Error calling model {model} after {max_retries} attempts: {e}")
                    return f"LLM Error: Could not get response from {model}. Ensure the service is accessible."
                import time
                time.sleep(2)

    def stream_llm_response(self, prompt: str, model: str, temperature: float = 0.2):
        """Streaming version of the LLM call."""
        url = f"{OLLAMA_BASE_URL}/api/generate"
        headers = {}
        if USE_CLOUD_ENDPOINT and CLOUD_API_KEY:
            headers["Authorization"] = f"Bearer {CLOUD_API_KEY}"
            
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": temperature}
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, stream=True, timeout=180)
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line.decode('utf-8'))
                    if 'response' in chunk:
                        yield chunk['response']
                    if chunk.get('done', False):
                        break
        except Exception as e:
            logger.error(f"Streaming error with model {model}: {e}")
            yield f"\n[Streaming Error: {str(e)}]"

    def perform_reasoning(self, query: str, context: List[Dict[str, Any]], chat_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Generates a reasoned answer based on the query, provided context, and chat history.
        """
        context_str = "\n---\n".join([f"Document ID: {d.get('doc_id', 'N/A')}\nContent: {d.get('content', 'N/A')}\nMetadata: {json.dumps(d.get('metadata', {}), indent=2)}" for d in context])
        
        history_str = ""
        if chat_history:
            for entry in chat_history[-3:]: # Include last 3 turns of conversation
                q = entry.get('query') or entry.get('content', '') if entry.get('role') == 'user' else ''
                r = entry.get('response') or entry.get('content', '') if entry.get('role') == 'assistant' else ''
                if q: history_str += f"\nUser: {q}"
                if r: history_str += f"\nMendy: {r}"

        prompt = f"""You are a helpful energy data analyst. Answer questions clearly, informatively, and comprehensively.

Your answers should be:
1. **Direct** - Start with the answer.
2. **Detailed** - Provide specific numbers, comparisons, and insights. Don't be too brief.
3. **Conversational** - Like explaining to a colleague.
4. **Accurate** - Use the exact numbers from the data.
5. **Analytical** - If you see high or low numbers, offer potential reasons or suggestions based on the context (e.g., "Low consumption might indicate downtime").
6. **Clean** - **NEVER** repeat the raw "Context data" or "Document ID" blocks in your output. Only use the information to form your answer.
7. **Speech-Friendly** - Format numbers with commas (e.g., "1,250,000") and units ("KWH") so the voice engine reads them as words, not single digits. DO NOT use scientific notation.
8. **Temporally Aware** - Use the "Current Date" provided below to resolve relative timeframes (e.g., if it's Jan 2025, "last month" is Dec 2024). Correlate numeric months (12) with their names (December) when searching the context data.

Example good answer:
Q: "What is the top feeder in July 2024?"
A: "The top consumer in July 2024 was **I/C Panel (Location: I/C-1)** with 20,585,392 KWH total consumption. This feeder consistently shows the highest readings across the monitoring period, indicating it is the primary power input for the facility."

Context data:
{context_str}

Current Date: {datetime.now().strftime('%Y-%m-%d')}

Question: "{query}"

Answer (be clear, helpful, and DO NOT repeat context):
"""
        logger.info(f"Performing reasoning for query (first 50 chars): {query[:50]}...")
        reasoned_answer = self._call_ollama_llm(prompt, self.reasoning_model, temperature=0.0)

        # Extract provenance from the LLM's response if possible, or infer from context
        provenance_docs = []
        for doc in context:
            doc_id = doc.get('doc_id')
            if doc_id and doc_id in reasoned_answer: # Check if doc_id exists and is in answer
                provenance_docs.append(doc_id)
        
        if not provenance_docs:
            # Fallback: if LLM didn't explicitly mention, include all context doc_ids as potential provenance
            provenance_docs = [d.get('doc_id') for d in context if d.get('doc_id')]

        return {
            "answer": reasoned_answer,
            "type": "Mendy-Reasoning", # Branded type
            "provenance": provenance_docs
        }

    def perform_streaming_reasoning(self, query: str, context: List[Dict[str, Any]], chat_history: List[Dict[str, str]] = None):
        """Generator version of perform_reasoning for Streamlit's st.write_stream."""
        context_str = "\n---\n".join([f"Document ID: {d.get('doc_id', 'N/A')}\nContent: {d.get('content', 'N/A')}\nMetadata: {json.dumps(d.get('metadata', {}), indent=2)}" for d in context])
        
        prompt = f"""You are a helpful energy data analyst. Answer questions clearly, informatively, and comprehensively.
        Use the following context to answer.
        
        Context data:
        {context_str if context_str else "No specific context data found. Answer as a general assistant."}
        
        Question: "{query}"
        
        Answer (be clear, helpful, and DO NOT repeat context or document IDs. If no context is provided, answer using your general knowledge as an AI energy assistant. 
        Note that today's date is {datetime.now().strftime('%Y-%m-%d')}):
        """
        logger.info(f"Performing streaming reasoning for query: {query[:50]}...")
        return self.stream_llm_response(prompt, self.reasoning_model, temperature=0.0)

    def generate_explanation(self, query: str, context: List[Dict[str, Any]], chat_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Generates an explanation or summary based on the query, provided context, and chat history.
        """
        context_str = "\n---\n".join([f"Document ID: {d.get('doc_id', 'N/A')}\nContent: {d.get('content', 'N/A')}\nMetadata: {json.dumps(d.get('metadata', {}), indent=2)}" for d in context])

        history_str = ""
        if chat_history:
            for entry in chat_history[-3:]: # Include last 3 turns of conversation
                history_str += f"\nUser: {entry['query']}\nMendy: {entry['response']}"

        prompt = f"""
        You are Mendy, an AI assistant designed to provide clear, concise, and human-like explanations and summaries.
        Based on the following context documents and previous conversation, provide a comprehensive explanation or summary to answer the query.
        Ensure your explanation is easy to understand and directly addresses the user's request. Always maintain a friendly and professional tone.
        Cite the Document IDs for the information you use.

        Previous Conversation (if any):
        {history_str}

        Query: "{query}"

        Context Documents:
        {context_str}

        Explanation/Summary from Mendy:
        """
        logger.info(f"Generating explanation for query (first 50 chars): {query[:50]}...")
        explanation = self._call_ollama_llm(prompt, self.explanation_model)

        # Extract provenance
        provenance_docs = []
        for doc in context:
            doc_id = doc.get('doc_id')
            if doc_id and doc_id in explanation: # Check if doc_id exists and is in explanation
                provenance_docs.append(doc_id)

        if not provenance_docs:
            provenance_docs = [d.get('doc_id') for d in context if d.get('doc_id')]

        return {
            "answer": explanation,
            "type": "Mendy-Explanation", # Branded type
            "provenance": provenance_docs
        }

# Example Usage (for testing/demonstration)
if __name__ == "__main__":
    llm_reasoning = LLMReasoning()

    # Dummy context documents for demonstration
    dummy_context = [
        {
            "doc_id": "doc1",
            "content": "The sales of product A increased by 15% in Q1 due to a successful marketing campaign.",
            "metadata": {"source": "sales_report.pdf", "page": 5}
        },
        {
            "doc_id": "doc2",
            "content": "Product B saw a 5% decrease in sales in the same quarter, possibly due to increased competition.",
            "metadata": {"source": "competitor_analysis.docx", "page": 2}
        }
    ]

    query_reason = "Why did sales of product A increase in Q1?"
    reason_result = llm_reasoning.perform_reasoning(query_reason, dummy_context)
    print(f"\nReasoning Result for \'{query_reason}\':")
    print(f"Answer: {reason_result['answer']}")
    print(f"Provenance: {reason_result['provenance']}")

    query_explain = "Summarize the sales performance of Product B in Q1."
    explain_result = llm_reasoning.generate_explanation(query_explain, dummy_context)
    print(f"\nExplanation Result for \'{query_explain}\':")
    print(f"Answer: {explain_result['answer']}")
    print(f"Provenance: {explain_result['provenance']}")
