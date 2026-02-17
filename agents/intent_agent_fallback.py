"""
Intent Agent - Fallback Version (Rule-Based)
Provides intent extraction without requiring Gemini API access
Uses pattern matching and NLP techniques as fallback
"""

import re
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict


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


class RuleBasedIntentExtractor:
    """Rule-based intent extraction using pattern matching"""
    
    # Product keywords by category
    PRODUCT_PATTERNS = {
        "Beauty & Personal Care": {
            "Haircare": ["shampoo", "conditioner", "hair oil", "hair product", "haircare", "hair mask"],
            "Skincare": ["moisturizer", "cleanser", "serum", "skincare", "face cream", "lotion"],
            "Grooming Kits": ["grooming kit", "grooming set", "shaving kit"],
            "Fragrances": ["perfume", "cologne", "fragrance", "scent", "deodorant"]
        },
        "Clothing & Accessories": {
            "Athletic Wear": ["running shoes", "sneakers", "trainers", "athletic shoes", "sports shoes"],
            "Casual Wear": ["t-shirt", "jeans", "casual wear", "shirt", "pants"],
            "Accessories": ["watch", "belt", "wallet", "bag", "sunglasses"]
        },
        "Home & Living": {
            "Kitchenware": ["cookware", "utensils", "kitchen", "pots", "pans"],
            "Furniture": ["chair", "table", "sofa", "bed", "furniture"],
            "Decor": ["artwork", "vase", "decoration", "decor"]
        },
        "Gifts & Photo Products": {
            "Photo Frames": ["photo frame", "picture frame", "frame"],
            "Gift Sets": ["gift set", "gift pack", "gift"]
        },
        "Nursery & Kids": {
            "Toys": ["toy", "toys", "playset", "action figure", "doll"],
            "Kids Furniture": ["crib", "changing table", "kids bed"]
        }
    }
    
    # Price patterns
    PRICE_PATTERNS = {
        r"\$(\d+)": "specific_price",
        r"under \$?(\d+)": "max_price",
        r"below \$?(\d+)": "max_price",
        r"less than \$?(\d+)": "max_price",
        r"over \$?(\d+)": "min_price",
        r"above \$?(\d+)": "min_price",
        r"more than \$?(\d+)": "min_price",
        r"between \$?(\d+) and \$?(\d+)": "range_price",
    }
    
    PRICE_KEYWORDS = {
        "cheap": {"max": 50, "label": "budget"},
        "budget": {"max": 50, "label": "budget"},
        "affordable": {"max": 80, "label": "affordable"},
        "mid-range": {"min": 50, "max": 150, "label": "mid-range"},
        "moderate": {"min": 50, "max": 150, "label": "mid-range"},
        "premium": {"min": 150, "max": 500, "label": "premium"},
        "expensive": {"min": 150, "max": 500, "label": "premium"},
        "luxury": {"min": 500, "label": "luxury"},
    }
    
    # Urgency patterns
    URGENCY_PATTERNS = {
        r"\b(urgent|asap|immediately|now)\b": ("urgent", 0),
        r"\btoday\b": ("urgent", 0),
        r"\btomorrow\b": ("high", 1),
        r"\bthis week\b": ("high", 7),
        r"\bnext week\b": ("high", 7),
        r"\bsoon\b": ("moderate", 14),
        r"\bno rush\b": ("low", None),
    }
    
    # Brand patterns (common brands)
    BRANDS = ["nike", "adidas", "apple", "samsung", "sony", "kmart", "urbancare", "freshskin"]
    
    # Color patterns
    COLORS = ["black", "white", "red", "blue", "green", "yellow", "pink", "purple", "orange", "brown", "gray", "grey"]
    
    # Size patterns
    SIZES = ["xs", "s", "m", "l", "xl", "xxl", "small", "medium", "large", "one size"]
    
    # Gender patterns
    GENDER_PATTERNS = {
        r"\b(men's|mens|male|for men|for him)\b": "Men",
        r"\b(women's|womens|female|for women|for her)\b": "Women",
        r"\b(kids|children|child|boys|girls)\b": "Kids",
        r"\b(unisex|all)\b": "Unisex",
    }
    
    def detect_category_subcategory(self, query: str) -> tuple:
        """Detect category and subcategory from query"""
        query_lower = query.lower()
        
        for category, subcats in self.PRODUCT_PATTERNS.items():
            for subcat, keywords in subcats.items():
                for keyword in keywords:
                    if keyword in query_lower:
                        # Extract product type
                        product_type = keyword.title()
                        return category, subcat, product_type
        
        return None, None, "Unknown Product"
    
    def extract_price_info(self, query: str) -> Optional[Dict[str, Any]]:
        """Extract price information from query"""
        query_lower = query.lower()
        
        # Check for specific price patterns
        for pattern, price_type in self.PRICE_PATTERNS.items():
            match = re.search(pattern, query_lower)
            if match:
                if price_type == "max_price":
                    return {"max": float(match.group(1)), "label": "budget"}
                elif price_type == "min_price":
                    return {"min": float(match.group(1)), "label": "premium"}
                elif price_type == "range_price":
                    return {"min": float(match.group(1)), "max": float(match.group(2)), "label": "custom"}
                elif price_type == "specific_price":
                    price = float(match.group(1))
                    return {"min": price * 0.8, "max": price * 1.2, "label": "specific"}
        
        # Check for price keywords
        for keyword, price_range in self.PRICE_KEYWORDS.items():
            if keyword in query_lower:
                return price_range
        
        return None
    
    def extract_urgency(self, query: str) -> tuple:
        """Extract urgency and timeline from query"""
        query_lower = query.lower()
        
        for pattern, (urgency, days) in self.URGENCY_PATTERNS.items():
            if re.search(pattern, query_lower):
                return urgency, days
        
        return "normal", None
    
    def extract_brand(self, query: str) -> Optional[str]:
        """Extract brand from query"""
        query_lower = query.lower()
        
        for brand in self.BRANDS:
            if brand in query_lower:
                return brand.title()
        
        # Extract potential brand mentions with "from" or "by"
        brand_match = re.search(r"\b(?:from|by)\s+([A-Z][a-zA-Z]+)\b", query)
        if brand_match:
            return brand_match.group(1)
        
        return None
    
    def extract_color(self, query: str) -> Optional[str]:
        """Extract color from query"""
        query_lower = query.lower()
        
        for color in self.COLORS:
            if color in query_lower:
                return color.title()
        
        return None
    
    def extract_size(self, query: str) -> Optional[str]:
        """Extract size from query"""
        query_lower = query.lower()
        
        for size in self.SIZES:
            if size in query_lower:
                return size.upper() if len(size) <= 3 else size.title()
        
        return None
    
    def extract_gender(self, query: str) -> Optional[str]:
        """Extract gender from query"""
        for pattern, gender in self.GENDER_PATTERNS.items():
            if re.search(pattern, query.lower()):
                return gender
        
        return None
    
    def extract_use_case(self, query: str) -> Optional[str]:
        """Extract use case from query"""
        # Look for "for..." patterns
        use_case_match = re.search(r"\bfor\s+([a-zA-Z\s]+?)(?:\s+|,|$)", query)
        if use_case_match:
            use_case = use_case_match.group(1).strip()
            # Filter out common words that aren't use cases
            if use_case.lower() not in ["me", "my", "her", "him", "them", "us"]:
                return use_case
        
        return None


