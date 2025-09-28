#!/bin/bash

# This script runs during the deployment process on Render

echo "🚀 Starting deployment setup..."

# Create project directory in the persistent disk
mkdir -p /data/campus_diary/chroma_data

# If there's an existing backup in the project, copy it to the persistent disk
if [ -d "./chroma_data" ]; then
    echo "📦 Found local ChromaDB data, copying to persistent storage..."
    cp -r ./chroma_data/* /data/campus_diary/chroma_data/
    echo "✅ Data copied successfully"
fi

echo "✨ Setup complete!"