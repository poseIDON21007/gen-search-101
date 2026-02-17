"""
Action Agent - Natural Language Response Generation
Generates a user-friendly natural language response from ranked products.
Per architecture: Action Agent → Gemini 1.5 Flash
"""

import os
import json
from typing import Dict, Any, List
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig


class ActionAgent:
    """Action Agent: generates natural language response using Gemini 2.5 Flash.

    Architecture position: final agent — takes Top 5 products and produces user response.
    """

    def __init__(self, project_id: str = None, region: str = "us-central1"):
        load_dotenv()
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
        self.region = region

        vertexai.init(project=self.project_id, location=self.region)
        self.model = GenerativeModel("gemini-2.5-flash")
        print("✓ Action Agent initialized (Gemini 2.5 Flash)")

    def generate_response(self, pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a natural language response from ranked products.

        Args:
            pipeline_data: Full pipeline dict with ranked_products

        Returns:
            pipeline_data with 'response' field added
        """
        ranked = pipeline_data.get("ranked_products", [])
        if not ranked:
            pipeline_data["response"] = "Sorry, I couldn't find any products matching your request. Could you try rephrasing your query?"
            return pipeline_data

        # Build prompt
        prompt = self._build_prompt(pipeline_data, ranked)

        try:
            config = GenerationConfig(
                temperature=0.7,
                max_output_tokens=1024,
            )
            response = self.model.generate_content(prompt, generation_config=config)
            pipeline_data["response"] = response.text.strip()
        except Exception as e:
            # Fallback to template response
            pipeline_data["response"] = self._template_response(pipeline_data, ranked)
            pipeline_data["response_source"] = "template_fallback"
            pipeline_data["response_error"] = str(e)

        return pipeline_data

    def _build_prompt(self, data: Dict[str, Any], products: List[Dict[str, Any]]) -> str:
        product_type = data.get("product_type", "products")
        category = data.get("primary_category", "")
        use_case = data.get("attributes", {}).get("use_case", "")
        weather = data.get("context", {}).get("weather", {})

        product_list = ""
        for i, p in enumerate(products, 1):
            product_list += f"""
{i}. **{p.get('title', 'Unknown')}**
   - Brand: {p.get('brand', 'N/A')}
   - Price: ${p.get('price_aud', 0):.2f} AUD
   - Color: {p.get('color', 'N/A')}
   - Stock: {p.get('stock_quantity', 0)} units
   - Match Score: {p.get('ranking_score', p.get('similarity_score', 0)):.0%}
"""

        prompt = f"""You are a helpful shopping assistant for an Australian retail store.

The customer asked about: {product_type}
Category: {category}
{'Use case: ' + use_case if use_case else ''}
{'Current weather: ' + str(weather.get('temp_c', '')) + '°C, ' + weather.get('condition', '') if weather else ''}

Here are the top matching products:
{product_list}

Write a friendly, concise response (3-5 sentences) that:
1. Acknowledges what they're looking for
2. Highlights the top 2-3 recommendations with key details (name, price)
3. Mentions why they're good matches
4. Keeps it conversational and helpful

Do NOT use markdown formatting. Write plain text only."""

        return prompt

    def _template_response(self, data: Dict[str, Any], products: List[Dict[str, Any]]) -> str:
        """Fallback template response when Gemini is unavailable."""
        product_type = data.get("product_type", "products")
        lines = [f"Here are my top recommendations for {product_type}:\n"]

        for i, p in enumerate(products[:5], 1):
            lines.append(
                f"{i}. {p.get('title', 'Unknown')} - ${p.get('price_aud', 0):.2f} AUD "
                f"({p.get('brand', 'N/A')}, {p.get('color', 'N/A')})"
            )

        lines.append(f"\nAll {len(products)} products are currently in stock and ready to ship!")
        return "\n".join(lines)


if __name__ == "__main__":
    agent = ActionAgent()

    sample = {
        "primary_category": "Beauty & Personal Care",
        "product_type": "Skincare",
        "attributes": {"use_case": "sensitive skin"},
        "context": {"weather": {"temp_c": 32, "condition": "Sunny"}},
        "ranked_products": [
            {"sku_id": "SKU-1", "title": "FreshSkin Premium Moisturizer", "brand": "FreshSkin", "price_aud": 45.0, "color": "White", "stock_quantity": 50, "ranking_score": 0.85},
            {"sku_id": "SKU-2", "title": "GlowLab Gentle Cleanser", "brand": "GlowLab", "price_aud": 32.0, "color": "Pink", "stock_quantity": 120, "ranking_score": 0.80},
        ],
    }

    result = agent.generate_response(sample)
    print(result["response"])