class IntentAgentFallback:
    """Fallback Intent Agent using rule-based extraction"""
    
    def __init__(self):
        """Initialize Fallback Intent Agent"""
        self.extractor = RuleBasedIntentExtractor()
        print(f"✓ Fallback Intent Agent initialized (Rule-Based)")
    
    def extract_intent(self, user_query: str, user_id: str = None, session_id: str = None) -> Intent:
        """Extract intent from user query
        
        Args:
            user_query: Raw user query
            user_id: Optional user ID
            session_id: Optional session ID
            
        Returns:
            Intent object with extracted information
        """
        extracted_slots = []
        
        # Extract category and subcategory
        category, subcategory, product_type = self.extractor.detect_category_subcategory(user_query)
        
        if category:
            extracted_slots.append(ExtractedSlot(
                slot="category",
                value=category,
                normalized=category,
                confidence=0.85
            ))
        
        # Extract price range
        price_info = self.extractor.extract_price_info(user_query)
        price_range = None
        if price_info:
            price_range = PriceRange(**price_info)
            extracted_slots.append(ExtractedSlot(
                slot="price_range",
                value=str(price_info),
                normalized=price_info,
                confidence=0.9
            ))
        
        # Extract urgency
        urgency, timeline_days = self.extractor.extract_urgency(user_query)
        if urgency != "normal":
            extracted_slots.append(ExtractedSlot(
                slot="urgency",
                value=urgency,
                normalized={"urgency": urgency, "days": timeline_days},
                confidence=0.8
            ))
        
        # Extract use case
        use_case = self.extractor.extract_use_case(user_query)
        
        # Extract filters
        brand = self.extractor.extract_brand(user_query)
        color = self.extractor.extract_color(user_query)
        size = self.extractor.extract_size(user_query)
        gender = self.extractor.extract_gender(user_query)
        
        # Build attributes
        attributes = IntentAttributes(
            use_case=use_case,
            price_range=price_range,
            urgency=urgency,
            timeline_days=timeline_days
        )
        
        # Build filters
        filters = IntentFilters(
            gender=gender,
            size=size,
            color=color,
            brand=brand,
            subcategory=subcategory
        )
        
        # Create Intent object
        intent = Intent(
            primary_category=category or "Unknown",
            subcategory=subcategory,
            product_type=product_type,
            attributes=attributes,
            filters=filters,
            intent_confidence=0.75,  # Rule-based has moderate confidence
            extracted_slots=extracted_slots
        )
        
        return intent
    
    def intent_to_dict(self, intent: Intent) -> Dict[str, Any]:
        """Convert Intent object to dictionary"""
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


if __name__ == "__main__":
    # Test the fallback agent
    agent = IntentAgentFallback()
    
    test_queries = [
        "I need cheap running shoes for a marathon next week",
        "Looking for premium skincare products",
        "Show me blue Nike sneakers under $100"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        intent = agent.extract_intent(query)
        print(json.dumps(agent.intent_to_dict(intent), indent=2))
