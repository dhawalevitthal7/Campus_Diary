import json
import ast
import re
import os
import chromadb
import pathlib
import google.generativeai as genai
from dotenv import load_dotenv
import types
from src.retrieval.clean_clause import group_conditions , cleanjson , normalize_where_clause
load_dotenv()

base_path = pathlib.Path(__file__).parent.parent.parent
CHROMA_DB_PATH = base_path / "chroma_data"
# --- Initialize Persistent Chroma client ---
client1 = chromadb.PersistentClient(path=CHROMA_DB_PATH)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# Initialize Gemini model
model = genai.GenerativeModel('gemini-2.0-flash')

# --- Create or get collection ---
collection = client1.get_or_create_collection(name="companies")

keywords = [
    "ctc","ctc_min","ctc_max"," domains","percent","location_1","location_2",
    "stipend","stipend_min","stipend_max","company_name","role","cgpa",
    "branch_1","branch_2","branch_3","branch_4",
]

# --- Step 3: Normalize keys and numeric values ---



def retriev(user_query: str) :
    systeminstruction = f"""
    You are a helpful assistant that helps to findout or filter metadata like {keywords} from user query{user_query}
    and then strictly return structure like this, dont add anything else.
    {{
        "location": "Bangalore",
        "ctc": 22,
        "skills": "communication",
    }}
    it could contain more than one key-value pair, which can be taken from user query only
    numeric_keys = {{"ctc", "stipend","cgpa","percent"}} this are numeric value
    also if there will LPA or CTC or package then return only one i.e. ctc in json
    if user query will have range between ctc so min value should map with ctc_min and max value should map with ctc_max
    if user query will have range between stipend so min value should map with stipend_min and max value should map with stipend_max
    also if user query have multiple location then map it with location_1 or location_2 if only single location then map it to location_1
    same goes for branch

    You are a professional coder with expertise in RAG systems.

    Your task is to **generate a valid `where_clause` for ChromaDB** by analyzing:
    1. {{
        "location": "Bangalore",
        "ctc": 22,
        "domain": "communication",
        }} 
        → structured data with possible filter values.
    2. {user_query} → natural language query from the user.

    ⚠ **Important Rules**:
    - Strictly use ONLY these operators supported by ChromaDB: `$eq`, `$ne`, `$gt`, `$gte`, `$lt`, `$lte`, `$in`, `$nin`.
    - NEVER use `$contains` or any other unsupported operator.
    - Output must **strictly follow this JSON format** and nothing else:
    {{
        "$and": [
            {{"location": {{"$eq": "Bangalore"}}}},
            {{"ctc": {{"$gt": 20}}}},
        ]
    }}

    - Choose the correct operator based on the context:
        * Equality match → `$eq`
        * Greater / less than → `$gt`, `$gte`, `$lt`, `$lte`
        * Multiple possible matches → `$in`

    Example:
    - If `user_query` = "Find Java developers in Bangalore with CTC greater than 20",
    and `user_filters` = `{{"domain": "Java", "location": "Bangalore", "ctc": 20}}`

    Return:
    {{
        "$and": [
            {{"domain": {{"$eq": "Java"}}}},
            {{"location_1": {{"$eq": "Bangalore"}}}},
            {{"ctc": {{"$gt": 20}}}}
        ]
    }}

    if there is only one condition then dont return and or operators.
    Your response **must only be the JSON object**, no extra text or explanation.
    """
    content = f"""
    user query: {user_query}
    """
    response = model.generate_content(
        contents=[systeminstruction, content]
    )
    where_clause = response.text
    cleaned_response = cleanjson(where_clause)
    raw_where_clause = json.loads(cleaned_response)
    normalized_clause = normalize_where_clause(raw_where_clause)
    if not normalized_clause:
        final_where_clause = {}
    else:
        final_where_clause = group_conditions(normalized_clause, group_type="$and")

    if final_where_clause and len(final_where_clause) > 0:
    # ✅ Use where filter
        results1 = collection.get(
            where=final_where_clause,
            limit=3
        )
    else:
        print("⚠️ Warning: final_where_clause is empty. Fetching without filter...")
        results1 = collection.get(
            limit=3 # Fetch top 10 without filtering
        )

    return results1