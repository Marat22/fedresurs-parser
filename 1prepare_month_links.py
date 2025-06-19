import datetime
import os
from urllib.parse import quote
import json
import sys
import argparse


OUTPUT_PATH = full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '1month_links.json')


def parse_date(date_str):
    """Parse YYYY-MM date string into datetime.date object"""
    try:
        year, month = map(int, date_str.split('-'))
        return datetime.date(year, month, 1)
    except (ValueError, IndexError):
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM")


def generate_fedresurs_links(search_string, start_date, end_date):
    base_url = "https://fedresurs.ru/encumbrances?searchString="
    encoded_search = quote(search_string)
    links = []

    current_date = start_date

    while current_date <= end_date:
        # Calculate the first day of the month
        first_day = current_date.replace(day=1)
        # Calculate the last day of the month
        if current_date.month == 12:
            last_day = current_date.replace(year=current_date.year + 1, month=1, day=1) - datetime.timedelta(days=1)
        else:
            last_day = current_date.replace(month=current_date.month + 1, day=1) - datetime.timedelta(days=1)

        # Format dates for URL (UTC time)
        begin_date = f"{first_day.year}-{first_day.month:02d}-{first_day.day:02d}T00:00:00.000Z"
        end_date_url = f"{last_day.year}-{last_day.month:02d}-{last_day.day:02d}T23:59:59.999Z"

        # Create the period parameter
        period_json = f'{{"beginJsDate":"{begin_date}","endJsDate":"{end_date_url}"}}'
        encoded_period = quote(period_json)

        # Create the full URL with search string
        url = f"{base_url}{encoded_search}&group=Leasing&period={encoded_period}&limit=15&offset=0"
        links.append((first_day.strftime("%Y-%m"), url))

        # Move to next month
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)

    return links


def save_links_to_json(search_string, start_date, end_date):
    """
    Generates monthly Fedresurs.ru links with search string and saves them to a JSON file.
    The file will contain a list of dictionaries with month and URL pairs.
    """
    # Generate the links
    monthly_links = generate_fedresurs_links(search_string, start_date, end_date)

    # Convert to a list of dictionaries for better JSON structure
    links_data = [{"month": month, "url": url} for month, url in monthly_links]

    # Save to JSON file
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(links_data, f, ensure_ascii=False, indent=2)

    print(f"Successfully saved {len(links_data)} monthly links to {OUTPUT_PATH}")
    print(f"Date range: {start_date.strftime('%Y-%m')} to {end_date.strftime('%Y-%m')}")
    print(f"Search string: '{search_string}'")


def get_current_month():
    """Return first day of current month as datetime.date"""
    today = datetime.date.today()
    return datetime.date(today.year, today.month, 1)


# Execute the functions
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate Fedresurs.ru search URLs for each month')
    parser.add_argument('search_string', help='Search string to use in queries')
    parser.add_argument('--start', default='2023-04',
                        help='Start date in YYYY-MM format (default: 2023-04)')
    parser.add_argument('--end',
                        default=get_current_month().strftime('%Y-%m'),
                        help='End date in YYYY-MM format (default: current month)')

    args = parser.parse_args()

    try:
        start_date = parse_date(args.start)
        end_date = parse_date(args.end)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    if start_date > end_date:
        print("Error: Start date cannot be after end date")
        sys.exit(1)

    save_links_to_json(args.search_string, start_date, end_date)
