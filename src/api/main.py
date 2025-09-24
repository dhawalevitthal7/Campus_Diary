from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.retrieval.final_retrieval import finalretrieval

app = FastAPI(title="RAG Query API")

# Configure host and port
HOST = "0.0.0.0"  # Allows external access
PORT = 8000       # Default port for FastAPI

@app.get("/")
def root():
    return {"message": "API is running!"}
    
# Request body schema
class QueryRequest(BaseModel):
    query: str

@app.post("/query")
async def query_endpoint(request: QueryRequest):
    try:
        response = finalretrieval(request.query)
        return {"query": request.query, "response": response}
    except Exception as e:
        import traceback
        error_details = {
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        print("Error details:", error_details)  # This will show in the server logs
        raise HTTPException(status_code=500, detail=error_details)

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
    print(f"Server running at http://{HOST}:{PORT}")
