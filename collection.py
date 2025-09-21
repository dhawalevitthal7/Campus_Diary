def init_chroma():
    """
    Initialize ChromaDB:
    - Check if the collection already has data.
    - If empty, populate it from the JSON folder.
    """
    if collection.count() == 0:
        print("⚡ ChromaDB is empty. Populating with company data...")
        process_all_json()
    else:
        print(f"✅ ChromaDB already initialized with {collection.count()} records.")

    return collection


if __name__ == "__main__":
    init_chroma()
