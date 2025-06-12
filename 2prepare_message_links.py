from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

class PageLoader:
    def __init__(self, headless=False):
        self.options = Options()
        if headless:
            self.options.add_argument("--headless=new")
        self.options.add_argument("--start-maximized")
        self.driver = None
        
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
        
        # Initial page load wait
        time.sleep(2)
        
        click_count = 0
        while True:
            try:
                # Wait for button to be clickable
                button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div.more_btn_wrapper div.more_btn")))
                
                # Scroll to button (some sites require element in viewport)
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                
                # Click using JavaScript to avoid interception issues
                self.driver.execute_script("arguments[0].click();", button)
                click_count += 1
                print(f"Clicked 'Load More' ({click_count} times)")
                
                # Wait for content to load - adjust based on network speed
                time.sleep(2)
                
            except Exception as e:
                print(f"Stopping: {str(e).split('.')[0]}")
                break
        
        print(f"Total clicks: {click_count}")
        return self.driver
    
    def close(self):
        """Close browser session"""
        if self.driver:
            self.driver.quit()
            self.driver = None

# Usage example
if __name__ == "__main__":
    # Initialize loader (set headless=True for background operation)
    loader = PageLoader(headless=False)
    
    try:
        # First URL processing
        url1 = "https://fedresurs.ru/encumbrances?group=Leasing&period=%7B%22beginJsDate%22%3A%222016-01-01T00%3A00%3A00.000Z%22%2C%22endJsDate%22%3A%222016-01-31T23%3A59%3A59.999Z%22%7D&limit=15&offset=0"
        driver = loader.load_all_pages(url1)
        
        # Perform additional actions with the loaded page
        # Example: extract data or take screenshot
        driver.save_screenshot("page1_fully_loaded.png")
        
        # Process another URL using the same session
        # url2 = "https://another-fedresurs-url.example"
        # loader.load_all_pages(url2)
        
    finally:
        # Close browser only when completely done
        # loader.close()
        pass