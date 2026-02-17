"""
Candidate Generation Agent
Retrieves relevant products using Vertex AI Search (Vector + Keyword hybrid).
Per architecture: Candidate Generation Agent → Vertex AI Search (Vector + Keyword)
"""

import os
import json
from typing import Dict, Any, List
from google.cloud import bigquery
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel
from dotenv import load_dotenv


class CandidateGenerationAgent:
    """Candidate Generation Agent: hybrid vector + keyword search.

    Architecture position: after Constraint Agent, before Ranking Agent.
    Uses Vertex AI Search via BigQuery vector similarity + keyword filtering.
    """

    def __init__(self, project_id: str = None, dataset_id: str = "product_embeddings",
                 table_id: str = "products_with_vectors", region: str = "us-central1"):
        load_dotenv()
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
        self.dataset_id = dataset_id
        self.table_id = table_id
        self.region = region
        self.table_ref = f"{self.project_id}.{self.dataset_id}.{self.table_id}"

        self.bq_client = bigquery.Client(project=self.project_id)
        aiplatform.init(project=self.project_id, location=self.region)
        self.embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")

        print("✓ Candidate Generation Agent initialized")

    def generate_candidates(
        self,
        constrained_intent: Dict[str, Any],
        top_k: int = 50,
    ) -> Dict[str, Any]:
        """Generate candidate products using hybrid search.

        Args:
            constrained_intent: Output from Constraint Agent
            top_k: Number of candidates to retrieve

        Returns:
            constrained_intent augmented with candidates list
        """
        # Build the search query text from intent
        search_text = self._build_search_text(constrained_intent)

        # Get embedding for the search text
        query_embedding = self._get_embedding(search_text)

        # Get constraint filters
        bq_filter = constrained_intent.get("constraints", {}).get(
            "bq_filter_clause", "1=1"
        )

        # Run hybrid search: vector similarity + constraint filters
        candidates = self._hybrid_search(query_embedding, bq_filter, top_k)

        # Fallback: if strict filters returned no results, relax to just stock + category
        if not candidates:
            relaxed_filter = "stock_quantity >= 1"
            category = constrained_intent.get("primary_category")
            if category and category != "Unknown":
                relaxed_filter += f" AND category LIKE '%{category}%'"
            candidates = self._hybrid_search(query_embedding, relaxed_filter, top_k)
            search_mode = "relaxed"
        else:
            search_mode = "strict"

        # Attach to intent
        constrained_intent["candidates"] = {
            "search_text": search_text,
            "search_mode": search_mode,
            "total_candidates": len(candidates),
            "products": candidates,
        }
        return constrained_intent

    def _build_search_text(self, intent: Dict[str, Any]) -> str:
        """Build a rich search text from intent fields."""
        parts = []

        product_type = intent.get("product_type", "")
        if product_type and product_type != "Unknown Product":
            parts.append(product_type)

        category = intent.get("primary_category", "")
        if category and category != "Unknown":
            parts.append(category)

        subcategory = intent.get("subcategory", "")
        if subcategory:
            parts.append(subcategory)

        # Use case
        attrs = intent.get("attributes", {})
        use_case = attrs.get("use_case")
        if use_case:
            parts.append(f"for {use_case}")

        # Filters
        filters = intent.get("filters", {})
        color = filters.get("color")
        if color:
            parts.append(color)
        brand = filters.get("brand")
        if brand:
            parts.append(brand)
        gender = filters.get("gender")
        if gender:
            parts.append(f"for {gender}")

        # Weather tags from context
        context = intent.get("context", {})
        weather_tags = context.get("weather_suggested_tags", [])
        if weather_tags:
            parts.extend(weather_tags[:3])

        return " ".join(parts) if parts else "products"

    def _get_embedding(self, text: str) -> List[float]:
        embeddings = self.embedding_model.get_embeddings([text])
        return embeddings[0].values

    def _hybrid_search(
        self,
        query_embedding: List[float],
        filter_clause: str,
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """Hybrid vector + keyword search using BigQuery."""

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
            p.gender,
            p.color,
            p.size,
            p.price_aud,
            p.stock_quantity,
            p.tags,
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
        WHERE {filter_clause}
        ORDER BY similarity_score DESC
        LIMIT {top_k}
        """

        results = list(self.bq_client.query(query).result())
        candidates = []
        for row in results:
            candidates.append({
                "sku_id": row.sku_id,
                "title": row.title,
                "description": row.description,
                "category": row.category,
                "subcategory": row.subcategory,
                "brand": row.brand,
                "gender": row.gender,
                "color": row.color,
                "size": row.size,
                "price_aud": float(row.price_aud) if row.price_aud else 0,
                "stock_quantity": row.stock_quantity,
                "tags": list(row.tags) if row.tags else [],
                "similarity_score": float(row.similarity_score) if row.similarity_score else 0,
            })
        return candidates


if __name__ == "__main__":
    agent = CandidateGenerationAgent()

    sample = {
        "primary_category": "Beauty & Personal Care",
        "subcategory": "Skincare",
        "product_type": "Moisturizer",
        "attributes": {"use_case": "sensitive skin", "price_range": {"max": 80}},
        "filters": {"brand": None, "color": None, "subcategory": "Skincare"},
        "intent_confidence": 0.9,
        "context": {"weather_suggested_tags": ["summer", "lightweight"]},
        "constraints": {
            "bq_filter_clause": "stock_quantity >= 1 AND price_aud <= 80 AND category = 'Beauty & Personal Care'",
        },
    }

    result = agent.generate_candidates(sample, top_k=5)
    for p in result["candidates"]["products"]:
        print(f"  {p['sku_id']} | {p['title'][:40]} | ${p['price_aud']} | sim:{p['similarity_score']:.4f}")
