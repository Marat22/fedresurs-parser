import argparse
import json
import os
import shutil
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# Create backup directory paths
BACKUPS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "BACKUPS")
STEP_BACKUPS_DIR = os.path.join(BACKUPS_DIR, "2_STEP_backups")
INPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "1month_links.json")
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "2month_links.json")

# Generate single backup filename at program start
backup_filename = f"{datetime.now().strftime('%Y-%m-%dT%H-%M-%S.%f')}_2month_links.json"
backup_path = os.path.join(STEP_BACKUPS_DIR, backup_filename)


def create_backup_dirs():
    """Create backup directories if they don't exist"""
    os.makedirs(STEP_BACKUPS_DIR, exist_ok=True)


def write_backup(data, total_links=0):
    """Write current data to the timestamped backup file"""
    try:
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\nBackup updated at {total_links} links: {backup_filename}")
    except Exception as e:
        print(f"Backup failed: {str(e)}")


class PageLoader:
    def __init__(self, headless=True):  # Changed default to headless=True
        self.options = Options()
        if headless:
            self.options.add_argument("--headless=new")
        self.options.add_argument("--start-maximized")
        self.driver = None
        self.main_window_handle = None

    def start_driver(self):
        if not self.driver:
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=self.options
            )

    def load_all_pages(self, url):
        """Loads all paginated content by repeatedly clicking 'Load More' button"""
        self.start_driver()
        self.driver.get(url)
        print(f"\nProcessing URL: {url}")
        self.main_window_handle = self.driver.current_window_handle

        time.sleep(2)  # Initial page load wait

        click_count = 0
        while True:
            try:
                button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div.more_btn_wrapper div.more_btn"))
                )
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                self.driver.execute_script("arguments[0].click();", button)
                click_count += 1
                print(f"Clicked 'Load More' ({click_count} times)")
                time.sleep(2)  # Content loading wait
            except Exception as e:
                print(f"Stopping: {str(e).split('.')[0]}")
                break

        print(f"Total clicks: {click_count}")
        return self.driver

    def get_all_links(self, keyword='прекращение'):
        """Extract links by clicking each block and capturing the URL"""
        print("Extracting links by clicking blocks...")

        # Find all clickable anchors using the proper selector
        anchors = self.driver.find_elements(
            By.CSS_SELECTOR, "div.info-link-container > el-info-link > a.info"
        )
        print(f"Found {len(anchors)} links to process")

        # Filter anchors by keyword if provided
        filtered_anchors = []
        skipped_by_keyword = 0

        if keyword:  # Only filter if keyword is not empty
            print(f"Filtering anchors by keyword: '{keyword}' (case-insensitive)")
            keyword_lower = keyword.lower()

            for anchor in anchors:
                try:
                    # Find the parent block for the anchor
                    block = anchor.find_element(
                        By.XPATH,
                        "./ancestor::div[contains(@class, 'u-card-result__wrapper')]"
                    )
                    block_text = block.text.lower()

                    # Check if keyword exists in block text
                    if keyword_lower in block_text:
                        filtered_anchors.append(anchor)
                    else:
                        skipped_by_keyword += 1
                except Exception as e:
                    print(f"Error finding parent block: {str(e)}. Skipping anchor...")
                    skipped_by_keyword += 1
        else:
            filtered_anchors = anchors  # No filtering when keyword is empty

        print(f"Filtered: {len(filtered_anchors)} anchors remain, skipped {skipped_by_keyword}")
        anchors = filtered_anchors  # Use filtered list for processing
        print(f"Processing {len(anchors)} links...")

        links = []
        processed_count = 0
        duplicate_count = 0

        for anchor in anchors:
            try:
                # Save the current window handle
                original_window = self.driver.current_window_handle

                # Scroll to the element before interacting
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", anchor)

                # Open the detail page in a new tab
                ActionChains(self.driver) \
                    .key_down(Keys.CONTROL) \
                    .click(anchor) \
                    .key_up(Keys.CONTROL) \
                    .perform()

                # Wait for the new tab to open
                WebDriverWait(self.driver, 10).until(
                    lambda d: len(d.window_handles) > len([original_window])
                )

                # Switch to the new tab
                new_window = [handle for handle in self.driver.window_handles
                              if handle != original_window][0]
                self.driver.switch_to.window(new_window)

                # Wait for the page to load
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
                time.sleep(0.5)  # Additional stabilization

                # Capture the URL
                detail_url = self.driver.current_url
                if detail_url not in links:  # Prevent duplicates
                    links.append(detail_url)
                    processed_count += 1
                    print(f"Processed {processed_count}/{len(anchors)}: {detail_url}")
                else:
                    duplicate_count += 1
                    print(f"Skipped duplicate: {detail_url}")

                # Close the detail tab
                self.driver.close()

                # Switch back to the original window
                self.driver.switch_to.window(original_window)

            except Exception as e:
                print(f"Error processing link: {str(e)}")
                # Ensure we return to the main window
                if self.main_window_handle in self.driver.window_handles:
                    self.driver.switch_to.window(self.main_window_handle)

        print(f"Successfully processed {len(links)} links")
        print(f"Summary: {duplicate_count} duplicates skipped, {skipped_by_keyword} skipped by keyword")
        return links

    def close(self):
        if self.driver:
            self.driver.quit()
            self.driver = None


