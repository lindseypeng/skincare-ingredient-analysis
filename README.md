
# 💄🧪 Skincare Ingredient Analysis

## ✨ Big Vision

Demystify the skincare industry for beginners.

Identify which skincare steps are truly necessary based on science rather than marketing.

Empower consumers to make better, more cost-effective skincare choices.

---

# 🧪 Exploratory Data Analysis Goals

### 1. 🢄 Top Ingredients Per Product Type
- For each product type (e.g., serum, moisturizer, toner), identify the **top N ingredients**.
- Understand the **functional purpose** of these ingredients (e.g., moisturizing, exfoliating, anti-aging).
- **Hypothesis**: If ingredient functions overlap a lot, steps may be redundant.

### 2. 🔬 Overlap Between Product Types
- Use **t-SNE** or **PCA** to project products based on ingredient composition into 2D space.
- Color by `product_type` to visualize **how distinct or similar** different product types are.
- **Hypothesis**: If moisturizers and serums cluster closely, they may not be fundamentally different.

### 3. 💰 Ingredient Presence and Price Correlation
- Explore if **expensive products** have *different* or *better* ingredients than cheaper ones.
- Calculate **average price** for products containing specific ingredients.
- **Hypothesis**: Some ingredients could correlate with higher price — or **price differences** could be branding rather than substance.

---

# 🧐 Main Product Ideas

### 🚀 Product Feature Idea: Ingredient Comparison Tool
- **Upload** 3 skincare products (e.g., low, medium, high price).
- **Analyze and compare**:
  - **Shared ingredients**: what's common between expensive and cheap?
  - **Unique ingredients**: are they correlated with price?
- **Goal**: Help users see if they’re paying more for *better formulation* or *just branding*.

---

# 🛠️ Technical Approach Summary

| Step | Description |
|:----:|-------------|
| 1. Data Cleaning | Parse ingredient lists, clean price data. |
| 2. Top Ingredient Analysis | Get top N ingredients per product type. |
| 3. Clustering | One-hot encode ingredients → t-SNE or PCA → visualize similarity. |
| 4. Price vs Ingredient Analysis | Normalize prices, compute average price per ingredient. |
| 5. Entropy Analysis | See how "specialized" or "universal" each ingredient is across product types. |
| 6. Prototype Tool | Build a simple app to upload 3 product ingredient lists and compare! |

---

# ✨ Key Takeaway
> **If most steps share similar functional ingredients, you might not need all 12 steps.**
>
> **If expensive products don’t have better ingredients, you’re paying for branding, not quality.**

---

# 🔄 Next Steps
- ✅ Collect and clean ingredient + product type + price data.
- ✅ Run top ingredient, overlap, and price correlation analyses.
- ⬜ Explore scientific literature for *function labels* (hydration, exfoliation, etc.)
- ⬜ Build a prototype comparison tool (start with Streamlit or a notebook).
