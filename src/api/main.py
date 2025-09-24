from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import sys
import os
import traceback
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.retrieval.final_retrieval import finalretrieval

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specific domains like ["https://lovable.dev", "https://*.lovableproject.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        # Get ChromaDB configuration
        from src.config import get_chroma_client, CHROMA_DB_PERSIST_DIRECTORY, IS_RENDER
        print(f"💾 Database directory: {CHROMA_DB_PERSIST_DIRECTORY}")
        print(f"🚀 Is Render: {IS_RENDER}")
        
        # Initialize ChromaDB
        try:
            client = get_chroma_client()
            collection = client.get_or_create_collection(name="companies")
            doc_count = collection.count()
            print(f"✅ Connected to ChromaDB. Collection has {doc_count} documents.")
        except Exception as db_error:
            print(f"❌ Database error: {str(db_error)}")
            print(f"Trace:\n{traceback.format_exc()}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Database connection failed",
                    "message": str(db_error),
                    "path": CHROMA_DB_PERSIST_DIRECTORY
                }
            )
        
        # Process query
        try:
            print(f"📝 Processing query: {request.query}")
            response = finalretrieval(request.query)
            print("✅ Query processed successfully")
            
            # Safely serialize response
            serialized_response = str(response) if response is not None else None
            
            return {
                "query": request.query,
                "response": serialized_response,
                "debug": {
                    "database": {
                        "path": str(CHROMA_DB_PERSIST_DIRECTORY),
                        "document_count": doc_count,
                        "is_render": IS_RENDER
                    }
                }
            }
        except Exception as query_error:
            print(f"❌ Query processing error: {str(query_error)}")
            print(f"Trace:\n{traceback.format_exc()}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Query processing failed",
                    "message": str(query_error)
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        print(f"Trace:\n{traceback.format_exc()}")
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
