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
        print(f"Processing query: {user_query}")
        # First try metadata-based search as it's faster
        res1 = serialize_chroma_result(retriev(user_query))
        print(f"Metadata search results: {len(res1.get('documents', []))} documents")
        
        # Only do embedding search if metadata search returns no results
        if not res1.get("documents"):
            print("No metadata results, trying embedding search")
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
        
        print(f"Found {len(all_docs)} matching companies")
        
        # Create a concise prompt for the model
        prompt = f"""
        User Query: {user_query}
        
        Found {len(all_docs)} matching companies. Here are the details:
        {json.dumps(all_docs, indent=2)}
        
        Please provide a clear, concise summary focusing on:
        1. Most relevant companies matching the query
        2. Key details (CTC, locations, requirements)
        3. Any specific matches to user criteria
        
        Keep the response brief and informative.
        """
        try:
            # Generate response using the model
            response = model.generate_content(prompt)
            
            if response and response.text:
                return response.text.strip()
            else:
                return "Unable to generate response. Please try again."
                
        except Exception as model_error:
            print(f"Error in generate_content: {str(model_error)}")
            return f"Error processing results: {str(model_error)}"
            
    except Exception as e:
        print(f"Error in finalretrieval: {str(e)}")
        return f"An error occurred while processing your query: {str(e)}"
