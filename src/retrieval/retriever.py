import os
import re
import json
import ast
import chromadb
import google.generativeai as genai

# Import generate_embedding from chroma_manager
from src.embedding.chroma_manager import generate_embedding

# Load Gemini API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise EnvironmentError("GEMINI_API_KEY not found! Please set it in environment variables.")

# Configure Gemini globally
genai.configure(api_key=GEMINI_API_KEY)

# ChromaDB configuration
CHROMA_DB_PATH = "data/chroma_db"

# Initialize ChromaDB Persistent Client
client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

# Get or create collection
collection = client.get_or_create_collection(name="companies")

keywords = [
    "AI chat bots", "GitHub", "HackerRank", "B.E/B.Tech", "multinational company",
    "Questions C, C++", "Web Methods", "Oracle", "Key Persons:", "Chairman:",
    "Spring Boot", "ReachJS", "MongoDB", "Angular JS", "Azure ML", "DevOps",
    "training program", "Innovate", "Java", "J2EE", "Design Patterns", "Spring MVC",
    "XML", "WebServices", "WebLogic", "DOM", "skills", "requirements", "Roles", "CTC",
    "Stipend", "Job Description", "Job Role", "The Area", "Requirements",
    "Selection Process", "Eligibility", "Location", "Compensation", "Role expectations",
    "Desired Competencies", "Key Persons", "Applications are invited", "Skill set",
    "Domains", "Evaluation Criteria", "Experience & Expectation", "What You'll Do",
    "What You'll Bring", "Responsibilities", "Qualifications", "Essential skills",
    "Key Responsibilities", "selection process"
]

def is_count_query(user_query: str) -> bool:
    """
    Detect if the user query is asking for a count of companies.
    """
    count_keywords = [
        r"how many companies", r"total companies", r"number of companies",
        r"count of companies", r"companies count", r"how many firms",
        r"total firms", r"number of firms"
    ]
    return any(re.search(pattern, user_query.lower()) for pattern in count_keywords)

def extract_user_filters(user_query: str):
    """
    Use Gemini to extract filters like location, skills, ctc, etc. from a natural language query.
    Returns JSON as string.
    """
    prompt = f"""
    You are a helpful assistant that extracts structured filter data from a user query.
    Return ONLY a valid JSON object, nothing else.
    
    Example output:
    {{
        "location": "Bangalore",
        "ctc": 20,
        "skills": "Java"
    }}
    
    Numeric fields: "ctc", "stipend".
    If both CTC and LPA are present, return only one.
    User query: {user_query}
    """

    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)

    filters_json = response.text.strip()
    print("\n[Gemini Raw Filters Output]:\n", filters_json)
    return filters_json

def clean_ai_response(response: str) -> str:
    """
    Remove markdown code fences like ```json ... ```
    """
    if not response or not isinstance(response, str):
        raise ValueError("AI response is empty or not a string")

    cleaned = re.sub(r"^```json\s*|\s*```$", "", response.strip(), flags=re.MULTILINE)
    return cleaned.strip()

def parse_filters_to_dict(filters_str: str):
    """
    Convert Gemini output string into a Python dictionary.
    """
    cleaned_response = clean_ai_response(filters_str)
    try:
        return json.loads(cleaned_response)
    except json.JSONDecodeError:
        return ast.literal_eval(cleaned_response)

numeric_keys = {"ctc", "lpa", "stipend"}

def normalize_where_clause(raw_clause):
    """
    Normalize the where clause:
    - Lowercase keys
    - Convert numeric strings to numbers
    """
    if isinstance(raw_clause, dict):
        new_dict = {}
        for key, value in raw_clause.items():
            if key in ["$and", "$or"]:
                new_dict[key] = [normalize_where_clause(v) for v in value]
            else:
                lower_key = key.lower()
                operator, val = next(iter(value.items())) if isinstance(value, dict) else ("$eq", value)

                if lower_key in numeric_keys and isinstance(val, str):
                    try:
                        val = float(val) if "." in val else int(val)
                    except ValueError:
                        pass

                new_dict[lower_key] = {operator: val}
        return new_dict
    return raw_clause

def group_conditions(where_dict, group_type="$and"):
    """
    Group multiple conditions under $and or $or only if more than one condition exists.
    """
    if not isinstance(where_dict, dict):
        return where_dict

    if not where_dict:
        return {}

    if "$and" in where_dict or "$or" in where_dict:
        return where_dict

    if len(where_dict) > 1:
        return {group_type: [{k: v} for k, v in where_dict.items()]}

    key, value = next(iter(where_dict.items()))
    return {key: value}


def build_where_clause(user_query: str):
    """
    Full pipeline: Extract filters -> Normalize -> Group -> Final where_clause
    """
    user_filters_raw = extract_user_filters(user_query)
    if not user_filters_raw:
        return {}

    parsed_filters = parse_filters_to_dict(user_filters_raw)
    print("\n[Parsed Filters as Dict]:\n", parsed_filters)

    normalized_clause = normalize_where_clause(parsed_filters)
    print("\n[Normalized Where Clause]:\n", normalized_clause)

    final_where_clause = group_conditions(normalized_clause, group_type="$and")
    print("\n[Final Where Clause for Chroma]:\n", json.dumps(final_where_clause, indent=4))
    return final_where_clause

def generate_final_answer(user_query, r1, r2):
    """
    Combine filter-based results {r1} and vector search results (r2),
    then ask Gemini to generate a natural language final answer.
    """

    system_prompt = f"""
    If the query "{user_query}" contains any keys from {keywords} and {r1} is not empty,
    then strictly consider only {r1}.
    Else, if both {r1} and {r2} are non-empty, analyze both and combine them
    to generate a precise answer.
    Else, if only {r2} is non-empty, consider {r2}.
    Focus only on the **company name and description** fields.
    The response must be in **plain text** and answer the user query directly and precisely.
    """

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=system_prompt
    )

    contents = f"""
    User query: {user_query}
    Filter-based results (r1): {r1}
    Vector-based results (r2): {r2}
    """

    response = model.generate_content(contents)
    return response.text.strip()

def query_chroma(user_query: str, limit=5):
    """
    Query ChromaDB collection using both filter-based and vector-based approaches.
    """

    # Handle count queries directly
    if is_count_query(user_query):
        total_companies = collection.count()
        answer = f"There are a total of {total_companies} companies in the database."
        print("\n[Count Query Detected]:", answer)
        return answer

    # Step A: Build where clause
    final_where_clause = build_where_clause(user_query)

    # Step B: Filter-based retrieval (r1)
    if final_where_clause and len(final_where_clause) > 0:
        r1 = collection.get(where=final_where_clause, limit=limit)
    else:
        print("Warning: final_where_clause is empty. Skipping filter-based retrieval...")
        r1 = {}

    # Step C: Vector-based retrieval (r2) using generate_embedding from chroma_manager
    query_vector = generate_embedding(user_query)
    r2 = collection.query(query_embeddings=[query_vector], n_results=limit)

    print("\n[Filter-based Results] r1:\n", r1)
    print("\n[Vector-based Results] r2:\n", r2)

    # Step D: Combine and generate final natural language response
    final_answer = generate_final_answer(user_query, r1, r2)
    print("\n[Final Answer]:\n", final_answer)
    return final_answer

# =========================================
# MAIN EXECUTION
# =========================================
# if __name__ == "__main__":
#     user_query = "Tell me about TravClan with CTC greater than 20"
#     result = query_chroma(user_query, limit=5)
#     print("\nUser Response:\n", result)
