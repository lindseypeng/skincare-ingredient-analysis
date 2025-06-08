import json
from typing import Dict, List
from sklearn.metrics import confusion_matrix, classification_report, precision_recall_fscore_support
from sklearn.model_selection import KFold
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime

def load_json_file(file_path: str) -> Dict:
    """Load and parse a JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def calculate_class_distribution(categories: List[str]) -> Dict:
    """Calculate distribution of categories to check for class imbalance."""
    total = len(categories)
    distribution = {}
    for category in set(categories):
        count = categories.count(category)
        distribution[category] = {
            'count': count,
            'percentage': count/total * 100
        }
    return distribution

def calculate_categorization_accuracy(gold_standard: Dict, predictions: Dict) -> Dict:
    """
    Calculate comprehensive accuracy metrics for the categorization algorithm.
    """
    true_categories = []
    pred_categories = []
    confidences = []
    
    total_samples = 0
    correct_predictions = 0
    category_matches = {}
    
    # Collect predictions and actual categories
    for sample in gold_standard['results']:
        if not isinstance(sample, dict) or 'manual_category' not in sample:
            continue
            
        total_samples += 1
        predicted = sample.get('predicted_category', '')
        manual = sample.get('manual_category', '')
        confidence = sample.get('confidence', 0)
        
        # Handle multiple manual categories
        manual_categories = [cat.strip() for cat in manual.split(',')] if ',' in manual else [manual]
        
        # Check if predicted category matches any of the manual categories
        is_correct = predicted in manual_categories
        if is_correct:
            correct_predictions += 1
            
        # For confusion matrix, use first manual category
        primary_manual_category = manual_categories[0]
        true_categories.append(primary_manual_category)
        pred_categories.append(predicted)
        confidences.append(confidence)
        
        # Track category-specific accuracy
        if primary_manual_category not in category_matches:
            category_matches[primary_manual_category] = {'correct': 0, 'total': 0}
        
        category_matches[primary_manual_category]['total'] += 1
        if is_correct:
            category_matches[primary_manual_category]['correct'] += 1

    # Calculate metrics
    overall_accuracy = correct_predictions / total_samples if total_samples > 0 else 0
    category_accuracy = {
        category: {
            'accuracy': stats['correct'] / stats['total'],
            'total_samples': stats['total']
        }
        for category, stats in category_matches.items()
    }
    
    # Calculate confusion matrix
    unique_categories = sorted(list(set(true_categories + pred_categories)))
    conf_matrix = confusion_matrix(true_categories, pred_categories, labels=unique_categories)
    
    # Calculate average confidence
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
    
    # Generate classification report
    class_report = classification_report(true_categories, pred_categories, output_dict=True)
    
    # Plot confusion matrix
    plt.figure(figsize=(12, 8))
    sns.heatmap(conf_matrix, annot=True, fmt='d', 
                xticklabels=unique_categories, 
                yticklabels=unique_categories)
    plt.title('Confusion Matrix')
    plt.xlabel('Predicted Category')
    plt.ylabel('True Category')
    plt.tight_layout()
    plt.savefig('confusion_matrix.png')
    plt.close()

    # Add class distribution analysis
    category_distribution = calculate_class_distribution(true_categories)
    
    # Calculate precision, recall, and F1 scores per category
    precision, recall, f1, support = precision_recall_fscore_support(
        true_categories, 
        pred_categories, 
        average=None,
        labels=unique_categories
    )
    
    # Convert numpy types to Python native types for JSON serialization
    detailed_metrics = {
        str(cat): {
            'precision': float(p),
            'recall': float(r),
            'f1': float(f),
            'support': int(s)
        } for cat, p, r, f, s in zip(unique_categories, precision, recall, f1, support)
    }

    return {
        'overall_accuracy': float(overall_accuracy),
        'total_samples': int(total_samples),
        'correct_predictions': int(correct_predictions),
        'category_accuracy': category_accuracy,
        'average_confidence': float(avg_confidence),
        'confusion_matrix': conf_matrix.tolist(),
        'classification_report': class_report,
        'category_distribution': category_distribution,
        'detailed_metrics': detailed_metrics,
        'timestamp': datetime.now().isoformat()
    }

def main():
    # Load the JSON files
    gold_standard = load_json_file('gold_standard_sample.json')
    predictions = load_json_file('categorized_products_enhanced.json')
    
    # Calculate accuracy metrics
    results = calculate_categorization_accuracy(gold_standard, predictions)
    
    # Print enhanced results
    print("\nCategorization Accuracy Results")
    print("==============================")
    print(f"Overall Accuracy: {results['overall_accuracy']:.2%}")
    print(f"Total Samples: {results['total_samples']}")
    print(f"Correct Predictions: {results['correct_predictions']}")
    print(f"Average Confidence: {results['average_confidence']:.2%}")
    
    print("\nCategory Distribution:")
    print("---------------------")
    for category, stats in results['category_distribution'].items():
        print(f"{category}: {stats['count']} samples ({stats['percentage']:.1f}%)")
    
    print("\nDetailed Metrics per Category:")
    print("-----------------------------")
    for category, metrics in results['detailed_metrics'].items():
        print(f"\n{category}:")
        print(f"  Precision: {metrics['precision']:.2%}")
        print(f"  Recall: {metrics['recall']:.2%}")
        print(f"  F1 Score: {metrics['f1']:.2%}")
        print(f"  Support: {metrics['support']}")

    # Save detailed results
    with open('accuracy_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\nDetailed results saved to 'accuracy_results.json'")
    print("Confusion matrix plot saved as 'confusion_matrix.png'")

if __name__ == "__main__":
    main()