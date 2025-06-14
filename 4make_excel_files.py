import json
import os
import argparse
from datetime import datetime
import pandas as pd

# Define the output columns
OUTPUT_COLUMNS = [
    "Ссылка",
    "Сообщение о договоре финансовой аренды",
    "Дата прекращения",
    "Причина прекращения",
    "Договор",
    "Срок финансовой аренды",
    "Лизингодатели",
    "Лизингополучатели",
    "ИНН",
    "ОГРНИП",
    "Предмет финансовой аренды (лизинга)",
    "Идентификатор",
    "Описание",
    "Классификатор",
    "Связанные сообщения",
]

# Placeholder for parse_columns function
def parse_columns(record: dict) -> dict:
    """
    Parse the record and return a dictionary with the required columns.
    This is a placeholder and should be implemented later.
    """
    return {k: "sample_data" for k in OUTPUT_COLUMNS}
    raise NotImplementedError("parse_columns function is not implemented yet.")

# Main script
def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Process JSON files and generate an Excel output.")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode (use ISO timestamp for output filename).")
    parser.add_argument("--force-recreate", action="store_true", help="Force recreate the output file.")
    args = parser.parse_args()

    # Directory containing JSON files
    raw_contents_dir = "3raw_contents"
    json_files = sorted([f for f in os.listdir(raw_contents_dir) if f.endswith(".json")])

    # Output filename
    if args.debug:
        output_filename = f"{datetime.now().isoformat()}.xlsx"
    else:
        output_filename = "final.xlsx"

    # Check if output file exists and should be recreated
    # if os.path.exists(output_filename) and not args.force_recreate:
    #     print(f"Output file '{output_filename}' already exists. Use --force-recreate to overwrite.")
    #     return

    # Initialize a list to store all parsed records
    all_records = []

    # Process each JSON file
    for json_file in json_files:
        file_path = os.path.join(raw_contents_dir, json_file)
        print(f"Processing file: {file_path}")

        # Load the JSON file
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Extract records from the JSON file
        for url, record in data.items():
            try:
                # Parse the record and append to the list
                parsed_record = parse_columns(record)
                all_records.append(parsed_record)
            except Exception as e:
                print(f"Error processing record in {file_path}: {e}")

    # Create a DataFrame from the parsed records
    df = pd.DataFrame(all_records, columns=OUTPUT_COLUMNS)

    # Write the DataFrame to an Excel file
    df.to_excel(output_filename, index=False)
    print(f"Output written to {output_filename}")

if __name__ == "__main__":
    main()