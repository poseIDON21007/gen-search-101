# Product Embeddings Pipeline with Google Vertex AI & BigQuery

This guide provides detailed steps to create vector embeddings for your product data using Google Vertex AI and store them in BigQuery.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Google Cloud Setup](#google-cloud-setup)
3. [Local Environment Setup](#local-environment-setup)
4. [Running the Pipeline](#running-the-pipeline)
5. [Querying Your Data](#querying-your-data)
6. [Understanding the Pipeline](#understanding-the-pipeline)
7. [Troubleshooting](#troubleshooting)

---

## 🔧 Prerequisites

- Python 3.8 or higher
- Google Cloud Platform (GCP) account
- Basic knowledge of terminal/command line

---

## ☁️ Google Cloud Setup

### Step 1: Create a GCP Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown at the top
3. Click "New Project"
4. Enter a project name (e.g., "product-embeddings")
5. Note your **Project ID** (you'll need this later)

### Step 2: Enable Required APIs

Enable the following APIs in your project:

```bash
# Using gcloud CLI (install from https://cloud.google.com/sdk/docs/install)
gcloud config set project YOUR_PROJECT_ID

# Enable Vertex AI API
gcloud services enable aiplatform.googleapis.com

# Enable BigQuery API
gcloud services enable bigquery.googleapis.com

# Enable Vertex AI Embeddings API
gcloud services enable generativelanguage.googleapis.com
```

**OR manually via Console:**
1. Go to [API Library](https://console.cloud.google.com/apis/library)
2. Search for and enable:
   - **Vertex AI API**
   - **BigQuery API**
   - **Cloud AI Platform API**

### Step 3: Set Up Authentication

#### Option A: Using gcloud CLI (Recommended for local development)

```bash
# Install gcloud CLI if you haven't already
# https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth application-default login

# Set your project
gcloud config set project YOUR_PROJECT_ID
```

#### Option B: Using Service Account (Recommended for production)

1. Go to [Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. Click "Create Service Account"
3. Name it (e.g., "embeddings-pipeline")
4. Grant these roles:
   - **Vertex AI User**
   - **BigQuery Data Editor**
   - **BigQuery Job User**
5. Click "Create Key" → Choose JSON
6. Download the JSON key file
7. Set environment variable:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/key.json"
   ```

### Step 4: Enable Billing

1. Go to [Billing](https://console.cloud.google.com/billing)
2. Link a billing account to your project
3. **Cost Estimate**: For your ~2,500 products:
   - Vertex AI Embeddings: ~$0.10 (very low cost)
   - BigQuery Storage: ~$0.02/month
   - Total: Less than $1

---

## 💻 Local Environment Setup

### Step 1: Install Python Dependencies

```bash
# Navigate to your project directory
cd "/Users/ddas1/Documents/Code-code/HACKATHON/Dummy DataSets"

# Install required packages
pip3 install -r requirements.txt

# Or install individually:
pip install google-cloud-aiplatform google-cloud-bigquery pandas python-dotenv tqdm
```

### Step 2: Configure Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your details:
   ```bash
   nano .env  # or use any text editor
   ```

3. Update the values:
   ```env
   GCP_PROJECT_ID=your-actual-project-id
   GCP_REGION=us-central1
   BIGQUERY_DATASET_ID=product_embeddings
   BIGQUERY_TABLE_ID=products_with_vectors
   ```

**Region Options:**
- `us-central1` (Iowa) - Recommended, lowest latency for most users
- `us-east1` (South Carolina)
- `europe-west1` (Belgium)
- `asia-northeast1` (Tokyo)

---

## 🚀 Running the Pipeline

### Run the Complete Pipeline

```bash
python3 create_embeddings_pipeline.py
```

### What Happens:

1. **Loads your JSON files** (all 5 files automatically)
2. **Creates text representations** of each product by combining:
   - Title
   - Description
   - Category & Subcategory
   - Brand
   - Color
   - Tags
3. **Generates embeddings** using Vertex AI's `textembedding-gecko@003` model
   - Each product gets a 768-dimensional vector
4. **Creates BigQuery dataset and table** automatically
5. **Inserts products with embeddings** into BigQuery

### Expected Output:

```
🚀 Starting Product Embeddings Pipeline

✓ Initialized pipeline for project: your-project-id
✓ Using region: us-central1
✓ Target table: product_embeddings.products_with_vectors
✓ Dataset product_embeddings already exists
✓ Created table products_with_vectors

============================================================
Processing: beauty_personal_care_500.json
============================================================
✓ Loaded 500 products from beauty_personal_care_500.json

📊 Processing 500 products...
Creating embeddings: 100%|███████████████| 500/500 [00:45<00:00, 11.2it/s]
✓ Created 500 embeddings

📤 Inserting 500 rows to BigQuery...
Inserting to BigQuery: 100%|████████████| 500/500 [00:02<00:00, 201.3it/s]
✓ Successfully inserted all rows to BigQuery

... (continues for all files)

✅ Pipeline completed successfully!
```

### Processing Time Estimates:

- **500 products**: ~1-2 minutes
- **All 2,500 products**: ~8-10 minutes

---

## 🔍 Querying Your Data

### View Your Data in BigQuery Console

1. Go to [BigQuery Console](https://console.cloud.google.com/bigquery)
2. Navigate to your dataset: `product_embeddings` → `products_with_vectors`
3. Click "Preview" to see your data

### Sample SQL Queries

#### 1. View All Products with Embeddings

```sql
SELECT 
  sku_id,
  title,
  category,
  brand,
  price_aud,
  ARRAY_LENGTH(embedding) as embedding_dimension
FROM `your-project-id.product_embeddings.products_with_vectors`
LIMIT 10;
```

#### 2. Find Similar Products (Vector Similarity Search)

```sql
-- First, get the embedding for a specific product
WITH target_product AS (
  SELECT embedding
  FROM `your-project-id.product_embeddings.products_with_vectors`
  WHERE sku_id = 'SKU-BEA-0001'
)

-- Then find similar products using cosine similarity
SELECT 
  p.sku_id,
  p.title,
  p.category,
  p.price_aud,
  -- Calculate cosine similarity
  (
    SELECT 
      SUM(p_elem * t_elem) / 
      (SQRT(SUM(p_elem * p_elem)) * SQRT(SUM(t_elem * t_elem)))
    FROM UNNEST(p.embedding) AS p_elem WITH OFFSET pos1
    JOIN UNNEST(t.embedding) AS t_elem WITH OFFSET pos2
    ON pos1 = pos2
  ) AS similarity_score
FROM `your-project-id.product_embeddings.products_with_vectors` p
CROSS JOIN target_product t
WHERE p.sku_id != 'SKU-BEA-0001'
ORDER BY similarity_score DESC
LIMIT 10;
```

#### 3. Search Products by Category

```sql
SELECT 
  sku_id,
  title,
  category,
  subcategory,
  brand,
  price_aud
FROM `your-project-id.product_embeddings.products_with_vectors`
WHERE category = 'Beauty & Personal Care'
ORDER BY price_aud DESC
LIMIT 20;
```

#### 4. Count Products by Category

```sql
SELECT 
  category,
  COUNT(*) as product_count,
  AVG(price_aud) as avg_price,
  MIN(price_aud) as min_price,
  MAX(price_aud) as max_price
FROM `your-project-id.product_embeddings.products_with_vectors`
GROUP BY category
ORDER BY product_count DESC;
```

---

## 🧠 Understanding the Pipeline

### How Vector Embeddings Work

1. **Text Representation**: Each product is converted to text combining all key attributes
2. **Embedding Model**: Vertex AI's `textembedding-gecko@003` converts text to a 768-dimensional vector
3. **Semantic Meaning**: Similar products have similar vectors (mathematically close in vector space)
4. **Use Cases**:
   - Product recommendations
   - Semantic search
   - Product categorization
   - Duplicate detection

### BigQuery Schema

The table includes these fields:
```
- sku_id (STRING, REQUIRED): Unique product identifier
- title (STRING): Product title
- description (STRING): Product description
- category (STRING): Main category
- subcategory (STRING): Subcategory
- brand (STRING): Brand name
- gender (STRING): Target gender
- color (STRING): Product color
- size (STRING): Product size
- price_aud (FLOAT): Price in AUD
- margin_percent (INTEGER): Profit margin
- stock_quantity (INTEGER): Available stock
- tags (STRING, REPEATED): Product tags array
- embedding (FLOAT, REPEATED): 768-dimensional vector
```

### Pipeline Architecture

```
JSON Files → Load Products → Create Text Representation
     ↓
Generate Embeddings (Vertex AI) → Batch Processing
     ↓
Create BigQuery Table → Insert Data → Complete
```

---

## 🔧 Troubleshooting

### Common Issues & Solutions

#### Issue: "Permission Denied" Error

**Solution:**
```bash
# Re-authenticate
gcloud auth application-default login

# Verify your account has the right permissions
gcloud projects get-iam-policy YOUR_PROJECT_ID
```

#### Issue: "API Not Enabled"

**Solution:**
```bash
# Enable all required APIs
gcloud services enable aiplatform.googleapis.com bigquery.googleapis.com
```

#### Issue: "Quota Exceeded"

**Solution:**
1. Check your quotas: [Quotas Page](https://console.cloud.google.com/iam-admin/quotas)
2. Request quota increase if needed
3. Reduce batch size in the script (change `batch_size=5` to `batch_size=1`)

#### Issue: "Module Not Found"

**Solution:**
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

#### Issue: Embeddings Taking Too Long

**Solution:**
- The script already uses batch processing (5 items at a time)
- You can increase batch size if you have higher quotas
- Processing ~500 products should take 1-2 minutes

---

## 📊 Cost Breakdown

### Estimated Costs (for ~2,500 products):

| Service | Usage | Cost |
|---------|-------|------|
| Vertex AI Embeddings | 2,500 requests | ~$0.10 |
| BigQuery Storage | ~50 MB | $0.02/month |
| BigQuery Queries | First 1 TB free | $0.00 |
| **Total** | | **~$0.12** |

### Cost Optimization Tips:

1. Use batch processing (already implemented)
2. Cache embeddings locally if re-running
3. Use BigQuery's free tier (1 TB queries/month)

---

## 🎯 Next Steps

After running the pipeline, you can:

1. **Build a Recommendation System**:
   - Use vector similarity to find related products
   - Implement "Similar Products" feature

2. **Semantic Search**:
   - Create embeddings for user queries
   - Find matching products using vector similarity

3. **Product Clustering**:
   - Use embeddings to automatically group similar products
   - Discover product patterns

4. **Export for ML Models**:
   - Use embeddings as features for ML models
   - Train custom recommendation models

---

## 📚 Additional Resources

- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [BigQuery Documentation](https://cloud.google.com/bigquery/docs)
- [Text Embeddings Guide](https://cloud.google.com/vertex-ai/docs/generative-ai/embeddings/get-text-embeddings)
- [Vector Similarity in BigQuery](https://cloud.google.com/blog/topics/developers-practitioners/find-anything-blazingly-fast-googles-vector-search-technology)

---

## 🤝 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review error messages in the console
3. Check [GCP Status Dashboard](https://status.cloud.google.com/)

---

## 📝 Notes

- The pipeline automatically handles all 5 JSON files
- Embeddings are created in batches to respect API limits
- BigQuery table is created automatically if it doesn't exist
- Progress bars show real-time status of the pipeline

**Happy embedding! 🚀**
