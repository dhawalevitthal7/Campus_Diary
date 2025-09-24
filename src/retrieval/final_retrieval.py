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


def finalretrieval(user_query:str):
    def serialize_chroma_result(result):
        if isinstance(result, dict):
            return {
                "ids": result.get("ids", []),
                "documents": result.get("documents", []),
                "metadatas": result.get("metadatas", [])
            }
        return str(result)
    
    # Get results from both retrievers
    res1 = serialize_chroma_result(retriev(user_query))
    res2 = serialize_chroma_result(generate_embedding(user_query))
    
    system_instruction = f"""
    Analyze the following search results and provide a user-friendly response 
    that summarizes the most relevant information based on the user's query: '{user_query}'.
    
    Result 1 (Metadata-based search):
    {json.dumps(res1, indent=2)}
    
    Result 2 (Embedding-based search):
    {json.dumps(res2, indent=2)}
    """
    
    content = user_query

    try:
        result = model.generate_content(
            contents=[system_instruction, content]
        )
        return result.text  # Return the text content of the response
    except Exception as e:
        print(f"Error in generate_content: {str(e)}")
        raise  # Re-raise the exception to be caught by the API endpoint
