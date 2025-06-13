#!/usr/bin/env python3
"""
Script to process links from 2month_links.json file.
Extracts content from each link and saves results by year.
"""

import json
import os
import argparse
from pathlib import Path
from typing import Dict, Any, List
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import time
from urllib.parse import urlparse


def setup_driver(headless: bool = True) -> webdriver.Chrome:
    """
    Setup Chrome WebDriver with appropriate options.
    
    Args:
        headless: Whether to run browser in headless mode
        
    Returns:
        Chrome WebDriver instance
    """
    options = Options()
    if headless:
        options.add_argument('--headless')
    
    # Additional Chrome options for stability
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    
    # Initialize driver
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)
    
    return driver


def parse_contents(driver: webdriver.Chrome, url: str) -> Dict[str, Any]:
    """
    Parse content from the given URL, extracting Публикатор and Сообщение sections.
    
    Args:
        driver: Chrome WebDriver instance
        url: URL to parse
        
    Returns:
        Dictionary with parsed content including 'Публикатор', 'Сообщение', and 'url'
    """
    try:
        driver.get(url)
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        parsed_data = {"url": url}
        
        # Parse Публикатор section
        publisher_data = parse_publisher_section(driver)
        if publisher_data:
            parsed_data["Публикатор"] = publisher_data
        
        # Parse Сообщение section
        message_data = parse_message_section(driver)
        if message_data:
            parsed_data["Сообщение"] = message_data
        
        return parsed_data
        
    except TimeoutException:
        print(f"Timeout loading page: {url}")
        return {"error": "timeout", "url": url}
    except WebDriverException as e:
        print(f"WebDriver error for {url}: {str(e)}")
        return {"error": f"webdriver_error: {str(e)}", "url": url}
    except Exception as e:
        print(f"Unexpected error for {url}: {str(e)}")
        return {"error": f"unexpected_error: {str(e)}", "url": url}


def parse_publisher_section(driver: webdriver.Chrome) -> Dict[str, Any]:
    """
    Parse the Публикатор (Publisher) section.
    
    Args:
        driver: Chrome WebDriver instance
        
    Returns:
        Dictionary with publisher information
    """
    publisher_data = {}
    
    try:
        # Find publisher section by header
        publisher_sections = driver.find_elements(By.XPATH, "//div[contains(@class, 'paragraph-header') and text()='Публикатор']/following-sibling::*")
        
        if not publisher_sections:
            return {}
        
        # Look for company publisher within publisher section
        for section in publisher_sections:
            # Extract company name
            name_elements = section.find_elements(By.XPATH, ".//div[contains(@class, 'name')]//span")
            if name_elements:
                publisher_data["название"] = name_elements[0].text.strip()
            
            # Extract IDs (ИНН, ОГРН, etc.)
            id_items = section.find_elements(By.XPATH, ".//div[contains(@class, 'id-item')]")
            for item in id_items:
                # Get the label (ИНН, ОГРН, etc.)
                label_elem = item.find_elements(By.XPATH, ".//div[contains(@class, 'id-item-name')]")
                value_elem = item.find_elements(By.XPATH, ".//span")
                
                if label_elem and value_elem:
                    label = label_elem[0].text.strip()
                    value = value_elem[0].text.strip()
                    if label and value:
                        # Convert numeric values to integers if possible
                        try:
                            publisher_data[label] = int(value)
                        except ValueError:
                            publisher_data[label] = value
            
            # If we found data, break (assuming first section has the main publisher info)
            if publisher_data:
                break
                
    except Exception as e:
        print(f"Error parsing publisher section: {str(e)}")
    
    return publisher_data

