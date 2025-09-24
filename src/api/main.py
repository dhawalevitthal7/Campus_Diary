from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import sys
import os
import traceback
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.retrieval.final_retrieval import finalretrieval

app = FastAPI(title="RAG Query API")

# Configure host and port
HOST = "0.0.0.0"  # Allows external access
PORT = 8000       # Default port for FastAPI

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

@app.post("/query")
async def query_endpoint(request: QueryRequest):
    try:
        # Get ChromaDB client and collection info
        from src.config import get_chroma_client
        client = get_chroma_client()
        collection = client.get_collection(name="companies")
        
        # Get collection stats
        collection_stats = {
            "count": collection.count(),
            "peek": collection.peek()
        }
        
        print(f"Debug - Collection stats: {collection_stats}")
        
        # Get the response
        response = finalretrieval(request.query)
        
        # Return both the response and debug info
        return {
            "query": request.query,
            "response": response,
            "debug": {
                "collection_stats": collection_stats,
                "chroma_path": os.getenv('CHROMA_DB_PATH', 'chroma_data'),
                "is_render": os.getenv('IS_RENDER', 'false')
            }
        }
    except Exception as e:
        import traceback
        error_details = {
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        print("Error details:", error_details)
        raise HTTPException(status_code=500, detail=error_details)

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
    print(f"Server running at http://{HOST}:{PORT}")
