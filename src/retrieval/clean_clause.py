import json
import ast
import re
import os
import chromadb
import google.generativeai as genai
from dotenv import load_dotenv
import types
load_dotenv()


numeric_keys = {"ctc", "lpa", "stipend"}

def cleanjson(text:str) -> str:
    """
    Remove markdown formatting such as ```json and ```
    """
    if not text or not isinstance(text, str):
        raise ValueError("AI response is empty or not a string")

    # Remove ```json and ```
    cleaned = re.sub(r"^```json\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
    return cleaned.strip()

def normalize_where_clause(raw_clause):
    """
    Recursively normalize the where clause:
    - Lowercase all keys.
    - Convert numeric strings to integers/floats.
    """
    if isinstance(raw_clause, dict):
        new_dict = {}
        for key, value in raw_clause.items():
            if key in ["$and", "$or"]:  # Logical operators
                new_dict[key] = [normalize_where_clause(v) for v in value]
            else:
                lower_key = key.lower()
                operator, val = next(iter(value.items()))

                # Convert numeric strings to integers/floats
                if lower_key in numeric_keys and isinstance(val, str):
                    try:
                        val = float(val) if "." in val else int(val)
                    except ValueError:
                        pass  # Leave as string if conversion fails

                new_dict[lower_key] = {operator: val}
        return new_dict
    return raw_clause

def group_conditions(where_dict, group_type="$and"):
    """
    Group conditions under $and/$or only if there are 2 or more conditions.
    Handles empty dictionaries safely.
    """
    if not isinstance(where_dict, dict):
        return where_dict

    # 🚨 Handle empty dictionary
    if not where_dict:
        print("⚠️ Warning: Empty where clause detected.")
        return {}

    # If dictionary already has $and or $or, leave as is
    if "$and" in where_dict or "$or" in where_dict:
        return where_dict

    # If multiple top-level keys, wrap them under $and or $or
    if len(where_dict) > 1:
        return {group_type: [{k: v} for k, v in where_dict.items()]}

    # If only one condition, return directly without $and
    key, value = next(iter(where_dict.items()))
    return {key: value}

