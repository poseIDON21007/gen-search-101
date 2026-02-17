"""
Constraint Agent - Business Rules Filtering
Applies pricing limits and inventory availability checks.
Per architecture: Constraint Agent → Pricing / Inventory Check
"""

import os
import json
from typing import Dict, Any, List, Optional
from google.cloud import bigquery
from dotenv import load_dotenv


class ConstraintAgent:
    """Constraint Agent: filters based on business rules — pricing and inventory.

    Architecture position: after Context Agent, before Candidate Generation Agent.
    """

    def __init__(self, project_id: str = None, dataset_id: str = "product_embeddings",
                 table_id: str = "products_with_vectors"):
        load_dotenv()
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
        self.dataset_id = dataset_id
        self.table_id = table_id
        self.table_ref = f"{self.project_id}.{self.dataset_id}.{self.table_id}"
        self.bq_client = bigquery.Client(project=self.project_id)

        # Business rules
        self.MIN_STOCK_THRESHOLD = 1  # Must have at least 1 in stock
        self.MAX_PRICE_CAP = 5000.0   # Safety cap

        print("✓ Constraint Agent initialized")

    def apply_constraints(self, enriched_intent: Dict[str, Any]) -> Dict[str, Any]:
        """Apply business constraints to the enriched intent.

        Args:
            enriched_intent: Output from Context Agent

        Returns:
            Enriched intent with constraints block added
        """
        constraints = {}

        # 1. Price constraints
        price_constraints = self._resolve_price_constraints(enriched_intent)
        constraints["price"] = price_constraints

        # 2. Inventory constraints
        inventory_info = self._check_inventory_availability(enriched_intent)
        constraints["inventory"] = inventory_info

        # 3. Category availability
        category = enriched_intent.get("primary_category")
        if category:
            cat_stats = self._get_category_stats(category)
            constraints["category_stats"] = cat_stats

        # 4. Build BigQuery filter clause for downstream agents
        bq_filters = self._build_bq_filters(enriched_intent, price_constraints)
        constraints["bq_filter_clause"] = bq_filters

        enriched_intent["constraints"] = constraints
        return enriched_intent

    def _resolve_price_constraints(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve price bounds from intent attributes."""
        attrs = intent.get("attributes", {})
        price_range = attrs.get("price_range", {})

        min_price = None
        max_price = None

        if price_range:
            if isinstance(price_range, dict):
                min_price = price_range.get("min")
                max_price = price_range.get("max")
            elif hasattr(price_range, "min"):
                min_price = price_range.min
                max_price = price_range.max

        # Apply safety cap
        if max_price is None or max_price > self.MAX_PRICE_CAP:
            max_price = self.MAX_PRICE_CAP

        if min_price is not None and min_price < 0:
            min_price = 0

        return {
            "min_price": min_price,
            "max_price": max_price,
            "label": price_range.get("label", "any") if isinstance(price_range, dict) else "any",
        }

    def _check_inventory_availability(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Check inventory levels for the target category."""
        category = intent.get("primary_category")
        if not category or category == "Unknown":
            return {"status": "unknown", "message": "No category identified"}

        try:
            query = f"""
            SELECT 
                COUNT(*) as total_products,
                SUM(CASE WHEN stock_quantity > 0 THEN 1 ELSE 0 END) as in_stock,
                AVG(stock_quantity) as avg_stock,
                MIN(price_aud) as min_price,
                MAX(price_aud) as max_price
            FROM `{self.table_ref}`
            WHERE category LIKE '%{category}%'
            """
            result = list(self.bq_client.query(query).result())[0]
            return {
                "status": "available",
                "total_products": result.total_products,
                "in_stock_count": result.in_stock,
                "avg_stock": float(result.avg_stock) if result.avg_stock else 0,
                "price_range_actual": {
                    "min": float(result.min_price) if result.min_price else 0,
                    "max": float(result.max_price) if result.max_price else 0,
                },
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _get_category_stats(self, category: str) -> Dict[str, Any]:
        """Get category-level stats for constraint decisions."""
        try:
            query = f"""
            SELECT 
                subcategory,
                COUNT(*) as count,
                COUNT(DISTINCT brand) as brands
            FROM `{self.table_ref}`
            WHERE category LIKE '%{category}%'
            GROUP BY subcategory
            ORDER BY count DESC
            LIMIT 10
            """
            results = list(self.bq_client.query(query).result())
            return {
                "subcategories": [
                    {"name": r.subcategory, "count": r.count, "brands": r.brands}
                    for r in results
                ]
            }
        except Exception as e:
            return {"error": str(e)}

    def _build_bq_filters(self, intent: Dict[str, Any], price: Dict[str, Any]) -> str:
        """Build WHERE clause fragments for BigQuery queries downstream."""
        conditions = []

        # Stock filter
        conditions.append(f"stock_quantity >= {self.MIN_STOCK_THRESHOLD}")

        # Price filters
        if price.get("min_price") is not None:
            conditions.append(f"price_aud >= {price['min_price']}")
        if price.get("max_price") is not None:
            conditions.append(f"price_aud <= {price['max_price']}")

        # Category filter (use LIKE for hierarchical categories like "Clothing & Accessories > Footwear")
        category = intent.get("primary_category")
        if category and category != "Unknown":
            conditions.append(f"category LIKE '%{category}%'")

        # Subcategory filter (use LIKE for fuzzy matching)
        filters = intent.get("filters", {})
        subcategory = filters.get("subcategory")
        if subcategory:
            conditions.append(f"(subcategory LIKE '%{subcategory}%' OR category LIKE '%{subcategory}%')")

        # Brand filter
        brand = filters.get("brand")
        if brand:
            conditions.append(f"brand = '{brand}'")

        # Color filter
        color = filters.get("color")
        if color:
            conditions.append(f"color = '{color}'")

        return " AND ".join(conditions) if conditions else "1=1"


if __name__ == "__main__":
    agent = ConstraintAgent()

    sample_enriched = {
        "primary_category": "Beauty & Personal Care",
        "subcategory": "Skincare",
        "product_type": "Moisturizer",
        "attributes": {
            "price_range": {"min": 20, "max": 80, "label": "affordable"},
            "urgency": "normal",
        },
        "filters": {"brand": None, "color": None, "subcategory": "Skincare"},
        "intent_confidence": 0.9,
        "context": {"weather": {"temp_c": 32, "season": "summer"}},
    }

    result = agent.apply_constraints(sample_enriched)
    print(json.dumps(result, indent=2, default=str))
