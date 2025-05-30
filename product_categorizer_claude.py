import json
import logging
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import re

'''Enhanced Cosmetic Product Categorizer

How the Script Categorizes Products
1. Ingredient-Based Rule Scoring
Each category (e.g., "Face Moisturizer", "Face Cleanser", etc.) has a set of rules:

*required_functions: e.g., "moisturizer/humectant", "emollient"
*key_ingredients: e.g., "hyaluronic acid", "glycerin"
*avoid_functions: e.g., "surfactant/cleansing" (optional)
*weight: how important this category is

For each product, the script:
*Counts matches between the product's ingredient functions and the category's required/avoid functions.
*Counts matches between the product's ingredient names and the category's key ingredients.
*Applies weights and bonuses/penalties for "beneficial" or "concerning" ingredients.
*Produces a score for each category.

2. Name-Based Matching
*Uses regex patterns and (optionally) fuzzy matching to look for category-specific keywords in the product title.
*If a regex match is found, it gives a high confidence score (e.g., 0.95).
*Fuzzy matching is a fallback if regex doesn't match.

3. NLP Zero-Shot Classification
*Uses a pre-trained NLP model (facebook/bart-large-mnli) to predict the category from the product title.
*Returns the top category and its confidence.

4. Combining Results
*If the NLP model's confidence is higher than the rule-based score and above 0.5, the NLP result is used.
*Otherwise, the rule-based result is used.
*The script also provides alternative categories and their scores.
'''

# Optional imports with fallbacks
try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    print("Warning: rapidfuzz not available, using basic string matching")
    RAPIDFUZZ_AVAILABLE = False

try:
    from transformers import pipeline
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    print("Warning: transformers not available, using rule-based classification only")
    TRANSFORMERS_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CategoryRule:
    """Data class for category classification rules"""
    required_functions: List[str]
    key_ingredients: List[str]
    avoid_functions: List[str] = None
    weight: float = 1.0
    min_confidence_threshold: float = 0.3

@dataclass
class CategorizationResult:
    """Data class for categorization results"""
    category: str
    confidence: float
    scores: Dict[str, float]
    reasoning: str
    ingredient_analysis: Dict[str, Any]
    alternative_categories: List[Tuple[str, float]] = None

class IngredientAnalyzer:
    """Separate class for ingredient analysis"""
    
    def __init__(self):
        # Common ingredient synonyms for better matching
        self.ingredient_synonyms = {
            'hyaluronic acid': ['sodium hyaluronate', 'hyaluronate'],
            'vitamin c': ['ascorbic acid', 'magnesium ascorbyl phosphate', 'sodium ascorbyl phosphate'],
            'retinol': ['retinyl palmitate', 'retinaldehyde', 'tretinoin'],
            'salicylic acid': ['bha', 'beta hydroxy acid'],
            'glycolic acid': ['aha', 'alpha hydroxy acid'],
            'exfoliant/scrub': ['scrub', 'exfoliant', 'peeling', 'microbeads', 'microdermabrasion'],
            # Add more as needed
        }
    
    def normalize_ingredient_name(self, ingredient_name: str) -> str:
        """Normalize ingredient names for better matching"""
        name = ingredient_name.lower().strip()
        # Check for synonyms
        for main_name, synonyms in self.ingredient_synonyms.items():
            if name in synonyms or any(syn in name for syn in synonyms):
                return main_name
        return name
    
    def analyze_ingredients(self, ingredients: List[Dict]) -> Dict[str, Any]:
        """Enhanced ingredient analysis with better categorization"""
        functions = []
        key_ingredients = []
        ratings = []
        concerns = []
        
        for ingredient in ingredients:
            # Extract functions
            if ingredient.get('what_it_does'):
                funcs = [f.strip().lower() for f in ingredient['what_it_does'].split(',')]
                functions.extend(funcs)
            
            # Normalize ingredient names
            ingredient_name = self.normalize_ingredient_name(
                ingredient.get('ingredient_name', '')
            )
            key_ingredients.append(ingredient_name)
            
            # Extract ratings and concerns
            if ingredient.get('id_rating'):
                ratings.append(ingredient['id_rating'])
            
            if ingredient.get('comedogen_rating'):
                if int(ingredient.get('comedogen_rating', 0)) > 2:
                    concerns.append('comedogenic')
        
        return {
            'functions': functions,
            'ingredients': key_ingredients,
            'ratings': ratings,
            'concerns': concerns,
            'function_counts': Counter(functions),
            'rating_counts': Counter(ratings),
            'total_ingredients': len(ingredients),
            'beneficial_ingredients': len([r for r in ratings if r in ['superstar', 'goodie']]),
            'concern_ingredients': len(concerns)
        }

