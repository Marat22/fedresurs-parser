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
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException, TimeoutException, \
    WebDriverException
import time
from typing import Dict, Any, Optional
from datetime import datetime
import shutil

# Global variable for backup directory
BACKUP_DIR = None


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
    options.add_argument(
        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

    # Initialize driver
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)

    return driver


def parse_contents(driver: webdriver.Chrome, url: str) -> Dict[str, Any]:
    """
    Main function to parse content from the given URL.

    Args:
        driver: Chrome WebDriver instance
        url: URL to parse

    Returns:
        Dictionary with parsed content or error information
    """
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        load_all_messages(driver)

        parsed_data = {"url": url}
        parsed_data.update(parse_page_sections(driver))

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


def load_all_messages(driver: webdriver.Chrome, timeout: int = 30) -> None:
    """
    Clicks 'Загрузить ещё' button repeatedly until it no longer appears.

    Args:
        driver: Chrome WebDriver instance
        timeout: Max number of retries before giving up
    """
    click_count = 0
    while click_count < timeout:
        try:
            # Wait for the button to become clickable
            load_more_button = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "more_btn_orange"))
            )
            # Scroll the button into view (helps prevent click issues)
            driver.execute_script("arguments[0].scrollIntoView(true);", load_more_button)
            time.sleep(0.5)  # Small pause after scrolling
            # Click the button
            load_more_button.click()
            print("Clicked 'Загрузить еще'")
            click_count += 1
            time.sleep(2)  # Allow content to load after clicking
        except (NoSuchElementException, TimeoutException):
            print("No more 'Загрузить еще' button found")
            break
        except StaleElementReferenceException:
            print("Stale element reference encountered, retrying...")
            continue
        except Exception as e:
            print(f"Unexpected error while loading more messages: {e}")
            break


def parse_page_sections(driver: webdriver.Chrome) -> Dict[str, Any]:
    """Parse all main sections of the page."""
    parsed_data = {}

    # Parse each section with separate functions
    parsed_data["ЗАГОЛОВОК"] = parse_header(driver)

    publisher_data = parse_publisher_section(driver)
    if publisher_data:
        parsed_data["Публикатор"] = publisher_data

    message_data = parse_message_section(driver)
    if message_data:
        parsed_data["Сообщение"] = message_data

    related_messages = parse_related_messages(driver)
    if related_messages:
        parsed_data["Связанные сообщения"] = related_messages

    return parsed_data


def parse_header(driver: webdriver.Chrome) -> Dict[str, str]:
    """Parse header information from the page.

    Returns:
        Dictionary with main header and subheader text
    """
    header_data = {
        "Основной заголовок": "",
        "Подзаголовок": ""
    }

    try:
        main_header = driver.find_element(By.CLASS_NAME, "headertext")
        header_data["Основной заголовок"] = main_header.text.strip()
    except NoSuchElementException:
        pass

    try:
        subheader = driver.find_element(By.CSS_SELECTOR, ".d-flex.align-items-center.header-item")
        header_data["Подзаголовок"] = subheader.text.strip()
    except NoSuchElementException:
        pass

    return header_data


def parse_publisher_section(driver) -> Optional[Dict[str, Any]]:
    """
    Parse the Публикатор section from the page.

    Args:
        driver: Chrome WebDriver instance

    Returns:
        Dictionary with publisher data: {"name": str, "ИНН": int, "ОГРН": int}
        Returns None if section not found or parsing fails
    """
    try:
        # Find the Публикатор section
        publisher_section = driver.find_element(
            By.CSS_SELECTOR,
            'information-page-item[header="Публикатор"]'
        )

        # Extract publisher data from the main element
        publisher_main = publisher_section.find_element(By.CLASS_NAME, "main")

        # Extract company name
        name = _extract_company_name(publisher_main)

        # Extract INN and OGRN
        inn = _extract_id_value(publisher_main, "inn")
        ogrn = _extract_id_value(publisher_main, "ogrn")

        # Validate that we have all required data
        if not all([name, inn, ogrn]):
            print("Warning: Missing required publisher data")
            return None

        return {
            "name": name,
            "ИНН": _safe_int_convert(inn),
            "ОГРН": _safe_int_convert(ogrn)
        }

    except NoSuchElementException as e:
        print(f"Publisher section not found: {str(e)}")
        return None
    except Exception as e:
        print(f"Error parsing publisher section: {str(e)}")
        return None


def _extract_company_name(publisher_main) -> Optional[str]:
    """Extract company name from publisher main element."""
    try:
        name_element = publisher_main.find_element(By.CSS_SELECTOR, ".name span")
        return name_element.text.strip()
    except NoSuchElementException:
        print("Company name not found")
        return None


