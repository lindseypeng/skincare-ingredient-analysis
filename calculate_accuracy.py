import json
from typing import Dict, List

def load_json_file(file_path: str) -> Dict:
    """Load and parse a JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def calculate_categorization_accuracy(gold_standard: Dict, predictions: Dict) -> Dict:
    """
    Calculate accuracy metrics for the categorization algorithm.
    
    Args:
        gold_standard: Dictionary containing manually labeled data
        predictions: Dictionary containing algorithm predictions
    
    Returns:
        Dictionary containing accuracy metrics
    """
    total_samples = 0
    correct_predictions = 0
    category_matches: Dict[str, Dict[str, int]] = {}  # Track matches by category
    
    # Create lookup dictionary for predictions
    pred_lookup = {
        f"{p.get('product_brand', '')}-{p.get('product_title', '')}": p.get('predicted_category', '')
        for p in predictions['results']
        if isinstance(p, dict) and 'product_brand' in p
    }

    for sample in gold_standard['results']:
        if not isinstance(sample, dict) or 'manual_category' not in sample:
            continue
            
        total_samples += 1
        product_key = f"{sample.get('product_brand', '')}-{sample.get('product_title', '')}"
        predicted = sample.get('predicted_category', '')
        manual = sample.get('manual_category', '')
        
        # Handle multiple manual categories
        manual_categories = [cat.strip() for cat in manual.split(',')] if ',' in manual else [manual]
        
        # Check if predicted category matches any of the manual categories
        is_correct = predicted in manual_categories
        if is_correct:
            correct_predictions += 1
            
        # Track category-specific accuracy
        primary_manual_category = manual_categories[0]  # Use first category as primary
        if primary_manual_category not in category_matches:
            category_matches[primary_manual_category] = {'correct': 0, 'total': 0}
        
        category_matches[primary_manual_category]['total'] += 1
        if is_correct:
            category_matches[primary_manual_category]['correct'] += 1

    # Calculate overall accuracy and per-category accuracy
    overall_accuracy = correct_predictions / total_samples if total_samples > 0 else 0
    category_accuracy = {
        category: {'accuracy': stats['correct'] / stats['total'], 'total_samples': stats['total']}
        for category, stats in category_matches.items()
    }

    return {
        'overall_accuracy': overall_accuracy,
        'total_samples': total_samples,
        'correct_predictions': correct_predictions,
        'category_accuracy': category_accuracy
    }

def main():
    # Load the JSON files
    gold_standard = load_json_file('gold_standard_sample.json')
    predictions = load_json_file('categorized_products_enhanced.json')
    
    # Calculate accuracy metrics
    results = calculate_categorization_accuracy(gold_standard, predictions)
    
    # Print results
    print("\nCategorization Accuracy Results")
    print("==============================")
    print(f"Overall Accuracy: {results['overall_accuracy']:.2%}")
    print(f"Total Samples: {results['total_samples']}")
    print(f"Correct Predictions: {results['correct_predictions']}")
    
    print("\nPer-Category Accuracy:")
    print("---------------------")
    for category, stats in results['category_accuracy'].items():
        print(f"{category}: {stats['accuracy']:.2%} ({stats['total_samples']} samples)")

if __name__ == "__main__":
    main()