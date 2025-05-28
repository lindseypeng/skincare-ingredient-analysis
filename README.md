# 🧴 Skincare Ingredient-Based Product Classifier

## 💡 Project Overview

This project aims to build a machine learning-friendly dataset of skincare products, using **ingredient functionalities** (e.g., soothing, exfoliating, antioxidant) as the foundation. The ultimate goal is to create **a model that can classify or recommend skincare products** based on their ingredient profiles — regardless of the product’s category label (like cream, serum, sunscreen), which is often missing or unclear on public databases.

Data is scraped from [INCIDecoder](https://incidecoder.com), a well-known ingredient analysis site, and processed to generate **binary functionality vectors** per product. Each vector reflects the presence or absence of key ingredient roles such as:

- Moisturizer/Humectant
- Soothing
- Antioxidant
- Exfoliant
- Sunscreen
- Emollient
- Preservative
- Skin Brightening
- Solvent
- Surfactant/Cleansing
- Skin-Identical Ingredient

This functionality-based encoding lays the groundwork for training models to:
- Predict product type based on ingredients
- Group similar products together (clustering or recommendation)
- Build explainable ML pipelines using ingredient science

---

## 🔍 Key Objectives

- ✅ Scrape product and ingredient data from INCIDecoder
- ✅ Extract and encode ingredient **functionalities**
- ✅ Build a **balanced dataset** across multiple key functionalities
- ⚙️ Handle missing metadata (e.g., ingredient ratings)
- 🧠 Create a supervised learning setup with labeled product categories
- 🔄 Explore similarity, clustering, or recommendation models in skincare

---

## 📈 Why This Project?

Skincare products are often marketed based on packaging and claims — not based on real ingredient science. This project flips the model: instead of starting with the product name or type, we analyze the **functional roles of each ingredient** to understand what a product *really* does.

By building a rich, functionality-based dataset:
- We improve explainability and transparency in product analysis
- We prepare a pipeline that can support clean, unbiased ML modeling
- We open the door to future tools for consumers or dermatologists looking for functional product suggestions

---

## 🔧 Tools & Stack

- **Python** for scraping, cleaning, and ML
- **BeautifulSoup / requests** for web scraping
- **pandas / numpy / scikit-learn** for data processing and modeling
- **Jupyter Notebooks** for exploration
- *(More tools may be added later as the project evolves)*

---

## 🚧 Project Status

- [x] Initial scraping script built and tested
- [x] Functionalities extracted and encoded
- [ ] Product category labels in progress (via heuristics and ML)
- [ ] ML model training & evaluation (planned)
- [ ] Interactive demo or notebook (future)

---

## 📌 Notes

This is a learning-driven project focused on applying ML to real-world data challenges.

---

## 🤝 Contributions

This is a personal and educational project. Feedback, suggestions, and collaboration ideas are welcome once the base structure is more complete.


