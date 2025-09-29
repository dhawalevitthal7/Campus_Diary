import json
import ast
import re
import os
import chromadb
import pathlib
import google.generativeai as genai
from dotenv import load_dotenv
import types
from .retriever1 import retriev
from .retriever2 import generate_embedding


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# Initialize Gemini model
model = genai.GenerativeModel('gemini-2.0-flash')


def serialize_chroma_result(result):
    """Normalize ChromaDB result into a consistent short form."""
    if not isinstance(result, dict):
        return {"ids": [], "documents": [], "metadatas": []}

    # Chroma can return nested lists; flatten first entry if needed
    ids = result.get("ids", [])
    documents = result.get("documents", [])
    metadatas = result.get("metadatas", [])

    if ids and isinstance(ids[0], list):
        ids = ids[0]
    if documents and isinstance(documents[0], list):
        documents = documents[0]
    if metadatas and isinstance(metadatas[0], list):
        metadatas = metadatas[0]

    return {
        "ids": ids[:3],
        "documents": documents[:3],
        "metadatas": metadatas[:3],
    }

def finalretrieval(user_query: str):
    """Process user query combining metadata and embedding retrieval."""
    try:
        print(f"Processing query: {user_query}")
        # Metadata-based search (fast path)
        res1 = serialize_chroma_result(retriev(user_query))
        print(f"Metadata search results: {len(res1.get('documents', []))} documents")

        # Embedding-based search only if metadata is empty (faster)
        res2 = {"ids": [], "documents": [], "metadatas": []}
        if not res1.get("documents"):
            res2 = serialize_chroma_result(generate_embedding(user_query))
        
        # Prepare results for response
        all_docs = []
        seen_docs = set()
        
        # Combine unique results from both searches, prefer metadata ordering
        for result in [res1, res2]:
            for doc, meta in zip(result.get("documents", []), result.get("metadatas", [])):
                if doc and doc not in seen_docs:
                    seen_docs.add(doc)
                    all_docs.append({"document": doc, "metadata": meta})
        
        if not all_docs:
            return "No matching companies found for your query. Please try different keywords."
        
        print(f"Found {len(all_docs)} matching companies")
        
        # Create a concise prompt for the model
        prompt = f"""
        User Query: {user_query}
        
        Found {len(all_docs)} matching companies. Here are the details:
        {json.dumps(all_docs, indent=2)}
        
        Please provide a clear response focusing on:
        1. Most relevant companies matching the query
        2. Key details (CTC, locations, requirements)
        3. Any specific matches to user criteria
        4. make response according to {user_query}.
        Keep the response informative.
        """
        try:
            # Generate response using the model with a soft timeout via threading
            import concurrent.futures
            def _gen():
                return model.generate_content(prompt)
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(_gen)
                try:
                    response = fut.result(timeout=6.0)
                except concurrent.futures.TimeoutError:
                    return "Here are the top matches based on the database search. The AI summary took too long; showing raw results instead.\n\n" + json.dumps(all_docs[:3], indent=2)

            if response and getattr(response, 'text', None):
                return response.text.strip()
            return "Unable to generate response. Please try again."

        except Exception as model_error:
            print(f"Error in generate_content: {str(model_error)}")
            return "Here are the top matches based on the database search. The AI summary failed; showing raw results instead.\n\n" + json.dumps(all_docs[:3], indent=2)
            
    except Exception as e:
        print(f"Error in finalretrieval: {str(e)}")
        return f"An error occurred while processing your query: {str(e)}"
