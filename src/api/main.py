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
PORT = int(os.getenv("PORT", "8000"))

# Add startup event to initialize ChromaDB
@app.on_event("startup")
async def startup_event():
    try:
        client = get_chroma_client()
        collection = client.get_or_create_collection(name="companies")
        print(f"✅ Successfully connected to ChromaDB. Collection has {collection.count()} documents.")
    except Exception as e:
        print(f"❌ Error initializing ChromaDB: {str(e)}")
        print(traceback.format_exc())

@app.get("/")
async def root():
    return {
        "message": "API is running!",
        "status": "healthy"
    }

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
    """Process the query asynchronously with optimized timeout"""
    async def _process_with_timeout():
        try:
            # Use a background task for the processing
            result = await asyncio.get_event_loop().run_in_executor(
                None, finalretrieval, query
            )
            return result
        except Exception as e:
            print(f"Processing error: {str(e)}")
            return None

    try:
        # Set a shorter timeout for faster response
        result = await asyncio.wait_for(_process_with_timeout(), timeout=8.0)
        
        if not result:
            return {
                "result": "No matching results found. Please try different search terms.",
                "cached": False,
                "status": "no_results"
            }
        
        if isinstance(result, str):
            if any(err in result.lower() for err in ["error", "unable", "failed"]):
                return {
                    "result": "Please try rephrasing your search query.",
                    "cached": False,
                    "status": "error"
                }
            return {
                "result": result,
                "cached": False,
                "status": "success"
            }
            
        return {
            "result": str(result),
            "cached": False,
            "status": "success"
        }
        
    except asyncio.TimeoutError:
        return {
            "result": "Request timed out. Please try a more specific search.",
            "cached": False,
            "status": "timeout"
        }
    except Exception as e:
        print(f"Query processing error: {str(e)}")
        traceback.print_exc()
        return {
            "result": "Service is currently busy. Please retry in a few moments.",
            "cached": False,
            "status": "error"
        }

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
    """Handle query requests with caching and fast async processing"""
    try:
        # Validate and clean query
        if not request.query or not request.query.strip():
            return JSONResponse(content={
                "result": "Please provide a valid search query.",
                "status": "error"
            })
            
        # Check cache first for instant response
        cache_key = request.query.strip().lower()
        cached_result = query_cache.get(cache_key)
        
        if cached_result:
            # Return cached result immediately
            cached_result["last_accessed"] = time.time()
            return JSONResponse(content={
                "result": cached_result["result"],
                "cached": True,
                "status": "success"
            })
            
        # Initialize ChromaDB with connection pooling
        try:
            client = get_chroma_client()  # Uses singleton pattern
            collection = client.get_or_create_collection(name="companies")
        except Exception as db_error:
            print(f"Database error: {str(db_error)}")
            return JSONResponse(
                content={
                    "result": "Unable to connect to database. Please try again.",
                    "status": "error"
                },
                status_code=503
            )
            
        # Process query with timeout
        print(f"Processing query: {request.query}")
        result = await process_query(request.query)
        
        # Only cache successful results
        if result.get("result") and not result.get("result").startswith("Error"):
            query_cache[cache_key] = {
                "result": result["result"],
                "last_accessed": time.time()
            }
            # Clean old cache entries in background
            background_tasks.add_task(clean_cache)
        
        # Return response
        return JSONResponse(content={
            "result": result["result"],
            "cached": False,
            "status": "success"
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
