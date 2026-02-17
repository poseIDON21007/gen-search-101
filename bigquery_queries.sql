-- Sample BigQuery Queries for Product Embeddings
-- Replace 'your-project-id' with your actual GCP project ID

-- =============================================================================
-- 1. View Sample Products with Embedding Dimensions
-- =============================================================================
SELECT 
  sku_id,
  title,
  category,
  brand,
  price_aud,
  ARRAY_LENGTH(embedding) as embedding_dimension
FROM `your-project-id.product_embeddings.products_with_vectors`
LIMIT 10;


-- =============================================================================
-- 2. Find Products Similar to a Specific Product (by SKU)
-- =============================================================================
WITH target_product AS (
  SELECT 
    embedding,
    title as target_title
  FROM `your-project-id.product_embeddings.products_with_vectors`
  WHERE sku_id = 'SKU-BEA-0001'  -- Change this SKU ID
)

SELECT 
  p.sku_id,
  p.title,
  p.category,
  p.subcategory,
  p.brand,
  p.price_aud,
  p.stock_quantity,
  -- Calculate cosine similarity between product and target
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
WHERE p.sku_id != 'SKU-BEA-0001'  -- Exclude the target product
ORDER BY similarity_score DESC
LIMIT 20;


-- =============================================================================
-- 3. Product Statistics by Category
-- =============================================================================
SELECT 
  category,
  COUNT(*) as total_products,
  COUNT(DISTINCT brand) as unique_brands,
  AVG(price_aud) as avg_price,
  MIN(price_aud) as min_price,
  MAX(price_aud) as max_price,
  AVG(stock_quantity) as avg_stock,
  SUM(stock_quantity) as total_stock
FROM `your-project-id.product_embeddings.products_with_vectors`
GROUP BY category
ORDER BY total_products DESC;


-- =============================================================================
-- 4. Top 10 Most Expensive Products by Category
-- =============================================================================
WITH ranked_products AS (
  SELECT 
    sku_id,
    title,
    category,
    brand,
    price_aud,
    stock_quantity,
    ROW_NUMBER() OVER (PARTITION BY category ORDER BY price_aud DESC) as rank
  FROM `your-project-id.product_embeddings.products_with_vectors`
)
SELECT 
  category,
  title,
  brand,
  price_aud,
  stock_quantity
FROM ranked_products
WHERE rank <= 10
ORDER BY category, price_aud DESC;


-- =============================================================================
-- 5. Search by Multiple Filters
-- =============================================================================
SELECT 
  sku_id,
  title,
  category,
  subcategory,
  brand,
  color,
  size,
  price_aud,
  stock_quantity,
  tags
FROM `your-project-id.product_embeddings.products_with_vectors`
WHERE 
  category = 'Beauty & Personal Care'
  AND price_aud BETWEEN 20 AND 100
  AND stock_quantity > 100
ORDER BY price_aud ASC
LIMIT 50;


-- =============================================================================
-- 6. Products with Low Stock (Inventory Alert)
-- =============================================================================
SELECT 
  sku_id,
  title,
  category,
  brand,
  stock_quantity,
  price_aud
FROM `your-project-id.product_embeddings.products_with_vectors`
WHERE stock_quantity < 100
ORDER BY stock_quantity ASC
LIMIT 50;


-- =============================================================================
-- 7. Product Search by Tag
-- =============================================================================
SELECT 
  sku_id,
  title,
  category,
  brand,
  price_aud,
  tags
FROM `your-project-id.product_embeddings.products_with_vectors`
WHERE 'haircare' IN UNNEST(tags)  -- Change tag as needed
ORDER BY price_aud DESC
LIMIT 20;


-- =============================================================================
-- 8. Revenue Potential Analysis
-- =============================================================================
SELECT 
  category,
  COUNT(*) as product_count,
  SUM(stock_quantity * price_aud) as total_inventory_value,
  SUM(stock_quantity * price_aud * margin_percent / 100) as potential_profit,
  AVG(margin_percent) as avg_margin
