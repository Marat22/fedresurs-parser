import datetime
from urllib.parse import quote
import json

def generate_fedresurs_links():
    base_url = "https://fedresurs.ru/encumbrances?group=Leasing&period="
    links = []
    
    start_date = datetime.date(2016, 1, 1)
    end_date = datetime.date(2025, 6, 30)
    
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
        
        # Create the full URL
        url = f"{base_url}{encoded_period}&limit=15&offset=0"
        links.append((first_day.strftime("%Y-%m"), url))
        
        # Move to next month
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)
    
    return links

def save_links_to_json():
    """
    Generates monthly Fedresurs.ru links and saves them to a JSON file.
    The file will contain a list of dictionaries with month and URL pairs.
    """
    # Generate the links
    monthly_links = generate_fedresurs_links()
    
    # Convert to a list of dictionaries for better JSON structure
    links_data = [{"month": month, "url": url} for month, url in monthly_links]
    
    # Save to JSON file
    with open('1month_links.json', 'w', encoding='utf-8') as f:
        json.dump(links_data, f, ensure_ascii=False, indent=2)
    
    print(f"Successfully saved {len(links_data)} monthly links to 1month_links.json")

# Execute the functions
if __name__ == "__main__":
    save_links_to_json()