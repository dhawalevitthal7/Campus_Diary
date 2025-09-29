import json
import pathlib

# Resolve project root relative to this file (src/chunking/json_chunker.py)
project_root = pathlib.Path(__file__).resolve().parents[2]

# Input file path
input_path = project_root / "data" / "raw" / "companies.json"

# Output directory path
output_dir = project_root / "data" / "chunked_json"

# Create the output folder if it doesn't exist (including parents)
output_dir.mkdir(parents=True, exist_ok=True)

# Load the combined JSON data
with open(input_path, "r", encoding="utf-8") as f:
    all_companies_data = json.load(f)

# Define the chunk size
chunk_size = 4

# Split the data into chunks and save each chunk
for i in range(0, len(all_companies_data), chunk_size):
    chunk = all_companies_data[i : i + chunk_size]
    chunk_filename = output_dir / f"companies_chunk_{i // chunk_size + 1}.json"
    with open(chunk_filename, "w", encoding="utf-8") as f:
        json.dump(chunk, f, indent=4)
    print(f"Saved chunk to {chunk_filename.resolve()}")

print("\nFinished splitting companies data into chunks.")
