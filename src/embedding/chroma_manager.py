import json
import os
import uuid
import pathlib
import chromadb
import google.generativeai as genai
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

# === PATHS ===
BASE_DIR = pathlib.Path(__file__).resolve().parents[2]
JSON_FOLDER_PATH = BASE_DIR / "data" / "chunked_json"
CHROMA_DB_PATH = BASE_DIR / "data" / "chroma_db"

# === Gemini API Key ===
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise EnvironmentError("GEMINI_API_KEY not found! Please set it as an environment variable.")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# === Persistent Chroma Client ===
client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))

# Create or get collection
companies_collection = client.get_or_create_collection(name="companies")


# ---------------------
# Embedding Generation
# ---------------------
def generate_embedding(text: str):
    """Generate an embedding vector using Gemini."""
    try:
        response = genai.embed_content(
            model="models/text-embedding-004",
            content=text
        )
        return response['embedding']
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return [0.0] * 768  # fallback to avoid crashing


# ---------------------
# Metadata Processing
# ---------------------
def extract_metadata(company):
    """Extract clean metadata from a company JSON."""
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
    """Build a clean text string for Gemini embeddings."""
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

    ids, documents, metadatas, embeddings = [], [], [], []

    print(f"🔹 Processing file: {json_path}")
    for company in companies_data:
        company_id = f"{company['Name'].strip()}_{uuid.uuid4()}"
        text = build_embedding_text(company)
        vector = generate_embedding(text)

        ids.append(company_id)
        documents.append(text)
        metadatas.append(extract_metadata(company))
        embeddings.append(vector)

    companies_collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings
    )


def process_all_json():
    """Process all JSON files inside JSON_FOLDER_PATH."""
    if not JSON_FOLDER_PATH.exists():
        raise FileNotFoundError(f"JSON folder not found: {JSON_FOLDER_PATH}")

    for file_name in os.listdir(JSON_FOLDER_PATH):
        if file_name.endswith(".json"):
            process_json_file(JSON_FOLDER_PATH / file_name)

    print("✅ All JSON files processed and embedded into Chroma successfully!")


# ---------------------
# Initialization
# ---------------------
def init_chroma():
    """
    Initialize Chroma:
    - If the collection is empty, populate it with company data.
    """
    if companies_collection.count() == 0:
        print("⚡ ChromaDB is empty. Populating with data...")
        process_all_json()
    else:
        print(f"✅ ChromaDB already initialized with {companies_collection.count()} records.")

    return companies_collection


# ---------------------
# Run standalone
# ---------------------
if __name__ == "__main__":
    init_chroma()
