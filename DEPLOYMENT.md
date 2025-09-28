# Campus Diary Deployment Guide

## ChromaDB Setup and Persistence

### Local Development

1. First-time setup:
   ```bash
   # Install dependencies
   pip install -r requirements.txt
   
   # Initialize ChromaDB with company data
   python collection.py
   ```
   This will create a `chroma_data` directory in your project root.

2. The data will persist between runs as long as the `chroma_data` directory exists.

3. Before deploying, backup your data:
   ```bash
   python src/utils/backup_db.py backup
   ```
   This creates:
   - `backup/chroma_backup.json`: Portable data backup
   - `backup/chroma_data/`: Full ChromaDB directory backup

## Project Structure
```
/
├── chroma_data/         # Local ChromaDB data directory
├── src/                 # Source code
├── render_setup.sh      # Render deployment setup script
└── ...
```

## Local Setup

1. Configure environment variables:
   ```bash
   cp .env.template .env
   ```
   Edit `.env` and set:
   - `GEMINI_API_KEY`: Your Google Gemini API key
   - `CHROMA_DB_PATH`: Should be set to "chroma_data"

2. Initialize the database locally:
   ```bash
   python collection.py
   ```

3. The database will be created in the `chroma_data` directory at your project root.

### Render Deployment

1. In your Render dashboard, set environment variables:
   ```
   GEMINI_API_KEY=your_api_key
   IS_RENDER=true
   ```

2. Set up persistent storage:
   - Go to "Disks" in dashboard
   - Add a new disk
   - Mount path: `/data`
   - Size: At least 1GB

3. Initial deployment:
   ```bash
   # First, backup your local data
   python src/utils/backup_db.py backup
   
   # Copy backup to Render's /data directory
   scp backup/chroma_data.zip render:/data/
   ```

4. Build commands in Render:
   ```bash
   # Build command
   if [ ! -d "/data/chroma_data" ]; then
     cp -r chroma_data /data/
   fi
   
   # Start command
   uvicorn src.api.main:app --host 0.0.0.0 --port $PORT
   ```

Your ChromaDB will now:
- Use the same data between deployments
- Store data in `/data/chroma_data`
- Persist across restarts and updates

## Database Management

### Persistence
- ChromaDB data is stored in the `chroma_data` directory
- This directory is excluded from Git via `.gitignore`
- Always ensure the persistence directory exists and has proper permissions

### Backups
- Use the backup script to create database backups:
  ```
  python src/utils/backup_db.py
  ```
- Backups are stored in the `backups` directory
- Only the last 5 backups are kept to manage storage

## Deployment Checklist

1. Environment Setup:
   - [ ] Copy `.env.template` to `.env`
   - [ ] Configure all environment variables
   - [ ] Ensure `chroma_data` directory exists

2. Database Setup:
   - [ ] Verify ChromaDB persistence directory is properly configured
   - [ ] Set up regular backups (recommended: daily)
   - [ ] Test database connection and persistence

3. Security Considerations:
   - [ ] Secure the ChromaDB data directory with proper permissions
   - [ ] Use strong API keys and keep them secure
   - [ ] Configure firewall rules if needed
   - [ ] Implement rate limiting for API endpoints

## Maintenance

1. Regular Backups:
   - Run backups daily using the provided script
   - Store backups in a secure location
   - Verify backup integrity regularly

2. Monitoring:
   - Monitor disk space usage
   - Check application logs for errors
   - Monitor API response times

3. Updates:
   - Keep ChromaDB and dependencies updated
   - Test updates in a staging environment first
   - Maintain backup before applying updates

## Troubleshooting

1. If ChromaDB fails to start:
   - Check persistence directory permissions
   - Verify environment variables are set correctly
   - Check disk space availability

2. If data is not persisting:
   - Verify CHROMA_DB_PATH is set correctly
   - Check file system permissions
   - Verify ChromaDB is configured for persistence mode

3. API Issues:
   - Check API logs for errors
   - Verify environment variables
   - Check network connectivity and firewall settings