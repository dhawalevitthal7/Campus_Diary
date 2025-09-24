import os
import pathlib
from dotenv import load_dotenv

load_dotenv()

# Base paths
IS_RENDER = str(os.getenv('IS_RENDER', '')).lower() == 'true'

# Set up database paths
if IS_RENDER:
    # Use mounted disk on Render
    BASE_PATH = '/data'
    CHROMA_DB_PATH = os.getenv('CHROMA_DB_PATH', 'chroma_data')
    CHROMA_DB_PERSIST_DIRECTORY = os.path.join(BASE_PATH, CHROMA_DB_PATH)
else:
    # Local development path
    BASE_PATH = pathlib.Path(__file__).parent.parent
    CHROMA_DB_PATH = os.getenv('CHROMA_DB_PATH', 'chroma_data')
    CHROMA_DB_PERSIST_DIRECTORY = str(BASE_PATH / CHROMA_DB_PATH)

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