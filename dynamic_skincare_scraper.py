from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import json
import time

class DynamicSkincareScraper:
    def __init__(self, driver_path=None):
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        self.driver = webdriver.Chrome(executable_path=driver_path, options=chrome_options) if driver_path else webdriver.Chrome(options=chrome_options)

    def scrape_product_skim_through_table(self, product_url):
        self.driver.get(product_url)
        # Wait for the table to load
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "showmore-section-ingredlist-table"))
            )
        except Exception:
            print("Skim through table did not load.")
            return None

        # Get initial number of rows
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        table_section = soup.find('div', id='showmore-section-ingredlist-table')
        table = table_section.find('table', class_='product-skim') if table_section else None
        tbody = table.find('tbody') if table else None
        initial_rows = len(tbody.find_all('tr')) if tbody else 0

        # Click the "more" button if it exists and is visible
        try:
            more_btn = self.driver.find_element(By.CSS_SELECTOR, "#showmore-section-ingredlist-table .showmore-link")
            if more_btn.is_displayed():
                self.driver.execute_script("arguments[0].click();", more_btn)
                # Wait until the number of rows increases
                WebDriverWait(self.driver, 5).until(
                    lambda d: (
                        len(
                            BeautifulSoup(
                                d.page_source, 'html.parser'
                            ).find('div', id='showmore-section-ingredlist-table')
                             .find('table', class_='product-skim')
                             .find('tbody')
                             .find_all('tr')
                        ) > initial_rows
                    )
                )
                time.sleep(0.5)  # Give a little extra time for animation/lazy load
        except Exception as e:
            print(f"No or unresponsive 'more' button: {e}")

        # Now parse the fully expanded table
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        product_name = self.extract_product_name(soup)
        product_type = self.extract_product_type(soup)
        tags = self.extract_tags(soup)
        skim_table = self.extract_skim_through_table(soup)
        print(f"Number of chemical ingredients scraped from skim_through_table: {len(skim_table)}")
        return {
            "product_name": product_name,
            "type": product_type,
            "tags": tags,
            "skim_through_table": skim_table
        }

    def extract_product_name(self, soup):
        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)
        title = soup.find('title')
        if title:
            return title.get_text(strip=True)
        return "Unknown Product"

    def extract_product_type(self, soup):
        # Try to find the type/category (e.g., cleanser, serum) from breadcrumbs or meta
        breadcrumb = soup.find('ol', class_='breadcrumb')
        if breadcrumb:
            items = breadcrumb.find_all('li')
            if len(items) > 1:
                return items[-2].get_text(strip=True).lower()
        # Fallback: look for meta or category tags
        meta_type = soup.find('meta', {'property': 'og:type'})
        if meta_type and meta_type.get('content'):
            return meta_type['content'].lower()
        return None

    def extract_tags(self, soup):
        # Try to find tags/highlights (e.g., alcohol-free, sulfate-free)
        tags = []
        tag_spans = soup.find_all('span', class_='tag')
        for tag in tag_spans:
            tag_text = tag.get_text(strip=True)
            if tag_text:
                tags.append(tag_text)
        # Also check for badges or highlights
        badge_spans = soup.find_all('span', class_='badge')
        for badge in badge_spans:
            badge_text = badge.get_text(strip=True)
            if badge_text and badge_text not in tags:
                tags.append(badge_text)
        return tags if tags else None

    def extract_skim_through_table(self, soup):
        table_data = []
        table_section = soup.find('div', id='showmore-section-ingredlist-table')
        if not table_section:
            print("No skim through table section found.")
            return table_data
        table = table_section.find('table', class_='product-skim')
        if not table:
            print("No skim through table found.")
            return table_data
        tbody = table.find('tbody')
        if not tbody:
            print("No table body found.")
            return table_data

        for row in tbody.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) != 4:
                continue

            # Ingredient name (just the name)
            ingred_a = cells[0].find('a', class_='ingred-detail-link')
            ingredient_name = ingred_a.get_text(strip=True) if ingred_a else cells[0].get_text(strip=True).strip() or None
            if not ingredient_name:
                continue

            # What-it-does (list of strings)
            what_it_does = [a.get_text(strip=True) for a in cells[1].find_all('a', class_='ingred-function-link')]
            if not what_it_does:
                what_it_does = None

            # Irritancy/comedogenicity as a single string (first two values only)
            irrcom_val = None
            spans = cells[2].find_all('span')
            values = []
            if spans:
                for s in spans:
                    val = s.get_text(strip=True)
                    if val:
                        values.append(val)
                # Only take the first two values
                if len(values) >= 2:
                    irrcom_val = f"{values[0]},{values[1]}"
                elif len(values) == 1:
                    irrcom_val = values[0]
                else:
                    irrcom_val = None
            else:
                # fallback: try to parse text
                irrcom_text = cells[2].get_text(strip=True)
                if irrcom_text:
                    parts = [p.strip() for p in irrcom_text.replace('/', ',').split(',') if p.strip()]
                    if len(parts) >= 2:
                        irrcom_val = f"{parts[0]},{parts[1]}"
                    elif len(parts) == 1:
                        irrcom_val = parts[0]
                    else:
                        irrcom_val = None

            # ID-Rating
            id_rating_span = cells[3].find('span', class_='our-take')
            id_rating = id_rating_span.get_text(strip=True) if id_rating_span else None

            table_data.append({
                "ingredient_name": ingredient_name,
                "what_it_does": what_it_does,
                "irritancy/comedogenicity": irrcom_val,
                "id_rating": id_rating
            })

        return table_data

    def close(self):
        self.driver.quit()

def main():
    # If you have chromedriver in your PATH, you don't need to specify driver_path
    scraper = DynamicSkincareScraper()
    product_url = "https://incidecoder.com/products/eve-lom-cleanser"
    print(f"Scraping skim_through_table for: {product_url}")
    result = scraper.scrape_product_skim_through_table(product_url)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    scraper.close()

if __name__ == "__main__":
    main()