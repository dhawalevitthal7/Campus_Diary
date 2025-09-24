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
    Handles empty dictionaries and invalid cases safely.
    """
    if not isinstance(where_dict, dict):
        return None

    # 🚨 Handle empty dictionary
    if not where_dict:
        print("⚠️ Warning: Empty where clause detected.")
        return None

    # If dictionary already has $and or $or operators
    if any(op in where_dict for op in ["$and", "$or"]):
        for op in ["$and", "$or"]:
            if op in where_dict:
                conditions = where_dict[op]
                # Validate conditions is a non-empty list with at least 2 items
                if not isinstance(conditions, list) or len(conditions) < 2:
                    print(f"⚠️ Warning: Invalid {op} conditions")
                    return None
        return where_dict

    # Convert flat dictionary to list of conditions
    conditions = []
    for key, value in where_dict.items():
        if isinstance(value, dict):
            conditions.append({key: value})
        else:
            print(f"⚠️ Warning: Invalid value format for key {key}")
            return None

    # Return based on number of conditions
    if len(conditions) == 0:
        return None
    elif len(conditions) == 1:
        # Single condition, return without group operator
        return conditions[0]
    else:
        # Multiple conditions, group under specified operator
        return {group_type: conditions}
    return {key: value}

