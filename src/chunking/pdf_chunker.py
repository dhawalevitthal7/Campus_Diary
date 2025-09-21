import json
import pathlib

BASE_DIR = pathlib.Path(__file__).resolve().parents[2]

INPUT_JSON = BASE_DIR / "data" / "raw_json" / "companies.json"   
OUTPUT_DIR = BASE_DIR / "data" / "chunked_json"                 
CHUNK_SIZE = 4                                                    

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def split_json_file(input_file, output_dir, chunk_size):
    """Split a JSON list into smaller chunked JSON files."""
    # Check if file exists
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found at: {input_file}")

    # Load data
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("The input JSON must contain a list of objects.")

    # Split and save
    for i in range(0, len(data), chunk_size):
        chunk = data[i: i + chunk_size]
        chunk_filename = output_dir / f"companies_chunk_{(i // chunk_size) + 1}.json"
        with open(chunk_filename, "w", encoding="utf-8") as f:
            json.dump(chunk, f, indent=4)
        print(f"Saved chunk to {chunk_filename}")

    print("\n🎉 Finished splitting JSON into chunks!")


if __name__ == "__main__":
    split_json_file(INPUT_JSON, OUTPUT_DIR, CHUNK_SIZE)
