import json
import random
from collections import defaultdict
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_all_categories(data):
    """Extract all unique categories from the dataset"""
    return set(product['predicted_category'] for product in data['results'])

def create_gold_standard_sample(input_file='categorized_products_enhanced.json', 
                              output_file='gold_standard_sample.json',
                              sample_size=75):
    """
    Create a balanced sample for gold standard manual categorization
    Keeps all original fields and adds manual_category field
    """
    try:
        # Load original data
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Group products by predicted category
        products_by_category = defaultdict(list)
        for product in data['results']:
            products_by_category[product['predicted_category']].append(product)
        
        # Get all unique categories
        categories = list(products_by_category.keys())
        logger.info(f"Found {len(categories)} unique categories: {', '.join(categories)}")
        
        # Calculate samples per category
        samples_per_category = sample_size // len(categories)
        remainder = sample_size % len(categories)
        logger.info(f"Will sample approximately {samples_per_category} products per category")
        
        # Sample products from each category
        gold_standard = []
        category_counts = {}
        
        for category in categories:
            category_products = products_by_category[category]
            # Take minimum between available products and desired samples
            n_samples = min(samples_per_category + (1 if remainder > 0 else 0), 
                          len(category_products))
            remainder = max(0, remainder - 1)
            
            sampled_products = random.sample(category_products, n_samples)
            category_counts[category] = n_samples
            
            # Add manual_category field while preserving all original fields
            for product in sampled_products:
                product_copy = dict(product)  # Create a copy to avoid modifying original
                product_copy['manual_category'] = ""  # Add empty manual_category field
                gold_standard.append(product_copy)
        
        # Save to new file with metadata
        output_data = {
            'metadata': {
                'total_samples': len(gold_standard),
                'sampling_date': datetime.now().isoformat(),
                'category_distribution': category_counts
            },
            'results': gold_standard
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        # Print summary
        logger.info(f"Created gold standard sample with {len(gold_standard)} products")
        logger.info("Category distribution:")
        for category, count in category_counts.items():
            logger.info(f"- {category}: {count}")
            
    except Exception as e:
        logger.error(f"Error creating gold standard sample: {e}")
        raise

def process_dataset(self, products_data, nlp_model=None):
    """Process multiple products and create gold standard sample with manual_category field."""
    results = []
    for product in products_data:
        result = self.categorize_product(product, nlp_model)
        
        # Create product entry with reordered fields
        categorized_product = {
            'product_brand': product['product_brand'],
            'product_title': product['product_title'],
            'predicted_category': result.category,
            'manual_category': "",  # Empty field for manual annotation
            'confidence': result.confidence,
            'category_scores': result.scores,
            'reasoning': result.reasoning,
            'total_ingredients': len(product['ingredients']),
            'ingredients': [
                {
                    'name': ingredient.get('ingredient_name', ''),
                    'functions': ingredient.get('what_it_does', '').split(',') if ingredient.get('what_it_does') else [],
                    'irritancy_comedogenicity': ingredient.get('irritancy/comedogenicity', ''),
                    'id_rating': ingredient.get('id_rating', '')
                }
                for ingredient in product['ingredients']
            ],
            'key_functions': list(result.ingredient_analysis['function_counts'].keys()),
            'beneficial_ingredients': result.ingredient_analysis['rating_counts'].get('superstar', 0),
            'concern_ingredients': result.ingredient_analysis.get('concern_ingredients', 0),
            'alternative_categories': result.alternative_categories or [],
            'flagged_for_review': False
        }
        results.append(categorized_product)
    return results

if __name__ == "__main__":
    create_gold_standard_sample()