class NameMatcher:
    """Separate class for product name matching"""
    
    def __init__(self):
        self.name_patterns = {
            'Face Moisturizer': [
                r'\b(face cream|facial moisturizer|day cream|night cream)\b',
                r'\b(hydrating cream|moisturizing cream|face lotion)\b',
                r'\b(anti-aging cream|firming cream)\b'
            ],
            'Face Cleanser': [
                r'\b(face wash|facial cleanser|cleansing gel|cleansing foam)\b',
                r'\b(micellar water|face soap|cleansing oil|makeup remover)\b'
            ],
            'Face Serum': [
                r'\b(face serum|facial serum|serum|essence)\b',
                r'\b(concentrate|drops|ampoule)\b'
            ],
            'Acne Treatment': [
                r'\b(acne treatment|spot treatment|blemish|acne cream)\b',
                r'\b(acne gel|anti-acne|pimple)\b'
            ],
            'Face Mask': [
                r'\b(face mask|facial mask|sheet mask|clay mask)\b',
                r'\b(mud mask|hydrogel mask|sleeping mask|peel-off)\b'
            ],
            'Exfoliant/Scrub': [
                r'\b(exfoliant|scrub|peeling|face scrub)\b',
                r'\b(exfoliating|chemical peel)\b'
            ],
            'Sunscreen': [
                r'\b(sunscreen|spf|sun protection|sunblock)\b',
                r'\b(uv protection|broad spectrum)\b'
            ],
            'Face Toner': [
                r'\b(toner|astringent|face mist|facial mist)\b',
                r'\b(essence water|refreshing water)\b'
            ],
            'Brightening Treatment': [
                r'\b(brightening|whitening|dark spot|pigmentation)\b',
                r'\b(vitamin c serum|radiance|glow)\b'
            ],
            # Hair care
            'Shampoo': [r'\b(shampoo|hair wash|cleansing shampoo)\b'],
            'Conditioner': [r'\b(conditioner|hair conditioner|rinse)\b'],
            'Hair Mask': [r'\b(hair mask|hair treatment mask|deep conditioning)\b'],
            'Hair Treatment': [r'\b(hair serum|hair oil|leave-in|scalp treatment)\b'],
            # Body care
            'Body Moisturizer': [r'\b(body lotion|body cream|body butter|hand cream)\b'],
            'Body Wash': [r'\b(body wash|shower gel|body soap|bath gel)\b']
        }
    
    def match_by_name(self, product_title: str, threshold: float = 0.8) -> Tuple[Optional[str], float]:
        """Enhanced name matching using regex patterns and fuzzy matching"""
        title_lower = product_title.lower()
        best_category = None
        best_score = 0
        
        # First try regex patterns
        for category, patterns in self.name_patterns.items():
            for pattern in patterns:
                if re.search(pattern, title_lower):
                    return category, 0.95  # High confidence for regex matches
        
        # Fallback to fuzzy matching if available
        if RAPIDFUZZ_AVAILABLE:
            simple_patterns = {
                'Face Moisturizer': ['face cream', 'facial moisturizer', 'day cream'],
                'Face Cleanser': ['face wash', 'facial cleanser', 'cleansing gel'],
                'Face Serum': ['face serum', 'facial serum', 'serum'],
                'Sunscreen': ['sunscreen', 'sun protection'],
                'Shampoo': ['shampoo'],
                'Conditioner': ['conditioner']
            }
            
            for category, patterns in simple_patterns.items():
                for pattern in patterns:
                    score = fuzz.partial_ratio(pattern, title_lower) / 100
                    if score > best_score and score >= threshold:
                        best_score = score
                        best_category = category
        
        return best_category, best_score

