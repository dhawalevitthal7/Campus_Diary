import json
import os
import uuid
import chromadb
import google.generativeai as genai
import pathlib
from dotenv import load_dotenv

load_dotenv()

base_path = pathlib.Path(__file__).parent.parent.parent

# --- CONFIGURATION ---
JSON_FOLDER_PATH = base_path / "data" / "chunked_json"  # Folder containing multiple JSON files
CHROMA_DB_PATH = base_path / "chroma_data"   # Path for persistent Chroma database
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")   # Replace with your valid Gemini API key

# --- Initialize Persistent Chroma client ---
client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

# --- Create or get collection ---
collection = client.get_or_create_collection(name="companies")

# --- Initialize Gemini Client ---
genai.configure(api_key=GEMINI_API_KEY)
print("✅Gemini client initialized successfully!")

def generate_embedding(text: str):
    """
    Generate embedding using Google's Gemini text-embedding-004 model.
    """
    try:
        response = genai.embed_content(
            model="models/text-embedding-004",
            content=text
        )
        return response['embedding']  # Returns a list of floats (768 dimensions)
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return [0.0] * 768  # fallback to prevent pipeline crash

# --- Function to clean and extract metadata ---
def extract_metadata(company):
    """
    Extract and clean metadata from company JSON.
    - Converts keys to lowercase and underscores.
    - Keeps numeric values like CTC, LPA, Stipend as numbers.
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

    meta["name"] = company["Name"].strip()  # Always include company name
    return meta

# --- Function to build clean embedding text ---
def build_embedding_text(company):
    """
    Build a text representation of the company for embeddings.
    """
    text = f"Company Name: {company['Name']}\n"
    text += f"Description: {company.get('description', '')}\n"
    for item in company.get("Keys", []):
        text += f"{item['key']}: {item['value']}\n"
    return text

# --- Function to process a single JSON file ---
def process_json_file(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        companies_data = json.load(f)

    print(f"✅ Loaded {len(companies_data)} companies from {os.path.basename(json_path)}")

    ids, documents, metadatas, embeddings = [], [], [], []

    print("🔹 Generating embeddings using Gemini...")
    for company in companies_data:
        # ✅ Create unique ID using UUID
        company_id = f"{company['Name'].strip()}_{uuid.uuid4()}"

        text = build_embedding_text(company)
        vector = generate_embedding(text)  # Gemini embedding

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

    print(f"🎉 Added {len(ids)} companies from {os.path.basename(json_path)} to Chroma!\n")

# --- MAIN LOOP: Process every JSON file in the folder ---
for file_name in os.listdir(JSON_FOLDER_PATH):
    if file_name.endswith(".json"):  # Only process .json files
        file_path = os.path.join(JSON_FOLDER_PATH, file_name)
        process_json_file(file_path)

print("🚀 All JSON files processed and embedded into Chroma successfully!")
