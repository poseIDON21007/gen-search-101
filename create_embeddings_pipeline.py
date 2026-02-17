"""
Product Embeddings Pipeline
Creates vector embeddings for product data using Google Vertex AI
and stores them in BigQuery.
"""

import json
import os
from typing import List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm

from google.cloud import aiplatform
from google.cloud import bigquery
from vertexai.language_models import TextEmbeddingModel


class ProductEmbeddingsPipeline:
    """Pipeline for creating and storing product embeddings."""
    
    def __init__(
        self,
        project_id: str,
        region: str,
        dataset_id: str,
        table_id: str
    ):
        """Initialize the pipeline with GCP configuration.
        
        Args:
            project_id: Google Cloud Project ID
            region: GCP region (e.g., 'us-central1')
            dataset_id: BigQuery dataset ID
            table_id: BigQuery table ID
        """
        self.project_id = project_id
        self.region = region
        self.dataset_id = dataset_id
        self.table_id = table_id
        
        # Initialize Vertex AI
        aiplatform.init(project=project_id, location=region)
        
        # Initialize BigQuery client
        self.bq_client = bigquery.Client(project=project_id)
        
        # Initialize embedding model (using latest stable version)
        self.embedding_model = TextEmbeddingModel.from_pretrained(
            "text-embedding-004"
        )
        
        print(f"✓ Initialized pipeline for project: {project_id}")
        print(f"✓ Using region: {region}")
        print(f"✓ Target table: {dataset_id}.{table_id}")
    
    def create_product_text(self, product: Dict[str, Any]) -> str:
        """Create a rich text representation of the product for embedding.
        
        Args:
            product: Product dictionary
            
        Returns:
            Formatted text string for embedding
        """
        # Combine key product fields into a rich text representation
        text_parts = [
            f"Product: {product.get('title', '')}",
            f"Description: {product.get('description', '')}",
            f"Category: {product.get('category', '')}",
            f"Subcategory: {product.get('subcategory', '')}",
            f"Brand: {product.get('brand', '')}",
            f"Color: {product.get('color', '')}",
            f"Tags: {', '.join(product.get('tags', []))}"
        ]
        
        return " | ".join(text_parts)
    
    def create_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 5
    ) -> List[List[float]]:
        """Create embeddings for a batch of texts.
        
        Args:
            texts: List of text strings to embed
            batch_size: Number of texts to process at once
            
        Returns:
            List of embedding vectors
        """
        all_embeddings = []
        
        # Process in batches to avoid API limits
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = self.embedding_model.get_embeddings(batch)
            all_embeddings.extend([emb.values for emb in embeddings])
        
        return all_embeddings
    
    def create_bigquery_table(self, schema_fields: List[bigquery.SchemaField]):
        """Create BigQuery table if it doesn't exist.
        
        Args:
            schema_fields: List of BigQuery schema fields
        """
        dataset_ref = self.bq_client.dataset(self.dataset_id)
        
        # Create dataset if it doesn't exist
        try:
            self.bq_client.get_dataset(dataset_ref)
            print(f"✓ Dataset {self.dataset_id} already exists")
        except Exception:
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = self.region
            self.bq_client.create_dataset(dataset)
            print(f"✓ Created dataset {self.dataset_id}")
        
        # Create table if it doesn't exist
        table_ref = dataset_ref.table(self.table_id)
        
        try:
            self.bq_client.get_table(table_ref)
            print(f"✓ Table {self.table_id} already exists")
        except Exception:
            table = bigquery.Table(table_ref, schema=schema_fields)
            self.bq_client.create_table(table)
            print(f"✓ Created table {self.table_id}")
    
    def load_json_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Load products from a JSON file.
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            List of product dictionaries
        """
        with open(file_path, 'r') as f:
            products = json.load(f)
        print(f"✓ Loaded {len(products)} products from {Path(file_path).name}")
        return products
    
    def process_products(
        self,
        products: List[Dict[str, Any]],
        batch_size: int = 5
    ) -> List[Dict[str, Any]]:
        """Process products and create embeddings.
        
        Args:
            products: List of product dictionaries
            batch_size: Batch size for embedding API calls
            
        Returns:
            List of products with embeddings added
        """
        print(f"\n📊 Processing {len(products)} products...")
        
        # Create text representations
        product_texts = [self.create_product_text(p) for p in products]
        
        # Create embeddings with progress bar
        all_embeddings = []
        with tqdm(total=len(product_texts), desc="Creating embeddings") as pbar:
            for i in range(0, len(product_texts), batch_size):
                batch = product_texts[i:i + batch_size]
                embeddings = self.embedding_model.get_embeddings(batch)
                all_embeddings.extend([emb.values for emb in embeddings])
                pbar.update(len(batch))
        
        # Add embeddings to products
        for product, embedding in zip(products, all_embeddings):
            product['embedding'] = embedding
        
        print(f"✓ Created {len(all_embeddings)} embeddings")
        return products
    
    def insert_to_bigquery(
        self,
        products_with_embeddings: List[Dict[str, Any]],
        batch_size: int = 100
    ):
        """Insert products with embeddings into BigQuery.
        
        Args:
            products_with_embeddings: Products with embedding vectors
            batch_size: Batch size for BigQuery insertions
        """
        table_ref = f"{self.project_id}.{self.dataset_id}.{self.table_id}"
        
        # Prepare rows for BigQuery
        rows_to_insert = []
        for product in products_with_embeddings:
            # Convert store_availability dict to JSON string for BigQuery JSON field
            store_avail = product.get('store_availability')
            if store_avail and isinstance(store_avail, dict):
                store_avail = json.dumps(store_avail)
            
            row = {
                'sku_id': product.get('sku_id'),
                'title': product.get('title'),
                'description': product.get('description'),
                'category': product.get('category'),
                'subcategory': product.get('subcategory'),
                'brand': product.get('brand'),
                'gender': product.get('gender'),
                'color': product.get('color'),
                'size': product.get('size'),
                'price_aud': product.get('price_aud'),
                'margin_percent': product.get('margin_percent'),
                'stock_quantity': product.get('stock_quantity'),
                'fulfillment_eta_days': product.get('fulfillment_eta_days'),
                'discount_percent': product.get('discount_percent'),
                'warranty_information': product.get('warranty_information'),
                'return_policy': product.get('return_policy'),
                'store_availability': store_avail,
                'tags': product.get('tags', []),
                'embedding': product['embedding']
            }
            rows_to_insert.append(row)
        
        # Insert in batches
        print(f"\n📤 Inserting {len(rows_to_insert)} rows to BigQuery...")
        
        errors = []
        with tqdm(total=len(rows_to_insert), desc="Inserting to BigQuery") as pbar:
            for i in range(0, len(rows_to_insert), batch_size):
                batch = rows_to_insert[i:i + batch_size]
                insert_errors = self.bq_client.insert_rows_json(table_ref, batch)
                if insert_errors:
                    errors.extend(insert_errors)
                pbar.update(len(batch))
        
        if errors:
            print(f"⚠ Encountered {len(errors)} errors during insertion")
            for error in errors[:5]:  # Show first 5 errors
                print(f"  Error: {error}")
        else:
            print(f"✓ Successfully inserted all rows to BigQuery")
    
    def run_pipeline(self, json_files: List[str], batch_size: int = 5):
        """Run the complete pipeline for multiple JSON files.
        
        Args:
            json_files: List of JSON file paths
            batch_size: Batch size for API calls
        """
        print("🚀 Starting Product Embeddings Pipeline\n")
        
        # Define BigQuery schema
        schema = [
            bigquery.SchemaField("sku_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("title", "STRING"),
            bigquery.SchemaField("description", "STRING"),
            bigquery.SchemaField("category", "STRING"),
            bigquery.SchemaField("subcategory", "STRING"),
            bigquery.SchemaField("brand", "STRING"),
            bigquery.SchemaField("gender", "STRING"),
            bigquery.SchemaField("color", "STRING"),
            bigquery.SchemaField("size", "STRING"),
            bigquery.SchemaField("price_aud", "FLOAT"),
            bigquery.SchemaField("margin_percent", "INTEGER"),
            bigquery.SchemaField("stock_quantity", "INTEGER"),
            bigquery.SchemaField("fulfillment_eta_days", "INTEGER"),
            bigquery.SchemaField("discount_percent", "INTEGER"),
            bigquery.SchemaField("warranty_information", "STRING"),
            bigquery.SchemaField("return_policy", "STRING"),
            bigquery.SchemaField("store_availability", "JSON"),
            bigquery.SchemaField("tags", "STRING", mode="REPEATED"),
            bigquery.SchemaField("embedding", "FLOAT", mode="REPEATED"),
        ]
        
        # Create BigQuery table
        self.create_bigquery_table(schema)
        
        # Process each JSON file
        for json_file in json_files:
            print(f"\n{'='*60}")
            print(f"Processing: {Path(json_file).name}")
            print(f"{'='*60}")
            
            # Load products
            products = self.load_json_file(json_file)
            
            # Create embeddings
            products_with_embeddings = self.process_products(
                products,
                batch_size=batch_size
            )
            
            # Insert to BigQuery
            self.insert_to_bigquery(products_with_embeddings)
        
        print(f"\n{'='*60}")
        print("✅ Pipeline completed successfully!")
        print(f"{'='*60}")
        print(f"\nYou can now query your data in BigQuery:")
        print(f"  Dataset: {self.dataset_id}")
        print(f"  Table: {self.table_id}")


def main():
    """Main function to run the pipeline."""
    # Load environment variables
    load_dotenv()
    
    # Get configuration from environment
    project_id = os.getenv('GCP_PROJECT_ID')
    region = os.getenv('GCP_REGION', 'us-central1')
    dataset_id = os.getenv('BIGQUERY_DATASET_ID', 'product_embeddings')
    table_id = os.getenv('BIGQUERY_TABLE_ID', 'products_with_vectors')
    
    if not project_id:
        raise ValueError(
            "GCP_PROJECT_ID not found in environment. "
            "Please set it in .env file or environment variables."
        )
    
    # Initialize pipeline
    pipeline = ProductEmbeddingsPipeline(
        project_id=project_id,
        region=region,
        dataset_id=dataset_id,
        table_id=table_id
    )
    
    # Get all JSON files in current directory
    current_dir = Path(__file__).parent
    json_files = [
        'beauty_personal_care_500.json',
        'gifts_photo_products_500.json',
        'kmart_clothing_accessories_structured.json',
        'kmart_home_living_products_structured.json',
        'nursery_kids_500.json'
    ]
    
    # Convert to full paths
    json_file_paths = [str(current_dir / file) for file in json_files]
    
    # Filter to only existing files
    existing_files = [f for f in json_file_paths if Path(f).exists()]
    
    if not existing_files:
        print("❌ No JSON files found!")
        return
    
    print(f"Found {len(existing_files)} JSON files to process")
    
    # Run the pipeline
    pipeline.run_pipeline(existing_files, batch_size=5)


if __name__ == "__main__":
    main()