FROM `your-project-id.product_embeddings.products_with_vectors`
GROUP BY category
ORDER BY total_inventory_value DESC;


-- =============================================================================
-- 9. Find Products by Brand and Color
-- =============================================================================
SELECT 
  sku_id,
  title,
  brand,
  color,
  price_aud,
  stock_quantity
FROM `your-project-id.product_embeddings.products_with_vectors`
WHERE 
  brand = 'UrbanCare'  -- Change brand name
  AND color = 'White'  -- Change color
ORDER BY price_aud ASC;


-- =============================================================================
-- 10. Gender-Based Product Distribution
-- =============================================================================
SELECT 
  gender,
  category,
  COUNT(*) as product_count,
  AVG(price_aud) as avg_price,
  SUM(stock_quantity) as total_stock
FROM `your-project-id.product_embeddings.products_with_vectors`
GROUP BY gender, category
ORDER BY gender, product_count DESC;


-- =============================================================================
-- 11. Find Similar Products Within Same Category
-- =============================================================================
WITH target_product AS (
  SELECT 
    embedding,
    category,
    title as target_title
  FROM `your-project-id.product_embeddings.products_with_vectors`
  WHERE sku_id = 'SKU-CLO-WOM-0001'  -- Change this SKU
)

SELECT 
  p.sku_id,
  p.title,
  p.subcategory,
  p.brand,
  p.color,
  p.price_aud,
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
WHERE 
  p.category = t.category  -- Same category only
  AND p.sku_id != 'SKU-CLO-WOM-0001'  -- Exclude target
ORDER BY similarity_score DESC
LIMIT 15;


-- =============================================================================
-- 12. Price Point Analysis
-- =============================================================================
SELECT 
  CASE 
    WHEN price_aud < 50 THEN 'Budget (< $50)'
    WHEN price_aud < 100 THEN 'Mid-range ($50-100)'
    WHEN price_aud < 200 THEN 'Premium ($100-200)'
    ELSE 'Luxury ($200+)'
  END as price_segment,
  COUNT(*) as product_count,
  AVG(margin_percent) as avg_margin,
  SUM(stock_quantity) as total_stock
FROM `your-project-id.product_embeddings.products_with_vectors`
GROUP BY price_segment
ORDER BY 
  CASE 
    WHEN price_segment = 'Budget (< $50)' THEN 1
    WHEN price_segment = 'Mid-range ($50-100)' THEN 2
    WHEN price_segment = 'Premium ($100-200)' THEN 3
    ELSE 4
  END;


-- =============================================================================
-- 13. Cross-Sell Recommendations (Different Category, Similar Embedding)
-- =============================================================================
WITH target_product AS (
  SELECT 
    embedding,
    category as target_category,
    title as target_title
  FROM `your-project-id.product_embeddings.products_with_vectors`
  WHERE sku_id = 'SKU-BEA-0001'  -- Product someone is viewing
)

SELECT 
  p.sku_id,
  p.title,
  p.category,
  p.brand,
  p.price_aud,
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
WHERE 
  p.category != t.target_category  -- Different category for cross-sell
ORDER BY similarity_score DESC
LIMIT 10;


-- =============================================================================
-- 14. Export Data for Analysis (with embeddings)
-- =============================================================================
-- Note: This exports to Google Cloud Storage
-- Uncomment and modify the path to use
/*
EXPORT DATA OPTIONS(
  uri='gs://your-bucket-name/product_embeddings_export/*.json',
  format='JSON'
) AS
SELECT 
  sku_id,
  title,
  category,
  brand,
  price_aud,
  embedding
FROM `your-project-id.product_embeddings.products_with_vectors`;
*/


-- =============================================================================
-- 15. Embedding Quality Check
-- =============================================================================
-- Verify all embeddings have the correct dimension (should be 768 for gecko)
SELECT 
  ARRAY_LENGTH(embedding) as embedding_size,
  COUNT(*) as product_count
FROM `your-project-id.product_embeddings.products_with_vectors`
GROUP BY embedding_size
ORDER BY product_count DESC;
