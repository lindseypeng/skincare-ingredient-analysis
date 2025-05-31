import json
from collections import Counter
from rapidfuzz import fuzz

# Add these imports for NLP
from transformers import pipeline

class SkincareProductCategorizer:
    def __init__(self):
        # Define categorization rules based on ingredient functionalities
        self.category_rules = {
            'Face Moisturizer': {
                'required_functions': ['moisturizer/humectant', 'emollient'],
                'key_ingredients': ['hyaluronic acid', 'glycerin', 'ceramide', 'cholesterol', 'squalane'],
                'avoid_functions': ['surfactant/cleansing'],
                'weight': 1.0
            },
            'Face Cleanser': {
                'required_functions': ['surfactant/cleansing'],
                'key_ingredients': ['sulfate', 'cleansing', 'foam', 'micellar'],
                'avoid_functions': ['moisturizer/humectant'],
                'weight': 1.2
            },
            'Face Serum': {
                'required_functions': ['antioxidant', 'skin-identical ingredient', 'cell-communicating ingredient'],
                'key_ingredients': ['vitamin c', 'niacinamide', 'retinol', 'peptide', 'hyaluronic acid'],
                'avoid_functions': ['surfactant/cleansing', 'abrasive/scrub'],
                'weight': 1.1
            },
            'Acne Treatment': {
                'required_functions': ['anti-acne', 'antimicrobial/antibacterial', 'exfoliant'],
                'key_ingredients': ['salicylic acid', 'benzoyl peroxide', 'glycolic acid', 'tea tree'],
                'weight': 1.3
            },
            'Face Mask': {
                'required_functions': ['absorbent/mattifier', 'moisturizer/humectant', 'soothing'],
                'key_ingredients': ['clay', 'charcoal', 'sheet mask', 'hydrogel'],
                'weight': 1.2
            },
            'Exfoliant/Scrub': {
                'required_functions': ['abrasive/scrub', 'exfoliant'],
                'key_ingredients': ['glycolic acid', 'lactic acid', 'scrub', 'beads'],
                'weight': 1.4
            },
            'Sunscreen': {
                'required_functions': ['sunscreen'],
                'key_ingredients': ['zinc oxide', 'titanium dioxide', 'avobenzone', 'spf'],
                'weight': 1.5
            },
            'Face Toner': {
                'required_functions': ['astringent', 'buffering', 'soothing'],
                'key_ingredients': ['witch hazel', 'rose water', 'toner', 'essence'],
                'avoid_functions': ['emollient', 'surfactant/cleansing'],
                'weight': 1.1
            },
            'Brightening Treatment': {
                'required_functions': ['skin brightening', 'antioxidant'],
                'key_ingredients': ['vitamin c', 'kojic acid', 'arbutin', 'niacinamide'],
                'weight': 1.2
            },
            # HAIR CARE PRODUCTS
            'Shampoo': {
                'required_functions': ['surfactant/cleansing', 'deodorant'],
                'key_ingredients': ['sulfate', 'shampoo', 'cleansing', 'foam'],
                'avoid_functions': ['emollient', 'moisturizer/humectant'],
                'weight': 1.3
            },
            'Conditioner': {
                'required_functions': ['emollient', 'moisturizer/humectant', 'emulsion stabilising'],
                'key_ingredients': ['conditioner', 'silicone', 'protein', 'keratin'],
                'avoid_functions': ['surfactant/cleansing'],
                'weight': 1.2
            },
            'Hair Mask': {
                'required_functions': ['moisturizer/humectant', 'emollient'],
                'key_ingredients': ['hair mask', 'deep conditioning', 'protein', 'oil'],
                'weight': 1.3
            },
            'Hair Treatment': {
                'required_functions': ['cell-communicating ingredient', 'antioxidant'],
                'key_ingredients': ['serum', 'oil', 'leave-in', 'treatment'],
                'weight': 1.2
            },
            # BODY CARE PRODUCTS
            'Body Moisturizer': {
                'required_functions': ['moisturizer/humectant', 'emollient'],
                'key_ingredients': ['body lotion', 'body cream', 'butter', 'oil'],
                'weight': 1.0
            },
            'Body Wash': {
                'required_functions': ['surfactant/cleansing', 'deodorant'],
                'key_ingredients': ['body wash', 'shower gel', 'soap'],
                'weight': 1.1
            }
        }

        self.name_patterns = {
            'Face Moisturizer': ['face cream', 'facial moisturizer', 'day cream', 'night cream', 
                               'hydrating cream', 'moisturizing cream', 'face lotion'],
            'Face Cleanser': ['face wash', 'facial cleanser', 'cleansing gel', 'cleansing foam', 
                            'micellar water', 'face soap', 'cleansing oil'],
            'Face Serum': ['face serum', 'facial serum', 'serum', 'essence', 'concentrate', 'drops'],
            'Acne Treatment': ['acne treatment', 'spot treatment', 'blemish', 'acne cream', 'acne gel'],
            'Face Mask': ['face mask', 'facial mask', 'sheet mask', 'clay mask', 'mud mask', 
                         'hydrogel mask', 'sleeping mask'],
            'Exfoliant/Scrub': ['exfoliant', 'scrub', 'peeling', 'face scrub', 'exfoliating'],
            'Sunscreen': ['sunscreen', 'spf', 'sun protection', 'sunblock', 'uv protection'],
            'Face Toner': ['toner', 'astringent', 'face mist', 'facial mist', 'essence water'],
            'Brightening Treatment': ['brightening', 'whitening', 'dark spot', 'pigmentation', 
                                    'vitamin c serum'],
            # HAIR CARE
            'Shampoo': ['shampoo', 'hair wash', 'cleansing shampoo'],
            'Conditioner': ['conditioner', 'hair conditioner', 'rinse'],
            'Hair Mask': ['hair mask', 'hair treatment mask', 'deep conditioning', 'hair pack'],
            'Hair Treatment': ['hair serum', 'hair oil', 'leave-in', 'hair treatment', 
                             'hair essence', 'scalp treatment'],
            # BODY CARE
            'Body Moisturizer': ['body lotion', 'body cream', 'body butter', 'body oil', 
                               'hand cream', 'foot cream'],
            'Body Wash': ['body wash', 'shower gel', 'body soap', 'bath gel']
        }

    def analyze_ingredients(self, ingredients):
        functions = []
        key_ingredients = []
        ratings = []
        for ingredient in ingredients:
            if ingredient.get('what_it_does'):
                functions.extend([f.strip() for f in ingredient['what_it_does'].split(',')])
            ingredient_name = ingredient.get('ingredient_name', '').lower()
            key_ingredients.append(ingredient_name)
            if ingredient.get('id_rating'):
                ratings.append(ingredient['id_rating'])
        return {
            'functions': functions,
            'ingredients': key_ingredients,
            'ratings': ratings,
            'function_counts': Counter(functions),
            'rating_counts': Counter(ratings)
        }

    def score_category(self, product_analysis, category_name, category_rules):
        score = 0
        for required_func in category_rules['required_functions']:
            if any(required_func in func for func in product_analysis['functions']):
                score += 2 * category_rules['weight']
        for key_ingredient in category_rules['key_ingredients']:
            if any(key_ingredient in ingredient for ingredient in product_analysis['ingredients']):
                score += 1.5 * category_rules['weight']
        if 'avoid_functions' in category_rules:
            for avoid_func in category_rules['avoid_functions']:
                if any(avoid_func in func for func in product_analysis['functions']):
                    score -= 1.0 * category_rules['weight']
        return max(0, score)

    def categorize_by_name(self, product_title, threshold=80):
        title_lower = product_title.lower()
        best_category = None
        best_score = 0
        for category, patterns in self.name_patterns.items():
            for pattern in patterns:
                score = fuzz.partial_ratio(pattern, title_lower)
                if score > best_score and score >= threshold:
                    best_score = score
                    best_category = category
        if best_category:
            return best_category, best_score / 100.0
        return None, 0

    def categorize_product(self, product, nlp_model=None):
        ingredient_analysis = self.analyze_ingredients(product['ingredients'])
        category_scores = {}
        for category, rules in self.category_rules.items():
            category_scores[category] = self.score_category(ingredient_analysis, category, rules)
        name_category, name_confidence = self.categorize_by_name(product['product_title'])
        if name_category:
            category_scores[name_category] = category_scores.get(name_category, 0) + (2 * name_confidence)
        # Rule-based result
        if not category_scores or max(category_scores.values()) == 0:
            rule_category = 'Uncategorized'
            rule_confidence = 0.0
        else:
            best_category = max(category_scores.items(), key=lambda x: x[1])
            rule_category = best_category[0]
            rule_confidence = min(best_category[1] / 10, 1.0)
        # NLP result
        nlp_category, nlp_conf, nlp_scores = nlp_categorize_product(
            product['product_title'],
            list(self.category_rules.keys()),
            model=nlp_model
        )
        # Use NLP if its confidence is higher
        if nlp_conf > rule_confidence:
            return {
                'category': nlp_category,
                'confidence': nlp_conf,
                'scores': nlp_scores,
                'reasoning': 'NLP zero-shot classification (title only)',
                'ingredient_analysis': ingredient_analysis
            }
        else:
            return {
                'category': rule_category,
                'confidence': rule_confidence,
                'scores': category_scores,
                'reasoning': f"Classified based on ingredient functions and product name",
                'ingredient_analysis': ingredient_analysis
            }

    def process_dataset(self, products_data, nlp_model=None):
        results = []
        for product in products_data:
            result = self.categorize_product(product, nlp_model=nlp_model)
            categorized_product = {
                'product_brand': product['product_brand'],
                'product_title': product['product_title'],
                'predicted_category': result['category'],
                'confidence': result['confidence'],
                'category_scores': result['scores'],
                'reasoning': result['reasoning'],
                'total_ingredients': len(product['ingredients']),
                'key_functions': list(result['ingredient_analysis']['function_counts'].keys()),
                'superstar_ingredients': result['ingredient_analysis']['rating_counts'].get('superstar', 0),
                'goodie_ingredients': result['ingredient_analysis']['rating_counts'].get('goodie', 0)
            }
            results.append(categorized_product)
        return results

    def generate_insights(self, results):
        categories = [r['predicted_category'] for r in results]
        category_counts = Counter(categories)
        avg_confidence = sum(r['confidence'] for r in results) / len(results)
        insights = {
            'total_products': len(results),
            'category_distribution': dict(category_counts),
            'average_confidence': avg_confidence,
            'high_confidence_products': len([r for r in results if r['confidence'] > 0.7]),
            'uncategorized_products': category_counts.get('Uncategorized', 0)
        }
        return insights