def parse_message_section(driver: webdriver.Chrome) -> Dict[str, Any]:
    """
    Parse the Сообщение (Message) section.
    
    Args:
        driver: Chrome WebDriver instance
        
    Returns:
        Dictionary with message information
    """
    message_data = {}
    
    try:
        # Find message section by header
        message_sections = driver.find_elements(By.XPATH, "//div[contains(@class, 'paragraph-header') and text()='Сообщение']/following-sibling::*")
        
        if not message_sections:
            return {}
        
        for section in message_sections:
            # Parse info items (key-value pairs)
            info_items = section.find_elements(By.XPATH, ".//div[contains(@class, 'info-item')]")
            for item in info_items:
                key_elem = item.find_elements(By.XPATH, ".//div[contains(@class, 'info-item-name')]")
                value_elem = item.find_elements(By.XPATH, ".//div[contains(@class, 'info-item-value')]")
                
                if key_elem and value_elem:
                    key = key_elem[0].text.strip()
                    value = extract_text_content(value_elem[0])
                    if key and value:
                        message_data[key] = value
            
            # Parse tables (subject contracts, etc.)
            tables = section.find_elements(By.XPATH, ".//table[contains(@class, 'message-table')]")
            for table in tables:
                table_data = parse_message_table(table)
                if table_data:
                    # Get table header to determine the key
                    header_elem = section.find_elements(By.XPATH, ".//div[contains(@class, 'message-text-header')]")
                    table_key = header_elem[0].text.strip() if header_elem else "Таблица"
                    message_data[table_key] = table_data
            
            # Parse nested message components
            message_components = section.find_elements(By.XPATH, ".//*[contains(@class, 'sfact-message') or contains(@_nghost, 'sfact-message')]")
            for component in message_components:
                component_data = parse_message_component(component)
                message_data.update(component_data)
        
    except Exception as e:
        print(f"Error parsing message section: {str(e)}")
    
    return message_data

def parse_message_table(table_element) -> Dict[str, Any]:
    """
    Parse a table within the message section.
    
    Args:
        table_element: WebElement of the table
        
    Returns:
        Dictionary with table data
    """
    table_data = {}
    
    try:
        rows = table_element.find_elements(By.TAG_NAME, "tr")
        
        for row in rows[1:]:  # Skip header row
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) >= 2:
                # First cell is typically the number/index
                row_num = cells[0].text.strip()
                
                # Parse the row data
                row_data = {}
                
                # Second cell often contains structured data
                if len(cells) > 1:
                    # Look for inner items in second cell
                    inner_items = cells[1].find_elements(By.XPATH, ".//div[contains(@class, 'td-inner-item')]")
                    subject_data = {}
                    
                    for inner_item in inner_items:
                        label_elem = inner_item.find_elements(By.XPATH, ".//div[contains(@class, 'fw-light')]")
                        value_elem = inner_item.find_elements(By.XPATH, ".//div[not(contains(@class, 'fw-light'))]")
                        
                        if label_elem and len(value_elem) > 1:  # Skip the label div
                            label = label_elem[0].text.strip()
                            value = extract_text_content(value_elem[1])
                            if label and value:
                                subject_data[label] = value
                    
                    if subject_data:
                        row_data["Предмет финансовой аренды (лизинга)"] = subject_data
                
                # Third cell is typically description
                if len(cells) > 2:
                    description = cells[2].text.strip()
                    if description:
                        row_data["Описание"] = description
                
                if row_data and row_num:
                    table_data[row_num] = row_data
                    
    except Exception as e:
        print(f"Error parsing table: {str(e)}")
    
    return table_data


def parse_message_component(component_element) -> Dict[str, Any]:
    """
    Parse individual message components (financial lease contracts, etc.).
    
    Args:
        component_element: WebElement of the component
        
    Returns:
        Dictionary with component data
    """
    component_data = {}
    
    try:
        # Parse all info items within this component
        info_items = component_element.find_elements(By.XPATH, ".//div[contains(@class, 'info-item')]")
        for item in info_items:
            key_elem = item.find_elements(By.XPATH, ".//div[contains(@class, 'info-item-name')]")
            value_elem = item.find_elements(By.XPATH, ".//div[contains(@class, 'info-item-value')]")
            
            if key_elem and value_elem:
                key = key_elem[0].text.strip()
                value = extract_text_content(value_elem[0])
                if key and value:
                    component_data[key] = value
                    
    except Exception as e:
        print(f"Error parsing message component: {str(e)}")
    
    return component_data
def extract_text_content(element) -> str:
    """
    Extract clean text content from an element, handling spans and nested elements.
    
    Args:
        element: WebElement to extract text from
        
    Returns:
        Clean text string
    """
    try:
        # First try to get all text
        text = element.text.strip()
        if text:
            return text
        
        # If no text, try to get from spans
        spans = element.find_elements(By.TAG_NAME, "span")
        if spans:
            return " ".join([span.text.strip() for span in spans if span.text.strip()])
        
        # Fallback to inner text
        return element.get_attribute("innerText").strip()
        
    except Exception:
        return ""


def clean_and_convert_value(value: str) -> Any:
    """
    Clean and convert string values to appropriate types.
    
    Args:
        value: String value to clean and convert
        
    Returns:
        Converted value (int, float, or cleaned string)
    """
    if not value:
        return ""
    
    value = value.strip()
    
    # Try to convert to integer
    try:
        return int(value.replace(" ", ""))
    except ValueError:
        pass
    
    # Try to convert to float
    try:
        return float(value.replace(" ", "").replace(",", "."))
    except ValueError:
        pass
    
    # Return as clean string
    return value
