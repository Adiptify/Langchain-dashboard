# 📦 Production Handover & Integration Guide

## 🎯 Purpose
This document is designed for **Web Developers** who need to integrate the Energy Data RAG Backend into a production website or dashboard.

## 🏗️ Architecture Overview
The system is currently a **Python-based Local Application**. To integrate it into a web app (e.g., React, Next.js, Vue), you will need to expose the Python core as an API.

### Current Stack
*   **Core Logic:** Python (`1_core/`)
*   **Database:** SQLite (`4_data/data_prototype/metadata.db`) + FAISS (`4_data/data_prototype/indexes/`)
*   **LLM:** Local Ollama instance

## 🔌 Integration Strategy (Recommended)

To connect this to a web frontend, we recommend wrapping the core logic in a **FastAPI** or **Flask** server.

### 1. API Endpoints Needed
You should create a simple Python API that exposes the following endpoints:

#### `POST /query`
*   **Input:** `{"question": "How much energy did we use in July?"}`
*   **Logic:**
    1.  Import `LLMReasoning` and `EmbeddingStore` from `1_core`.
    2.  Call `llm_reasoning.answer_question(question)`.
*   **Output:** `{"answer": "In July, the plant used...", "sources": [...]}`

#### `POST /reset`
*   **Input:** `{}`
*   **Logic:** Clear any server-side caching.
*   **Output:** `{"status": "success"}`

### 2. Python Interface Code
Here is how you programmatically interact with the backend from your API server:

```python
import sys
import os

# Add 1_core to path
sys.path.append(os.path.join(os.path.dirname(__file__), '1_core'))

from embedding_store import EmbeddingStore
from llm_reasoning import LLMReasoning

# Initialize (do this once on server startup)
embedding_store = EmbeddingStore()
llm_reasoning = LLMReasoning()

def process_user_question(user_question):
    """
    Call this function when your API receives a request.
    """
    # 1. Search Vector DB
    # Note: The system automatically handles global context injection internally
    results = embedding_store.search(user_question, k=5)
    
    # 2. Generate Answer
    answer = llm_reasoning.get_answer(user_question, results)
    
    return answer
```

## ⚠️ Critical Integration Notes

### 1. Data Persistence
*   The system relies on `metadata.db` and `faiss.index` existing in `4_data/data_prototype/`.
*   **Do not delete these files** during deployment. They contain the ingested knowledge base.
*   If you deploy to a container (Docker), ensure `4_data/` is mounted as a persistent volume.

### 2. LLM Dependency
*   The system requires **Ollama** to be running on the server (`localhost:11434`).
*   If deploying to cloud (AWS/GCP), you might need to swap the local Ollama calls in `1_core/llm_reasoning.py` for an API call to OpenAI/Anthropic or a hosted LLM service if you cannot run Ollama.

### 3. "Hard Reset" Feature
*   The current UI has a "Hard Reset" button to clear history. In a stateless API, you don't need to worry about clearing history *unless* you implement a conversation memory in your API. The RAG core itself is stateless per request.

## 📂 Folder Structure for Deployment
```
/backend
  ├── main.py              # Your new FastAPI/Flask server
  ├── 1_core/              # COPY THIS FOLDER (Logic)
  ├── 4_data/              # COPY THIS FOLDER (Database)
  └── Requirements.txt     # Python dependencies
```
