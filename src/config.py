import os
import pathlib
from dotenv import load_dotenv

load_dotenv()

# Base paths
IS_RENDER = str(os.getenv('IS_RENDER', '')).lower() == 'true'

# Set up base project path
if IS_RENDER:
    # On Render, the app is deployed to /opt/render/project/src
    BASE_PATH = pathlib.Path('/opt/render/project/src')
else:
    # Local development path (root of your project)
    BASE_PATH = pathlib.Path(__file__).parent.parent

# Set up ChromaDB path
CHROMA_DB_PATH = os.getenv('CHROMA_DB_PATH', 'chroma_data')

# ChromaDB persistence directory
if IS_RENDER:
    # On Render, store data in the persistent disk at /data/project_name/chroma_data
    RENDER_DATA_DIR = pathlib.Path('/data/campus_diary')
    CHROMA_DB_PERSIST_DIRECTORY = str(RENDER_DATA_DIR / CHROMA_DB_PATH)
    # Create the project directory in /data if it doesn't exist
    os.makedirs(RENDER_DATA_DIR, exist_ok=True)
else:
    # Local development: use chroma_data in project root
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