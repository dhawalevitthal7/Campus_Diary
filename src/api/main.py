from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.retrieval.retriever import query_chroma

app = FastAPI(title="RAG Query API")

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
