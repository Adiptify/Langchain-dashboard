import faiss
import numpy as np
import json
import os
import requests
import sqlite3
import re
import difflib
from typing import List, Dict, Any, Optional
import time # Added for timing in _get_embedding

from config import EMBED_MODEL, OLLAMA_BASE_URL, FAISS_INDEX_FILE, ID_MAP_FILE, METADATA_DB_PATH
from utils import logger, log_process_completion
from ingestion_pipeline import Document # Assuming Document class is in ingestion_pipeline

class EmbeddingStore:
    def __init__(self):
        self.faiss_index = None
        self.doc_id_to_faiss_id = {}
        self.faiss_id_to_doc_id = {} # Map FAISS index id (str) -> our doc_ids
        self.embedding_dimension = None
        self.ollama_base_url = OLLAMA_BASE_URL
        self.embedding_model = EMBED_MODEL
        self._init_db()
        self._load_or_create_index()

    def _init_db(self):
        conn = sqlite3.connect(METADATA_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                file_id TEXT,
                file_name TEXT,
                doc_type TEXT,
                content TEXT,
                metadata TEXT
            )
        """)
        conn.commit()
        conn.close()
        log_process_completion("Metadata DB initialization", details="Ensured documents table exists")

    def _load_or_create_index(self):
        if os.path.exists(FAISS_INDEX_FILE) and os.path.exists(ID_MAP_FILE):
            try:
                self.faiss_index = faiss.read_index(FAISS_INDEX_FILE)
                with open(ID_MAP_FILE, 'r') as f:
                    self.doc_id_to_faiss_id = json.load(f)
                # Reconstruct faiss_id_to_doc_id from doc_id_to_faiss_id
                self.faiss_id_to_doc_id = {str(v): k for k, v in self.doc_id_to_faiss_id.items()}
                logger.info(f"Loaded FAISS index with {self.faiss_index.ntotal} documents and dimension {self.faiss_index.d}")
                log_process_completion("FAISS index loading", details=f"Loaded existing index with {self.faiss_index.ntotal} documents")
            except Exception as e:
                logger.error(f"Error loading FAISS index or ID map: {e}", exc_info=True)
                log_process_completion("FAISS index loading", status="failed", details=str(e))
                self._create_new_index() # Fallback to creating a new index
        else:
            logger.info("No existing FAISS index or ID map found. Creating new index.")
            self._create_new_index()

    def _create_new_index(self):
        # Dimension will be set after the first embedding is generated
        self.faiss_index = None
        self.doc_id_to_faiss_id = {}
        self.faiss_id_to_doc_id = {} # Map FAISS index id (str) -> our doc_ids
        self.embedding_dimension = None
        log_process_completion("FAISS index creation", details="Initialized an empty index")

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        # Ollama expects a list of texts for batching, but for single text, we can send as is
        logger.info(f"Requesting embedding for text (first 50 chars): {text[:50]}...")
        start_time = time.time()
        try:
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/embeddings",
                json={
                    "model": EMBED_MODEL,
                    "prompt": text,
                    "options": {"num_gpu": 1}
                },
                # timeout=60 # Removed timeout for embedding generation to prevent premature interruptions
            )
            end_time = time.time()
            response.raise_for_status()
            embedding_data = response.json()
            logger.info(f"Ollama embedding response status: {response.status_code}, time: {end_time - start_time:.2f}s")
            # logger.debug(f"Raw Ollama response: {json.dumps(embedding_data, indent=2)}") # Too verbose for regular logging

            if "embedding" in embedding_data and embedding_data["embedding"]:
                # Check if embedding is an empty list
                if not embedding_data["embedding"]:
                    logger.warning(f"Ollama returned an empty embedding list for text: {text[:50]}...")
                    # Generate a fallback embedding
                    return self._generate_fallback_embedding(text)
                return embedding_data["embedding"]
            else:
                logger.warning(f"Ollama returned no 'embedding' key or it was empty for text: {text[:50]}...")
                logger.warning(f"Full Ollama response: {json.dumps(embedding_data)}")
                # Generate a fallback embedding
                return self._generate_fallback_embedding(text)
        except requests.exceptions.RequestException as e:
            end_time = time.time()
            logger.error(f"Error getting embedding from Ollama (took {end_time - start_time:.2f}s): {e}", exc_info=True)
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Ollama error response status: {e.response.status_code}")
                logger.error(f"Ollama error response body: {e.response.text}")
            return None

    def _get_embedding_with_retry(self, text: str, max_retries: int = 3) -> Optional[List[float]]:
        """Get embedding with retry mechanism for failed requests"""
        for attempt in range(max_retries):
            try:
                # Use a simpler approach for retry
                response = requests.post(
                    f"{self.ollama_base_url}/api/embeddings",
                    json={
                        "model": self.embedding_model,
                        "prompt": text[:200]  # Limit text length
                    },
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()
                
                if "embedding" in data and data["embedding"]:
                    logger.info(f"Retry {attempt + 1} successful for embedding")
                    return data["embedding"]
                else:
                    logger.warning(f"Retry {attempt + 1} failed: empty embedding")
                    if attempt < max_retries - 1:
                        time.sleep(1)  # Wait before retry
                        continue
                    
            except Exception as e:
                logger.warning(f"Retry {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                    
        logger.error(f"All {max_retries} retry attempts failed for embedding")
        return None

    def _generate_fallback_embedding(self, text: str) -> List[float]:
        """Generate a fallback embedding when Ollama fails"""
        import hashlib
        import numpy as np
        
        # Create a deterministic embedding based on text content
        text_hash = hashlib.md5(text.encode()).hexdigest()
        # Convert hash to numbers and create a 768-dimensional vector
        hash_bytes = bytes.fromhex(text_hash)
        
        # Create a 768-dimensional vector from the hash
        embedding = []
        for i in range(768):
            byte_idx = i % len(hash_bytes)
            embedding.append((hash_bytes[byte_idx] / 255.0) * 2 - 1)  # Normalize to [-1, 1]
        
        logger.info(f"Generated fallback embedding for text: {text[:50]}...")
        return embedding

    def add_documents(self, documents: List[Document]):
        new_embeddings = []
        new_doc_ids = []

        for doc in documents:
            embedding = self._get_embedding(doc.content)
            if embedding:
                new_embeddings.append(embedding)
                new_doc_ids.append(doc.doc_id)
                logger.info(f"Adding document to store - Doc ID: {doc.doc_id}, Type: {doc.doc_type}, Content: {doc.content[:100]}...")

                # Store metadata in SQLite
                conn = sqlite3.connect(METADATA_DB_PATH)
                cursor = conn.cursor()
                # Deduplicate by doc_id
                cursor.execute("SELECT 1 FROM documents WHERE doc_id = ?", (doc.doc_id,))
                exists = cursor.fetchone() is not None
                if not exists:
                    cursor.execute(
                        "INSERT INTO documents (doc_id, file_id, file_name, doc_type, content, metadata) VALUES (?, ?, ?, ?, ?, ?)",
                        (doc.doc_id, doc.file_id, doc.file_name, doc.doc_type, doc.content, json.dumps(doc.metadata))
                    )
                conn.commit()
                conn.close()

        if not new_embeddings:
            logger.warning("No new embeddings generated for the provided documents.")
            log_process_completion("Add documents to store", status="skipped", details="No embeddings generated")
            return

        new_embeddings_np = np.array(new_embeddings).astype('float32')

        if self.faiss_index is None:
            self.embedding_dimension = new_embeddings_np.shape[1]
            self.faiss_index = faiss.IndexFlatL2(self.embedding_dimension)
            logger.info(f"Created new FAISS IndexFlatL2 with dimension {self.embedding_dimension}")

        # Ensure the dimension matches existing index
        if self.embedding_dimension != new_embeddings_np.shape[1]:
            logger.error(f"Embedding dimension mismatch. Expected {self.embedding_dimension}, got {new_embeddings_np.shape[1]}")
            log_process_completion("Add documents to store", status="failed", details="Embedding dimension mismatch")
            return

        self.faiss_index.add(new_embeddings_np)

        # Update doc_id mappings
        for i, doc_id in enumerate(new_doc_ids):
            faiss_id = self.faiss_index.ntotal - len(new_doc_ids) + i
            self.doc_id_to_faiss_id[doc_id] = faiss_id
            self.faiss_id_to_doc_id[str(faiss_id)] = doc_id
        
        self._persist_index()
        log_process_completion("Add documents to store", details=f"Added {len(new_embeddings)} documents to FAISS and metadata DB")

    def clear_store(self):
        """Robustly clear all data from the embedding store and metadata DB."""
        import shutil
        logger.info("Clearing all data from embedding store...")
        
        # Close FAISS index
        self.faiss_index = None
        self.doc_id_to_faiss_id = {}
        self.faiss_id_to_doc_id = {}
        
        # Delete files
        files_to_delete = [FAISS_INDEX_FILE, ID_MAP_FILE, METADATA_DB_PATH]
        for file_path in files_to_delete:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"Deleted: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to delete {file_path}: {e}")
        
        # Re-initialize
        self._init_db()
        self._create_new_index()
        logger.info("Embedding store cleared and re-initialized.")

    def _persist_index(self):
        faiss.write_index(self.faiss_index, FAISS_INDEX_FILE)
        with open(ID_MAP_FILE, 'w') as f:
            # Ensure doc_id_to_faiss_id is saved as a dictionary
            json.dump(self.doc_id_to_faiss_id, f)
        log_process_completion("Persist FAISS index and ID map")

    def _extract_keywords(self, query: str) -> List[str]:
        """Extract potential technical terms and expand date patterns."""
        # Common non-distinctive words in this domain
        STOPWORDS = {
            'SHOW', 'ME', 'THE', 'AVG', 'AVERAGE', 'DAILY', 'LOAD', 'FOR', 'AND', 'WITH',
            'TOTAL', 'PLANT', 'CONSUMPTION', 'WHICH', 'WHAT', 'WAS', 'TELL', 'CHECK',
            'FIND', 'CONTEXT', 'DATA', 'ENERGY'
        }
        
        # Find alphanumeric terms with dashes, at least 2 chars for numeric months
        terms = re.findall(r'\b[A-Za-z0-9\-/]{2,}\b', query)
        
        # Filter stopwords
        raw_keywords = [t.upper() for t in terms if t.upper() not in STOPWORDS]
        
        # Date Expansion logic
        month_map = {
            '01': ['01', '1', 'JAN', 'JANUARY'],
            '02': ['02', '2', 'FEB', 'FEBRUARY'],
            '03': ['03', '3', 'MAR', 'MARCH'],
            '04': ['04', '4', 'APR', 'APRIL'],
            '05': ['05', '5', 'MAY'],
            '06': ['06', '6', 'JUN', 'JUNE'],
            '07': ['07', '7', 'JUL', 'JULY'],
            '08': ['08', '8', 'AUG', 'AUGUST'],
            '09': ['09', '9', 'SEP', 'SEPT', 'SEPTEMBER'],
            '10': ['10', 'OCT', 'OCTOBER'],
            '11': ['11', 'NOV', 'NOVEMBER'],
            '12': ['12', 'DEC', 'DECEMBER']
        }
        
        expanded_keywords = []
        for kw in raw_keywords:
            expanded_keywords.append(kw)
            # Check if kw is a month number (1-12) or month name
            kw_clean = kw.lstrip('0')
            match_found = False
            for m_num, aliases in month_map.items():
                if kw in aliases or kw_clean == m_num.lstrip('0'):
                    expanded_keywords.extend(aliases)
                    match_found = True
                    break
            
            # Check for pattern MM/YY or MM-YY
            if not match_found and ('/' in kw or '-' in kw):
                parts = re.split(r'[/\-]', kw)
                if len(parts) >= 2:
                    for p in parts:
                        p_clean = p.lstrip('0')
                        for m_num, aliases in month_map.items():
                            if p == m_num or p_clean == m_num.lstrip('0'):
                                expanded_keywords.extend(aliases)
        
        # Prioritize keywords: 
        # 1. Terms with dashes or numbers (likely technical IDs)
        # 2. Longer terms
        # 3. Rest
        def get_priority(k):
            score = len(k)
            if '-' in k: score += 10
            if any(c.isdigit() for c in k): score += 5
            return score

        sorted_keywords = sorted(list(set(expanded_keywords)), key=get_priority, reverse=True)
        return sorted_keywords

    def keyword_search(self, query: str, k: int = 5, date_filter: Optional[Dict[str, str]] = None, primary_entities: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Exact and fuzzy keyword lookup in the SQLite metadata."""
        keywords = self._extract_keywords(query)
        if not keywords:
            keywords = []
            
        # Combine extracted keywords with primary entities for comprehensive search
        if primary_entities:
            keywords = list(set(keywords + primary_entities))
            
        if not keywords:
            return []
            
        conn = sqlite3.connect(METADATA_DB_PATH)
        cursor = conn.cursor()
        
        results = []
        seen_ids = set()
        
        # Build date SQL if filter exists
        date_sql = ""
        date_params = []
        if date_filter and date_filter.get('start_date') and date_filter.get('end_date'):
            # This assumes metadata contains dates. For 'row' docs we check specific date fields
            # For this simplified version, we search within the JSON metadata if specific date fields aren't indexed
            # Refinement: We'll filter globally by the detected range where possible
            date_sql = " AND (json_extract(metadata, '$.created_at') BETWEEN ? AND ?)"
            date_params = [date_filter['start_date'], date_filter['end_date'] + "T23:59:59"]

        for kw in keywords:
            # 1. Exact/Fuzzy SQL Search
            query_sql = f"SELECT doc_id, file_id, file_name, doc_type, content, metadata FROM documents WHERE (content LIKE ? OR metadata LIKE ?){date_sql} LIMIT ?"
            params = [f'%{kw}%', f'%{kw}%'] + date_params + [k]
            cursor.execute(query_sql, params)
            rows = cursor.fetchall()
            
            # 2. Advanced Fuzzy Match (Typo Tolerance)
            if not rows and len(kw) > 3:
                cursor.execute("SELECT DISTINCT json_extract(metadata, '$.feeder') as fname FROM documents WHERE doc_type = 'feeder_data'")
                all_feeders = [r[0] for r in cursor.fetchall() if r[0]]
                
                matches = difflib.get_close_matches(kw, all_feeders, n=2, cutoff=0.7)
                if matches:
                    cursor.execute(query_sql, [f'%{matches[0]}%', f'%{matches[0]}%'] + date_params + [k])
                    rows = cursor.fetchall()

            for row in rows:
                if row[0] not in seen_ids:
                    metadata = json.loads(row[5])
                    
                    # Boost score if primary entity is found
                    score = 1.2
                    if primary_entities:
                        content_upper = row[4].upper()
                        meta_str_upper = row[5].upper()
                        for ent in primary_entities:
                            if ent.upper() in content_upper or ent.upper() in meta_str_upper:
                                score += 2.0 # Significant boost for technical codes (e.g., L21)
                                break

                    results.append({
                        "doc_id": row[0],
                        "file_id": row[1],
                        "file_name": row[2],
                        "doc_type": row[3],
                        "content": row[4],
                        "metadata": metadata,
                        "score": score,
                        "match_type": "keyword"
                    })
                    seen_ids.add(row[0])
        
        conn.close()
        return results[:k]

    def vector_search(self, query: str, k: int = 5, file_id_filter: Optional[str] = None, date_filter: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """Semantic similarity search using FAISS."""
        query_embedding = self._get_embedding(query)
        if query_embedding is None:
            return []

        if not self.faiss_index or self.faiss_index.ntotal == 0:
            return []

        # Vector search doesn't support filters directly, so we retrieve more then filter
        search_k = k * 3 if date_filter or file_id_filter else k
        D, I = self.faiss_index.search(np.array([query_embedding]).astype('float32'), search_k)

        results = []
        conn = sqlite3.connect(METADATA_DB_PATH)
        cursor = conn.cursor()

        for i, doc_idx in enumerate(I[0]):
            if doc_idx == -1:
                continue

            doc_id = self.faiss_id_to_doc_id.get(str(doc_idx))
            if doc_id:
                # Build filter SQL
                sql = "SELECT file_id, file_name, doc_type, content, metadata FROM documents WHERE doc_id = ?"
                params = [doc_id]
                
                if date_filter and date_filter.get('start_date') and date_filter.get('end_date'):
                    sql += " AND (json_extract(metadata, '$.created_at') BETWEEN ? AND ?)"
                    params.extend([date_filter['start_date'], date_filter['end_date'] + "T23:59:59"])
                
                cursor.execute(sql, params)
                doc_data = cursor.fetchone()
                
                if doc_data:
                    retrieved_file_id, file_name, doc_type, content, metadata_str = doc_data
                    if file_id_filter is None or retrieved_file_id == file_id_filter:
                        distance = float(D[0][i])
                        similarity_score = 1 / (1 + distance / 100)
                        
                        results.append({
                            "doc_id": doc_id,
                            "file_id": retrieved_file_id,
                            "file_name": file_name,
                            "doc_type": doc_type,
                            "content": content,
                            "metadata": json.loads(metadata_str),
                            "distance": distance,
                            "score": similarity_score,
                            "match_type": "vector"
                        })
            if len(results) >= k:
                break
                
        conn.close()
        return results

    def search(self, query: str, k: int = 5, file_id_filter: Optional[str] = None, date_filter: Optional[Dict[str, str]] = None, primary_entities: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Hybrid Search: Combines keyword precision with vector intelligence."""
        # 1. Keyword search (Precision)
        kw_results = self.keyword_search(query, k=k, date_filter=date_filter, primary_entities=primary_entities)
        
        # 2. Vector search (Intelligence)
        vec_results = self.vector_search(query, k=k, file_id_filter=file_id_filter, date_filter=date_filter)
        
        # 3. Merge and deduplicate
        combined = kw_results.copy()
        seen_ids = {doc['doc_id'] for doc in kw_results}
        
        for doc in vec_results:
            if doc['doc_id'] not in seen_ids:
                # Still check if vector results contain primary entities for post-retrieval boost
                if primary_entities:
                    content_upper = doc['content'].upper()
                    meta_upper = str(doc['metadata']).upper()
                    for ent in primary_entities:
                        if ent.upper() in content_upper or ent.upper() in meta_upper:
                            doc['score'] += 0.5 # Smaller boost for semantic matches
                            break
                            
                combined.append(doc)
                seen_ids.add(doc['doc_id'])
        
        # Sort by score 
        combined.sort(key=lambda x: x['score'], reverse=True)
        return combined[:k]

    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(METADATA_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "doc_id": row[0],
                "file_id": row[1],
                "file_name": row[2],
                "doc_type": row[3],
                "content": row[4],
                "metadata": json.loads(row[5]),
            }
        return None
    def get_documents_by_type(self, doc_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve documents of a specific type from the metadata DB."""
        conn = sqlite3.connect(METADATA_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT doc_id, file_id, file_name, doc_type, content, metadata FROM documents WHERE doc_type = ? ORDER BY doc_id DESC LIMIT ?",
            (doc_type, limit)
        )
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            results.append({
                "doc_id": row[0],
                "file_id": row[1],
                "file_name": row[2],
                "doc_type": row[3],
                "content": row[4],
                "metadata": json.loads(row[5]),
            })
        return results

    def get_latest_plant_stats(self) -> Dict[str, Any]:
        """Fetch the most recent plant summary and daily totals for KPI generation."""
        # Get plant summaries, sorted by total consumption (most complete first)
        summaries = self.get_documents_by_type("plant_summary", limit=5)
        # Filter for non-zero (though database should ideally only have non-zero now)
        summaries = [s for s in summaries if s['metadata'].get('total', 0) > 0]
        summaries.sort(key=lambda x: x['metadata'].get('total', 0), reverse=True)
        
        latest_summary = summaries[0] if summaries else None
        
        # Get latest 7 daily totals
        daily_totals = self.get_documents_by_type("daily_total", limit=7)
        
        return {
            "summary": latest_summary,
            "daily_history": daily_totals
        }
