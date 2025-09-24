import json
import ast
import re
import os
import chromadb
import pathlib
import google.generativeai as genai
from dotenv import load_dotenv
import types
load_dotenv()

from ..config import get_chroma_client

# --- Initialize Persistent Chroma client ---
client1 = get_chroma_client()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# Initialize Gemini model
model = genai.GenerativeModel('gemini-2.0-flash')

# --- Create or get collection ---
collection = client1.get_or_create_collection(name="companies")

def generate_embedding(text: str):
    """
    Generate embedding using Google's Gemini text-embedding-004 model.
    """
    try:
        response = genai.embed_content(
            model="models/text-embedding-004",
            content=text
        )
        query_vector = response['embedding']  # Returns a list of floats (768 dimensions)
    except Exception as e:
        print(f"❌ Error generating embedding: {e}")
        query_vector = [0.0] * 768  # Fallback to prevent pipeline crash

    results2 = collection.query(
        query_embeddings=[query_vector],
        n_results=3
    )
    return results2