"""
Intent Agent - NLU and Slot Filling
Converts natural language queries to structured JSON using Gemini 2.5 Flash
"""

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig


@dataclass
class PriceRange:
    """Price range structure"""
    min: Optional[float] = None
    max: Optional[float] = None
    label: str = ""


@dataclass
class IntentAttributes:
    """Extracted intent attributes"""
    use_case: Optional[str] = None
    price_range: Optional[PriceRange] = None
    urgency: str = "normal"
    timeline_days: Optional[int] = None


@dataclass
class IntentFilters:
    """Product filters"""
    gender: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None
    brand: Optional[str] = None
    subcategory: Optional[str] = None


@dataclass
class ExtractedSlot:
    """Individual slot extraction"""
    slot: str
    value: str
    normalized: Any
    confidence: float = 1.0


@dataclass
class Intent:
    """Complete intent structure"""
    primary_category: str
    subcategory: Optional[str]
    product_type: str
    attributes: IntentAttributes
    filters: IntentFilters
    intent_confidence: float
    extracted_slots: List[ExtractedSlot]


class ProductTaxonomy:
    """Product taxonomy and normalization mappings"""
    
    # Category taxonomy
    CATEGORIES = {
        "Beauty & Personal Care": {
            "id": "CAT_BEAUTY_001",
            "subcategories": {
                "Haircare": ["shampoo", "conditioner", "hair product", "haircare"],
                "Skincare": ["moisturizer", "cleanser", "serum", "skincare"],
                "Grooming Kits": ["grooming kit", "grooming set", "men's grooming"],
                "Fragrances": ["perfume", "cologne", "fragrance", "scent"]
            }
        },
        "Clothing & Accessories": {
            "id": "CAT_CLOTHING_001",
            "subcategories": {
                "Athletic Wear": ["running shoes", "sneakers", "trainers", "athletic footwear"],
                "Casual Wear": ["t-shirt", "jeans", "casual clothing"],
                "Accessories": ["watch", "belt", "wallet", "bag"]
            }
        },
        "Home & Living": {
            "id": "CAT_HOME_001",
            "subcategories": {
                "Kitchenware": ["cookware", "utensils", "kitchen equipment"],
                "Furniture": ["chair", "table", "sofa", "bed"],
                "Decor": ["artwork", "vase", "decorative item"]
            }
        },
        "Gifts & Photo Products": {
            "id": "CAT_GIFTS_001",
            "subcategories": {
                "Photo Frames": ["photo frame", "picture frame"],
                "Gift Sets": ["gift set", "gift pack"]
            }
        },
        "Nursery & Kids": {
            "id": "CAT_KIDS_001",
            "subcategories": {
                "Toys": ["toy", "playset", "action figure"],
                "Kids Furniture": ["crib", "changing table", "kids bed"]
            }
        }
    }
    
    # Price range mappings
    PRICE_RANGES = {
        "budget": {"min": 0, "max": 50, "label": "budget"},
        "cheap": {"min": 0, "max": 50, "label": "budget"},
        "affordable": {"min": 0, "max": 80, "label": "affordable"},
        "mid-range": {"min": 50, "max": 150, "label": "mid-range"},
        "moderate": {"min": 50, "max": 150, "label": "mid-range"},
        "premium": {"min": 150, "max": 500, "label": "premium"},
        "expensive": {"min": 150, "max": 500, "label": "premium"},
        "luxury": {"min": 500, "max": None, "label": "luxury"},
    }
    
    # Urgency mappings
    URGENCY_PATTERNS = {
        "asap": "urgent",
        "urgent": "urgent",
        "need now": "urgent",
        "immediately": "urgent",
        "today": "urgent",
        "this week": "high",
        "next week": "high",
        "soon": "moderate",
        "eventually": "low",
        "no rush": "low"
    }
    
    @classmethod
    def normalize_price_range(cls, price_term: str) -> Dict[str, Any]:
        """Normalize price terms to price ranges"""
        price_term = price_term.lower().strip()
        return cls.PRICE_RANGES.get(price_term, {"min": 0, "max": None, "label": "any"})
    
    @classmethod
    def detect_category(cls, query: str) -> tuple[Optional[str], Optional[str]]:
        """Detect category and subcategory from query"""
        query_lower = query.lower()
        
        for category, cat_data in cls.CATEGORIES.items():
            for subcat, keywords in cat_data["subcategories"].items():
                for keyword in keywords:
                    if keyword in query_lower:
                        return category, subcat
        
        return None, None
    
    @classmethod
    def normalize_urgency(cls, timeline_text: str) -> tuple[str, Optional[int]]:
        """Normalize urgency and extract timeline"""
        timeline_lower = timeline_text.lower()
        
        # Check urgency patterns
        urgency = "normal"
        for pattern, urgency_level in cls.URGENCY_PATTERNS.items():
            if pattern in timeline_lower:
                urgency = urgency_level
                break
        
        # Extract days
        days = None
        if "today" in timeline_lower or "now" in timeline_lower:
            days = 0
        elif "tomorrow" in timeline_lower:
            days = 1
        elif "this week" in timeline_lower:
            days = 7
        elif "next week" in timeline_lower:
            days = 7
        elif "month" in timeline_lower:
            days = 30
        
        return urgency, days


