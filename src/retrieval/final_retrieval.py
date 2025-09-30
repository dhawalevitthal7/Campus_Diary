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


def serialize_chroma_result(result):
    """Normalize Chroma result to flat lists and cap to top-K."""
    if not isinstance(result, dict):
        return {"ids": [], "documents": [], "metadatas": []}
    ids = result.get("ids", [])
    docs = result.get("documents", [])
    metas = result.get("metadatas", [])
    # Flatten nested list shape [[...]] → [...]
    if ids and isinstance(ids[0], list):
        ids = ids[0]
    if docs and isinstance(docs[0], list):
        docs = docs[0]
    if metas and isinstance(metas[0], list):
        metas = metas[0]
    TOP_K = 3
    return {"ids": ids[:TOP_K], "documents": docs[:TOP_K], "metadatas": metas[:TOP_K]}

def finalretrieval(user_query: str):
    """Process user query and return relevant results quickly"""
    try:
        print(f"Processing query: {user_query}")
        # Run both retrieval paths in parallel for completeness
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            fut_meta = ex.submit(retriev, user_query)
            fut_vec = ex.submit(generate_embedding, user_query)
            raw_meta = fut_meta.result()
            raw_vec = fut_vec.result()
        res1 = serialize_chroma_result(raw_meta)
        res2 = serialize_chroma_result(raw_vec)
        print(f"Metadata search results: {len(res1.get('documents', []))} documents")
        print(f"Embedding search results: {len(res2.get('documents', []))} documents")
        
        # Prepare results for response (dedupe, then compact view for speed)
        all_docs = []
        seen_docs = set()
        
        for result in [res1, res2]:
            for doc, meta in zip(result.get("documents", []), result.get("metadatas", [])):
                if doc and doc not in seen_docs:
                    seen_docs.add(doc)
                    all_docs.append({"document": doc, "metadata": meta})
        
        if not all_docs:
            return "No matching companies found for your query. Please try different keywords."
        
        print(f"Found {len(all_docs)} matching companies")
        
        # Build compact context to minimize prompt size and speed up generation
        compact = []
        for item in all_docs[:4]:
            meta = item.get("metadata", {}) or {}
            compact.append({
                "name": meta.get("name") or meta.get("company_name"),
                "role": meta.get("role") or meta.get("domain"),
                "ctc": meta.get("ctc") or meta.get("ctc_min") or meta.get("lpa"),
                "locations": [
                    loc for loc in [meta.get("location_1"), meta.get("location_2")] if loc
                ],
                "eligibility": {
                    "cgpa": meta.get("cgpa") or meta.get("percent"),
                    "branches": [
                        b for b in [meta.get("branch_1"), meta.get("branch_2"), meta.get("branch_3"), meta.get("branch_4")] if b
                    ]
                }
            })

        prompt = f"""
        User Query: {user_query}
        Context (concise): {json.dumps(compact, indent=2)}
        Task: Write a detailed answer based only on the context. Include roles, CTC, locations, and eligibility if present. Keep it informative and helpful.
        also modify your answer according to user query.
        """
        # Fast generation with a strict time cap; fall back to template if slow
        import concurrent.futures
        def _gen():
            return model.generate_content(prompt)
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(_gen)
                response = fut.result(timeout=2.0)
                if response and getattr(response, 'text', None):
                    return response.text.strip()
        except Exception as model_error:
            print(f"Model generation issue: {str(model_error)}")

        # Fallback ultra-fast templated response
        lines = []
        for c in compact:
            lines.append(
                f"- {c.get('name') or 'Company'} | Role: {c.get('role') or 'N/A'} | CTC: {c.get('ctc') or 'N/A'} | Locations: {', '.join(c.get('locations', [])) or 'N/A'}"
            )
        return "\n".join(lines) if lines else "No matching results found."
            
    except Exception as e:
        print(f"Error in finalretrieval: {str(e)}")
        return f"An error occurred while processing your query: {str(e)}"