# NLP helper function
def nlp_categorize_product(title, categories, model=None):
    if model is None:
        model = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
    result = model(title, categories)
    return result['labels'][0], result['scores'][0], dict(zip(result['labels'], result['scores']))

def main():
    with open("data/incidecoder_function_scrape.json", "r", encoding="utf-8") as f:
        sample_data = json.load(f)
    categorizer = SkincareProductCategorizer()
    print("Loading NLP model (this may take a minute)...")
    nlp_model = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
    results = categorizer.process_dataset(sample_data, nlp_model=nlp_model)
    print("=== SKINCARE PRODUCT CATEGORIZATION RESULTS ===\n")
    for result in results:
        print(f"Brand: {result['product_brand']}")
        print(f"Product: {result['product_title']}")
        print(f"Predicted Category: {result['predicted_category']}")
        print(f"Confidence: {result['confidence']:.2f}")
        print(f"Key Functions: {', '.join(result['key_functions'][:5])}")
        print(f"Superstar Ingredients: {result['superstar_ingredients']}")
        print(f"Goodie Ingredients: {result['goodie_ingredients']}")
        print(f"Reasoning: {result['reasoning']}")
        print("-" * 50)
    insights = categorizer.generate_insights(results)
    print("\n=== DATASET INSIGHTS ===")
    print(f"Total Products: {insights['total_products']}")
    print(f"Category Distribution: {insights['category_distribution']}")
    print(f"Average Confidence: {insights['average_confidence']:.2f}")
    print(f"High Confidence Products: {insights['high_confidence_products']}")
    with open("categorized_products.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()