import json
import os
import uuid
import pathlib
import chromadb
import google.generativeai as genai
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

# PATHS 
BASE_DIR = pathlib.Path(__file__).resolve().parents[2]
JSON_FOLDER_PATH = BASE_DIR / "data" / "chunked_json"
CHROMA_DB_PATH = BASE_DIR / "chroma_data"


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise EnvironmentError("GEMINI_API_KEY not found! Please set it as an environment variable.")

genai.configure(api_key=GEMINI_API_KEY)

from src.config import get_chroma_client

# Persistent Chroma Client via shared config
client = get_chroma_client()

# Create or get collection
collection = client.get_or_create_collection(name="companies")

# Embedding Generation
def generate_embedding(text: str):
    """
    Generate embedding using Google's Gemini text-embedding-004 model.
    Returns a list of floats (768 dimensions)
    """
    try:
        response = genai.embed_content(
            model="models/text-embedding-004",
            content=text
        )
        return response['embedding']
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return [0.0] * 768  # fallback to prevent pipeline crash


# Metadata Processing
def extract_metadata(company):
    """
    Extract and clean metadata from company JSON.
    - Converts keys to lowercase and underscores
    - Keeps numeric values like CTC, LPA, Stipend as numbers
    """
    meta = {}
    numeric_keys = {"ctc", "lpa", "stipend"}

    for item in company.get("Keys", []):
        key_name = item["key"].lower().replace(" ", "_")
        value = item["value"]

        # Convert numeric values where appropriate
        if key_name in numeric_keys and isinstance(value, (int, float, str)):
            try:
                value = float(str(value).replace(",", ""))
            except (ValueError, TypeError):
                pass

        meta[key_name] = value

    meta["name"] = company["Name"].strip()  # Always include company name
    return meta

# Text Processing
def build_embedding_text(company):
    """Build a clean text string for embedding generation."""
    text = f"Company Name: {company['Name']}\n"
    text += f"Description: {company.get('description', '')}\n"
    for item in company.get("Keys", []):
        text += f"{item['key']}: {item['value']}\n"
    return text

# ---------------------
# JSON Processing
# ---------------------
def process_json_file(json_path):
    """Process a single JSON file and store data into ChromaDB."""
    with open(json_path, "r", encoding="utf-8") as f:
        companies_data = json.load(f)

    print(f"Processing {len(companies_data)} companies from {os.path.basename(json_path)}")

    ids, documents, metadatas, embeddings = [], [], [], []

    for company in companies_data:
        # Generate unique ID
        company_id = f"{company['Name'].strip()}_{uuid.uuid4()}"

        text = build_embedding_text(company)
        vector = generate_embedding(text)

        ids.append(company_id)
        documents.append(text)
        metadatas.append(extract_metadata(company))
        embeddings.append(vector)

    # Add data to Chroma
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings
    )

    print(f"Added {len(ids)} companies to ChromaDB from {os.path.basename(json_path)}")

def process_all_json():
    """Process all JSON files in the chunked_json directory."""
    if not JSON_FOLDER_PATH.exists():
        raise FileNotFoundError(f"JSON folder not found: {JSON_FOLDER_PATH}")

    for file_name in os.listdir(JSON_FOLDER_PATH):
        if file_name.endswith(".json"):
            process_json_file(JSON_FOLDER_PATH / file_name)

    print("All JSON files processed and embedded into ChromaDB successfully!")


# Initialization
def init_chroma():
    """
    Initialize ChromaDB:
    - If collection is empty, populate with company data
    - If not empty, verify the existing data
    Returns the initialized collection
    """
    if collection.count() == 0:
        print("ChromaDB is empty. Populating with data...")
        process_all_json()
    else:
        print(f"ChromaDB already initialized with {collection.count()} records")

    return collection

# ---------------------
# Main Entry Point
# ---------------------
if __name__ == "__main__":
    init_chroma()
