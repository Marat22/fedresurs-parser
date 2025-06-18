import glob
import json
import os
from typing import Dict, List, Any, Set

import pandas as pd


def read_json_files(folder_path: str) -> List[Dict]:
    """
    Read all JSON files from the specified directory in order.

    Args:
        folder_path: Path to directory containing JSON files

    Returns:
        List of dictionaries containing all JSON data
    """
    all_data = []

    if not os.path.exists(folder_path):
        print(f"Error: Directory {folder_path} does not exist")
        return all_data

    # Get all JSON files and sort them
    json_files = sorted(glob.glob(os.path.join(folder_path, "*.json")))

    if not json_files:
        print(f"No JSON files found in {folder_path}")
        return all_data

    print(f"Found {len(json_files)} JSON files in {folder_path}")

    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_data.append(data)
                print(f"Successfully read: {os.path.basename(file_path)}")
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    return all_data


def extract_special_fields(record: Dict) -> Dict[str, str]:
    """
    Extract and format special fields: 'Связанные сообщения' and 'Предметы финансовой аренды (лизинга)'.

    Args:
        record: Single record from JSON data

    Returns:
        Dictionary with formatted special fields
    """
    special_fields = {}

    # Handle "Связанные сообщения"
    if 'Сообщение' in record and 'Связанные сообщения' in record['Сообщение']:
        related_messages = record['Сообщение']['Связанные сообщения']
        formatted_messages = []

        for key, value in related_messages.items():
            formatted_messages.append(f'{key}: "{value}"')

        special_fields['Связанные сообщения'] = '\n'.join(formatted_messages)

    # Handle "Предметы финансовой аренды (лизинга)"
    if 'Сообщение' in record and 'Предметы финансовой аренды (лизинга)' in record['Сообщение']:
        items = record['Сообщение']['Предметы финансовой аренды (лизинга)']

        identifiers = []
        classifiers = []
        descriptions = []

        for key, item in items.items():
            identifiers.append(f"{key}. {item.get('Идентификатор', 'нет данных')}")
            classifiers.append(f"{key}. {item.get('Классификатор', 'нет данных')}")
            descriptions.append(f"{key}. {item.get('Описание', 'нет данных')}")

        special_fields['Идентификатор'] = ' \n'.join(identifiers)
        special_fields['Классификатор'] = ' \n'.join(classifiers)
        special_fields['Описание'] = ' \n'.join(descriptions)

    return special_fields


def flatten_record(record: Dict, parent_key: str = '', separator: str = ' ') -> Dict[str, Any]:
    """
    Flatten nested dictionary structure.

    Args:
        record: Dictionary to flatten
        parent_key: Parent key for nested structure
        separator: Separator for nested keys

    Returns:
        Flattened dictionary
    """
    items = []

    for key, value in record.items():
        new_key = f"{key} ({parent_key})" if parent_key else key

        if isinstance(value, dict):
            # Skip special nested objects that are handled separately
            if key in ['Связанные сообщения', 'Предметы финансовой аренды (лизинга)', 'ЗАГОЛОВОК']:
                continue
            items.extend(flatten_record(value, new_key, separator).items())
        else:
            items.append((new_key, value))

    return dict(items)


def get_all_columns(all_records: List[Dict]) -> Set[str]:
    """
    Get all unique column names from all records.

    Args:
        all_records: List of all flattened records

    Returns:
        Set of all unique column names
    """
    all_columns = set()

    for record in all_records:
        all_columns.update(record.keys())

    return all_columns


def process_single_record(url: str, record_data: Dict) -> Dict[str, Any]:
    """
    Process a single record and extract all data.

    Args:
        url: URL key for the record
        record_data: The record data

    Returns:
        Processed record as dictionary
    """
    # Start with the URL
    processed_record = {'url': url}

    # Extract special fields first
    special_fields = extract_special_fields(record_data)
    processed_record.update(special_fields)

    # Extract header fields
    if 'ЗАГОЛОВОК' in record_data:
        header_data = record_data['ЗАГОЛОВОК']
        processed_record['Основной заголовок'] = header_data.get('Основной заголовок', '')
        processed_record['Подзаголовок'] = header_data.get('Подзаголовок', '')
    else:
        processed_record['Основной заголовок'] = ''
        processed_record['Подзаголовок'] = ''

    # Flatten the regular fields
    flattened = flatten_record(record_data)
    processed_record.update(flattened)

    return processed_record


def convert_to_excel(json_data_list: List[Dict], output_file: str) -> None:
    """
    Convert JSON data to Excel format with clickable hyperlinks in the 'url' column.
    """
    all_processed_records = []

    # Process each JSON file
    for json_data in json_data_list:
        for url, record_data in json_data.items():
            processed_record = process_single_record(url, record_data)
            all_processed_records.append(processed_record)

    if not all_processed_records:
        print("No records to process")
        return

    # Create DataFrame with all columns
    df = pd.DataFrame(all_processed_records)

    # Reorder columns to put special fields first
    special_columns = ['url', 'Основной заголовок', 'Подзаголовок', 'Идентификатор', 'Классификатор', 'Описание', 'Связанные сообщения']
    remaining_columns = [col for col in df.columns if col not in special_columns]

    # Order columns: special fields first, then others
    ordered_columns = [col for col in special_columns if col in df.columns] + sorted(remaining_columns)
    df = df.reindex(columns=ordered_columns)

    # Optional: Save original URLs for reference
    df['original_url'] = df['url']

    # Format 'url' column as Excel HYPERLINK formula
    df['url'] = df['url'].apply(
        lambda x: f'=HYPERLINK("{x}", "{x}")' if pd.notna(x) and x.startswith('http') else x
    )

    # Save to Excel
    try:
        df.to_excel(output_file, index=False, engine='openpyxl')
        print(f"Excel file saved: {output_file}")
        print(f"Total records processed: {len(all_processed_records)}")
        print(f"Total columns: {len(df.columns)}")
    except Exception as e:
        print(f"Error saving Excel file: {e}")

def main():
    """
    Main function to process JSON files and create Excel output.
    """
    # Define the directory path
    directory_path = "3raw_contents"

    # Output file name changed to "output.xlsx"
    output_file = "output.xlsx"

    try:
        # Read all JSON files from the directory
        print(f"Reading JSON files from directory: {directory_path}")
        json_data_list = read_json_files(directory_path)

        if not json_data_list:
            print("No JSON data found. Please check your directory path and ensure it contains JSON files.")
            return

        # Convert to Excel
        print("Converting to Excel...")
        convert_to_excel(json_data_list, output_file)

        print("Process completed successfully!")

    except Exception as e:
        print(f"Error during processing: {e}")


if __name__ == "__main__":
    main()
