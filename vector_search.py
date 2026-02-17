"""
Vector Search Utilities
Query and search products using vector embeddings in BigQuery.
"""

import os
from typing import List, Dict, Any
from dotenv import load_dotenv

from google.cloud import bigquery
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel


class VectorSearcher:
    """Utilities for searching products using vector embeddings."""
    
    def __init__(self, project_id: str, dataset_id: str, table_id: str, region: str = "us-central1"):
        """Initialize the vector searcher.
        
        Args:
            project_id: Google Cloud Project ID
            dataset_id: BigQuery dataset ID
            table_id: BigQuery table ID
            region: GCP region
        """
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.table_id = table_id
        self.region = region
        
        # Initialize clients
        self.bq_client = bigquery.Client(project=project_id)
        aiplatform.init(project=project_id, location=region)
        self.embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")
        
        self.table_ref = f"{project_id}.{dataset_id}.{table_id}"
    
    def get_embedding_for_text(self, text: str) -> List[float]:
        """Get embedding vector for a text query.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        embeddings = self.embedding_model.get_embeddings([text])
        return embeddings[0].values
    
    def search_similar_products(
        self,
        query_text: str,
        top_k: int = 10,
        category_filter: str = None
    ) -> List[Dict[str, Any]]:
        """Search for products similar to the query text.
        
        Args:
            query_text: Natural language query
            top_k: Number of results to return
            category_filter: Optional category to filter by
            
        Returns:
            List of similar products with similarity scores
        """
        # Get embedding for query
        query_embedding = self.get_embedding_for_text(query_text)
        
        # Build filter clause
        filter_clause = ""
        if category_filter:
            filter_clause = f"WHERE category = '{category_filter}'"
        
        # Create SQL query for vector similarity search
        query = f"""
        WITH query_embedding AS (
          SELECT {query_embedding} AS embedding
        )
        SELECT 
          p.sku_id,
          p.title,
          p.description,
          p.category,
          p.subcategory,
          p.brand,
          p.color,
          p.price_aud,
          p.stock_quantity,
          -- Calculate cosine similarity
          (
            SELECT 
              SUM(p_elem * q_elem) / 
              (SQRT(SUM(p_elem * p_elem)) * SQRT(SUM(q_elem * q_elem)))
            FROM UNNEST(p.embedding) AS p_elem WITH OFFSET pos1
            JOIN UNNEST(q.embedding) AS q_elem WITH OFFSET pos2
            ON pos1 = pos2
          ) AS similarity_score
        FROM `{self.table_ref}` p
        CROSS JOIN query_embedding q
        {filter_clause}
        ORDER BY similarity_score DESC
        LIMIT {top_k}
        """
        
        query_job = self.bq_client.query(query)
        results = query_job.result()
        
        return [dict(row) for row in results]
    
    def find_similar_to_product(
        self,
        sku_id: str,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Find products similar to a specific product.
        
        Args:
            sku_id: SKU ID of the reference product
            top_k: Number of results to return
            
        Returns:
            List of similar products with similarity scores
        """
        query = f"""
        WITH target_product AS (
          SELECT embedding, title
          FROM `{self.table_ref}`
          WHERE sku_id = '{sku_id}'
        )
        SELECT 
          p.sku_id,
          p.title,
          p.description,
          p.category,
          p.subcategory,
          p.brand,
          p.color,
          p.price_aud,
          p.stock_quantity,
          (
            SELECT 
              SUM(p_elem * t_elem) / 
              (SQRT(SUM(p_elem * p_elem)) * SQRT(SUM(t_elem * t_elem)))
            FROM UNNEST(p.embedding) AS p_elem WITH OFFSET pos1
            JOIN UNNEST(t.embedding) AS t_elem WITH OFFSET pos2
            ON pos1 = pos2
          ) AS similarity_score
        FROM `{self.table_ref}` p
        CROSS JOIN target_product t
        WHERE p.sku_id != '{sku_id}'
        ORDER BY similarity_score DESC
        LIMIT {top_k}
        """
        
        query_job = self.bq_client.query(query)
        results = query_job.result()
        
        return [dict(row) for row in results]
    
    def get_product_by_sku(self, sku_id: str) -> Dict[str, Any]:
        """Get product details by SKU ID.
        
        Args:
            sku_id: SKU ID
            
        Returns:
            Product details
        """
        query = f"""
        SELECT 
          sku_id,
          title,
          description,
          category,
          subcategory,
          brand,
          color,
          size,
          price_aud,
          stock_quantity,
          tags
        FROM `{self.table_ref}`
        WHERE sku_id = '{sku_id}'
        """
        
        query_job = self.bq_client.query(query)
        results = list(query_job.result())
        
        return dict(results[0]) if results else None
    
    def search_by_filters(
        self,
        category: str = None,
        brand: str = None,
        min_price: float = None,
        max_price: float = None,
        color: str = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search products using traditional filters.
        
        Args:
            category: Category filter
            brand: Brand filter
            min_price: Minimum price
            max_price: Maximum price
            color: Color filter
            limit: Number of results
            
        Returns:
            List of matching products
        """
        conditions = []
        
        if category:
            conditions.append(f"category = '{category}'")
        if brand:
            conditions.append(f"brand = '{brand}'")
        if min_price is not None:
            conditions.append(f"price_aud >= {min_price}")
        if max_price is not None:
            conditions.append(f"price_aud <= {max_price}")
        if color:
            conditions.append(f"color = '{color}'")
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        query = f"""
        SELECT 
          sku_id,
          title,
          description,
          category,
          subcategory,
          brand,
          color,
          price_aud,
          stock_quantity
        FROM `{self.table_ref}`
        {where_clause}
        ORDER BY price_aud DESC
        LIMIT {limit}
        """
        
        query_job = self.bq_client.query(query)
        results = query_job.result()
        
        return [dict(row) for row in results]


def main():
    """Example usage of VectorSearcher."""
    load_dotenv()
    
    project_id = os.getenv('GCP_PROJECT_ID')
    dataset_id = os.getenv('BIGQUERY_DATASET_ID', 'product_embeddings')
    table_id = os.getenv('BIGQUERY_TABLE_ID', 'products_with_vectors')
    
    searcher = VectorSearcher(project_id, dataset_id, table_id)
    
    print("🔍 Vector Search Examples\n")
    
    # Example 1: Search by natural language query
    print("Example 1: Search for 'soft comfortable clothing for women'")
    print("-" * 60)
    results = searcher.search_similar_products(
        "soft comfortable clothing for women",
        top_k=5
    )
    
    for i, product in enumerate(results, 1):
        print(f"{i}. {product['title']}")
        print(f"   Category: {product['category']}")
        print(f"   Price: ${product['price_aud']:.2f}")
        print(f"   Similarity: {product['similarity_score']:.4f}")
        print()
    
    # Example 2: Find similar products
    if results:
        first_sku = results[0]['sku_id']
        print(f"\nExample 2: Products similar to {first_sku}")
        print("-" * 60)
        
        similar = searcher.find_similar_to_product(first_sku, top_k=5)
        
        for i, product in enumerate(similar, 1):
            print(f"{i}. {product['title']}")
            print(f"   Category: {product['category']}")
            print(f"   Similarity: {product['similarity_score']:.4f}")
            print()
    
    # Example 3: Filter search
    print("\nExample 3: Search by filters (Beauty & Personal Care)")
    print("-" * 60)
    filtered = searcher.search_by_filters(
        category="Beauty & Personal Care",
        min_price=20,
        max_price=100,
        limit=5
    )
    
    for i, product in enumerate(filtered, 1):
        print(f"{i}. {product['title']}")
        print(f"   Brand: {product['brand']}")
        print(f"   Price: ${product['price_aud']:.2f}")
        print()


if __name__ == "__main__":
    main()
