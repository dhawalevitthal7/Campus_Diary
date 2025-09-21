
import chromadb

# Path where your ChromaDB data is stored
CHROMA_DB_PATH = "data/chroma_db"


client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
client.delete_collection(name='companies')