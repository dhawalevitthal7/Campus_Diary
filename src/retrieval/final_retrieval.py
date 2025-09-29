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
    """Safely serialize ChromaDB results with optimization"""
    if isinstance(result, dict):
        # Limit to top 3 most relevant results to improve response time
        return {
            "ids": result.get("ids", [])[:3],
            "documents": result.get("documents", [])[:3],
            "metadatas": result.get("metadatas", [])[:3]
        }
    return str(result)

def finalretrieval(user_query: str):
    """Process user query and return relevant results quickly"""
    try:
        # First try metadata-based search as it's faster
        res1 = serialize_chroma_result(retriev(user_query))
        
        # Only do embedding search if metadata search returns no results
        if not res1.get("documents"):
            res2 = serialize_chroma_result(generate_embedding(user_query))
        else:
            res2 = {"ids": [], "documents": [], "metadatas": []}
        
        # Prepare results for response
        all_docs = []
        seen_docs = set()
        
        # Combine unique results from both searches
        for result in [res1, res2]:
            for doc, meta in zip(result.get("documents", []), result.get("metadatas", [])):
                if doc and doc not in seen_docs:
                    seen_docs.add(doc)
                    all_docs.append({"document": doc, "metadata": meta})
        
        if not all_docs:
            return "No matching companies found for your query. Please try different keywords."
            
        # Create a concise instruction for faster processing
        system_instruction = f"""
        Analyze these {len(all_docs)} companies for query: '{user_query}'
        Focus on most relevant matches for job criteria.
        Key points: company names, CTC, locations, requirements.
        Keep response clear and brief.
        """
        result = model.generate_content(
            contents=[system_instruction, content]
        )
        return result.text  # Return the text content of the response
    except Exception as e:
        print(f"Error in generate_content: {str(e)}")
        raise  # Re-raise the exception to be caught by the API endpoint
