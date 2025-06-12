import json
import os
import shutil
import argparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, TimeoutException

class PageLoader:
    def __init__(self, headless=False):
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
    
    def get_all_links(self):
        """Extract links by clicking each block and capturing the URL"""
        print("Extracting links by clicking blocks...")
        
        # Find all clickable anchors using the proper selector
        anchors = self.driver.find_elements(
            By.CSS_SELECTOR, "div.info-link-container > el-info-link > a.info"
        )
        print(f"Found {len(anchors)} links to process")
        
        links = []
        processed_count = 0
        
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
        
        print(f"Successfully processed {processed_count}/{len(anchors)} links")
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

def process_links_file(input_file, output_file, force_recreate=False):
    """Process all URLs in JSON file and update with extracted links"""
    initialize_output_file(input_file, output_file, force_recreate)
    
    # Read from output file which may already contain processed entries
    with open(output_file, 'r+', encoding='utf-8') as f:
        data = json.load(f)
        loader = PageLoader(headless=False)
        
        try:
            for i, entry in enumerate(data):
                if "links_inside" in entry and not force_recreate:
                    print(f"Skipping already processed: {entry['month']}")
                    continue
                
                print(f"\n{'='*50}\nProcessing month: {entry['month']}\n{'='*50}")
                loader.load_all_pages(entry['url'])
                entry["links_inside"] = loader.get_all_links()
                
                # Update JSON file after each processed entry
                f.seek(0)
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.truncate()
                print(f"Updated JSON for {entry['month']}")
                
                # Close and reopen browser periodically to prevent memory issues
                if (i + 1) % 5 == 0:
                    print("Restarting browser to prevent memory leaks")
                    loader.close()
        except Exception as e:
            print(f"Processing failed: {str(e)}")
        finally:
            loader.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process monthly links from Fedresurs')
    parser.add_argument('--force-recreate', action='store_true',
                        help='Recreate output file even if it exists')
    args = parser.parse_args()
    
    process_links_file("1month_links.json", "2month_links.json", args.force_recreate)