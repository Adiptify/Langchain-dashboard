# 🚀 QUICK START GUIDE

## Step-by-Step Setup & Running

### ✅ Step 1: Install Dependencies
```bash
pip install -r Requirements.txt
```

### ✅ Step 2: Start Ollama (in a separate terminal)
```bash
ollama serve
```

### ✅ Step 3: Ingest Data (First Time Only)
```bash
cd 2_scripts
python 1_ingest_data.py
```

This will:
- Read the Excel file from `4_data/`
- Extract and preprocess the data
- Create embeddings
- Store in `4_data/data_prototype/`

**Expected output:**
```
✅ Created 153 documents
🔋 TOTAL PLANT CONSUMPTION: 18,221,587.14 KWH
✅ COMPLETE! Documents in store: 153
```

### ✅ Step 4: Run Streamlit UI
```bash
cd ../3_ui
streamlit run 2_run_streamlit_ui.py
```

**Or from root directory:**
```bash
streamlit run 3_ui/2_run_streamlit_ui.py
```

### ✅ Step 5: Open Browser
Go to: **http://localhost:8501**

---

## 📁 Folder Structure

```
langchain-agentic-dashboard/
│
├── 1_core/                          # Core backend files (don't run directly)
│   ├── config.py                    # Configuration
│   ├── smart_preprocessor.py        # Data extraction logic
│   ├── embedding_store.py           # Vector search
│   ├── llm_reasoning.py            # LLM query answering
│   ├── router.py                   # Query routing
│   ├── agent_tools.py              # Calculations
│   ├── utils.py                    # Utilities
│   ├── user_profiles.py            # User management
│   └── ingestion_pipeline.py       # Legacy file processing
│
├── 2_scripts/                       # Scripts to run (in order)
│   └── 1_ingest_data.py            # ⚡ RUN THIS FIRST (one time)
│
├── 3_ui/                           # User interface
│   └── 2_run_streamlit_ui.py       # ⚡ RUN THIS TO START UI
│
├── 4_data/                         # Data files
│   ├── Energy Consumption Daily Report MHS Ele - Copy.xlsx
│   └── data_prototype/             # Generated databases & indexes
│
├── docs/                           # Documentation
│   ├── PRODUCTION_HANDOVER.md      # For web developers
│   └── README.md                   # Project overview
│
└── Requirements.txt                # Python dependencies
```

---

## 🎯 What Each Script Does

### 1️⃣ `2_scripts/1_ingest_data.py`
**Purpose:** Load and process Excel data into the system
**When to run:** 
- First time setup
- When you have a new Excel file to add
**Time:** ~5 seconds

### 2️⃣ `3_ui/2_run_streamlit_ui.py`
**Purpose:** Start the web interface for testing
**When to run:** Every time you want to use the chatbot
**Time:** Runs continuously until you stop it (Ctrl+C)

---

## 🔧 Troubleshooting

**Error: "Module not found"**
→ Run: `pip install -r Requirements.txt`

**Error: "LLM Error" or timeout**
→ Check Ollama is running: `ollama serve`
→ Check models are installed: `ollama list`
→ Install if needed: `ollama pull llama3.2` and `ollama pull nomic-embed-text`

**Error: "No data found"**
→ Run: `python 2_scripts/1_ingest_data.py`

**Port already in use (8501)**
→ Streamlit will automatically try 8502, 8503, etc.
→ Or stop the existing one: `pkill -f streamlit`

---

## 📦 For Web Developers

See `docs/PRODUCTION_HANDOVER.md` for integration guide with REST API examples.
