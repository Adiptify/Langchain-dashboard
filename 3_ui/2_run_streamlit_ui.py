import streamlit as st
import sys
import os

# Configure page
st.set_page_config(
    page_title="Energy Data Chatbot",
    page_icon="🤖",
    layout="wide"
)

# Add path to core modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
core_dir = os.path.join(parent_dir, '1_core')
sys.path.insert(0, core_dir)
sys.path.insert(0, parent_dir)

# Import core modules
from embedding_store import EmbeddingStore
from llm_reasoning import LLMReasoning
from suggestion_engine import suggestion_engine
from user_profiles import user_profile_manager
from smart_preprocessor import JSWEnergyPreprocessor

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'user_id' not in st.session_state:
    # For prototype, we'll try to find an existing user or create one
    from user_profiles import user_profile_manager
    try:
        # Check if any user exists
        import sqlite3
        conn = sqlite3.connect(user_profile_manager.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM user_profiles LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        if row:
            st.session_state.user_id = row[0]
        else:
            st.session_state.user_id = user_profile_manager.create_user_profile("tester", "test@example.com")
    except:
        st.session_state.user_id = "default_user"
if 'briefing_shown' not in st.session_state:
    st.session_state.briefing_shown = False

# Header
st.title("🤖 Energy Data Chatbot")
st.markdown("Ask questions about your energy consumption data")

# Daily Briefing
if not st.session_state.briefing_shown:
    if user_profile_manager.check_first_login_of_day(st.session_state.user_id):
        with st.container():
            st.markdown("---")
            st.markdown("### 🌅 Good Morning! Here is your daily briefing:")
            with st.spinner("Preparing your briefing..."):
                briefing = suggestion_engine.generate_daily_briefing(st.session_state.user_id)
                st.info(briefing)
            if st.button("Got it!"):
                st.session_state.briefing_shown = True
                st.rerun()
            st.markdown("---")
    else:
        st.session_state.briefing_shown = True

# Sidebar
st.sidebar.title("Controls")
if st.sidebar.button("💥 Hard Reset (Fix All Errors)"):
    st.cache_resource.clear()
    if 'messages' in st.session_state:
        st.session_state.messages = []
    st.rerun()

# Initialize components (cached)
@st.cache_resource
def get_components():
    embedding_store = EmbeddingStore()
    llm = LLMReasoning()
    return embedding_store, llm

embedding_store, llm = get_components()

# Chat interface
st.markdown("### 💬 Chat")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

def process_query(query_text):
    """Unified function to process a query with streaming and global context injection."""
    st.session_state.messages.append({"role": "user", "content": query_text})
    
    with st.chat_message("user"):
        st.markdown(query_text)
    
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Search for relevant data
                results = embedding_store.search(query_text, k=5)
                
                # Global context injection (Summaries and Monthly Totals)
                try:
                    import sqlite3
                    import json
                    conn = sqlite3.connect(os.path.join(parent_dir, '4_data', 'data_prototype', 'metadata.db'))
                    cursor = conn.cursor()
                    # Fetch plant summaries and individual monthly totals
                    cursor.execute("SELECT content, metadata, doc_type FROM documents WHERE doc_type IN ('plant_summary', 'monthly_total')")
                    summary_rows = cursor.fetchall()
                    conn.close()
                    
                    for content, meta_str, dtype in summary_rows:
                        prefix = "GLOBAL PLANT SUMMARY" if dtype == 'plant_summary' else "MONTH TOTAL"
                        results.insert(0, {
                            "doc_id": f"injected_{dtype}_{os.urandom(3).hex()}",
                            "content": f"{prefix}:\n{content}",
                            "metadata": json.loads(meta_str),
                            "doc_type": dtype,
                            "score": 1.0 # Highest relevance
                        })
                except Exception as e:
                    print(f"Failed to inject global context: {e}")

                if not results:
                    response = "No data found. Please upload files using the script: `python 2_scripts/1_ingest_data.py`"
                    st.markdown(response)
                else:
                    # Get LLM response (streaming)
                    response_generator = llm.perform_streaming_reasoning(query_text, results)
                    response = st.write_stream(response_generator)
                
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.error(f"Error: {str(e)}")

# Chat input
if prompt := st.chat_input("Ask about energy consumption..."):
    process_query(prompt)

# Handle suggested query injection
if 'suggested_query' in st.session_state:
    q = st.session_state.pop('suggested_query')
    process_query(q)
    st.rerun()

# Sidebar
with st.sidebar:
    st.markdown("### 💡 Suggestions")
    suggestions = suggestion_engine.get_query_suggestions(st.session_state.user_id)
    for sug in suggestions:
        if st.button(f"🔍 {sug}", key=f"sug_{sug}"):
            st.session_state.suggested_query = sug
            st.rerun()
    
    st.markdown("### ℹ️ Info")
    st.info("This is a simplified chatbot interface for testing.")
    
    st.markdown("### 📁 Data Status")
    try:
        # Check if data exists
        import sqlite3
        conn = sqlite3.connect(os.path.join(parent_dir, '4_data', 'data_prototype', 'metadata.db'))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM documents")
        doc_count = cursor.fetchone()[0]
        conn.close()
        
        st.success(f"✅ {doc_count} documents loaded")
        
        # New KPI Cards in Streamlit
        kpi_data = embedding_store.get_latest_plant_stats()
        summary = kpi_data.get('summary')
        if summary:
            st.markdown("---")
            st.markdown("#### 📊 Key Stats")
            meta = summary.get('metadata', {})
            st.metric("Peak Month", f"{meta.get('peak_month', 'N/A')}")
            st.metric("Highest Day", f"{meta.get('peak_day', 'N/A')}")
            st.metric("Total Plant Cons.", f"{meta.get('total', 0):,.0f} KWH")
    except:
        st.warning("⚠️ No data loaded. Run: `python 2_scripts/1_ingest_data.py`")
    
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

    if st.sidebar.button("💥 Hard Reset (Fix All Errors)"):
        st.cache_resource.clear()
        es = EmbeddingStore()
        es.clear_store()
        if 'messages' in st.session_state:
            st.session_state.messages = []
        st.success("System reset complete. Data cleared.")
        st.rerun()

    st.markdown("---")
    st.markdown("### 📥 Ingest New Data")
    uploaded_file = st.file_uploader("Upload JSW Energy Excel", type=["xlsx"])
    
    if uploaded_file is not None:
        if st.button("🚀 Start Ingestion"):
            with st.status("Ingesting data...", expanded=True) as status:
                st.write("🗑️ Clearing old database...")
                # Re-init embedding store to clear specifically
                st.cache_resource.clear()
                es = EmbeddingStore()
                es.clear_store()
                
                st.write("📊 Processing Excel file...")
                processor = JSWEnergyPreprocessor()
                docs = processor.process_file(uploaded_file)
                
                if docs:
                    st.write(f"💾 Adding {len(docs)} documents to store...")
                    es.add_documents(docs)
                    st.success(f"✅ Ingestion complete! {len(docs)} docs loaded.")
                    status.update(label="Ingestion Complete!", state="complete", expanded=False)
                    st.rerun()
                else:
                    st.error("❌ No documents were extracted.")
                    status.update(label="Ingestion Failed", state="error")