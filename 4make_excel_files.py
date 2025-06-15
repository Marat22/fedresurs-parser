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
    """
    parsed_data = {}

    # Extract 'Ссылка'
    parsed_data["Ссылка"] = record.get("url", "")

    # Extract 'Сообщение о договоре финансовой аренды'
    parsed_data["Сообщение о договоре финансовой аренды"] = record.get("Сообщение", {}).get("Договор", "")

    # Extract 'Дата прекращения' and 'Причина прекращения'
    # This part is more complex and depends on the structure of the data.
    # For now, we'll leave them as placeholders or empty strings.
    parsed_data["Дата прекращения"] = record.get("Сообщение", {}).get("Дата прекращения", "")
    parsed_data["Причина прекращения"] = record.get("Сообщение", {}).get("Причина прекращения", "")

    # Extract 'Договор'
    parsed_data["Договор"] = record.get("Сообщение", {}).get("Договор", "")

    # Extract 'Срок финансовой аренды'
    parsed_data["Срок финансовой аренды"] = record.get("Сообщение", {}).get("Срок финансовой аренды", "")

    # Extract 'Лизингодатели'
    publ = record.get("Публикатор", {})
    parsed_data["Лизингодатели"] = f"{publ.get('name', '')}\nИНН\n{publ.get('ИНН', '')}\nОГРН\n{publ.get('ОГРН', '')}"

    # Extract 'Лизингополучатели'
    msg = record.get("Сообщение", {})
    parsed_data["Лизингополучатели"] = msg.get("Лизингополучатели", "")

    # Extract 'ИНН' and 'ОГРНИП'
    parsed_data["ИНН"] = publ.get("ИНН", "")
    parsed_data["ОГРНИП"] = msg.get("ОГРНИП", "")

    # Extract 'Предмет финансовой аренды (лизинга)'
    # Combine all identifiers, descriptions, and classifiers from the 'Предметы финансовой аренды (лизинга)' field
    items = msg.get("Предметы финансовой аренды (лизинга)", {})
    identificators = []
    descriptions = []
    classifiers = []

    for key in items:
        item = items[key]
        identificators.append(item.get("Идентификатор", ""))
        descriptions.append(item.get("Описание", ""))
        classifiers.append(item.get("Классификатор", ""))

    parsed_data["Предмет финансовой аренды (лизинга)"] = "\n".join(identificators)

    # Extract 'Идентификатор'
    parsed_data["Идентификатор"] = "\n".join(f"№{k}. {i}" for k, i in enumerate(identificators, 1))

    # Extract 'Описание'
    parsed_data["Описание"] = "\n".join(f"№{k}. {i}" for k, i in enumerate(descriptions, 1))

    # Extract 'Классификатор'
    parsed_data["Классификатор"] = "\n".join(f"№{k}. {i}" for k, i in enumerate(classifiers, 1))

    # Extract 'Связанные сообщения'
    related_messages = record.get("Связанные сообщения", {})
    related_entries = []
    for key, value in related_messages.items():
        related_entries.append(f"{key} {value}")
    parsed_data["Связанные сообщения"] = "\n".join(related_entries)

    # Return the parsed data as a dictionary
    return {k: parsed_data.get(k, "") for k in OUTPUT_COLUMNS}

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