import shutil
import os
import datetime
from pathlib import Path
from src.config import CHROMA_DB_PERSIST_DIRECTORY

def backup_chromadb():
    """
    Create a backup of the ChromaDB data directory.
    The backup will be created in a 'backups' folder with a timestamp.
    """
    # Create backups directory if it doesn't exist
    backup_dir = Path('backups')
    backup_dir.mkdir(exist_ok=True)

    # Generate timestamp for the backup
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = backup_dir / f'chroma_backup_{timestamp}'

    try:
        # Create the backup
        shutil.copytree(CHROMA_DB_PERSIST_DIRECTORY, backup_path)
        print(f"Backup created successfully at {backup_path}")
        
        # Keep only the last 5 backups
        backups = sorted(backup_dir.glob('chroma_backup_*'))
        if len(backups) > 5:
            for old_backup in backups[:-5]:
                shutil.rmtree(old_backup)
                print(f"Removed old backup: {old_backup}")
                
        return True
    except Exception as e:
        print(f"Error creating backup: {e}")
        return False

if __name__ == "__main__":
    backup_chromadb()