def initialize_output_file(input_file, output_file, force_recreate=False):
    """Create output file if it doesn't exist or force recreate is requested"""
    if force_recreate and os.path.exists(output_file):
        print(f"Forcing recreation of {output_file}")
        os.remove(output_file)

    if not os.path.exists(output_file):
        print(f"Creating {output_file} from {input_file}")
        shutil.copyfile(input_file, output_file)
        return True

    print(f"Using existing file: {output_file}")
    return False


def process_links_file(input_file, output_file, force_recreate=False, headless=True, keyword='прекращение'):
    """Process all URLs in JSON file and update with extracted links"""
    create_backup_dirs()  # Ensure backup directories exist

    initialize_output_file(input_file, output_file, force_recreate)

    # Read data from output file
    with open(output_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Write initial backup
    write_backup(data, 0)

    loader = PageLoader(headless=headless)
    total_links = 0
    backup_interval = 1  # Backup every `backup_interval` links
    next_backup_threshold = backup_interval

    try:
        for i, entry in enumerate(data):
            if "links_inside" in entry and not force_recreate:
                # Count existing links if we're not reprocessing
                total_links += len(entry["links_inside"])
                print(f"Skipping already processed: {entry['month']} (Total links: {total_links})")
                continue

            print(f"\n{'=' * 50}\nProcessing month: {entry['month']}\n{'=' * 50}")
            loader.load_all_pages(entry['url'])
            entry["links_inside"] = loader.get_all_links(keyword=keyword)
            num_links = len(entry["links_inside"])
            total_links += num_links

            # Update JSON file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"Updated JSON for {entry['month']} (Links added: {num_links}, Total: {total_links})")

            # Update backup if we've passed the threshold
            if total_links >= next_backup_threshold:
                write_backup(data, total_links)
                next_backup_threshold += backup_interval

            # Restart browser periodically
            if (i + 1) % 5 == 0:
                print("Restarting browser to prevent memory leaks")
                loader.close()
                loader = PageLoader(headless=headless)
    except Exception as e:
        print(f"Processing failed: {str(e)}")
    finally:
        # Create final backup
        loader.close()
        write_backup(data, total_links)
        print(f"\nProcessing complete. Final total links: {total_links}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process monthly links from Fedresurs')
    parser.add_argument('--force-recreate', action='store_true',
                        help='Recreate output file even if it exists')
    parser.add_argument('--keyword', type=str, default='прекращение',
                        help='Keyword to filter blocks (case-insensitive). Empty string processes all links')
    args = parser.parse_args()

    process_links_file(
        INPUT_PATH,
        OUTPUT_PATH,
        force_recreate=args.force_recreate,
        headless=False,  # НЕ ТРОГАТЬ! по-другому не работает
        keyword=args.keyword
    )
