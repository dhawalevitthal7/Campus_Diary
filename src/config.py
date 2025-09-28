import os
import pathlib
from dotenv import load_dotenv

load_dotenv()

# Base paths
IS_RENDER = str(os.getenv('IS_RENDER', '')).lower() == 'true'

# Get the absolute path to the project root directory
PROJECT_ROOT = pathlib.Path(__file__).parent.parent.absolute()

# ChromaDB will always be in a directory named 'chroma_data' for consistency
CHROMA_DB_PATH = 'chroma_data'

# Set up the ChromaDB persistence directory
if IS_RENDER:
    # On Render, use the persistent disk mounted at /data
    CHROMA_DB_PERSIST_DIRECTORY = str(pathlib.Path('/data/chroma_data'))
else:
    # In local development, use the chroma_data directory in project root
    CHROMA_DB_PERSIST_DIRECTORY = str(PROJECT_ROOT / CHROMA_DB_PATH)

# Ensure the persistence directory exists
os.makedirs(CHROMA_DB_PERSIST_DIRECTORY, exist_ok=True)

print(f"📂 ChromaDB persistence directory: {CHROMA_DB_PERSIST_DIRECTORY}")

# ChromaDB settings
import chromadb
CHROMA_SETTINGS = chromadb.config.Settings(
    allow_reset=False,  # Prevent accidental database resets
    anonymized_telemetry=False,  # Disable telemetry for security
    is_persistent=True  # Ensure persistence is always enabled
)

# Create ChromaDB persist directory if it doesn't exist
os.makedirs(CHROMA_DB_PERSIST_DIRECTORY, exist_ok=True)

# API settings
API_HOST = os.getenv('API_HOST', '0.0.0.0')
API_PORT = int(os.getenv('API_PORT', '8000'))

def get_chroma_client():
    """
    Get a ChromaDB client with the configured settings.
    Returns:
        ChromaDB client instance
    """
    import chromadb
    return chromadb.PersistentClient(
        path=CHROMA_DB_PERSIST_DIRECTORY,
        settings=CHROMA_SETTINGS
    )