import os
import json
import shutil
import chromadb
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def backup_chroma_data(output_dir: str = "backup"):
    """
    Backup ChromaDB data and documents to a portable format
    """
    from src.config import get_chroma_client
    
    # Create backup directory
    backup_dir = Path(output_dir)
    backup_dir.mkdir(exist_ok=True)
    
    # Get ChromaDB collection
    client = get_chroma_client()
    collection = client.get_collection("companies")
    
    # Get all documents and their metadata
    results = collection.get()
    
    # Save to a JSON file
    backup_data = {
        "ids": results["ids"],
        "documents": results["documents"],
        "metadatas": results["metadatas"],
        "embeddings": results["embeddings"]
    }
    
    with open(backup_dir / "chroma_backup.json", "w") as f:
        json.dump(backup_data, f)
    
    print(f"✅ Backed up {len(results['ids'])} documents to {backup_dir}")
    return backup_dir / "chroma_backup.json"

def restore_chroma_data(backup_file: str):
    """
    Restore ChromaDB data from backup
    """
    from src.config import get_chroma_client
    
    # Load backup data
    with open(backup_file, "r") as f:
        backup_data = json.load(f)
    
    # Get ChromaDB collection
    client = get_chroma_client()
    
    # Delete existing collection if it exists
    try:
        client.delete_collection("companies")
    except:
        pass
    
    # Create new collection
    collection = client.create_collection("companies")
    
    # Restore data
    if backup_data["ids"]:
        collection.add(
            ids=backup_data["ids"],
            documents=backup_data["documents"],
            metadatas=backup_data["metadatas"],
            embeddings=backup_data["embeddings"]
        )
    
    print(f"✅ Restored {len(backup_data['ids'])} documents to ChromaDB")
    return len(backup_data['ids'])

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["backup", "restore"])
    parser.add_argument("--file", help="Backup file path for restore")
    args = parser.parse_args()
    
    if args.action == "backup":
        backup_chroma_data()
    elif args.action == "restore":
        if not args.file:
            print("❌ Please provide backup file path with --file")
            exit(1)
        restore_chroma_data(args.file)