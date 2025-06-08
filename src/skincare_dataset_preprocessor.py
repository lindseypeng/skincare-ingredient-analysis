import json
import pandas as pd
import numpy as np
from collections import Counter, defaultdict
import re

class SkincareMLPreprocessor:
    def __init__(self):
        # All possible functions from your data
        self.all_functions = [
            'abrasive/scrub', 'absorbent/mattifier', 'anti-acne', 'antimicrobial/antibacterial',
            'antioxidant', 'astringent', 'buffering', 'cell-communicating ingredient',
            'chelating', 'colorant', 'deodorant', 'emollient', 'emulsifying',
            'emulsion stabilising', 'exfoliant', 'moisturizer/humectant', 'perfuming',
            'preservative', 'skin brightening', 'skin-identical ingredient', 'solvent',
            'soothing', 'sunscreen', 'surfactant/cleansing', 'viscosity controlling'
        ]
        
        # ID ratings
        self.id_ratings = ['superstar', 'goodie', 'icky']
        
    def parse_irritancy_comedogenicity(self, value):
        """Parse irritancy/comedogenicity values like '0,0', '1,2', '0-3,0-3'"""
        if not value or value == "":
            return None, None
        
        try:
            parts = value.split(',')
            if len(parts) == 2:
                # Handle ranges like '0-3'
                irritancy = parts[0].strip()
                comedogenicity = parts[1].strip()
                
                # Extract numeric values (take max if range)
                if '-' in irritancy:
                    irr_vals = [int(x) for x in irritancy.split('-')]
                    irritancy_score = max(irr_vals)
                else:
                    irritancy_score = int(irritancy)
                
                if '-' in comedogenicity:
                    com_vals = [int(x) for x in comedogenicity.split('-')]
                    comedogenicity_score = max(com_vals)
                else:
                    comedogenicity_score = int(comedogenicity)
                
                return irritancy_score, comedogenicity_score
        except:
            return None, None
        
        return None, None
    
    def extract_product_features(self, product):
        """Extract comprehensive features from a single product"""
        features = {
            'product_brand': product['product_brand'],
            'product_title': product['product_title'],
            'predicted_category': product['predicted_category'],
            'confidence': product['confidence'],
            'total_ingredients': product['total_ingredients']
        }
        
        # Initialize function counters
        function_counts = {func.replace('/', '_').replace(' ', '_'): 0 for func in self.all_functions}
        function_presence = {func.replace('/', '_').replace(' ', '_'): 0 for func in self.all_functions}
        
        # Initialize rating counters
        rating_counts = {f'{rating}_count': 0 for rating in self.id_ratings}
        rating_percentages = {f'{rating}_percentage': 0.0 for rating in self.id_ratings}
        
        # Safety metrics
        irritancy_scores = []
        comedogenicity_scores = []
        
        # Ingredient names for reference
        ingredient_names = []
        
        # Process each ingredient
        for ingredient in product.get('ingredients', []):
            ingredient_names.append(ingredient.get('name', ''))
            
            # Process functions
            for function in ingredient.get('functions', []):
                clean_function = function.replace('/', '_').replace(' ', '_')
                if clean_function in function_counts:
                    function_counts[clean_function] += 1
                    function_presence[clean_function] = 1
            
            # Process ID ratings
            id_rating = ingredient.get('id_rating', '')
            if id_rating in self.id_ratings:
                rating_counts[f'{id_rating}_count'] += 1
            
            # Process safety scores
            irritancy, comedogenicity = self.parse_irritancy_comedogenicity(
                ingredient.get('irritancy_comedogenicity', '')
            )
            if irritancy is not None:
                irritancy_scores.append(irritancy)
            if comedogenicity is not None:
                comedogenicity_scores.append(comedogenicity)
        
        # Add function features
        features.update(function_counts)
        features.update({f'{k}_binary': v for k, v in function_presence.items()})
        
        # Add rating features
        features.update(rating_counts)
        if product['total_ingredients'] > 0:
            for rating in self.id_ratings:
                features[f'{rating}_percentage'] = rating_counts[f'{rating}_count'] / product['total_ingredients']
        
        # Add safety features
        features['avg_irritancy'] = np.mean(irritancy_scores) if irritancy_scores else 0
        features['max_irritancy'] = max(irritancy_scores) if irritancy_scores else 0
        features['avg_comedogenicity'] = np.mean(comedogenicity_scores) if comedogenicity_scores else 0
        features['max_comedogenicity'] = max(comedogenicity_scores) if comedogenicity_scores else 0
        features['safety_concern_ingredients'] = len([s for s in irritancy_scores + comedogenicity_scores if s > 2])
        
        # Function diversity metrics
        features['function_diversity'] = sum(1 for count in function_counts.values() if count > 0)
        features['total_functions'] = sum(function_counts.values())
        features['avg_functions_per_ingredient'] = features['total_functions'] / max(product['total_ingredients'], 1)
        
        # Add ingredient names as a list (for reference)
        features['ingredient_names'] = ingredient_names
        
        return features
    
    def create_ml_dataset(self, json_file_path):
        """Convert JSON file to ML-ready dataset"""
        # Load JSON data
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        # Extract products from results
        if 'results' in data:
            products = data['results']
        else:
            products = data  # Assume data is already a list of products
        
        # Process each product
        processed_products = []
        for product in products:
            features = self.extract_product_features(product)
            processed_products.append(features)
        
        # Create DataFrame
        df = pd.DataFrame(processed_products)
        
        return df
    
    def generate_feature_report(self, df):
        """Generate a report about the features"""
        report = {
            'dataset_shape': df.shape,
            'categories': df['predicted_category'].value_counts().to_dict(),
            'feature_types': {
                'function_counts': [col for col in df.columns if col.endswith('_count') and not any(rating in col for rating in self.id_ratings)],
                'function_binary': [col for col in df.columns if col.endswith('_binary')],
                'rating_features': [col for col in df.columns if any(rating in col for rating in self.id_ratings)],
                'safety_features': ['avg_irritancy', 'max_irritancy', 'avg_comedogenicity', 'max_comedogenicity', 'safety_concern_ingredients'],
                'diversity_features': ['function_diversity', 'total_functions', 'avg_functions_per_ingredient']
            },
            'missing_values': df.isnull().sum().to_dict(),
            'high_correlation_pairs': []
        }
        
        # Find highly correlated features
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        correlation_matrix = df[numeric_cols].corr()
        
        high_corr_pairs = []
        for i in range(len(correlation_matrix.columns)):
            for j in range(i+1, len(correlation_matrix.columns)):
                if abs(correlation_matrix.iloc[i, j]) > 0.9:
                    high_corr_pairs.append({
                        'feature1': correlation_matrix.columns[i],
                        'feature2': correlation_matrix.columns[j],
                        'correlation': correlation_matrix.iloc[i, j]
                    })
        
        report['high_correlation_pairs'] = high_corr_pairs
        
        return report
    
    def save_datasets(self, df, base_filename):
        """Save different versions of the dataset for different ML approaches"""
        
        # 1. Full dataset with all features
        df.to_csv(f'{base_filename}_full.csv', index=False)
        
        # 2. Binary features only (for cosine similarity)
        binary_cols = ['product_brand', 'product_title', 'predicted_category'] + \
                     [col for col in df.columns if col.endswith('_binary')]
        df_binary = df[binary_cols]
        df_binary.to_csv(f'{base_filename}_binary.csv', index=False)
        
        # 3. Count features (for clustering)
        count_cols = ['product_brand', 'product_title', 'predicted_category'] + \
                    [col for col in df.columns if any(func.replace('/', '_').replace(' ', '_') in col 
                     for func in self.all_functions) and not col.endswith('_binary')]
        df_counts = df[count_cols]
        df_counts.to_csv(f'{base_filename}_counts.csv', index=False)
        
        # 4. ML-ready dataset (numeric features only, no ingredient names)
        ml_cols = [col for col in df.columns if col not in ['ingredient_names', 'product_brand', 'product_title']]
        df_ml = df[ml_cols]
        df_ml.to_csv(f'{base_filename}_ml_ready.csv', index=False)
        
        print(f"✅ Saved 4 dataset versions:")
        print(f"   - {base_filename}_full.csv (Complete dataset)")
        print(f"   - {base_filename}_binary.csv (Binary features for cosine similarity)")
        print(f"   - {base_filename}_counts.csv (Count features for clustering)")
        print(f"   - {base_filename}_ml_ready.csv (Numeric features for ML models)")