class IntentAgent:
    """Intent extraction and slot-filling agent using Gemini 2.5 Flash"""
    
    def __init__(self, project_id: str, region: str = "us-central1"):
        """Initialize Intent Agent
        
        Args:
            project_id: GCP project ID
            region: GCP region
        """
        self.project_id = project_id
        self.region = region
        
        # Initialize Vertex AI
        vertexai.init(project=project_id, location=region)
        
        # Initialize Gemini 2.5 Flash (using standard model name)
        # Alternative models: "gemini-pro", "text-bison@002"
        self.model = GenerativeModel("gemini-2.5-flash")
        
        # Initialize taxonomy
        self.taxonomy = ProductTaxonomy()
        
        print(f"✓ Intent Agent initialized with Gemini 2.5 Flash")
    
    def _build_prompt(self, user_query: str) -> str:
        """Build prompt for intent extraction
        
        Args:
            user_query: Raw user query
            
        Returns:
            Formatted prompt
        """
        prompt = f"""You are an expert product intent extraction agent for an e-commerce platform.

Your task is to analyze the user query, understand & enrich the context , connect the query to relevant products and extract structured information in JSON format. 

AVAILABLE CATEGORIES:
{json.dumps(list(self.taxonomy.CATEGORIES.keys()), indent=2)}

AVAILABLE SUBCATEGORIES (by category):
{json.dumps({cat: list(data["subcategories"].keys()) for cat, data in self.taxonomy.CATEGORIES.items()}, indent=2)}

USER QUERY: "{user_query}"

EXTRACT THE FOLLOWING:
1. Product category (from available categories)
2. Product subcategory (from available subcategories)
3. Specific product type/name
4. Budget/price preferences (cheap, affordable, premium, luxury, or specific amounts)
5. Urgency indicators (urgent, soon, no rush, etc.)
6. Specific filters: gender, size, color, brand
7. Use case or context (e.g., "for marathon", "for work", "for kids")

OUTPUT FORMAT (STRICT JSON):
{{
  "product_category": "category name or null",
  "product_subcategory": "subcategory name or null",
  "product_type": "specific product name",
  "budget_term": "price term or null",
  "urgency_term": "urgency indicator or null",
  "use_case": "use case or null",
  "gender": "gender or null",
  "size": "size or null",
  "color": "color or null",
  "brand": "brand or null",
  "confidence": 0.0-1.0
}}

Return ONLY the JSON object, no explanations."""

        return prompt
    
    def extract_intent(self, user_query: str, user_id: str = None, session_id: str = None) -> Intent:
        """Extract intent from user query
        
        Args:
            user_query: Raw user query
            user_id: Optional user ID for personalization
            session_id: Optional session ID for context
            
        Returns:
            Intent object with extracted information
        """
        # Build and send prompt to Gemini
        prompt = self._build_prompt(user_query)
        
        # Configure generation
        generation_config = GenerationConfig(
            temperature=1.0,  # Low temperature for consistent extraction
            top_p=0.8,
            top_k=40,
            max_output_tokens=2048,
        )
        
        # Generate response
        response = self.model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        # Parse JSON response
        try:
            # Extract JSON from response
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:-3]
            elif response_text.startswith("```"):
                response_text = response_text[3:-3]
            
            extracted_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"⚠ Failed to parse JSON from response: {e}")
            print(f"Response: {response.text}")
            # Return default intent
            extracted_data = {
                "product_category": None,
                "product_subcategory": None,
                "product_type": user_query,
                "confidence": 0.5
            }
        
        # Normalize extracted data
        return self._normalize_intent(extracted_data, user_query)
    
    def _normalize_intent(self, extracted_data: Dict[str, Any], original_query: str) -> Intent:
        """Normalize extracted data to Intent object
        
        Args:
            extracted_data: Raw extracted data from LLM
            original_query: Original user query
            
        Returns:
            Normalized Intent object
        """
        extracted_slots = []
        
        # Normalize category (fallback to detection)
        category = extracted_data.get("product_category")
        subcategory = extracted_data.get("product_subcategory")
        
        if not category:
            category, subcategory = self.taxonomy.detect_category(original_query)
        
        if category:
            extracted_slots.append(ExtractedSlot(
                slot="category",
                value=category,
                normalized=category,
                confidence=extracted_data.get("confidence", 0.8)
            ))
        
        # Normalize price range
        price_range = None
        budget_term = extracted_data.get("budget_term")
        if budget_term:
            normalized_price = self.taxonomy.normalize_price_range(budget_term)
            price_range = PriceRange(**normalized_price)
            extracted_slots.append(ExtractedSlot(
                slot="budget",
                value=budget_term,
                normalized=normalized_price,
                confidence=0.9
            ))
        
        # Normalize urgency
        urgency = "normal"
        timeline_days = None
        urgency_term = extracted_data.get("urgency_term")
        if urgency_term:
            urgency, timeline_days = self.taxonomy.normalize_urgency(urgency_term)
            extracted_slots.append(ExtractedSlot(
                slot="urgency",
                value=urgency_term,
                normalized={"urgency": urgency, "days": timeline_days},
                confidence=0.85
            ))
        
        # Build attributes
        attributes = IntentAttributes(
            use_case=extracted_data.get("use_case"),
            price_range=price_range,
            urgency=urgency,
            timeline_days=timeline_days
        )
        
        # Build filters
        filters = IntentFilters(
            gender=extracted_data.get("gender"),
            size=extracted_data.get("size"),
            color=extracted_data.get("color"),
            brand=extracted_data.get("brand"),
            subcategory=subcategory
        )
        
        # Create Intent object
        intent = Intent(
            primary_category=category or "Unknown",
            subcategory=subcategory,
            product_type=extracted_data.get("product_type", "Unknown"),
            attributes=attributes,
            filters=filters,
            intent_confidence=extracted_data.get("confidence", 0.7),
            extracted_slots=extracted_slots
        )
        
        return intent
    
    def intent_to_dict(self, intent: Intent) -> Dict[str, Any]:
        """Convert Intent object to dictionary
        
        Args:
            intent: Intent object
            
        Returns:
            Dictionary representation
        """
        result = {
            "primary_category": intent.primary_category,
            "subcategory": intent.subcategory,
            "product_type": intent.product_type,
            "attributes": {
                "use_case": intent.attributes.use_case,
                "price_range": asdict(intent.attributes.price_range) if intent.attributes.price_range else None,
                "urgency": intent.attributes.urgency,
                "timeline_days": intent.attributes.timeline_days
            },
            "filters": asdict(intent.filters),
            "intent_confidence": intent.intent_confidence,
            "extracted_slots": [asdict(slot) for slot in intent.extracted_slots]
        }
        return result


# Example usage
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    project_id = os.getenv("GCP_PROJECT_ID")
    
    # Initialize agent
    agent = IntentAgent(project_id=project_id)
    
    # Test queries
    test_queries = [
        "I need cheap running shoes for a marathon next week",
        "Looking for premium skincare products for sensitive skin",
        "Need a gift for my wife, something elegant under $100",
        "Urgent: kids toys for 5 year old boy, delivery today"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"{'='*60}")
        
        intent = agent.extract_intent(query)
        intent_dict = agent.intent_to_dict(intent)
        
        print(json.dumps(intent_dict, indent=2))
