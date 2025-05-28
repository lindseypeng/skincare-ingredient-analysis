import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
import re
import logging
import json
from bs4 import BeautifulSoup

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class INCIDecoderScraper:
    def __init__(self, headless=True):
        """Initialize the scraper with Chrome options"""
        self.chrome_options = Options()
        if headless:
            self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--window-size=1920,1080")
        self.driver = None
        
    def start_driver(self):
        """Start the Chrome driver"""
        try:
            self.driver = webdriver.Chrome(options=self.chrome_options)
            self.driver.implicitly_wait(10)
            logger.info("Chrome driver started successfully")
        except Exception as e:
            logger.error(f"Failed to start Chrome driver: {e}")
            raise
    
    def close_driver(self):
        """Close the Chrome driver"""
        if self.driver:
            self.driver.quit()
            logger.info("Chrome driver closed")
    
    def expand_ingredients_table(self):
        """Click the 'more' button to expand all ingredients"""
        try:
            # Wait for the page to load
            time.sleep(2)
            
            # Look for both mobile and desktop "more" buttons
            more_buttons = self.driver.find_elements(By.CSS_SELECTOR, ".showmore-link")
            
            for button in more_buttons:
                try:
                    if button.is_displayed() and button.is_enabled():
                        # Scroll to the button to ensure it's visible
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                        time.sleep(1)
                        
                        # Click the button
                        self.driver.execute_script("arguments[0].click();", button)
                        logger.info("Clicked 'more' button to expand ingredients")
                        time.sleep(2)  # Wait for content to load
                        break
                except Exception as e:
                    logger.warning(f"Could not click 'more' button: {e}")
                    continue
                    
        except Exception as e:
            logger.warning(f"No 'more' button found or error expanding table: {e}")
    
    def extract_irritancy_comedogenicity(self, cell_text):
        """Extract irritancy and comedogenicity values from the cell text"""
        irritancy = None
        comedogenicity = None
        
        if cell_text:
            # Look for patterns like "0,1" or "0,0-2"
            pattern = r'(\d+),\s*(\d+)(?:-(\d+))?'
            match = re.search(pattern, cell_text)
            if match:
                irritancy = int(match.group(1))
                # For comedogenicity, if there's a range (e.g., "0-2"), take the higher value
                comedogenicity = int(match.group(3)) if match.group(3) else int(match.group(2))
        
        return irritancy, comedogenicity
    
    def scrape_product_ingredients(self, product_url):
        """Scrape ingredients from a single product page"""
        try:
            logger.info(f"Scraping product: {product_url}")
            self.driver.get(product_url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Get product brand
            try:
                brand_elem = self.driver.find_element(By.CSS_SELECTOR, "a.underline[href*='/brands/']")
                product_brand = brand_elem.text.strip()
            except NoSuchElementException:
                product_brand = "Unknown Brand"

            # Get product title
            try:
                title_elem = self.driver.find_element(By.CSS_SELECTOR, "#product-title")
                product_title = title_elem.text.strip()
            except NoSuchElementException:
                product_title = "Unknown Title"

            # Expand the ingredients table
            self.expand_ingredients_table()

            # --- NEW: Use BeautifulSoup for robust extraction ---
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            table = soup.select_one(".product-skim")
            ingredients_data = []
            if table:
                rows = table.select("tbody tr")
                logger.info(f"Found {len(rows)} ingredient rows")
                for row in rows:
                    cells = row.find_all("td")
                    if len(cells) >= 4:
                        ingredient_name = cells[0].get_text(strip=True)
                        if not ingredient_name:
                            continue  # Skip empty rows!
                        what_it_does = cells[1].get_text(strip=True)
                        irrcom_val = cells[2].get_text(strip=True) or None
                        id_rating = cells[3].get_text(strip=True)
                        ingredients_data.append({
                            'ingredient_name': ingredient_name,
                            'what_it_does': what_it_does,
                            'irritancy/comedogenicity': irrcom_val,
                            'id_rating': id_rating
                        })
            else:
                logger.error("Could not find ingredients table")
                return {}

            logger.info(f"Extracted {len(ingredients_data)} ingredients for {product_title}")
            return {
                "product_brand": product_brand,
                "product_title": product_title,
                "ingredients": ingredients_data
            }

        except Exception as e:
            logger.error(f"Error scraping product {product_url}: {e}")
            return {}
    
    def scrape_multiple_products(self, product_urls):
        """Scrape multiple products and return combined data"""
        all_data = []
        
        for i, url in enumerate(product_urls, 1):
            logger.info(f"Processing product {i}/{len(product_urls)}")
            
            try:
                product_data = self.scrape_product_ingredients(url)
                all_data.extend(product_data)
                
                # Add a small delay between requests to be respectful
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Failed to scrape {url}: {e}")
                continue
        
        return all_data
    
    def save_to_csv(self, data, filename="incidecoder_products.csv"):
        """Save scraped data to CSV file"""
        if not data:
            logger.warning("No data to save")
            return
        
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False)
        logger.info(f"Data saved to {filename}")
        
        # Print summary statistics
        logger.info(f"Total ingredients: {len(df)}")
        logger.info(f"Unique products: {df['product_name'].nunique()}")
        logger.info(f"Unique ingredients: {df['ingredient_name'].nunique()}")
        
    def save_to_json(self, data, filename="incidecoder_products.json"):
        """Save scraped data to JSON file"""
        if not data:
            logger.warning("No data to save")
            return
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Data saved to {filename}")

