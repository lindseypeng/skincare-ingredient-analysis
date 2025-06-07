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
        
        categories = list(products_by_category.keys())
        logger.info(f"Found {len(categories)} unique categories: {', '.join(categories)}")
        
        # Calculate minimum samples per category to reach total sample_size
        base_samples = sample_size // len(categories)
        extra_samples = sample_size % len(categories)
        
        gold_standard = []
        category_counts = {}
        
        # Sample products from each category
        for category in categories:
            category_products = products_by_category[category]
            n_samples = base_samples + (1 if extra_samples > 0 else 0)
            extra_samples = max(0, extra_samples - 1)
            
            # Ensure we don't try to sample more than available
            n_samples = min(n_samples, len(category_products))
            sampled_products = random.sample(category_products, n_samples)
            category_counts[category] = n_samples
            
            for product in sampled_products:
                # Create new product dict with reordered fields
                new_product = {
                    'product_brand': product['product_brand'],
                    'product_title': product['product_title'],
                    'predicted_category': product['predicted_category'],
                    'manual_category': "",  # Place manual_category right after predicted_category
                    'confidence': product['confidence'],
                    'category_scores': product['category_scores'],
                    'reasoning': product['reasoning'],
                    'total_ingredients': product['total_ingredients'],
                    'ingredients': product['ingredients'],
                    'key_functions': product['key_functions'],
                    'beneficial_ingredients': product.get('beneficial_ingredients', 0),
                    'concern_ingredients': product.get('concern_ingredients', 0),
                    'alternative_categories': product.get('alternative_categories', []),
                    'flagged_for_review': product.get('flagged_for_review', False)
                }
                gold_standard.append(new_product)
        
        # If we still need more samples to reach 75, add from categories with most products
        remaining = sample_size - len(gold_standard)
        if remaining > 0:
            # Sort categories by number of remaining products
            categories_by_size = sorted(
                [(cat, len(products_by_category[cat])) for cat in categories],
                key=lambda x: x[1],
                reverse=True
            )
            
            for category, _ in categories_by_size:
                if remaining <= 0:
                    break
                    
                unused_products = [p for p in products_by_category[category] 
                                 if p not in sampled_products]
                if unused_products:
                    product = random.choice(unused_products)
                    new_product = {
                        'product_brand': product['product_brand'],
                        'product_title': product['product_title'],
                        'predicted_category': product['predicted_category'],
                        'manual_category': "",
                        'confidence': product['confidence'],
                        'category_scores': product['category_scores'],
                        'reasoning': product['reasoning'],
                        'total_ingredients': product['total_ingredients'],
                        'ingredients': product['ingredients'],
                        'key_functions': product['key_functions'],
                        'beneficial_ingredients': product.get('beneficial_ingredients', 0),
                        'concern_ingredients': product.get('concern_ingredients', 0),
                        'alternative_categories': product.get('alternative_categories', []),
                        'flagged_for_review': product.get('flagged_for_review', False)
                    }
                    gold_standard.append(new_product)
                    category_counts[category] += 1
                    remaining -= 1
        
        # Save to file with metadata
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