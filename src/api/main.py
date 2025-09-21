from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.retrieval.retriever import query_chroma
from src.embedding.chroma_manager import init_chroma

app = FastAPI(title="RAG Query API")

# Initialize ChromaDB on startup
collection = init_chroma()

@app.get("/")
def root():
    return {"message": "API is running!"}
    
# Request body schema
class QueryRequest(BaseModel):
    query: str

@app.post("/query")
async def query_endpoint(request: QueryRequest):
    try:
        response = query_chroma(request.query, limit=20)
        return {"query": request.query, "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))