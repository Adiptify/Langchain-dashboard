"""
Suggestion engine for the LangChain agentic dashboard.
Generates daily briefings and data-driven query suggestions for users.
"""

import json
from typing import List, Dict, Any
from datetime import datetime
from user_profiles import user_profile_manager
from llm_reasoning import LLMReasoning
from utils import logger
from config import LLM_REASON_MODEL

from embedding_store import EmbeddingStore

class SuggestionEngine:
    def __init__(self):
        self.llm = LLMReasoning()
        self.store = EmbeddingStore()
        
    def generate_daily_briefing(self, user_id: str) -> str:
        """Generate a daily briefing for the user based on real plant data and user history."""
        analytics = user_profile_manager.get_user_analytics(user_id, days=7)
        profile = user_profile_manager.get_user_profile(user_id)
        
        # Fetch real plant stats
        plant_stats = self.store.get_latest_plant_stats()
        summary = plant_stats.get('summary')
        daily_history = plant_stats.get('daily_history', [])
        
        # Format plant data for the prompt
        plant_data_context = "No plant data available yet."
        if summary:
            plant_data_context = f"Total Plant Consumption: {summary['metadata'].get('total', 0):,.1f} KWH"
            if daily_history:
                history_str = "\n".join([f"- {d['content']}" for d in daily_history])
                plant_data_context += f"\nRecent Daily Trends:\n{history_str}"
        
        prompt = f"""You are Mendy, an AI assistant for the JSW Energy Dashboard. Generate a concise, friendly daily briefing for {profile.username if profile else 'User'}.
        
        REAL-TIME PLANT DATA:
        {plant_data_context}
        
        USER ACTIVITY (Last 7 Days):
        - Total Searches: {analytics['total_searches']}
        - Success Rate: {analytics['success_rate']:.1f}%
        
        Current Date: {datetime.now().strftime('%Y-%m-%d')}
        
        BRIEFING REQUIREMENTS:
        1. Keep it under 150 words.
        2. Analyze the plant data: mention the total consumption or a recent trend.
        3. Provide one actionable KPI insight (e.g., 'Consumption is steady' or 'Check the peak on [Date]').
        4. Suggest a specific data query based on the current plant status.
        5. Use a professional, expert tone.
        
        DAILY BRIEFING:
        """
        
        # Use the reasoning model for briefing generation
        briefing = self.llm._call_ollama_llm(prompt, LLM_REASON_MODEL)
        user_profile_manager.update_briefing_date(user_id)
        return briefing

    def get_query_suggestions(self, user_id: str, limit: int = 5) -> List[str]:
        """Get intelligent query suggestions for the user based on real plant data."""
        analytics = user_profile_manager.get_user_analytics(user_id, days=30)
        
        # 1. Base suggestions from user history
        history_queries = [q['query'] for q in analytics['common_queries'][:2]]
        
        # 2. Data-driven suggestions from real feeders in the system
        data_suggestions = []
        try:
            # Get a sample of recent feeders to suggest queries for them
            recent_feeders = self.store.get_documents_by_type("feeder_data", limit=5)
            for doc in recent_feeders:
                feeder_name = doc['metadata'].get('feeder')
                if feeder_name and len(data_suggestions) < 3:
                    data_suggestions.append(f"Check the consumption for {feeder_name}")
                    data_suggestions.append(f"Show me the avg daily load for {feeder_name}")
        except Exception as e:
            logger.warning(f"Failed to generate data-driven suggestions: {e}")

        # 3. Intelligent general suggestions
        general_suggestions = [
            "What was the total energy used this month?",
            "Identify the highest consuming feeder",
            "Are there any consumption anomalies today?",
            "Summarize the daily plant totals"
        ]
        
        # Combine all, preserving history first
        combined = history_queries + data_suggestions + general_suggestions
        
        # Remove duplicates and return limited list
        seen = set()
        final = []
        for q in combined:
            if q not in seen:
                final.append(q)
                seen.add(q)
        
        return final[:limit]

# Global instance
suggestion_engine = SuggestionEngine()
