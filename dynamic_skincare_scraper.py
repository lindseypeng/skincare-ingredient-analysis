import requests
from bs4 import BeautifulSoup
import json
import time
import re
from urllib.parse import quote_plus
import pandas as pd
from collections import Counter
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import os

class DynamicSkincareScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Initialize sets to collect all unique categories found during scraping
        self.all_functions = set()
        self.all_categories = set()
        self.all_ingredients = set()
        self.all_tags = set()
        
    def scrape_incidecoder_products(self, product_types=['cleanser', 'toner', 'serum', 'moisturizer', 'sunscreen'], max_per_type=10):
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
                
                count = 0
                for link in product_links:
                    if count >= max_per_type:
                        break
                        
                    product_name = link.get_text(strip=True)
                    product_url = link.get('href')
                    
                    if product_url and 'products' in product_url:
                        full_url = f"https://incidecoder.com{product_url}"
                        print(f"  Scraping: {product_name}")
                        
                        product_data = self.scrape_product_details(full_url, product_name, product_type)
                        
                        if product_data:
                            all_products.append(product_data)
                            count += 1
                            
                        time.sleep(2)  # Be respectful
                        
            except Exception as e:
                print(f"Error scraping {product_type}: {str(e)}")
                continue
                
        return all_products
    
    def scrape_product_details(self, product_url, product_name, product_type):
        """Scrape detailed product information from INCIDecoder product page"""
        try:
            response = self.session.get(product_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            product_data = {
                'name': product_name,
                'brand': None,
                'type': product_type,
                'url': product_url,
                'image': None,
                'tags': [],
                'raw_ingredients': [],
                'ingredient_details': {},  # Store all extracted details per ingredient
                'website_categories': {},  # Categories as defined by the website
                'ingredient_functions': {},  # Functions as defined by the website
                'raw_text_content': ""  # Store all text for later NLP analysis
            }
            
            # Extract brand
            brand_elements = soup.find_all(['a', 'span', 'div'], class_=['underline', 'brand', 'brand-name'])
            for elem in brand_elements:
                if elem.get_text(strip=True) and len(elem.get_text(strip=True)) < 50:
                    product_data['brand'] = elem.get_text(strip=True)
                    break
            
            # Extract image URL
            img_elements = soup.find_all('img')
            for img in img_elements:
                src = img.get('src')
                if src and any(keyword in src.lower() for keyword in ['product', 'bottle', 'package']):
                    product_data['image'] = src
                    break
            
            # Extract ALL tags (let the website decide what's important)
            tag_elements = soup.find_all(['span', 'div'], class_=re.compile(r'tag|badge|label'))
            for tag_elem in tag_elements:
                tag_text = tag_elem.get_text(strip=True)
                if tag_text and len(tag_text) < 100:  # Reasonable length filter
                    product_data['tags'].append(tag_text)
                    self.all_tags.add(tag_text.lower())
            
            # Extract raw ingredients list
            ingredient_sections = soup.find_all(['div', 'section'], 
                                              class_=re.compile(r'ingredient|inci', re.I))
            
            for section in ingredient_sections:
                # Look for ingredient links/names
                ingredient_links = section.find_all(['a', 'span'], 
                                                  class_=re.compile(r'ingred|ingredient', re.I))
                for link in ingredient_links:
                    ingredient_name = link.get_text(strip=True)
                    if ingredient_name and len(ingredient_name) < 100:
                        product_data['raw_ingredients'].append(ingredient_name)
                        self.all_ingredients.add(ingredient_name.lower())
            
            # Extract ALL structured data from tables/lists
            tables = soup.find_all('table')
            for table in tables:
                self.extract_table_data(table, product_data)
            
            # Extract categorized information from structured sections
            sections = soup.find_all(['div', 'section'], id=True)
            for section in sections:
                section_id = section.get('id', '').lower()
                section_data = self.extract_section_data(section, section_id)
                if section_data:
                    product_data['website_categories'][section_id] = section_data
            
            # Store raw text content for later NLP analysis
            product_data['raw_text_content'] = soup.get_text()
            
            # Extract ingredient details dynamically
            product_data['ingredient_details'] = self.extract_all_ingredient_details(soup)

            # Extract key ingredients by function (from first .ingredlist-by-function-block)
            product_data['key_ingredients'] = self.extract_key_ingredients(soup)

            
            
            print(f"    ✓ Extracted {len(product_data['raw_ingredients'])} ingredients")
            print(f"    ✓ Found {len(product_data['key_ingredients'])} key ingredients")
            print(f"    ✓ Found {len(product_data['website_categories'])} categories")
            print(f"    ✓ Tags: {', '.join(product_data['tags'][:3])}{'...' if len(product_data['tags']) > 3 else ''}")
            
            return product_data
            
        except Exception as e:
            print(f"    ✗ Error scraping {product_name}: {str(e)}")
            return None

    def extract_key_ingredients(self, soup):
        """Extract key ingredients by function from the first .ingredlist-by-function-block"""
        block = soup.find('div', class_='ingredlist-by-function-block')
        if not block:
            return []

        key_ingredients = []
        for div in block.find_all('div', recursive=False):
            func_elem = div.find('a', class_='func-link')
            if not func_elem:
                continue
            function = func_elem.get_text(strip=True)

            ingredients = []
            for ingred_link in div.find_all('a', class_='ingred-link'):
                name = ingred_link.get_text(strip=True)
                url = ingred_link.get('href')
                if url and not url.startswith('http'):
                    url = f"https://incidecoder.com{url}"
                ingredients.append({'name': name, 'url': url})

            if ingredients:
                key_ingredients.append({
                    'function': function,
                    'ingredients': ingredients
                })

        return key_ingredients

    def extract_table_data(self, table, product_data):
        """Extract data from any table structure"""
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                key = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)
                if key and value:
                    product_data['ingredient_functions'][key] = value
                    self.all_functions.add(value.lower())
    
    def extract_section_data(self, section, section_id):
        """Extract structured data from any section"""
        section_data = {}
        
        # Look for lists
        lists = section.find_all(['ul', 'ol'])
        for lst in lists:
            items = [li.get_text(strip=True) for li in lst.find_all('li')]
            if items:
                section_data['list_items'] = items
        
        # Look for key-value pairs
        strong_elements = section.find_all(['strong', 'b', 'h3', 'h4', 'h5'])
        for strong in strong_elements:
            title = strong.get_text(strip=True)
            if title:
                # Get following text
                next_text = ""
                next_elem = strong.next_sibling
                while next_elem and len(next_text) < 500:
                    if hasattr(next_elem, 'get_text'):
                        next_text += next_elem.get_text(strip=True) + " "
                    elif isinstance(next_elem, str):
                        next_text += next_elem.strip() + " "
                    next_elem = next_elem.next_sibling
                    if next_elem and next_elem.name in ['strong', 'b', 'h3', 'h4', 'h5']:
                        break
                
                if next_text.strip():
                    section_data[title] = next_text.strip()
                    self.all_categories.add(title.lower())
        
        return section_data if section_data else None
    
    def extract_all_ingredient_details(self, soup):
        """Extract any available details for each ingredient"""
        ingredient_details = {}
        
        # Look for ingredient explanation blocks
        ingredient_blocks = soup.find_all(['div', 'section'], 
                                        class_=re.compile(r'ingredient|explanation', re.I))
        
        for block in ingredient_blocks:
            # Try to find ingredient name
            name_elem = block.find(['h3', 'h4', 'h5', 'strong', 'b'])
            if name_elem:
                ingredient_name = name_elem.get_text(strip=True)
                
                # Extract all text content from this block
                block_text = block.get_text(strip=True)
                
                # Look for specific patterns
                details = {
                    'full_text': block_text,
                    'functions': [],
                    'benefits': [],
                    'concerns': []
                }
                
                # Simple keyword-based categorization
                text_lower = block_text.lower()
                
                # Functions
                function_keywords = ['moisturizing', 'cleansing', 'exfoliating', 'antioxidant', 
                                   'preservative', 'emulsifier', 'surfactant', 'humectant',
                                   'soothing', 'anti-aging', 'brightening']
                for keyword in function_keywords:
                    if keyword in text_lower:
                        details['functions'].append(keyword)
                
                # Benefits
                benefit_keywords = ['hydrating', 'smoothing', 'softening', 'protecting',
                                  'healing', 'calming', 'nourishing', 'strengthening']
                for keyword in benefit_keywords:
                    if keyword in text_lower:
                        details['benefits'].append(keyword)
                
                # Concerns
                concern_keywords = ['irritating', 'comedogenic', 'sensitizing', 'drying']
                for keyword in concern_keywords:
                    if keyword in text_lower:
                        details['concerns'].append(keyword)
                
                ingredient_details[ingredient_name] = details
        
        return ingredient_details
    
    def analyze_scraped_data(self, products):
        """Analyze all scraped data to find patterns and create dynamic features"""
        print("\n🔍 Analyzing scraped data for patterns...")
        
        analysis_results = {
            'most_common_functions': Counter(),
            'most_common_categories': Counter(), 
            'most_common_ingredients': Counter(),
            'most_common_tags': Counter(),
            'product_type_patterns': {},
            'suggested_features': []
        }
        
        # Analyze patterns across all products
        for product in products:
            product_type = product['type']
            
            if product_type not in analysis_results['product_type_patterns']:
                analysis_results['product_type_patterns'][product_type] = {
                    'common_ingredients': Counter(),
                    'common_functions': Counter(),
                    'common_tags': Counter()
                }
            
            # Count occurrences
            for ingredient in product['raw_ingredients']:
                analysis_results['most_common_ingredients'][ingredient.lower()] += 1
                analysis_results['product_type_patterns'][product_type]['common_ingredients'][ingredient.lower()] += 1
            
            for func in product['ingredient_functions'].values():
                analysis_results['most_common_functions'][func.lower()] += 1
                analysis_results['product_type_patterns'][product_type]['common_functions'][func.lower()] += 1
            
            for tag in product['tags']:
                analysis_results['most_common_tags'][tag.lower()] += 1
                analysis_results['product_type_patterns'][product_type]['common_tags'][tag.lower()] += 1
        
        # Generate suggested features based on frequency
        print("\n📊 Most common elements found:")
        print(f"Functions: {list(analysis_results['most_common_functions'].most_common(10))}")
        print(f"Ingredients: {list(analysis_results['most_common_ingredients'].most_common(10))}")
        print(f"Tags: {list(analysis_results['most_common_tags'].most_common(10))}")
        
        # Suggest binary features for ML
        min_frequency = max(2, len(products) * 0.1)  # At least 10% of products
        
        for func, count in analysis_results['most_common_functions'].most_common(20):
            if count >= min_frequency:
                analysis_results['suggested_features'].append(f'has_function_{func.replace(" ", "_")}')
        
        for ingredient, count in analysis_results['most_common_ingredients'].most_common(30):
            if count >= min_frequency:
                clean_name = re.sub(r'[^\w]', '_', ingredient.lower())
                analysis_results['suggested_features'].append(f'contains_{clean_name}')
        
        for tag, count in analysis_results['most_common_tags'].most_common(15):
            if count >= min_frequency:
                clean_name = re.sub(r'[^\w]', '_', tag.lower())
                analysis_results['suggested_features'].append(f'tagged_{clean_name}')
        
        return analysis_results
    
    def create_dynamic_features(self, products, analysis_results):
        """Create ML features based on the analysis results"""
        print(f"\n🤖 Creating {len(analysis_results['suggested_features'])} dynamic features...")
        
        featured_products = []
        
        for product in products:
            featured_product = product.copy()
            
            # Basic numeric features
            featured_product['total_ingredients'] = len(product['raw_ingredients'])
            featured_product['total_functions'] = len(product['ingredient_functions'])
            featured_product['total_tags'] = len(product['tags'])
            featured_product['total_categories'] = len(product['website_categories'])
            
            # Dynamic binary features based on analysis
            for feature in analysis_results['suggested_features']:
                featured_product[feature] = False
                
                if feature.startswith('has_function_'):
                    func_name = feature.replace('has_function_', '').replace('_', ' ')
                    featured_product[feature] = any(func_name in func.lower() 
                                                  for func in product['ingredient_functions'].values())
                
                elif feature.startswith('contains_'):
                    ingredient_name = feature.replace('contains_', '').replace('_', ' ')
                    featured_product[feature] = any(ingredient_name in ing.lower() 
                                                  for ing in product['raw_ingredients'])
                
                elif feature.startswith('tagged_'):
                    tag_name = feature.replace('tagged_', '').replace('_', ' ')
                    featured_product[feature] = any(tag_name in tag.lower() 
                                                  for tag in product['tags'])
            
            featured_products.append(featured_product)
        
        return featured_products
    
    def save_products(self, products, analysis_results=None, filename='skincare_products'):
        """Save products to JSON and CSV files with analysis"""
        # Save detailed JSON
        save_data = {
            'products': products,
            'scraping_metadata': {
                'total_products': len(products),
                'unique_ingredients_found': len(self.all_ingredients),
                'unique_functions_found': len(self.all_functions),
                'unique_categories_found': len(self.all_categories),
                'unique_tags_found': len(self.all_tags)
            }
        }
        
        if analysis_results:
            save_data['analysis'] = analysis_results
        
        with open(f'{filename}.json', 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        
        # Create flattened version for CSV
        flattened_products = []
        for product in products:
            flat_product = {}
            
            # Basic info
            for key in ['name', 'brand', 'type', 'url', 'image']:
                flat_product[key] = product.get(key)
            
            # Join list fields
            flat_product['tags'] = ' | '.join(product.get('tags', []))
            flat_product['raw_ingredients'] = ' | '.join(product.get('raw_ingredients', []))
            
            # Functions summary
            func_summary = []
            for ingredient, function in product.get('ingredient_functions', {}).items():
                func_summary.append(f"{ingredient}: {function}")
            flat_product['ingredient_functions'] = ' | '.join(func_summary)
            
            # All boolean and numeric features
            for key, value in product.items():
                if isinstance(value, (bool, int, float)) or key.startswith(('has_', 'is_', 'contains_', 'tagged_')) or key.endswith('_count'):
                    flat_product[key] = value
            
            flattened_products.append(flat_product)
        
        # Save CSV
        df = pd.DataFrame(flattened_products)
        df.to_csv(f'{filename}.csv', index=False)
        
        print(f"\n✅ Saved {len(products)} products:")
        print(f"   📄 {filename}.json (detailed data + analysis)")
        print(f"   📊 {filename}.csv (flattened for ML)")
        
        if analysis_results:
            print(f"   🎯 Generated {len(analysis_results['suggested_features'])} dynamic features")
            print(f"   📈 Found {len(self.all_ingredients)} unique ingredients")
            print(f"   🏷️ Found {len(self.all_tags)} unique tags")

def main():
    scraper = DynamicSkincareScraper()
    
    print("🧴 Starting Dynamic Skincare Product Scraping...")
    print("This version automatically discovers categories and ingredients!")
    print("=" * 60)
    
    # Scrape products
    products = scraper.scrape_incidecoder_products(max_per_type=5)
    
    if products:
        print(f"\n✅ Successfully scraped {len(products)} products")
        
        # Analyze the scraped data to find patterns
        analysis_results = scraper.analyze_scraped_data(products)
        
        # Create dynamic features based on what we found
        featured_products = scraper.create_dynamic_features(products, analysis_results)
        
        # Save everything
        scraper.save_products(featured_products, analysis_results, 'dynamic_skincare_analysis')
        
        print("\n🎉 Dynamic analysis completed!")
        print("✨ Features were automatically generated based on the actual data found")
        print("📊 Check the JSON file for suggested features and analysis results")
        print("🔧 You can now modify the feature generation logic based on your needs")
        
    else:
        print("❌ No products were scraped successfully")

if __name__ == "__main__":
    main()