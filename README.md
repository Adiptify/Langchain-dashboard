# ⚡️ Energy Data RAG Chatbot

## 📖 Introduction
This project is a **Retrieval-Augmented Generation (RAG)** system designed to analyze and chat with industrial energy consumption reports (Excel files). It allows users to ask natural language questions about energy usage, feeder data, and plant performance, providing accurate, data-backed answers.

The system solves the challenge of manually digging through massive Excel sheets by ingesting the data into a vector database and using a Local LLM to reason over it.

## ⚙️ Methodology

### 1. Data Ingestion & Preprocessing (`1_core/smart_preprocessor.py`)
*   **Smart Extraction:** The system parses complex Excel reports, identifying monthly sheets, feeder names, and daily readings.
*   **Outlier Detection:** It implements a robust outlier detection algorithm to filter out erroneous data spikes (e.g., monthly totals masquerading as daily readings).
*   **Sanity Checks:** Strict validation ensures no negative values or cumulative reading errors are ingested.

### 2. Vector Storage (`1_core/embedding_store.py`)
*   **Embeddings:** Text chunks (feeder summaries, daily totals) are converted into vector embeddings using **Ollama**.
*   **Storage:** These embeddings are stored in a local **FAISS** index for ultra-fast similarity search.
*   **Metadata:** Rich metadata (date, feeder location, KWH value) is stored alongside vectors in a SQLite database (`metadata.db`) for precise retrieval.

### 3. RAG & Reasoning (`1_core/llm_reasoning.py`)
*   **Retrieval:** When a user asks a question, the system searches the FAISS index for the most relevant data points.
*   **Global Context:** It automatically injects a "Global Plant Summary" into the context to ensure the LLM always knows the big picture (total consumption, number of feeders).
*   **LLM Generation:** The retrieved data + user question are sent to a Local LLM (Llama 3.2 via Ollama) to generate a natural language response.

## 🤖 LLM & Tech Stack
*   **LLM:** [Llama 3.2](https://ollama.com/library/llama3.2) (via Ollama) - Chosen for its speed and reasoning capabilities on local hardware.
*   **Embeddings:** Ollama Embeddings.
*   **Vector DB:** FAISS (Facebook AI Similarity Search).
*   **Backend:** Python.
*   **Frontend:** Streamlit.

## 🚀 How to Run

### Prerequisites
1.  **Python 3.10+**
2.  **Ollama** installed and running (`ollama serve`).
3.  **Llama 3.2 Model:** Run `ollama pull llama3.2` in your terminal.

### Installation
```bash
# Clone the repository
git clone https://github.com/phalgunreddy/langchain-agentic-dashboard.git
cd langchain-agentic-dashboard

# Install dependencies
pip install -r Requirements.txt
```

### Running the System
**1. Ingest Data (Only needed once or when data changes):**
```bash
cd 2_scripts
python 1_ingest_data.py
```
*This will process the Excel file in `4_data/` and create the vector index.*

**2. Run the Chat Interface:**
```bash
# From the root directory
streamlit run 3_ui/2_run_streamlit_ui.py
```
*Access the app at `http://localhost:8501`*

## 🛠️ Troubleshooting
*   **"20 Million" Error?** Click the **"💥 Hard Reset"** button in the sidebar to clear the cache and chat history.
*   **LLM Connection Error?** Ensure Ollama is running (`ollama serve`).
