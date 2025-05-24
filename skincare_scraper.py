import requests
from bs4 import BeautifulSoup
import json
import time
import re
from urllib.parse import quote_plus
import pandas as pd

class SkincareScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def scrape_incidecoder_products(self, product_types=['cleanser', 'toner', 'serum', 'moisturizer', 'sunscreen']):
        """Scrape products from INCIDecoder using search"""
        all_products = []
        
        for product_type in product_types:
            print(f"Scraping {product_type} products...")
            
            # Search for products of this type
            search_url = f"https://incidecoder.com/search?query={product_type}"
            
            try:
                response = self.session.get(search_url)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find product links
                product_links = soup.find_all('a', class_='klavika')
                
                print(f"Found {len(product_links)} {product_type} products")
                
                for link in product_links[:20]:  # Limit to first 20 products per type
                    product_name = link.get_text(strip=True)
                    product_url = link.get('href')
                    
                    if product_url and 'products' in product_url:
                        full_url = f"https://incidecoder.com{product_url}"
                        product_data = self.scrape_product_details(full_url, product_name, product_type)
                        
                        if product_data:
                            all_products.append(product_data)
                            
                        time.sleep(1)  # Be respectful
                        
            except Exception as e:
                print(f"Error scraping {product_type}: {str(e)}")
                continue
                
        return all_products
    
    def scrape_product_details(self, product_url, product_name, product_type):
        """Scrape individual product details from INCIDecoder"""
        try:
            response = self.session.get(product_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract ingredients
            ingredient_links = soup.find_all('a', class_='ingred-link black')
            ingredients = []
            for ing_link in ingredient_links:
                ingredient = ing_link.get_text(strip=True)
                if ingredient:
                    ingredients.append(ingredient.lower())
            
            # Remove duplicates and join with semicolon
            unique_ingredients = list(set(ingredients))
            ingredients_string = ';'.join(unique_ingredients) + ';'
            
            # Extract brand
            brand_link = soup.find('a', class_='underline')
            brand = brand_link.get_text(strip=True) if brand_link else "Unknown"
            
            # Extract image URL
            img_element = soup.select_one('#product-main-image img')
            image_url = img_element.get('src') if img_element else None
            
            product_data = {
                'name': product_name.lower(),
                'brand': brand,
                'type': product_type,
                'image': image_url,
                'ingredients': ingredients_string
            }
            
            print(f"Scraped: {product_name}")
            return product_data
            
        except Exception as e:
            print(f"Error scraping product {product_name}: {str(e)}")
            return None
    
    def analyze_with_skincarisma(self, products):
        """Analyze products using Skincarisma (like the first TypeScript file)"""
        analyzed_products = []
        
        for product in products:
            print(f"Analyzing: {product['name']}")
            
            # Prepare ingredients string for Skincarisma URL
            input_string = product['ingredients'].replace(';', '%2C+')
            input_string = input_string.replace(' ', '+')
            input_string = input_string.replace('(', '%28')
            input_string = input_string.replace(')', '%29')
            
            analysis_url = f"https://www.skincarisma.com/products/analyze?utf8=%E2%9C%93&product%5Bingredient%5D={input_string}"
            
            try:
                response = self.session.get(analysis_url)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract effects
                effects = soup.find_all(class_='effect-wrapper')
                effect_text = ' '.join([effect.get_text(strip=True) for effect in effects])
                
                acne_fighting = 'Acne-Fighting' in effect_text
                anti_aging = 'Anti-Aging' in effect_text
                brightening = 'Brightening' in effect_text
                uv_protection = 'UV Protection' in effect_text
                
                # Extract safety rating
                safety_elements = soup.find_all(class_='progress')
                safety = 0
                if safety_elements:
                    safety_text = safety_elements[0].get_text(strip=True)
                    match = re.search(r'(\d+)%', safety_text)
                    if match:
                        safety = int(match.group(1))
                
                # Extract skin type compatibility from ingredients table
                table_container = soup.find(class_='ingredients-table')
                oily, dry, sensitive, comedogenic = 0, 0, 0, 0
                
                if table_container:
                    table_text = table_container.get_text()
                    table_text = re.sub(r'\s+', '', table_text)
                    
                    # Count skin type compatibility
                    good_oily = table_text.count("GoodforOilySkin")
                    bad_oily = table_text.count("BadforOilySkin")
                    good_dry = table_text.count("GoodforDrySkin")
                    bad_dry = table_text.count("BadforDrySkin")
                    good_sensitive = table_text.count("GoodforSensitiveSkin")
                    bad_sensitive = table_text.count("BadforSensitiveSkin")
                    
                    oily = 1 if good_oily > bad_oily else 0
                    dry = 1 if good_dry > bad_dry else 0
                    sensitive = 1 if good_sensitive > bad_sensitive else 0
                    
                    # Extract comedogenic ratings
                    comedogenic_ratings = re.findall(r'ComedogenicRating\((\d)', table_text)
                    if comedogenic_ratings:
                        ratings = [int(r) for r in comedogenic_ratings]
                        avg_rating = sum(ratings) / len(ratings)
                        comedogenic = 1 if avg_rating <= 2 else 0
                
                # Add analysis to product
                analyzed_product = product.copy()
                analyzed_product.update({
                    'safety': safety,
                    'oily': oily,
                    'dry': dry,
                    'sensitive': sensitive,
                    'comedogenic': comedogenic,
                    'acne_fighting': acne_fighting,
                    'anti_aging': anti_aging,
                    'brightening': brightening,
                    'uv_protection': uv_protection
                })
                
                analyzed_products.append(analyzed_product)
                time.sleep(2)  # Be respectful to Skincarisma
                
            except Exception as e:
                print(f"Error analyzing {product['name']}: {str(e)}")
                # Add product without analysis
                analyzed_products.append(product)
                continue
        
        return analyzed_products
    
    def save_products(self, products, filename='products'):
        """Save products to JSON and CSV"""
        # Save as JSON
        with open(f'{filename}.json', 'w', encoding='utf-8') as f:
            json.dump(products, f, indent=2, ensure_ascii=False)
        
        # Save as CSV
        df = pd.DataFrame(products)
        df.to_csv(f'{filename}.csv', index=False)
        
        print(f"Saved {len(products)} products to {filename}.json and {filename}.csv")

def main():
    scraper = SkincareScraper()
    
    print("Starting product scraping...")
    
    # Step 1: Scrape products from INCIDecoder
    products = scraper.scrape_incidecoder_products()
    
    if products:
        print(f"\nScraped {len(products)} products from INCIDecoder")
        
        # Save initial products
        scraper.save_products(products, 'incidecoder_products')
        
        # Step 2: Analyze with Skincarisma
        print("\nStarting Skincarisma analysis...")
        analyzed_products = scraper.analyze_with_skincarisma(products)
        
        # Save final analyzed products
        scraper.save_products(analyzed_products, 'analyzed_products')
        
        print(f"\nCompleted! Analyzed {len(analyzed_products)} products")
        print("Files created:")
        print("- incidecoder_products.json (raw product data)")
        print("- incidecoder_products.csv")
        print("- analyzed_products.json (with Skincarisma analysis)")
        print("- analyzed_products.csv")
    else:
        print("No products were scraped successfully")

if __name__ == "__main__":
    main()