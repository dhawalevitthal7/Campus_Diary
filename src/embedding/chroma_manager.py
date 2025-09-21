import json
import os
import uuid
import pathlib
import chromadb
import google.generativeai as genai

from dotenv import load_dotenv
load_dotenv() 


BASE_DIR = pathlib.Path(__file__).resolve().parents[2]

JSON_FOLDER_PATH = BASE_DIR / "data" / "chunked_json"

# Persistent ChromaDB folder (now inside data/chroma_db)
CHROMA_DB_PATH = BASE_DIR / "data" / "chroma_db"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise EnvironmentError(" GEMINI_API_KEY not found! Please set it as an environment variable.")

# Persistent Chroma client
client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))

# Create or get collection
collection = client.get_or_create_collection(name="companies")

genai.configure(api_key=GEMINI_API_KEY)

def generate_embedding(text: str):
    """
    Generate an embedding vector using Google's Gemini embedding model.
    """
    try:
        response = genai.embed_content(
            model="models/text-embedding-004",
            content=text
        )
        return response['embedding']
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return [0.0] * 768  # Fallback to avoid pipeline crash


def extract_metadata(company):
    """
    Extract clean metadata from company JSON:
    - Converts keys to lowercase with underscores
    - Converts numeric values for CTC, LPA, Stipend
    """
    meta = {}
    numeric_keys = {"ctc", "lpa", "stipend"}

    for item in company.get("Keys", []):
        key_name = item["key"].lower().replace(" ", "_")
        value = item["value"]

        if key_name in numeric_keys and isinstance(value, str):
            try:
                value = float(value) if "." in value else int(value)
            except ValueError:
                pass

        meta[key_name] = value

    meta["name"] = company["Name"].strip()
    return meta


def build_embedding_text(company):
    """
    Build a clean text string representation of a company.
    This is what we send to Gemini to generate embeddings.
    """
    text = f"Company Name: {company['Name']}\n"
    text += f"Description: {company.get('description', '')}\n"
    for item in company.get("Keys", []):
        text += f"{item['key']}: {item['value']}\n"
    return text


def process_json_file(json_path):
    """
    Process a single JSON file:
    - Load data
    - Generate embeddings
    - Store results in ChromaDB
    """
    with open(json_path, "r", encoding="utf-8") as f:
        companies_data = json.load(f)

    ids, documents, metadatas, embeddings = [], [], [], []

    print("🔹 Generating embeddings using Gemini...")
    for company in companies_data:
        company_id = f"{company['Name'].strip()}_{uuid.uuid4()}"
        text = build_embedding_text(company)
        vector = generate_embedding(text)

        ids.append(company_id)
        documents.append(text)
        metadatas.append(extract_metadata(company))
        embeddings.append(vector)

    # Add data to Chroma collection
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings
    )

def process_all_json():
    """
    Process all JSON files inside the JSON_FOLDER_PATH.
    """
    if not JSON_FOLDER_PATH.exists():
        raise FileNotFoundError(f" JSON folder not found: {JSON_FOLDER_PATH}")

    for file_name in os.listdir(JSON_FOLDER_PATH):
        if file_name.endswith(".json"):
            file_path = JSON_FOLDER_PATH / file_name
            process_json_file(file_path)

    print(" All JSON files processed and embedded into Chroma successfully!")


if __name__ == "__main__":
    process_all_json()
