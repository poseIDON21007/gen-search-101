"""
Ranking Agent
Re-ranks candidate products by relevance using weighted scoring.
Per architecture: Ranking Agent (Vertex AutoModel / XGBoost) → Top 5 Products
For hackathon we use a weighted scoring heuristic (no trained model yet).
"""

import json
from typing import Dict, Any, List


class RankingAgent:
    """Ranking Agent: scores and re-ranks candidates to produce Top-N products.

    Architecture position: after Candidate Generation, before Action Agent.
    Uses a weighted feature scoring approach (pluggable with AutoML later).
    """

    # Feature weights (tuneable)
    WEIGHTS = {
        "similarity": 0.45,   # Vector similarity is primary signal
        "price_fit": 0.20,    # How well price matches budget
        "stock": 0.10,        # Prefer in-stock items
        "relevance": 0.15,    # Keyword / filter match bonus
        "popularity": 0.10,   # Stock-as-proxy for popularity
    }

    def __init__(self):
        print("✓ Ranking Agent initialized")

    def rank(
        self,
        pipeline_data: Dict[str, Any],
        top_n: int = 5,
    ) -> Dict[str, Any]:
        """Rank candidates and return top N.

        Args:
            pipeline_data: Full pipeline dict with candidates
            top_n: Number of top products to return

        Returns:
            pipeline_data with ranked_products added
        """
        candidates = pipeline_data.get("candidates", {}).get("products", [])
        if not candidates:
            pipeline_data["ranked_products"] = []
            return pipeline_data

        intent_filters = pipeline_data.get("filters", {})
        price_range = pipeline_data.get("attributes", {}).get("price_range", {})
        if isinstance(price_range, dict):
            target_max = price_range.get("max")
            target_min = price_range.get("min", 0)
        else:
            target_max = None
            target_min = 0

        scored = []
        for product in candidates:
            score = self._score_product(product, intent_filters, target_min, target_max)
            scored.append({**product, "ranking_score": score})

        scored.sort(key=lambda x: x["ranking_score"], reverse=True)
        top_products = scored[:top_n]

        pipeline_data["ranked_products"] = top_products
        pipeline_data["ranking_meta"] = {
            "total_candidates": len(candidates),
            "top_n": top_n,
            "score_range": {
                "min": round(scored[-1]["ranking_score"], 4) if scored else 0,
                "max": round(scored[0]["ranking_score"], 4) if scored else 0,
            },
        }
        return pipeline_data

    def _score_product(
        self,
        product: Dict[str, Any],
        filters: Dict[str, Any],
        target_min: float,
        target_max: float,
    ) -> float:
        """Compute weighted score for a single product."""

        # 1. Similarity score (from vector search, already 0-1)
        sim = product.get("similarity_score", 0)

        # 2. Price fit (1.0 if within range, decays outside)
        price = product.get("price_aud", 0)
        price_fit = self._price_fit_score(price, target_min, target_max)

        # 3. Stock score (1.0 if well stocked, lower otherwise)
        stock = product.get("stock_quantity", 0)
        stock_score = min(stock / 100.0, 1.0) if stock > 0 else 0

        # 4. Relevance bonus (filter match)
        relevance = self._filter_match_score(product, filters)

        # 5. Popularity proxy (stock level as proxy)
        popularity = min(stock / 200.0, 1.0) if stock > 0 else 0

        total = (
            self.WEIGHTS["similarity"] * sim
            + self.WEIGHTS["price_fit"] * price_fit
            + self.WEIGHTS["stock"] * stock_score
            + self.WEIGHTS["relevance"] * relevance
            + self.WEIGHTS["popularity"] * popularity
        )
        return round(total, 6)

    def _price_fit_score(self, price: float, target_min: float, target_max: float) -> float:
        if target_max is None and target_min is None:
            return 0.5  # Neutral if no preference

        if target_max is not None and target_min is not None:
            if target_min <= price <= target_max:
                return 1.0
            elif price < target_min:
                return max(0, 1 - (target_min - price) / target_min) if target_min > 0 else 0.5
            else:
                return max(0, 1 - (price - target_max) / target_max) if target_max > 0 else 0
        elif target_max is not None:
            return 1.0 if price <= target_max else max(0, 1 - (price - target_max) / target_max)
        else:
            return 1.0 if price >= target_min else max(0, price / target_min) if target_min > 0 else 0.5

    def _filter_match_score(self, product: Dict[str, Any], filters: Dict[str, Any]) -> float:
        if not filters:
            return 0.5

        matches = 0
        total = 0

        for key in ["brand", "color", "gender", "subcategory"]:
            filter_val = filters.get(key)
            if filter_val:
                total += 1
                product_val = product.get(key, "")
                if product_val and filter_val.lower() in product_val.lower():
                    matches += 1

        return matches / total if total > 0 else 0.5


if __name__ == "__main__":
    agent = RankingAgent()

    sample = {
        "attributes": {"price_range": {"min": 20, "max": 80}},
        "filters": {"brand": None, "color": None, "subcategory": "Skincare"},
        "candidates": {
            "products": [
                {"sku_id": "SKU-1", "title": "Product A", "price_aud": 45.0, "stock_quantity": 50, "similarity_score": 0.85, "subcategory": "Skincare"},
                {"sku_id": "SKU-2", "title": "Product B", "price_aud": 120.0, "stock_quantity": 10, "similarity_score": 0.90, "subcategory": "Haircare"},
                {"sku_id": "SKU-3", "title": "Product C", "price_aud": 30.0, "stock_quantity": 200, "similarity_score": 0.70, "subcategory": "Skincare"},
            ]
        },
    }

    result = agent.rank(sample, top_n=2)
    for p in result["ranked_products"]:
        print(f"  {p['sku_id']} | {p['title']} | ${p['price_aud']} | rank_score:{p['ranking_score']}")
