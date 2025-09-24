import json
import ast
import re
import os
import chromadb
import pathlib
import google.generativeai as genai
from dotenv import load_dotenv
import types
from .retriever1 import retriev
from .retriever2 import generate_embedding


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# Initialize Gemini model
model = genai.GenerativeModel('gemini-2.0-flash')


def finalretrieval(user_query:str):
    res1 = retriev(user_query)
    res2 = generate_embedding(user_query)
    system_instruction = f"""
    analyse both the results {res1} and {res2} and then by having context of both the results 
    you have to make perfect analysed decision on whatever user query is {user_query}. 
    and according to user query and considering both the query you have to make user friendly response 
    """
    content = f"""
        resluts: {res1} and {res2}
        user query : {user_query}
    """

    try:
        result = model.generate_content(
            contents=[system_instruction, content]
        )
        return result.text  # Return the text content of the response
    except Exception as e:
        print(f"Error in generate_content: {str(e)}")
        raise  # Re-raise the exception to be caught by the API endpoint
