# Product Embeddings Pipeline - Quick Reference

## 📁 Files Created

| File | Purpose |
|------|---------|
| `README.md` | Complete setup guide with detailed steps |
| `create_embeddings_pipeline.py` | Main pipeline script to create embeddings |
| `vector_search.py` | Utilities for searching products using embeddings |
| `bigquery_queries.sql` | Sample SQL queries for BigQuery |
| `requirements.txt` | Python dependencies |
| `quickstart.sh` | Automated setup script (run `./quickstart.sh`) |
| `.env.example` | Environment variable template |

## 🚀 Quick Start (3 Steps)

### Step 1: Google Cloud Setup (5 minutes)

```bash
# 1. Create GCP project at https://console.cloud.google.com
# 2. Enable APIs
gcloud services enable aiplatform.googleapis.com bigquery.googleapis.com

# 3. Authenticate
gcloud auth application-default login
```

### Step 2: Local Setup (2 minutes)

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set your GCP_PROJECT_ID
nano .env
```

### Step 3: Run Pipeline (5-10 minutes)

```bash
# Option A: Automated
./quickstart.sh

# Option B: Manual
python create_embeddings_pipeline.py
```

## 📊 What Gets Created

### BigQuery Table Structure

```
Dataset: product_embeddings
Table: products_with_vectors

Schema:
├── sku_id (STRING) - Unique product ID
├── title (STRING) - Product title
├── description (STRING) - Product description
├── category (STRING) - Main category
├── subcategory (STRING) - Subcategory
├── brand (STRING) - Brand name
├── gender (STRING) - Target gender
├── color (STRING) - Product color
├── size (STRING) - Product size
├── price_aud (FLOAT) - Price in AUD
├── margin_percent (INTEGER) - Profit margin
├── stock_quantity (INTEGER) - Stock level
├── tags (STRING[]) - Array of tags
└── embedding (FLOAT[]) - 768-dimensional vector
```

## 🔍 How to Use Embeddings

### 1. Semantic Search

```python
from vector_search import VectorSearcher

searcher = VectorSearcher(
    project_id="your-project-id",
    dataset_id="product_embeddings",
    table_id="products_with_vectors"
)

# Natural language search
results = searcher.search_similar_products(
    "comfortable women's clothing for summer",
    top_k=10
)
```

### 2. Find Similar Products

```python
# Find products similar to a specific SKU
similar = searcher.find_similar_to_product(
    sku_id="SKU-BEA-0001",
    top_k=10
)
```

### 3. BigQuery SQL

```sql
-- Find similar products using SQL
WITH target AS (
  SELECT embedding FROM products_with_vectors 
  WHERE sku_id = 'SKU-BEA-0001'
)
SELECT p.*, 
  COSINE_SIMILARITY(p.embedding, t.embedding) as score
FROM products_with_vectors p
CROSS JOIN target t
ORDER BY score DESC
LIMIT 10;
```

## 💡 Common Use Cases

### 1. Product Recommendations
- **Similar Products**: "Customers who viewed this also viewed..."
- **Cross-Sell**: Recommend complementary products from different categories
- **Upsell**: Find premium alternatives with higher similarity

### 2. Search & Discovery
- **Semantic Search**: Natural language product search
- **Visual Search**: Combine with image embeddings (future enhancement)
- **Faceted Search**: Combine embeddings with traditional filters

### 3. Analytics
- **Product Clustering**: Group similar products automatically
- **Gap Analysis**: Find underserved product spaces
- **Trend Detection**: Identify emerging product themes

### 4. Inventory Optimization
- **Duplicate Detection**: Find near-duplicate products
- **Assortment Planning**: Balance product variety
- **Dynamic Pricing**: Price similar products competitively

## 🎯 Pipeline Architecture

```
┌─────────────────┐
│  JSON Files     │
│  (5 files)      │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Load & Parse Products          │
│  - beauty_personal_care_500     │
│  - gifts_photo_products_500     │
│  - kmart_clothing_accessories   │
│  - kmart_home_living_products   │
│  - nursery_kids_500             │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Create Text Representation     │
│  Combine: Title + Description   │
│         + Category + Brand      │
│         + Color + Tags          │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Vertex AI Embeddings           │
│  Model: textembedding-gecko@003 │
│  Output: 768-dim vectors        │
│  Batch: 5 products at a time    │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  BigQuery Storage               │
│  Dataset: product_embeddings    │
│  Table: products_with_vectors   │
│  ~2,500 products with vectors   │
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Query & Search                 │
│  - Vector similarity            │
│  - Traditional filters          │
│  - Combined queries             │
└─────────────────────────────────┘
```

## 📈 Performance & Costs

### Processing Time
- **500 products**: ~1-2 minutes
- **2,500 products**: ~8-10 minutes
- **Throughput**: ~4-5 products/second

### Costs (Approximate)
| Service | Usage | Cost |
|---------|-------|------|
| Vertex AI Embeddings | 2,500 requests | $0.10 |
| BigQuery Storage | 50 MB/month | $0.02 |
| BigQuery Queries | First 1 TB free | $0.00 |
| **Total** | **One-time** | **~$0.12** |

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| "Permission Denied" | Run `gcloud auth application-default login` |
| "API not enabled" | Run `gcloud services enable aiplatform.googleapis.com` |
| "Module not found" | Run `pip install -r requirements.txt` |
| Slow processing | Normal - embeddings take time. Be patient! |
| Rate limits | Script has built-in batching (5 items/batch) |

## 📚 Next Steps

1. **Run the Pipeline**
   ```bash
   ./quickstart.sh
   ```

2. **View Your Data**
   - Open [BigQuery Console](https://console.cloud.google.com/bigquery)
   - Navigate to `product_embeddings` dataset
   - Click "Preview" on `products_with_vectors` table

3. **Try Sample Queries**
   - Open `bigquery_queries.sql`
   - Copy queries to BigQuery Console
   - Replace `your-project-id` with your actual project ID

4. **Test Vector Search**
   ```bash
   python vector_search.py
   ```

5. **Build Your Application**
   - Use `VectorSearcher` class in your app
   - Implement product recommendations
   - Create semantic search features

## 🆘 Support

- **Documentation**: See `README.md` for detailed guide
- **Sample Queries**: Check `bigquery_queries.sql`
- **GCP Issues**: Visit [GCP Status](https://status.cloud.google.com/)
- **Vertex AI Docs**: https://cloud.google.com/vertex-ai/docs

## 📝 Key Commands

```bash
# Setup
./quickstart.sh                    # Automated setup
pip install -r requirements.txt    # Install dependencies

# Main Pipeline
python create_embeddings_pipeline.py    # Create embeddings

# Search & Query
python vector_search.py             # Example searches

# GCP Commands
gcloud auth application-default login    # Authenticate
gcloud services enable aiplatform.googleapis.com  # Enable API
gcloud config set project PROJECT_ID     # Set project
```

---

**Ready to start? Run: `./quickstart.sh`** 🚀