def extract_year_from_month(month_str: str) -> str:
    """
    Extract year from month string (e.g., '2016-10' -> '2016').
    
    Args:
        month_str: Month string in format 'YYYY-MM'
        
    Returns:
        Year as string
    """
    return month_str.split('-')[0]


def load_input_data(input_file: str) -> List[Dict[str, Any]]:
    """
    Load data from input JSON file.
    
    Args:
        input_file: Path to input JSON file
        
    Returns:
        List of month data dictionaries
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_existing_results(output_file: str) -> Dict[str, Any]:
    """
    Load existing results from output file if it exists.
    
    Args:
        output_file: Path to output file
        
    Returns:
        Dictionary with existing results or empty dict if file doesn't exist
    """
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            print(f"Warning: Could not read existing file {output_file}, starting fresh")
            return {}
    return {}


def save_results(output_file: str, results: Dict[str, Any]) -> None:
    """
    Save results to output file.
    
    Args:
        output_file: Path to output file
        results: Dictionary with results to save
    """
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def process_links(input_file: str, output_dir: str, force_recreate: bool, show_browser: bool) -> None:
    """
    Main function to process all links from input file.
    
    Args:
        input_file: Path to input JSON file
        output_dir: Directory to save output files
        force_recreate: Whether to recreate output files
        show_browser: Whether to show browser during processing
    """
    # Load input data
    print(f"Loading data from {input_file}")
    data = load_input_data(input_file)
    
    # Group links by year
    links_by_year = {}
    months_without_links = []
    
    for month_data in data:
        year = extract_year_from_month(month_data['month'])
        
        # Check if month has links_inside field
        if 'links_inside' not in month_data or not month_data['links_inside']:
            months_without_links.append(month_data['month'])
            continue
            
        if year not in links_by_year:
            links_by_year[year] = []
        links_by_year[year].extend(month_data['links_inside'])
    
    # Print warning for months without links
    if months_without_links:
        print(f"Warning: {len(months_without_links)} months have no 'links_inside' field and will be ignored:")
        for month in months_without_links:
            print(f"  - {month}")
    
    print(f"Found links for years: {sorted(links_by_year.keys())}")
    
    # Process each year
    driver = None
    try:
        driver = setup_driver(headless=not show_browser)
        print(f"Browser setup complete (headless: {not show_browser})")
        
        for year in sorted(links_by_year.keys()):
            output_file = os.path.join(output_dir, f"raw_contents{year}.json")
            
            # Load existing results unless force recreate
            if force_recreate:
                year_results = {}
                print(f"Force recreating file for year {year}")
            else:
                year_results = load_existing_results(output_file)
                if year_results:
                    print(f"Loaded {len(year_results)} existing results for year {year}")
            
            links = links_by_year[year]
            print(f"Processing {len(links)} links for year {year}")
            
            processed_count = 0
            for i, link in enumerate(links, 1):
                # Skip if already processed
                if link in year_results:
                    print(f"  [{i}/{len(links)}] Skipping already processed: {link}")
                    continue
                
                print(f"  [{i}/{len(links)}] Processing: {link}")
                
                # Parse content
                content = parse_contents(driver, link)
                year_results[link] = content
                
                processed_count += 1
                
                # Save periodically (every 10 links)
                if processed_count % 1 == 0:
                    save_results(output_file, year_results)
                    print(f"    Saved intermediate results ({processed_count} new)")
                
                # Small delay to be respectful to the server
                time.sleep(1)
            
            # Final save for this year
            save_results(output_file, year_results)
            print(f"Completed year {year}: {processed_count} new links processed, {len(year_results)} total")
            
    finally:
        if driver:
            driver.quit()
            print("Browser closed")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Process links from 2month_links.json')
    parser.add_argument('--force-recreate', action='store_true',
                        help='Recreate output file even if it exists')
    parser.add_argument('--show', action='store_true',
                        help='Show browser during processing (disable headless mode)')
    
    args = parser.parse_args()
    
    # Configuration
    input_file = "2month_links.json"
    output_dir = "3raw_contents"
    
    # Validate input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found")
        return 1
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        process_links(input_file, output_dir, args.force_recreate, args.show)
        print("Processing completed successfully!")
        return 0
        
    except KeyboardInterrupt:
        print("\nProcessing interrupted by user")
        return 1
    except Exception as e:
        print(f"Error during processing: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main())