class NLPCategorizer:
    """Separate class for NLP-based categorization"""
    
    def __init__(self):
        self.model = None
        self.model_loaded = False
    
    def load_model(self):
        """Lazy loading of NLP model"""
        if not TRANSFORMERS_AVAILABLE:
            logger.warning("Transformers not available, skipping NLP categorization")
            return False
        
        if not self.model_loaded:
            try:
                logger.info("Loading NLP model...")
                self.model = pipeline(
                    "zero-shot-classification", 
                    model="facebook/bart-large-mnli",
                    device=0 if torch.cuda.is_available() else -1
                )
                self.model_loaded = True
                logger.info("NLP model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load NLP model: {e}")
                return False
        return True
    
    def categorize(self, text: str, categories: List[str]) -> Tuple[str, float, Dict[str, float]]:
        """NLP-based categorization"""
        if not self.load_model() or not self.model:
            return None, 0.0, {}
        
        try:
            result = self.model(text, categories)
            scores_dict = dict(zip(result['labels'], result['scores']))
            return result['labels'][0], result['scores'][0], scores_dict
        except Exception as e:
            logger.error(f"NLP categorization failed: {e}")
            return None, 0.0, {}

class CosmeticProductCategorizer:
    """Main categorizer class with improved architecture"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.ingredient_analyzer = IngredientAnalyzer()
        self.name_matcher = NameMatcher()
        self.nlp_categorizer = NLPCategorizer()
        
        # Load category rules
        if config_file:
            self.category_rules = self._load_config(config_file)
        else:
            self.category_rules = self._get_default_rules()
        
        self.category_names = list(self.category_rules.keys())
    
    def _get_default_rules(self) -> Dict[str, CategoryRule]:
        """Default category rules with improved structure"""
        return {
            'Face Moisturizer': CategoryRule(
                required_functions=['moisturizer/humectant', 'emollient'],
                key_ingredients=['hyaluronic acid', 'glycerin', 'ceramide', 'squalane'],
                avoid_functions=['surfactant/cleansing'],
                weight=1.0
            ),
            'Face Cleanser': CategoryRule(
                required_functions=['surfactant/cleansing'],
                key_ingredients=['sulfate', 'cleansing', 'foam', 'micellar'],
                avoid_functions=['moisturizer/humectant'],
                weight=1.2
            ),
            'Face Serum': CategoryRule(
                required_functions=['antioxidant', 'skin-identical ingredient', 'cell-communicating ingredient'],
                key_ingredients=['vitamin c', 'niacinamide', 'retinol', 'peptide', 'hyaluronic acid'],
                avoid_functions=['surfactant/cleansing', 'abrasive/scrub'],
                weight=1.1
            ),
            'Sunscreen': CategoryRule(
                required_functions=['sunscreen'],
                key_ingredients=['zinc oxide', 'titanium dioxide', 'avobenzone', 'spf'],
                weight=1.5,
                min_confidence_threshold=0.5
            ),
            'Acne Treatment': CategoryRule(
                required_functions=['anti-acne', 'antimicrobial/antibacterial', 'exfoliant'],
                key_ingredients=['salicylic acid', 'benzoyl peroxide', 'glycolic acid', 'tea tree'],
                weight=1.3
            ),
            # Add more categories as needed...
        }
    
    def _score_category(self, analysis: Dict, rule: CategoryRule) -> float:
        """Enhanced scoring with better logic"""
        score = 0
        
        # Function matching with partial matching
        for required_func in rule.required_functions:
            matches = sum(1 for func in analysis['functions'] 
                         if required_func.lower() in func.lower())
            score += matches * 2 * rule.weight
        
        # Key ingredient matching with normalized names
        for key_ingredient in rule.key_ingredients:
            matches = sum(1 for ingredient in analysis['ingredients'] 
                         if key_ingredient.lower() in ingredient.lower())
            score += matches * 1.5 * rule.weight
        
        # Penalty for avoided functions
        if rule.avoid_functions:
            for avoid_func in rule.avoid_functions:
                matches = sum(1 for func in analysis['functions'] 
                             if avoid_func.lower() in func.lower())
                score -= matches * 1.0 * rule.weight
        
        # Bonus for beneficial ingredients
        if analysis.get('beneficial_ingredients', 0) > 0:
            score += analysis['beneficial_ingredients'] * 0.5
        
        # Penalty for concerning ingredients
        if analysis.get('concern_ingredients', 0) > 0:
            score -= analysis['concern_ingredients'] * 0.3
        
        return max(0, score)
    
    def categorize_product(self, product: Dict) -> CategorizationResult:
        ingredient_analysis = self.ingredient_analyzer.analyze_ingredients(
            product.get('ingredients', [])
        )

        # 1. Name-based categorization (regex/fuzzy)
        name_category, name_confidence = self.name_matcher.match_by_name(
            product.get('product_title', '')
        )
        if name_category and name_confidence >= 0.7:
            return CategorizationResult(
                category=name_category,
                confidence=name_confidence,
                scores={name_category: name_confidence},
                reasoning="Name-based categorization (regex/fuzzy match)",
                ingredient_analysis=ingredient_analysis,
                alternative_categories=[]
            )

        # 2. NLP-based categorization (zero-shot)
        nlp_category, nlp_confidence, nlp_scores = self.nlp_categorizer.categorize(
            product.get('product_title', ''), self.category_names
        )
        if nlp_category and nlp_confidence >= 0.3:
            return CategorizationResult(
                category=nlp_category,
                confidence=nlp_confidence,
                scores=nlp_scores,
                reasoning="NLP zero-shot classification (title only)",
                ingredient_analysis=ingredient_analysis,
                alternative_categories=[(cat, score) for cat, score in nlp_scores.items() if cat != nlp_category and score > 0.1][:3]
            )

        # 3. Rule-based fallback (ingredients)
        category_scores = {}
        for category, rule in self.category_rules.items():
            category_scores[category] = self._score_category(ingredient_analysis, rule)
        if not category_scores or max(category_scores.values()) == 0:
            return CategorizationResult(
                category='Uncategorized',
                confidence=0.0,
                scores=category_scores,
                reasoning="Uncategorized: no confident match by name, NLP, or ingredients",
                ingredient_analysis=ingredient_analysis,
                alternative_categories=[]
            )
        sorted_scores = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
        rule_category = sorted_scores[0][0]
        rule_confidence = min(sorted_scores[0][1] / 10, 1.0)
        return CategorizationResult(
            category=rule_category,
            confidence=rule_confidence,
            scores=category_scores,
            reasoning="Rule-based fallback (ingredients)",
            ingredient_analysis=ingredient_analysis,
            alternative_categories=[(cat, score) for cat, score in sorted_scores[1:4] if score > 0]
        )
    
    def process_dataset(self, products_data: List[Dict]) -> List[Dict]:
        """Process entire dataset with progress tracking"""
        results = []
        total = len(products_data)
        
        logger.info(f"Processing {total} products...")
        
        for i, product in enumerate(products_data):
            if i % 50 == 0:
                logger.info(f"Processed {i}/{total} products")
            
            try:
                result = self.categorize_product(product)
                flagged = False

                # Compare NLP and rule-based (if both available)
                if result.reasoning == "NLP zero-shot classification (title only)":
                    # Optionally, run rule-based as well for comparison
                    ingredient_analysis = self.ingredient_analyzer.analyze_ingredients(product.get('ingredients', []))
                    category_scores = {cat: self._score_category(ingredient_analysis, rule) for cat, rule in self.category_rules.items()}
                    if category_scores:
                        rule_category = max(category_scores, key=category_scores.get)
                        if rule_category != result.category:
                            flagged = True

                categorized_product = {
                    'product_brand': product.get('product_brand', 'Unknown'),
                    'product_title': product.get('product_title', 'Unknown'),
                    'predicted_category': result.category,
                    'confidence': round(result.confidence, 3),
                    'category_scores': {k: round(v, 3) for k, v in result.scores.items()},
                    'reasoning': result.reasoning,
                    'total_ingredients': result.ingredient_analysis['total_ingredients'],
                    'key_functions': list(result.ingredient_analysis['function_counts'].keys())[:5],
                    'beneficial_ingredients': result.ingredient_analysis['beneficial_ingredients'],
                    'concern_ingredients': result.ingredient_analysis['concern_ingredients'],
                    'alternative_categories': result.alternative_categories[:2] if result.alternative_categories else [],
                    'flagged_for_review': flagged
                }
                results.append(categorized_product)
                
            except Exception as e:
                logger.error(f"Error processing product {i}: {e}")
                # Add error entry
                results.append({
                    'product_brand': product.get('product_brand', 'Unknown'),
                    'product_title': product.get('product_title', 'Unknown'),
                    'predicted_category': 'Error',
                    'confidence': 0.0,
                    'error': str(e)
                })
        
        logger.info(f"Completed processing {len(results)} products")
        return results
    
    def generate_insights(self, results: List[Dict]) -> Dict[str, Any]:
        """Generate comprehensive insights"""
        valid_results = [r for r in results if r['predicted_category'] != 'Error']
        
        categories = [r['predicted_category'] for r in valid_results]
        confidences = [r['confidence'] for r in valid_results]
        
        category_counts = Counter(categories)
        confidence_by_category = defaultdict(list)
        
        for result in valid_results:
            confidence_by_category[result['predicted_category']].append(result['confidence'])
        
        insights = {
            'total_products': len(results),
            'successfully_processed': len(valid_results),
            'errors': len(results) - len(valid_results),
            'category_distribution': dict(category_counts),
            'average_confidence': round(sum(confidences) / len(confidences), 3) if confidences else 0,
            'confidence_by_category': {
                cat: {
                    'avg': round(sum(confs) / len(confs), 3),
                    'min': round(min(confs), 3),
                    'max': round(max(confs), 3)
                }
                for cat, confs in confidence_by_category.items()
            },
            'high_confidence_products': len([r for r in valid_results if r['confidence'] > 0.7]),
            'low_confidence_products': len([r for r in valid_results if r['confidence'] < 0.3]),
            'uncategorized_products': category_counts.get('Uncategorized', 0)
        }
        
        return insights

def main():
    """Enhanced main function with better error handling"""
    try:
        # Load data
        data_file = "data/incidecoder_function_scrape.json"
        try:
            with open(data_file, "r", encoding="utf-8") as f:
                sample_data = json.load(f)
            logger.info(f"Loaded {len(sample_data)} products from {data_file}")
        except FileNotFoundError:
            logger.error(f"Data file not found: {data_file}")
            # Create sample data for testing
            sample_data = [
                {
                    "product_brand": "Test Brand",
                    "product_title": "Hydrating Face Moisturizer with Hyaluronic Acid",
                    "ingredients": [
                        {"ingredient_name": "Hyaluronic Acid", "what_it_does": "moisturizer/humectant", "id_rating": "superstar"},
                        {"ingredient_name": "Glycerin", "what_it_does": "moisturizer/humectant", "id_rating": "goodie"}
                    ]
                }
            ]
            logger.info("Using sample data for testing")
        
        # Initialize categorizer
        categorizer = CosmeticProductCategorizer()
        
        # Process products
        results = categorizer.process_dataset(sample_data)
        
        # Generate insights
        insights = categorizer.generate_insights(results)
        
        # Display results
        print("\n=== COSMETIC PRODUCT CATEGORIZATION RESULTS ===\n")
        
        for result in results[:10]:  # Show first 10 results
            print(f"Brand: {result['product_brand']}")
            print(f"Product: {result['product_title']}")
            print(f"Predicted Category: {result['predicted_category']}")
            print(f"Confidence: {result['confidence']}")
            
            if 'key_functions' in result:
                print(f"Key Functions: {', '.join(result['key_functions'])}")
            if 'beneficial_ingredients' in result:
                print(f"Beneficial Ingredients: {result['beneficial_ingredients']}")
            if 'alternative_categories' in result and result['alternative_categories']:
                alts = [f"{cat} ({score:.2f})" for cat, score in result['alternative_categories']]
                print(f"Alternative Categories: {', '.join(alts)}")
            
            print(f"Reasoning: {result.get('reasoning', 'N/A')}")
            print("-" * 60)
        
        # Display insights
        print("\n=== DATASET INSIGHTS ===")
        for key, value in insights.items():
            if isinstance(value, dict):
                print(f"{key.replace('_', ' ').title()}:")
                for sub_key, sub_value in value.items():
                    print(f"  {sub_key}: {sub_value}")
            else:
                print(f"{key.replace('_', ' ').title()}: {value}")
        
        # Save results
        output_file = "categorized_products_enhanced.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                'results': results,
                'insights': insights,
                'metadata': {
                    'total_processed': len(results),
                    'nlp_available': TRANSFORMERS_AVAILABLE,
                    'fuzzy_matching_available': RAPIDFUZZ_AVAILABLE
                }
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to {output_file}")
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        raise

if __name__ == "__main__":
    main()