def main():
    """Example usage"""
    preprocessor = SkincareMLPreprocessor()
    
    # Replace with your actual JSON file path
    json_file = "categorized_products_enhanced.json"
    
    try:
        # Create ML dataset
        print("🔄 Processing JSON file...")
        df = preprocessor.create_ml_dataset(json_file)
        
        # Generate report
        report = preprocessor.generate_feature_report(df)
        
        # Display report
        print(f"\n📊 DATASET REPORT")
        print(f"Dataset Shape: {report['dataset_shape']}")
        print(f"Categories: {report['categories']}")
        print(f"Function Count Features: {len(report['feature_types']['function_counts'])}")
        print(f"Binary Features: {len(report['feature_types']['function_binary'])}")
        print(f"Rating Features: {len(report['feature_types']['rating_features'])}")
        
        if report['high_correlation_pairs']:
            print(f"\n⚠️ Highly Correlated Features (>0.9):")
            for pair in report['high_correlation_pairs'][:5]:  # Show top 5
                print(f"   {pair['feature1']} ↔ {pair['feature2']}: {pair['correlation']:.3f}")
        
        # Save datasets
        print(f"\n💾 Saving datasets...")
        preprocessor.save_datasets(df, "skincare_dataset")
        
        print(f"\n🎯 RECOMMENDATIONS FOR ML:")
        print(f"1. For Product Similarity (Cosine): Use skincare_dataset_binary.csv")
        print(f"2. For Clustering (DBSCAN): Use skincare_dataset_counts.csv")
        print(f"3. For Classification Models: Use skincare_dataset_ml_ready.csv")
        print(f"4. Consider removing highly correlated features to avoid redundancy")
        
    except FileNotFoundError:
        print(f"❌ File '{json_file}' not found. Please update the file path.")
        print(f"💡 Usage example:")
        print(f"   preprocessor = SkincareMLPreprocessor()")
        print(f"   df = preprocessor.create_ml_dataset('your_file.json')")
        print(f"   preprocessor.save_datasets(df, 'output_name')")

if __name__ == "__main__":
    main()