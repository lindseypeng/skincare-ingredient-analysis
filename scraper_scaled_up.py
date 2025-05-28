import time
import pandas as pd
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
import re
import logging

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
            
            # Wait for the page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Get product name
            product_name = "Unknown Product"
            try:
                product_name_element = self.driver.find_element(By.CSS_SELECTOR, "h1, .product-name, .product-title")
                product_name = product_name_element.text.strip()
            except NoSuchElementException:
                logger.warning("Could not find product name")
            
            # Get product type
            product_type = "Unknown Type"
            try:
                # Look for product type in various possible locations
                type_selectors = [".product-type", ".category", ".breadcrumb a:last-child"]
                for selector in type_selectors:
                    try:
                        type_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        product_type = type_element.text.strip()
                        break
                    except NoSuchElementException:
                        continue
            except Exception as e:
                logger.warning(f"Could not find product type: {e}")
            
            # Expand the ingredients table
            self.expand_ingredients_table()
            
            # Find the ingredients table
            ingredients_data = []
            try:
                table = self.driver.find_element(By.CSS_SELECTOR, ".product-skim")
                rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
                
                logger.info(f"Found {len(rows)} ingredient rows")
                
                for row in rows:
                    try:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) >= 4:
                            # Extract ingredient name
                            ingredient_name = cells[0].text.strip()
                            
                            # Extract what-it-does
                            what_it_does = cells[1].text.strip()
                            
                            # Extract irritancy and comedogenicity
                            irr_com_text = cells[2].text.strip()
                            irritancy, comedogenicity = self.extract_irritancy_comedogenicity(irr_com_text)
                            
                            # Extract ID rating
                            id_rating = cells[3].text.strip()
                            
                            ingredients_data.append({
                                'product_name': product_name,
                                'product_type': product_type,
                                'ingredient_name': ingredient_name,
                                'what_it_does': what_it_does,
                                'irritancy': irritancy,
                                'comedogenicity': comedogenicity,
                                'id_rating': id_rating
                            })
                    except Exception as e:
                        logger.warning(f"Error processing ingredient row: {e}")
                        continue
                        
            except NoSuchElementException:
                logger.error("Could not find ingredients table")
                return []
            
            logger.info(f"Extracted {len(ingredients_data)} ingredients for {product_name}")
            return ingredients_data
            
        except Exception as e:
            logger.error(f"Error scraping product {product_url}: {e}")
            return []
    
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
    
    def save_to_json(self, data, filename="incidecoder_products.json"):
        """Save scraped data to JSON file optimized for ML processing"""
        if not data:
            logger.warning("No data to save")
            return
        
        # Group by product for better ML structure
        products_dict = {}
        for item in data:
            product_name = item['product_name']
            if product_name not in products_dict:
                products_dict[product_name] = {
                    'product_name': product_name,
                    'product_type': item['product_type'],
                    'ingredients': []
                }
            
            products_dict[product_name]['ingredients'].append({
                'ingredient_name': item['ingredient_name'],
                'what_it_does': item['what_it_does'],
                'irritancy': item['irritancy'],
                'comedogenicity': item['comedogenicity'],
                'id_rating': item['id_rating']
            })
        
        # Convert to list and add metadata for ML
        final_data = {
            'metadata': {
                'total_products': len(products_dict),
                'total_ingredients': len(data),
                'scraped_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'unique_ingredients': len(set(item['ingredient_name'] for item in data))
            },
            'products': list(products_dict.values())
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Data saved to {filename}")
        logger.info(f"Total products: {final_data['metadata']['total_products']}")
        logger.info(f"Total ingredients: {final_data['metadata']['total_ingredients']}")
        logger.info(f"Unique ingredients: {final_data['metadata']['unique_ingredients']}")
    
    def save_to_csv(self, data, filename="incidecoder_products.csv"):
        """Save scraped data to CSV file (backup method)"""
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
    
    def discover_all_product_urls(self, max_products=None, start_page=1):
        """Discover product URLs from the main products page and pagination"""
        all_product_urls = set()
        base_url = "https://incidecoder.com/products"
        
        # First, scrape from the main products page
        logger.info("Discovering products from main products page...")
        main_page_urls = self.scrape_product_urls_from_products_page(base_url)
        all_product_urls.update(main_page_urls)
        
        # Check for pagination or "newest products" section
        newest_urls = self.scrape_newest_products()
        all_product_urls.update(newest_urls)
        
        # Try to find more products through search/browse functionality
        search_urls = self.scrape_from_search_page(max_products)
        all_product_urls.update(search_urls)
        
        final_urls = list(all_product_urls)
        
        if max_products:
            final_urls = final_urls[:max_products]
            
        logger.info(f"Total unique product URLs discovered: {len(final_urls)}")
        return final_urls
    
    def scrape_product_urls_from_products_page(self, url):
        """Scrape product URLs from the main products page"""
        logger.info(f"Scraping product URLs from: {url}")
        
        try:
            self.driver.get(url)
            time.sleep(3)
            
            product_urls = set()
            
            # Look for product links in various sections
            selectors_to_try = [
                "a[href*='/products/']",  # General product links
                ".product-link",  # If they use a specific class
                "a[href^='/products/']",  # Links starting with /products/
                "div[class*='product'] a",  # Links within product divs
            ]
            
            for selector in selectors_to_try:
                try:
                    links = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for link in links:
                        href = link.get_attribute('href')
                        if href and '/products/' in href and href.startswith('https://incidecoder.com/products/'):
                            product_urls.add(href)
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            logger.info(f"Found {len(product_urls)} product URLs from main page")
            return list(product_urls)
            
        except Exception as e:
            logger.error(f"Error scraping main products page: {e}")
            return []
    
    def scrape_newest_products(self):
        """Scrape from the newest products section"""
        try:
            # Look for "See newest products" link or similar
            newest_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='newest'], a[href*='recent'], a[href*='latest']")
            
            product_urls = set()
            
            for link in newest_links:
                try:
                    href = link.get_attribute('href')
                    if href:
                        logger.info(f"Following newest products link: {href}")
                        self.driver.get(href)
                        time.sleep(2)
                        
                        # Scrape products from this page
                        page_urls = self.scrape_product_urls_from_products_page(href)
                        product_urls.update(page_urls)
                        
                except Exception as e:
                    logger.warning(f"Error following newest products link: {e}")
                    continue
            
            logger.info(f"Found {len(product_urls)} URLs from newest products")
            return list(product_urls)
            
        except Exception as e:
            logger.warning(f"Could not scrape newest products: {e}")
            return []
    
    def scrape_from_search_page(self, max_products=None):
        """Scrape products from the search page with different filters"""
        search_url = "https://incidecoder.com/search/product"
        product_urls = set()
        
        try:
            logger.info("Trying to discover products from search page...")
            self.driver.get(search_url)
            time.sleep(3)
            
            # Try to submit empty search to get all products or use common filters
            try:
                # Look for search form or filter options
                search_forms = self.driver.find_elements(By.CSS_SELECTOR, "form, .search-form")
                if search_forms:
                    # Try submitting empty search
                    search_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit'], .search-button")
                    search_button.click()
                    time.sleep(3)
                    
                    # Scrape results
                    page_urls = self.scrape_product_urls_from_products_page(self.driver.current_url)
                    product_urls.update(page_urls)
                    
            except Exception as e:
                logger.debug(f"Could not submit search form: {e}")
            
            # Try some common product type searches
            common_searches = ['moisturizer', 'serum', 'cleanser', 'sunscreen', 'toner']
            
            for search_term in common_searches:
                try:
                    # Go back to search page
                    self.driver.get(search_url)
                    time.sleep(2)
                    
                    # Find search input and enter term
                    search_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='search'], input[name*='search'], .search-input")
                    search_input.clear()
                    search_input.send_keys(search_term)
                    
                    # Submit search
                    search_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit'], .search-button")
                    search_button.click()
                    time.sleep(3)
                    
                    # Scrape results
                    page_urls = self.scrape_product_urls_from_products_page(self.driver.current_url)
                    product_urls.update(page_urls)
                    
                    logger.info(f"Found {len(page_urls)} products for search term: {search_term}")
                    
                    if max_products and len(product_urls) >= max_products:
                        break
                        
                except Exception as e:
                    logger.debug(f"Search for '{search_term}' failed: {e}")
                    continue
            
            logger.info(f"Found {len(product_urls)} URLs from search functionality")
            return list(product_urls)
            
        except Exception as e:
            logger.warning(f"Could not scrape from search page: {e}")
            return []

