import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from bs4 import BeautifulSoup

# These functions can be added later on:
# "antioxidant", "soothing", "buffering","surfactant-cleansing", "solvent", "skin-identical-ingredient"
FUNCTION_NAMES = [
    "moisturizer-humectant"
]

def click_next_page(driver):
    try:
        next_btn = driver.find_element(By.XPATH, "//a[contains(text(), 'Next page')]")
        if next_btn.is_displayed() and next_btn.is_enabled():
            driver.execute_script("arguments[0].click();", next_btn)
            time.sleep(2)
            return True
    except Exception:
        pass
    return False

def get_ingredient_urls_for_function(driver, function_name):
    base_url = f"https://incidecoder.com/ingredient-functions/{function_name}"
    driver.get(base_url)
    time.sleep(2)
    ingredient_urls = set()
    while True:
        links = driver.find_elements(By.CSS_SELECTOR, "a.klavika.simpletextlistitem[href^='/ingredients/']")
        for link in links:
            href = link.get_attribute('href')
            if href:
                if href.startswith("http"):
                    full_url = href
                else:
                    full_url = "https://incidecoder.com" + href
                ingredient_urls.add(full_url)
        if not click_next_page(driver):
            break
    return list(ingredient_urls)

def get_product_urls_for_ingredient(driver, ingredient_url):
    driver.get(ingredient_url)
    time.sleep(2)
    product_urls = set()
    while True:
        # Product links are in <a class="klavika simpletextlistitem" href="/products/...">
        links = driver.find_elements(By.CSS_SELECTOR, "a.klavika.simpletextlistitem[href^='/products/']")
        for link in links:
            href = link.get_attribute('href')
            if href:
                product_urls.add(href)
        if not click_next_page(driver):
            break
    return list(product_urls)

def scrape_product_details(driver, product_url):
    driver.get(product_url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    # Brand
    brand = None
    brand_tag = soup.select_one("a.underline[href^='/brands/']")
    if brand_tag:
        brand = brand_tag.get_text(strip=True)
    # Title
    title = None
    title_tag = soup.select_one("#product-title")
    if title_tag:
        title = title_tag.get_text(strip=True)
    # Highlights
    highlights = []
    for tag in soup.select('span.hashtag'):
        txt = tag.get_text(strip=True)
        if txt:
            highlights.append(txt)
    # Expand skim through table if "more" button exists
    try:
        more_btn = driver.find_element(By.CSS_SELECTOR, "#showmore-section-ingredlist-table .showmore-link")
        if more_btn.is_displayed() and more_btn.is_enabled():
            driver.execute_script("arguments[0].click();", more_btn)
            time.sleep(1)
            soup = BeautifulSoup(driver.page_source, "html.parser")
    except Exception:
        pass
    # Skim through table
    ingredients = []
    table = soup.select_one("#showmore-section-ingredlist-table .product-skim")
    if table:
        for row in table.select("tbody tr"):
            cells = row.find_all("td")
            if len(cells) >= 4:
                ingredient_name = cells[0].get_text(strip=True)
                what_it_does = cells[1].get_text(strip=True)
                irrcom = cells[2].get_text(strip=True)
                id_rating = cells[3].get_text(strip=True)
                ingredients.append({
                    "ingredient_name": ingredient_name,
                    "what_it_does": what_it_does,
                    "irritancy/comedogenicity": irrcom,
                    "id_rating": id_rating
                })
    return {
        "product_brand": brand,
        "product_title": title,
        "highlights": highlights,
        "ingredients": ingredients,
        "product_url": product_url
    }

def main():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=chrome_options)
    all_products = []
    seen_products = set()
    try:
        for function_name in FUNCTION_NAMES:
            print(f"Scraping function: {function_name}")
            ingredient_urls = get_ingredient_urls_for_function(driver, function_name)
            print(f"  Found {len(ingredient_urls)} ingredients")
            for ingredient_url in ingredient_urls:
                # Defensive: skip malformed URLs
                if not ingredient_url.startswith("http"):
                    print(f"  Skipping invalid ingredient URL: {ingredient_url}")
                    continue
                try:
                    product_urls = get_product_urls_for_ingredient(driver, ingredient_url)
                except Exception as e:
                    print(f"  Failed to load ingredient URL {ingredient_url}: {e}")
                    continue
                print(f"    Ingredient {ingredient_url} has {len(product_urls)} products")
                for product_url in product_urls:
                    if product_url in seen_products:
                        continue
                    seen_products.add(product_url)
                    try:
                        product_data = scrape_product_details(driver, product_url)
                        all_products.append(product_data)
                        print(f"      Scraped: {product_data['product_title']} ({product_url})")
                        if len(all_products) % 10 == 0:
                            with open("incidecoder_function_scrape_partial.json", "w", encoding="utf-8") as f:
                                json.dump(all_products, f, indent=2, ensure_ascii=False)
                            print(f"Saved {len(all_products)} products to incidecoder_function_scrape_partial.json")
                        if len(all_products) >= 500:  # LIMIT HERE
                            print(f"Reached product limit ({len(all_products)}). Stopping scrape.")
                            raise StopIteration
                    except Exception as e:
                        print(f"      Failed to scrape {product_url}: {e}")
                    time.sleep(1)  # Be polite to the server
    except StopIteration:
        print("Scraping stopped due to product limit.")
    finally:
        driver.quit()
        # Save to JSON
        with open("incidecoder_function_scrape.json", "w", encoding="utf-8") as f:
            json.dump(all_products, f, indent=2, ensure_ascii=False)
        print(f"\nSaved {len(all_products)} products to incidecoder_function_scrape.json")

if __name__ == "__main__":
    main()