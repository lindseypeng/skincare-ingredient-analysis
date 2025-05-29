# 🧪 Project Challenges & Strategy Summary

## 🔍 Problem Summary

This project involves scraping skincare product data from [INCIDecoder](https://incidecoder.com) based on **ingredient functionalities** (e.g., "moisturizer/humectant"). However, the website does **not** provide product category labels (e.g., cream, sunscreen, shampoo), which poses several challenges:

- Scraped products come from mixed categories without any explicit label.
- Initial scraping was based only on a single functionality ("moisturizer/humectant"), meaning all products have that feature active — this reduces input variability.
- Lack of category data complicates both **classification** and **recommendation** logic for ML modeling.

---

## 🛠️ Category Creation Options

### 🔹 Option 1: Categorize Products via Heuristics (Python)
- **Goal:** Add a `product_type` column (e.g., “sunscreen”, “moisturizer”) by parsing product names or URLs.
- **Challenge:** Risk of misclassification due to ambiguity or naming inconsistency.
- **Pros:** Quick and rule-based.
- **Cons:** Potentially noisy labels, not scalable for complex naming patterns.

### 🔹 Option 2: Predict Categories via Supervised Learning
- **Goal:** Use ingredients/functionality features to train a simple classifier to predict product categories.
- **How:** Manually label ~100 products to create a training set. Apply Decision Tree or Logistic Regression for initial modeling.
- **Pros:** Great ML practice, scalable once trained.
- **Cons:** Requires manual labeling effort to start.

---

## ✅ My Adopted Strategy

### 1. **Scrape Balanced Products Across Functionalities**
Instead of focusing only on one functionality (e.g., "moisturizer"), I will modify the scraper to collect **an equal number of products** for selected, commonly occurring ingredient functionalities.

### 2. **Target Functionalities Chosen for ML Input Vectors**

| Functionality              | Why It’s Useful                                              |
|---------------------------|--------------------------------------------------------------|
| moisturizer/humectant     | Core of most skincare products                               |
| soothing                  | Popular for sensitive skin and anti-inflammatory effects     |
| antioxidant               | Common in anti-aging and repair formulations                 |
| exfoliant                 | Important for cell turnover and renewal                      |
| sunscreen                 | Highly relevant for product classification                   |
| emollient                 | Crucial for skin barrier repair                              |
| preservative              | Present in nearly all formulations                          |
| skin brightening          | Popular and trend-driven functionality                       |
| solvent                   | Indicates formulation properties                             |
| surfactant/cleansing      | Common in shampoos, face washes, and cleansers               |
| skin-identical-ingredient | Key for dermatological formulation design                    |

- **Minimum target:** 50–75 products per functionality  
- **Ideal target:** 100+ products per functionality

This balanced sampling reduces feature skew (e.g., all products having `moisturizer=1`) and supports better generalization in ML.

---

## 📐 Modeling Benefits of This Setup

- **Balanced Feature Distribution:** Avoids binary columns where every product has the same value.
- **Explainable ML Input:** Products become vectors like `[1, 0, 0, 1, ...]` based on presence of functionalities.
- **Cleaner Dataset:** Each product is uniquely scraped and linked to a set of ingredient functionalities.
- **Supports Supervised Learning:** Once labeled, product types can be used as targets for classification models.

---

## ⚠️ Additional Data Challenges

### 🔸 Rare Functionalities
Some types like `chelating`, `deodorant`, or `colorant` are too specific or underrepresented. These will be excluded to avoid imbalance and modeling noise.

### 🔸 Skewed Ingredient Representation
Certain functionalities are dominated by widely known ingredients (e.g., **Niacinamide** for skin brightening). This may bias the dataset.
- **Mitigation:** Consider using **TF-IDF weighting** of ingredients instead of pure binary presence.

### 🔸 Missing Metadata
Not all ingredients come with `irritancy`, `comedogenicity`, or `ID-rating` info.
- **Solution:** Use `NaN` as placeholder and flag missing values for potential imputation.

---

## ✅ Final Goal

Build a structured, balanced dataset of skincare products by scraping **equal numbers across key functionalities**, and generate an ML-ready matrix where each product is encoded by its ingredient functionalities.

- Apply **manual or heuristic labeling** to a subset for supervised classification.
- Enable future **recommendation** or **similarity search** based on functionality profiles.
- Maintain **explainability** of predictions by grounding them in ingredient science.

---

📁 _This file is part of the project documentation to help explain data collection, limitations, and modeling strategies._
