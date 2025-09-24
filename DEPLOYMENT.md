# Deployment Guide for ChromaDB Application

## Environment Setup

1. Copy `.env.template` to `.env` and fill in the required values:
   ```
   cp .env.template .env
   ```

2. Configure the following environment variables:
   - `GEMINI_API_KEY`: Your Google Gemini API key
   - `CHROMA_DB_PATH`: Path to store ChromaDB data (default: chroma_data)
   - `CHROMA_DB_HOST`: Host for ChromaDB (default: localhost)
   - `CHROMA_DB_PORT`: Port for ChromaDB (default: 8000)
   - `API_HOST`: Host for the FastAPI application (default: 0.0.0.0)
   - `API_PORT`: Port for the FastAPI application (default: 8000)

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