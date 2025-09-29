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

keywords = [
    "ctc","ctc_min","ctc_max"," domains","percent","location_1","location_2",
    "stipend","stipend_min","stipend_max","company_name","role","cgpa",
    "branch_1","branch_2","branch_3","branch_4",
]

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
    except Exception:
        model = None
else:
    model = None


def serialize_chroma_result(result):
    """Normalize ChromaDB result into a consistent short form."""
    if not isinstance(result, dict):
        return {"ids": [], "documents": [], "metadatas": []}

    # Chroma can return nested lists; flatten first entry if needed
    ids = result.get("ids", [])
    documents = result.get("documents", [])
    metadatas = result.get("metadatas", [])

    if ids and isinstance(ids[0], list):
        ids = ids[0]
    if documents and isinstance(documents[0], list):
        documents = documents[0]
    if metadatas and isinstance(metadatas[0], list):
        metadatas = metadatas[0]

    return {
        "ids": ids[:3],
        "documents": documents[:3],
        "metadatas": metadatas[:3],
    }

def prioritize_docs_for_query(all_docs, user_query: str):
    """Rank documents higher if company name or role appears in the query."""
    if not all_docs:
        return []
    uq = (user_query or "").lower()
    def score(item):
        meta = item.get("metadata", {}) or {}
        name = (meta.get("name") or meta.get("company_name") or "").lower()
        role = (meta.get("role") or meta.get("domain") or "").lower()
        s = 0
        if name and name in uq:
            s += 10
        if role and role in uq:
            s += 3
        return s
    return sorted(all_docs, key=score, reverse=True)

def finalretrieval(user_query: str):
    """Process user query combining metadata and embedding retrieval."""
    try:
        print(f"Processing query: {user_query}")
        # Run both retrievers in parallel and combine
        try:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
                fut_embed = ex.submit(generate_embedding, user_query)
                fut_meta = ex.submit(retriev, user_query)
                raw_embed = fut_embed.result()
                raw_meta = fut_meta.result()
        except Exception as e:
            print(f"Parallel retrieval error: {str(e)}")
            raw_embed = generate_embedding(user_query)
            raw_meta = retriev(user_query)

        res2 = serialize_chroma_result(raw_embed)
        res1 = serialize_chroma_result(raw_meta)
        print(f"Embedding search results: {len(res2.get('documents', []))} documents")
        print(f"Metadata search results: {len(res1.get('documents', []))} documents")
        
        # Prepare results for response
        all_docs = []
        seen_docs = set()
        
        # Combine unique results from both searches, prefer embedding ordering
        for result in [res2, res1]:
            for doc, meta in zip(result.get("documents", []), result.get("metadatas", [])):
                if doc and doc not in seen_docs:
                    seen_docs.add(doc)
                    all_docs.append({"document": doc, "metadata": meta})
        
        if not all_docs:
            return "No matching companies found for your query. Please try different keywords."
        
        print(f"Found {len(all_docs)} matching companies")
        
        ranked_docs = prioritize_docs_for_query(all_docs, user_query)
        # Create a detailed prompt for accurate responses
        prompt = f"""
        User Query: {user_query}
        
        Retrieved company data (ranked by relevance):
        {json.dumps(ranked_docs[:5], indent=2)}
        
        Instructions:
        1. If the query asks "how can I be best fit" or preparation for a specific company:
           - Analyze the company's requirements from the retrieved data
           - Extract: required skills, CGPA/percent criteria, eligible branches, locations, CTC ranges
           - Provide specific, actionable advice: what skills to learn, projects to build, topics to practice
           - Mention eligibility criteria and application process if available
           - Give concrete steps the user can take to improve their chances
        
        2. If asking about company details (placement process, CTC, roles):
           - Summarize the company's placement information from the data
           - Include specific roles, CTC ranges, locations, and requirements
           - Highlight key eligibility criteria and application details
        
        3. For general company queries:
           - Provide comprehensive information about the company based on retrieved data
           - Include roles, CTC, locations, and any special requirements
        
        Always base your response strictly on the retrieved data. Be specific, helpful, and actionable.
        """
        # Generate response directly (no timeout). If model is unavailable or fails, fall back.
        if model is not None:
            try:
                response = model.generate_content(prompt)
                if response and getattr(response, 'text', None):
                    return response.text.strip()
            except Exception as e:
                print(f"Model generation failed: {str(e)}")
        # Enhanced fallback summary without LLM
        summary_items = []
        for item in ranked_docs[:3]:
            meta = item.get("metadata", {}) or {}
            name = meta.get("name") or meta.get("company_name") or "Company"
            ctc = meta.get("ctc") or meta.get("ctc_min") or meta.get("lpa")
            locs = [meta.get("location_1"), meta.get("location_2")] 
            locs = ", ".join([l for l in locs if l]) or "N/A"
            role = meta.get("role") or meta.get("domain") or "N/A"
            cgpa = meta.get("cgpa") or meta.get("percent")
            branch = [meta.get("branch_1"), meta.get("branch_2"), meta.get("branch_3"), meta.get("branch_4")]
            branch = ", ".join([b for b in branch if b]) or "N/A"
            
            item_text = f"• {name}\n  Role: {role}\n  CTC: {ctc or 'N/A'} LPA\n  Locations: {locs}\n  Eligibility: CGPA {cgpa or 'N/A'}, Branches: {branch}"
            summary_items.append(item_text)
        
        return f"Based on the available data, here are the top matches:\n\n" + "\n\n".join(summary_items)
            
    except Exception as e:
        print(f"Error in finalretrieval: {str(e)}")
        return f"An error occurred while processing your query: {str(e)}"
