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

import sys
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.config import get_chroma_client

# Initialize Persistent Chroma client 
client1 = get_chroma_client()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel('gemini-2.0-flash')

# Create or get collection 
collection = client1.get_or_create_collection(name="companies")

keywords = [
    "ctc","ctc_min","ctc_max"," domains","percent","location_1","location_2",
    "stipend","stipend_min","stipend_max","company_name","role","cgpa",
    "branch_1","branch_2","branch_3","branch_4",
]

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

    try:
        print("Debug - Raw where clause:", raw_where_clause)
        print("Debug - Normalized clause:", normalized_clause)
        
        if not normalized_clause or not isinstance(normalized_clause, dict):
            print("Debug - No valid normalized clause, querying without filters")
            results1 = collection.get(
                limit=3
            )
        else:
            # Group conditions only if we have valid filters
            final_where_clause = group_conditions(normalized_clause, group_type="$and")
            print("Debug - Final where clause:", final_where_clause)
            
            # Special handling for empty where clause or single conditions
            if not final_where_clause or len(final_where_clause) == 0:
                results1 = collection.get(
                    limit=3
                )
            elif "$and" in final_where_clause and not final_where_clause["$and"]:
                # If $and list is empty, remove it and do a simple query
                results1 = collection.get(
                    limit=3
                )
            else:
                results1 = collection.get(
                    where=final_where_clause,
                    limit=3
                )
    except Exception as e:
        print(f"Error processing where clause: {e}")
        results1 = collection.get(
            limit=3
        )

    if final_where_clause and len(final_where_clause) > 0:
        results1 = collection.get(
            where=final_where_clause,
            limit=3
        )
    else:
        # When no filters, fetch without where clause
        results1 = collection.get(
            limit=3
        )

    return results1
