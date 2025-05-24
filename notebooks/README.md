# Cosmetic Product Ingredients Analysis

This project provides tools to scrape, process, and analyze cosmetic product ingredients from IncideCoder.com. It's designed to help you build a dataset for machine learning projects focused on cosmetic product analysis.

## Components

The project consists of three main components:

1. **IncideCoder Scraper (`incidecoder_scraper.py`)** - Scrapes product information from IncideCoder.com, including names, brands, ingredients, and product attributes.

2. **Scraper CLI (`scraper_cli.py`)** - A command-line interface for the scraper that makes it easy to configure and run scraping jobs.

3. **Cosmetic Data Processor (`cosmetic_data_processor.py`)** - Analyzes the scraped data to extract insights about ingredients, product types, and relationships between products.

## Setup

1. Install the required Python packages:

```bash
pip install requests beautifulsoup4 pandas numpy matplotlib seaborn
```

2. Make sure all three Python files are in the same directory.

## Usage

### Scraping Data

To scrape data from IncideCoder.com, use the scraper CLI:

```bash
python scraper_cli.py
```

This will scrape product information from the default categories (moisturizer, serum, cleanser, mask) with default settings.

#### Customizing the Scraping Process

You can customize the scraping process with various command-line arguments:

```bash
python scraper_cli.py --categories moisturizer serum --max-pages 3 --max-products 50 --output-csv my_dataset.csv --output-json my_dataset.json --delay-min 2 --delay-max 5
```

Available options:
- `--categories`: Product categories to scrape (default: moisturizer, serum, cleanser, mask)
- `--max-pages`: Maximum number of pages to scrape per category (default: 5)
- `--max-products`: Maximum number of products to scrape per category (default: 100)
- `--output-csv`: Filename for CSV output (default: incidecoder_products.csv)
- `--output-json`: Filename for JSON output (default: incidecoder_products.json)
- `--load-json`: Load previous results from JSON file (optional)
- `--delay-min`: Minimum delay between requests in seconds (default: 1.0)
- `--delay-max`: Maximum delay between requests in seconds (default: 3.0)

### Analyzing Data

Once you have scraped the data, you can use the Cosmetic Data Processor to analyze it:

```python
from cosmetic_data_processor import CosmeticDataProcessor

# Load and process data
processor = CosmeticDataProcessor('incidecoder_products.json')

# Get top ingredients
top_ingredients = processor.get_top_ingredients(20)
print("Top 20 most common ingredients:")
print(top_ingredients)

# Find products with a specific ingredient
products_with_ingredient = processor.get_products_with_ingredient('Hyaluronic Acid')
print(f"Found {len(products_with_ingredient)} products with Hyaluronic Acid")

# Plot top ingredients
processor.plot_top_ingredients(15)

# Find similar products to a reference product
if len(processor.products) > 0:
    reference_product_id = processor.products.iloc[0].id
    similar_products = processor.find_similar_products(reference_product_id)
    print(f"Products similar to {processor.products.iloc[0].name}:")
    print(similar_products)
```

## Data Structure

The scraped data includes the following information for each product:

- `id`: Unique identifier
- `name`: Product name
- `brand`: Brand name
- `type`: Product type (e.g., moisturizer, serum)
- `image`: URL to product image
- `ingredients`: List of ingredients
- `safety`: Safety rating
- `oily`, `dry`, `sensitive`: Boolean flags for skin type suitability
- `comedogenic`, `acne_fighting`, `anti_aging`, `brightening`, `uv`: Boolean flags for product functionality
- `url`: URL to the product page on IncideCoder.com
- `raw_ingredients_text`: Raw text of ingredients from the product page

## Machine Learning Project Ideas

With this dataset, you can build various machine learning models:

1. **Ingredient Similarity Analysis**: Find products with similar ingredients
2. **Product Classification**: Predict product type based on ingredients
3. **Function Prediction**: Predict product functionality (anti-aging, acne-fighting, etc.) based on ingredients
4. **Brand Ingredient Patterns**: Analyze ingredient patterns by brand
5. **Ingredient Networks**: Build a network of related ingredients to understand co-occurrence patterns
6. **Duplicate Detection**: Identify similar/duplicate products across different brands

## Ethical Considerations

When scraping websites, be considerate of the website's resources:

1. Use reasonable delays between requests (1-3 seconds is a good rule of thumb)
2. Don't scrape more data than you need
3. Respect the website's robots.txt file and terms of service
4. Consider reaching out to the website owners if you plan to do extensive scraping

## Next Steps

1. Clean and preprocess the ingredients data
2. Normalize ingredient names (handling synonyms and variations)
3. Apply machine learning techniques to your cleaned dataset
4. Consider adding sentiment analysis from product reviews
5. Create visualizations and dashboards for your findings
