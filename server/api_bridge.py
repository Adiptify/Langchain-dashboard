import sys
import os
import json
import sqlite3
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import shutil
import tempfile
import asyncio
import uuid
from faster_whisper import WhisperModel
import edge_tts

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
from utils import logger, log_process_completion

logger.info("==================================================")
logger.info("   MENDYGO AI BRIDGE - INITIALIZING SYSTEM       ")
logger.info("==================================================")

# Initialize components
logger.info("Initializing Embedding Store...")
embedding_store = EmbeddingStore()

logger.info("Initializing LLM Reasoning Engine...")
llm = LLMReasoning()

# Initialize Whisper Model (base for speed/accuracy balance)
logger.info("Loading Whisper STT model (this may take a moment)...")
whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
logger.info("Whisper STT model loaded successfully.")

app = FastAPI(title="MendyGo API Bridge")
logger.info("FastAPI application instance created.")
logger.info("System integration ready. Listening for requests...")
logger.info("==================================================")

class ChatRequest(BaseModel):
    prompt: str
    chat_history: Optional[List[Any]] = None

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/stats")
def get_stats():
    try:
        db_path = os.path.join(parent_dir, '4_data', 'data_prototype', 'metadata.db')
        if not os.path.exists(db_path):
            return {"document_count": 0, "status": "no_data"}
            
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM documents")
        doc_count = cursor.fetchone()[0]
        conn.close()
        return {"document_count": doc_count, "status": "ok"}
    except Exception as e:
        return {"error": str(e), "status": "error"}

@app.post("/ingest")
def ingest_file_api(payload: Dict[str, str]):
    file_path = payload.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=400, detail="Invalid file path")
    
    try:
        from smart_preprocessor import JSWEnergyPreprocessor
        processor = JSWEnergyPreprocessor()
        docs = processor.process_file(file_path)
        
        if docs:
            embedding_store.add_documents(docs)
            return {"status": "success", "count": len(docs), "message": f"Successfully ingested {len(docs)} documents."}
        else:
            return {"status": "error", "message": "No documents extracted from file."}
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Error during ingestion: {error_detail}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
def chat(request: ChatRequest):
    logger.info(f"Incoming Chat Request: {request.prompt[:50]}...")
    try:
        # Search for relevant data
        logger.info("Searching embedding store for relevant context...")
        results = embedding_store.search(request.prompt, k=5)
        logger.info(f"Retrieved {len(results)} context documents.")
        
        # Inject global context (Summaries and Monthly Totals)
        try:
            db_path = os.path.join(parent_dir, '4_data', 'data_prototype', 'metadata.db')
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                # Fetch plant summaries and individual monthly totals
                cursor.execute("SELECT content, metadata, doc_type FROM documents WHERE doc_type IN ('plant_summary', 'monthly_total')")
                summary_rows = cursor.fetchall()
                conn.close()
                
                for content, meta_str, dtype in summary_rows:
                    prefix = "GLOBAL PLANT SUMMARY" if dtype == 'plant_summary' else "MONTH TOTAL"
                    results.insert(0, {
                        "doc_id": f"injected_{dtype}_{uuid.uuid4().hex[:6]}",
                        "content": f"{prefix}:\n{content}",
                        "metadata": json.loads(meta_str),
                        "doc_type": dtype,
                        "score": 1.0 # Highest relevance
                    })
        except Exception as e:
            logger.error(f"Failed to inject global context: {e}")

        if not results:
            return {"answer": "No data found. Please ingest your data first.", "results": []}
            
        # Simplify results for LLM focus
        llm_context = [
            {"content": r["content"], "doc_type": r.get("doc_type", "data")} 
            for r in results
        ]
            
        # Get LLM response
        llm_result = llm.perform_reasoning(request.prompt, llm_context, chat_history=request.chat_history)
        return {
            "answer": llm_result.get("answer", "Unable to generate response"),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/suggestions")
def get_suggestions(user_id: str = "tester"):
    """Get query suggestions for the user"""
    try:
        suggestions = suggestion_engine.get_query_suggestions(user_id)
        return {"suggestions": suggestions}
    except Exception as e:
        logger.error(f"Error getting suggestions: {e}")
        return {"suggestions": [], "error": str(e)}

@app.get("/briefing")
def get_briefing(user_id: str = "tester"):
    """Get daily briefing for the user"""
    try:
        # Check if briefing should be shown
        should_show = user_profile_manager.check_first_login_of_day(user_id)
        if not should_show:
            return {"briefing": None, "should_show": False}
            
        briefing = suggestion_engine.generate_daily_briefing(user_id)
        return {"briefing": briefing, "should_show": True}
    except Exception as e:
        logger.error(f"Error generating briefing: {e}")
        return {"briefing": None, "should_show": False, "error": str(e)}

@app.get("/kpis")
def get_kpis():
    """Get plant-level KPIs for dashboard sidebar"""
    try:
        stats = embedding_store.get_latest_plant_stats()
        summary = stats.get('summary')
        
        if not summary:
            return {"kpis": None}
            
        metadata = summary.get('metadata', {})
        return {
            "kpis": {
                "total_consumption": metadata.get('total', 0),
                "peak_day": metadata.get('peak_day', "N/A"),
                "peak_day_val": metadata.get('peak_day_val', 0),
                "peak_month": metadata.get('peak_month', "N/A"),
                "coverage_months": len(metadata.get('months', []))
            }
        }
    except Exception as e:
        logger.error(f"Error getting KPIs: {e}")
        return {"kpis": None, "error": str(e)}

@app.post("/stt")
async def speech_to_text(file: UploadFile = File(...)):
    """Transcribe uploaded audio file using Whisper"""
    logger.info(f"Incoming STT Request: {file.filename}")
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{file.filename}")
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        segments, info = whisper_model.transcribe(temp_path, beam_size=5)
        text = " ".join([segment.text for segment in segments])
        
        return {"text": text.strip(), "language": info.language}
    except Exception as e:
        print(f"STT Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/tts")
async def text_to_speech(request: Dict[str, str]):
    """Generate neural speech using Edge-TTS"""
    prompt = request.get("prompt")
    logger.info(f"Incoming TTS Request: {prompt[:50]}...")
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")
    temp_dir = tempfile.gettempdir()
    output_filename = f"tts_{uuid.uuid4()}.mp3"
    output_path = os.path.join(temp_dir, output_filename)
    
    try:
        # Voice: en-US-AriaNeural or en-US-GuyNeural
        communicate = edge_tts.Communicate(prompt, "en-US-AriaNeural")
        await communicate.save(output_path)
        
        return FileResponse(
            path=output_path,
            media_type="audio/mpeg",
            filename=output_filename
        )
    except Exception as e:
        print(f"TTS Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    # Note: FileResponse handles clean up if we use background tasks, 
    # but for simplicity/reliability in this env, we'll keep it for now.
    # In a real system, we'd clean up periodicially.

@app.post("/clear")
def clear_data():
    """Wipe all system data"""
    try:
        embedding_store.clear_store()
        logger.info("System data wiped successfully.")
        return {"status": "success", "message": "All documents and indices cleared."}
    except Exception as e:
        logger.error(f"Error clearing data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