def _extract_id_value(publisher_main, id_type: str) -> Optional[str]:
    """
    Extract ID value (INN or OGRN) from publisher main element.

    Args:
        publisher_main: WebElement of the main publisher section
        id_type: "inn" or "ogrn"
    """
    try:
        id_element = publisher_main.find_element(
            By.CSS_SELECTOR,
            f'.id-item.{id_type} span'
        )
        return id_element.text.strip()
    except NoSuchElementException:
        print(f"{id_type.upper()} not found")
        return None


def _safe_int_convert(value: Optional[str]) -> Optional[int]:
    """Safely convert string to integer."""
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        print(f"Could not convert '{value}' to integer")
        return None


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
        message_sections = driver.find_elements(By.XPATH,
                                                "//div[contains(@class, 'paragraph-header') and text()='Сообщение']/following-sibling::*")

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
                    table_key = table_key[:36]
                    message_data[table_key] = table_data

            # Parse nested message components
            message_components = section.find_elements(By.XPATH,
                                                       ".//*[contains(@class, 'sfact-message') or contains(@_nghost, 'sfact-message')]")
            for component in message_components:
                component_data = parse_message_component(component)
                message_data.update(component_data)

    except Exception as e:
        print(f"Error parsing message section: {str(e)}")

    return message_data


def parse_related_messages(driver):
    """
    Parse the 'Связанные сообщения' section from the page.

    Args:
        driver: Chrome WebDriver instance

    Returns:
        Dictionary of related messages or empty dict if not found
    """
    related_messages = {}

    try:
        # Find the block with header "Связанные сообщения"
        header = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[@class='paragraph-header' and contains(., 'Связанные сообщения')]"))
        )

        # Get the parent container (the div with class "paragraph")
        related_block = header.find_element(By.XPATH, "./ancestor::div[@class='paragraph']")

        # Find all .info-item elements inside the block
        info_items = related_block.find_elements(By.CLASS_NAME, "info-item")

        for item in info_items:
            # Extract the number and date (e.g., "08980093 от 15.07.2021")
            try:
                number_date_element = item.find_element(By.CLASS_NAME, "flex-shrink-0")
                number_date = number_date_element.text.strip()
            except:
                number_date = ""

            # Extract the message title
            try:
                title_element = item.find_element(By.TAG_NAME, "a")
                title = title_element.text.strip()
            except:
                try:
                    title = item.find_element(By.CLASS_NAME, "current-message").text.strip()
                except:
                    title = ""

            if number_date and title:
                related_messages[number_date] = title

    except:
        # If block is not found, return empty dict
        pass

    return related_messages


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

                # Second cell contains structured data with inner items
                if len(cells) > 1:
                    # Look for inner items in second cell (Идентификатор, Классификатор)
                    inner_items = cells[1].find_elements(By.XPATH, ".//div[contains(@class, 'td-inner-item')]")

                    for inner_item in inner_items:
                        # Get all direct child divs of the inner item
                        child_divs = inner_item.find_elements(By.XPATH, "./div")

                        if len(child_divs) >= 2:
                            # First div is the label (with fw-light class)
                            label = child_divs[0].text.strip()
                            # Second div is the value
                            value = extract_text_content(child_divs[1])

                            if label and value:
                                row_data[label] = value

                # Third cell is typically description (Описание)
                if len(cells) > 2:
                    description = cells[2].text.strip()
                    if description:
                        row_data["Описание"] = description

                # Only add row if we have any data
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


def create_backup(output_file: str) -> None:
    """
    Create a backup of the current output file.

    Args:
        output_file: Path to the output file to backup
    """
    if not os.path.exists(output_file):
        return

    try:
        # Create backup directory if it doesn't exist
        os.makedirs(BACKUP_DIR, exist_ok=True)

        # Create backup filename with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
        backup_filename = os.path.join(BACKUP_DIR, os.path.basename(output_file))

        # Copy the file
        shutil.copy2(output_file, backup_filename)
        print(f"Created backup: {backup_filename}")
    except Exception as e:
        print(f"Error creating backup: {str(e)}")


def process_links(input_file: str, output_dir: str, force_recreate: bool, show_browser: bool) -> None:
    """
    Main function to process all links from input file.

    Args:
        input_file: Path to input JSON file
        output_dir: Directory to save output files
        force_recreate: Whether to recreate output files
        show_browser: Whether to show browser during processing
    """
    # Initialize backup directory
    global BACKUP_DIR
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S.%f")
    BACKUP_DIR = os.path.join("BACKUPS", "3_STEP_backups", timestamp)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    print(f"Backups will be stored in: {BACKUP_DIR}")

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

                # Save and backup periodically (every 10 links)
                if processed_count == 1 or processed_count % 10 == 0:
                    save_results(output_file, year_results)
                    create_backup(output_file)
                    print(f"    Saved intermediate results and backup ({processed_count} new)")

                # Small delay to be respectful to the server
                time.sleep(1)

            # Final save for this year
            save_results(output_file, year_results)
            create_backup(output_file)
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
    main()