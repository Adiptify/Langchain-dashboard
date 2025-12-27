"""
User profile and personalization system for the LangChain agentic dashboard.
Manages user preferences, custom filters, and personalized experiences.
"""

import json
import sqlite3
import uuid
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class UserProfile:
    """User profile data structure"""
    user_id: str
    username: str
    email: Optional[str] = None
    preferences: Dict[str, Any] = None
    created_at: str = None
    last_active: str = None
    total_sessions: int = 0
    total_queries: int = 0
    favorite_queries: List[str] = None
    custom_filters: Dict[str, Any] = None
    dashboard_layout: Dict[str, Any] = None
    notification_settings: Dict[str, bool] = None
    last_briefing_date: Optional[str] = None

@dataclass
class SearchFilter:
    """Search filter configuration"""
    filter_id: str
    name: str
    filter_type: str  # 'date_range', 'file_type', 'content_type', 'custom'
    parameters: Dict[str, Any]
    is_default: bool = False

class UserProfileManager:
    """
    Manages user profiles, preferences, and personalization features.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            from config import DATA_DIR
            db_path = os.path.join(DATA_DIR, "user_profiles.db")
        print(f"DEBUG: UserProfileManager initialized with db_path: {db_path}")
        self.db_path = db_path
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize user profiles database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # User profiles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT,
                preferences TEXT,
                created_at TEXT NOT NULL,
                last_active TEXT,
                total_sessions INTEGER DEFAULT 0,
                total_queries INTEGER DEFAULT 0,
                favorite_queries TEXT,
                custom_filters TEXT,
                dashboard_layout TEXT,
                notification_settings TEXT,
                last_briefing_date TEXT
            )
        """)
        
        # Create query_history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS query_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                query TEXT,
                response TEXT,
                timestamp TEXT,
                metadata TEXT,
                FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
            )
        """)
        
        # User search history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                query TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                result_count INTEGER,
                success BOOLEAN,
                FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
            )
        """)
        
        # User saved queries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS saved_queries (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                query TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                last_used TEXT,
                use_count INTEGER DEFAULT 0,
                tags TEXT,
                FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
            )
        """)
        
        # User custom filters table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS custom_filters (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                filter_type TEXT NOT NULL,
                parameters TEXT NOT NULL,
                is_default BOOLEAN DEFAULT FALSE,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def create_user_profile(self, username: str, email: Optional[str] = None) -> str:
        """Create a new user profile"""
        user_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        default_preferences = {
            "theme": "light",
            "language": "en",
            "timezone": "UTC",
            "date_format": "YYYY-MM-DD",
            "number_format": "en-US",
            "auto_save_queries": True,
            "show_tips": True,
            "default_file_limit": 100
        }
        
        default_notifications = {
            "email_notifications": False,
            "processing_complete": True,
            "error_alerts": True,
            "weekly_summary": False
        }
        
        profile = UserProfile(
            user_id=user_id,
            username=username,
            email=email,
            preferences=default_preferences,
            created_at=now,
            last_active=now,
            favorite_queries=[],
            custom_filters={},
            dashboard_layout={},
            notification_settings=default_notifications
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO user_profiles (user_id, username, email, preferences, created_at, 
                                    last_active, favorite_queries, custom_filters, 
                                    dashboard_layout, notification_settings, last_briefing_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, username, email, json.dumps(default_preferences), now, now,
            json.dumps([]), json.dumps({}), json.dumps({}), json.dumps(default_notifications), None
        ))
        
        conn.commit()
        conn.close()
        
        return user_id
    
    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, username, email, preferences, created_at, last_active,
                   total_sessions, total_queries, favorite_queries, custom_filters,
                   dashboard_layout, notification_settings, last_briefing_date
            FROM user_profiles WHERE user_id = ?
        """, (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return UserProfile(
            user_id=row[0],
            username=row[1],
            email=row[2],
            preferences=json.loads(row[3]) if row[3] else {},
            created_at=row[4],
            last_active=row[5],
            total_sessions=row[6] or 0,
            total_queries=row[7] or 0,
            favorite_queries=json.loads(row[8]) if row[8] else [],
            custom_filters=json.loads(row[9]) if row[9] else {},
            dashboard_layout=json.loads(row[10]) if row[10] else {},
            notification_settings=json.loads(row[11]) if row[11] else {},
            last_briefing_date=row[12]
        )
    
    def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]):
        """Update user preferences"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE user_profiles 
            SET preferences = ?, last_active = ?
            WHERE user_id = ?
        """, (json.dumps(preferences), datetime.now().isoformat(), user_id))
        
        conn.commit()
        conn.close()
    
    def add_favorite_query(self, user_id: str, query: str):
        """Add a query to user's favorites"""
        profile = self.get_user_profile(user_id)
        if not profile:
            return
        
        if query not in profile.favorite_queries:
            profile.favorite_queries.append(query)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE user_profiles 
                SET favorite_queries = ?
                WHERE user_id = ?
            """, (json.dumps(profile.favorite_queries), user_id))
            
            conn.commit()
            conn.close()
    
    def save_query(self, user_id: str, name: str, query: str, 
                   description: str = "", tags: List[str] = None) -> str:
        """Save a query for future use"""
        query_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO saved_queries (id, user_id, name, query, description, 
                                     created_at, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (query_id, user_id, name, query, description, now, json.dumps(tags or [])))
        
        conn.commit()
        conn.close()
        
        return query_id
    
    def get_saved_queries(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's saved queries"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, query, description, created_at, last_used, 
                   use_count, tags
            FROM saved_queries 
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
        
        queries = []
        for row in cursor.fetchall():
            queries.append({
                "id": row[0],
                "name": row[1],
                "query": row[2],
                "description": row[3],
                "created_at": row[4],
                "last_used": row[5],
                "use_count": row[6] or 0,
                "tags": json.loads(row[7]) if row[7] else []
            })
        
        conn.close()
        return queries
    
    def use_saved_query(self, query_id: str):
        """Mark a saved query as used"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE saved_queries 
            SET use_count = use_count + 1, last_used = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), query_id))
        
        conn.commit()
        conn.close()
    
    def create_custom_filter(self, user_id: str, name: str, filter_type: str, 
                           parameters: Dict[str, Any], is_default: bool = False) -> str:
        """Create a custom search filter"""
        filter_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO custom_filters (id, user_id, name, filter_type, parameters, 
                                      is_default, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (filter_id, user_id, name, filter_type, json.dumps(parameters), 
              is_default, now))
        
        conn.commit()
        conn.close()
        
        return filter_id
    
    def get_custom_filters(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's custom filters"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, filter_type, parameters, is_default, created_at
            FROM custom_filters 
            WHERE user_id = ?
            ORDER BY is_default DESC, created_at DESC
        """, (user_id,))
        
        filters = []
        for row in cursor.fetchall():
            filters.append({
                "id": row[0],
                "name": row[1],
                "filter_type": row[2],
                "parameters": json.loads(row[3]),
                "is_default": bool(row[4]),
                "created_at": row[5]
            })
        
        conn.close()
        return filters
    
    def get_search_suggestions(self, user_id: str, partial_query: str, limit: int = 10) -> List[str]:
        """Get search suggestions based on user's history and saved queries"""
        suggestions = []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get from search history
        cursor.execute("""
            SELECT DISTINCT query, COUNT(*) as frequency
            FROM search_history 
            WHERE user_id = ? AND query LIKE ? AND success = 1
            GROUP BY query
            ORDER BY frequency DESC, timestamp DESC
            LIMIT ?
        """, (user_id, f"%{partial_query}%", limit // 2))
        
        for row in cursor.fetchall():
            suggestions.append(row[0])
        
        # Get from saved queries
        cursor.execute("""
            SELECT query
            FROM saved_queries 
            WHERE user_id = ? AND (query LIKE ? OR name LIKE ?)
            ORDER BY use_count DESC, created_at DESC
            LIMIT ?
        """, (user_id, f"%{partial_query}%", f"%{partial_query}%", limit // 2))
        
        for row in cursor.fetchall():
            if row[0] not in suggestions:
                suggestions.append(row[0])
        
        conn.close()
        return suggestions[:limit]
    
    def log_search(self, user_id: str, query: str, result_count: int, success: bool):
        """Log a search query"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO search_history (id, user_id, query, timestamp, result_count, success)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), user_id, query, datetime.now().isoformat(), 
              result_count, success))
        
        # Update user's total query count
        cursor.execute("""
            UPDATE user_profiles 
            SET total_queries = total_queries + 1, last_active = ?
            WHERE user_id = ?
        """, (datetime.now().isoformat(), user_id))
        
        conn.commit()
        conn.close()
    
    def get_user_analytics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get user analytics and insights"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get search statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_searches,
                COUNT(CASE WHEN success = 1 THEN 1 END) as successful_searches,
                AVG(result_count) as avg_results,
                COUNT(DISTINCT DATE(timestamp)) as active_days
            FROM search_history 
            WHERE user_id = ? AND timestamp >= datetime('now', '-{} days')
        """.format(days), (user_id,))
        
        search_stats = cursor.fetchone()
        
        # Get most common queries
        cursor.execute("""
            SELECT query, COUNT(*) as frequency
            FROM search_history 
            WHERE user_id = ? AND timestamp >= datetime('now', '-{} days')
            GROUP BY query
            ORDER BY frequency DESC
            LIMIT 10
        """.format(days), (user_id,))
        
        common_queries = cursor.fetchall()
        
        # Get saved queries usage
        cursor.execute("""
            SELECT COUNT(*) as total_saved, SUM(use_count) as total_uses
            FROM saved_queries 
            WHERE user_id = ?
        """, (user_id,))
        
        saved_stats = cursor.fetchone()
        
        conn.close()
        
        return {
            "total_searches": search_stats[0] or 0,
            "successful_searches": search_stats[1] or 0,
            "success_rate": (search_stats[1] or 0) / (search_stats[0] or 1) * 100,
            "avg_results": search_stats[2] or 0,
            "active_days": search_stats[3] or 0,
            "common_queries": [{"query": q[0], "frequency": q[1]} for q in common_queries],
            "total_saved_queries": saved_stats[0] or 0,
            "total_saved_uses": saved_stats[1] or 0
        }

    def check_first_login_of_day(self, user_id: str) -> bool:
        """Check if this is the user's first login today for briefing purposes"""
        profile = self.get_user_profile(user_id)
        if not profile:
            return False
            
        today = datetime.now().date().isoformat()
        if not profile.last_briefing_date or profile.last_briefing_date != today:
            return True
        return False

    def update_briefing_date(self, user_id: str):
        """Update the last briefing date to today"""
        today = datetime.now().date().isoformat()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE user_profiles 
            SET last_briefing_date = ?
            WHERE user_id = ?
        """, (today, user_id))
        
        conn.commit()
        conn.close()

# Global user profile manager instance
user_profile_manager = UserProfileManager()
