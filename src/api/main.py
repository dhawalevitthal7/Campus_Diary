from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
import sys
import os
import traceback
import asyncio
from functools import lru_cache
from typing import Dict, Any, Optional
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.retrieval.final_retrieval import finalretrieval
from src.config import get_chroma_client
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Cache for storing query results
query_cache: Dict[str, Dict[str, Any]] = {}

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Configure host and port
HOST = "0.0.0.0"  
PORT = 8000       

@app.get("/")
def root():
    return {"message": "API is running!"}

@app.get("/status")
async def status():
    try:
        from src.config import get_chroma_client
        client = get_chroma_client()
        collection = client.get_collection(name="companies")
        
        return {
            "status": "ok",
            "collection": {
                "name": "companies",
                "count": collection.count(),
                "peek": collection.peek()
            },
            "environment": {
                "chroma_path": os.getenv('CHROMA_DB_PATH', 'chroma_data'),
                "is_render": os.getenv('IS_RENDER', 'false'),
                "persistence_path": os.path.join(os.getenv('IS_RENDER', 'false') and '/data' or os.path.dirname(os.path.dirname(__file__)), os.getenv('CHROMA_DB_PATH', 'chroma_data'))
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "trace": traceback.format_exc()
        }
    
# Request body schema
class QueryRequest(BaseModel):
    query: str

async def process_query(query: str) -> dict:
    """Process the query asynchronously with timeout"""
    try:
        # Set a timeout of 30 seconds for query processing
        result = await asyncio.wait_for(
            asyncio.to_thread(finalretrieval, query),
            timeout=30.0
        )
        return {"result": result, "cached": False}
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Query processing timed out")
    except Exception as e:
        print(f"Error processing query: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

def clean_cache(max_age: int = 3600, max_size: int = 1000):
    """Clean old cache entries"""
    current_time = time.time()
    
    # Remove entries older than max_age seconds
    keys_to_remove = [
        k for k, v in query_cache.items()
        if current_time - v["last_accessed"] > max_age
    ]
    
    for k in keys_to_remove:
        del query_cache[k]
    
    # If still too many entries, remove oldest ones
    if len(query_cache) > max_size:
        sorted_entries = sorted(
            query_cache.items(),
            key=lambda x: x[1]["last_accessed"]
        )
        for k, _ in sorted_entries[:len(query_cache) - max_size]:
            del query_cache[k]

@app.post("/query")
async def query_endpoint(request: QueryRequest, background_tasks: BackgroundTasks):
    """Handle query requests with caching and async processing"""
    try:
        # Check cache first
        cache_key = request.query.strip().lower()
        cached_result = query_cache.get(cache_key)
        
        if cached_result:
            # Update cache access time
            cached_result["last_accessed"] = time.time()
            return JSONResponse(content={
                "result": cached_result["result"],
                "cached": True
            })
            
        # Initialize ChromaDB
        try:
            client = get_chroma_client()
            collection = client.get_or_create_collection(name="companies")
            doc_count = collection.count()
            print(f"Connected to ChromaDB. Collection has {doc_count} documents.")
        except Exception as db_error:
            print(f"Database error: {str(db_error)}")
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Database connection failed",
                    "message": str(db_error)
                }
            )
            
        # Process query with timeout
        print(f"Processing query: {request.query}")
        result = await process_query(request.query)
        
        # Cache the result
        query_cache[cache_key] = {
            "result": result["result"],
            "last_accessed": time.time()
        }
        
        # Clean old cache entries in background
        background_tasks.add_task(clean_cache)
        
        # Return response with debug info
        return JSONResponse(content={
            "result": result["result"],
            "cached": False,
            "debug": {
                "query": request.query,
                "collection_size": doc_count
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error in query endpoint: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Unexpected error",
                "message": str(e)
            }
        )

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
    print(f"Server running at http://{HOST}:{PORT}")