# Updated main function for automated discovery
def main():
    """Main function with automated product discovery"""
    scraper = INCIDecoderScraper(headless=False)  # Set to True for headless mode
    
    try:
        scraper.start_driver()
        
        # Automatically discover product URLs
        logger.info("Starting automated product discovery...")
        product_urls = scraper.discover_all_product_urls(max_products=50)  # Adjust max_products as needed
        
        if not product_urls:
            logger.error("No product URLs discovered!")
            return
        
        logger.info(f"Discovered {len(product_urls)} product URLs")
        
        # Scrape all discovered products
        all_data = scraper.scrape_multiple_products(product_urls)
        
        # Save to JSON
        if all_data:
            scraper.save_to_json(all_data, "incidecoder_automated_scrape.json")
            
            # Display summary
            df = pd.DataFrame(all_data)
            print(f"\nScraping completed!")
            print(f"Total products scraped: {df['product_name'].nunique()}")
            print(f"Total ingredients found: {len(df)}")
            print(f"Unique ingredients: {df['ingredient_name'].nunique()}")
            
            # Show sample data
            print("\nSample of scraped data:")
            print(df.head(10).to_string())
        else:
            logger.warning("No data was scraped!")
            
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
    
    finally:
        scraper.close_driver()

# Function to scrape specific number of products with progress tracking
def scrape_with_progress(max_products=500, output_file="incidecoder_products.json"):
    """Scrape products with progress tracking and resume capability"""
    scraper = INCIDecoderScraper(headless=True)
    
    try:
        scraper.start_driver()
        
        # Discover all available product URLs
        logger.info("Discovering all available products...")
        all_urls = scraper.discover_all_product_urls()
        
        if max_products:
            all_urls = all_urls[:max_products]
        
        logger.info(f"Will scrape {len(all_urls)} products")
        
        all_data = []
        failed_urls = []
        
        for i, url in enumerate(all_urls, 1):
            logger.info(f"Processing product {i}/{len(all_urls)}: {url}")
            
            try:
                product_data = scraper.scrape_product_ingredients(url)
                if product_data:
                    all_data.extend(product_data)
                    logger.info(f"✓ Successfully scraped {len(product_data)} ingredients")
                else:
                    failed_urls.append(url)
                    logger.warning(f"✗ No data found for {url}")
                
                # Save progress every 10 products
                if i % 10 == 0:
                    temp_filename = f"temp_{output_file}"
                    scraper.save_to_json(all_data, temp_filename)
                    logger.info(f"Progress saved to {temp_filename}")
                
                # Respectful delay
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Failed to scrape {url}: {e}")
                failed_urls.append(url)
                continue
        
        # Final save
        if all_data:
            scraper.save_to_json(all_data, output_file)
            logger.info(f"Final data saved to {output_file}")
            
            # Summary
            df = pd.DataFrame(all_data)
            print(f"\n=== SCRAPING SUMMARY ===")
            print(f"Products processed: {len(all_urls)}")
            print(f"Products successfully scraped: {df['product_name'].nunique()}")
            print(f"Failed URLs: {len(failed_urls)}")
            print(f"Total ingredients: {len(df)}")
            print(f"Unique ingredients: {df['ingredient_name'].nunique()}")
            
            if failed_urls:
                print(f"\nFailed URLs:")
                for url in failed_urls[:10]:  # Show first 10 failed URLs
                    print(f"  - {url}")
        
    except Exception as e:
        logger.error(f"Scraping process failed: {e}")
    
    finally:
        scraper.close_driver()

if __name__ == "__main__":
    # For automated discovery and scraping
    # main()
    
    # For large-scale scraping with progress tracking (recommended for ML)
    scrape_with_progress(max_products=500, output_file="incidecoder_ml_dataset.json")