# Additional utility function to scrape product URLs from category pages
def scrape_product_urls_from_category(scraper, category_url, max_products=None):
    """Scrape product URLs from a category page, scrolling and clicking 'Show more' if needed."""
    logger.info(f"Scraping product URLs from: {category_url}")
    scraper.driver.get(category_url)
    time.sleep(3)
    product_urls = set()
    last_count = 0

    while True:
        # Scroll to bottom to trigger JS loading
        scraper.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        # Click "Show more" if present
        try:
            show_more = scraper.driver.find_element(By.CSS_SELECTOR, ".showmore-link")
            if show_more.is_displayed() and show_more.is_enabled():
                scraper.driver.execute_script("arguments[0].click();", show_more)
                logger.info("Clicked 'Show more' on category page")
                time.sleep(2)
        except Exception:
            pass  # No more button

        # Collect product links
        product_links = scraper.driver.find_elements(By.CSS_SELECTOR, "a[href*='/products/']")
        for link in product_links:
            href = link.get_attribute('href')
            if href and '/products/' in href:
                product_urls.add(href)
                if max_products and len(product_urls) >= max_products:
                    break

        # Stop if no new products are loaded
        if len(product_urls) == last_count or (max_products and len(product_urls) >= max_products):
            break
        last_count = len(product_urls)

    logger.info(f"Found {len(product_urls)} product URLs")
    return list(product_urls)

# Example usage
def main():
    scraper = INCIDecoderScraper(headless=True)
    try:
        scraper.start_driver()
        # Example: scrape from cleansers category, up to 1000 products
        category_url = "https://incidecoder.com/products/category/cleanser"
        product_urls = scrape_product_urls_from_category(scraper, category_url, max_products=1000)
        logger.info(f"Total product URLs to scrape: {len(product_urls)}")
        all_data = []
        for i, url in enumerate(product_urls, 1):
            logger.info(f"Scraping product {i}/{len(product_urls)}: {url}")
            product_data = scraper.scrape_product_ingredients(url)
            if product_data:
                all_data.append(product_data)
            time.sleep(1)
        scraper.save_to_json(all_data, filename="incidecoder_1000_products.json")
        logger.info("Scraping complete!")
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
    finally:
        scraper.close_driver()

if __name__ == "__main__":
    main()