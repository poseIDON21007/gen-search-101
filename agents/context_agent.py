"""
Context Agent - Enrichment Layer
Enriches the intent with contextual data: weather, location, session history.
Per architecture: Context Agent → Function Call → Weather/Location API, Session History
"""

import os
import json
import requests
from typing import Dict, Any, Optional
from datetime import datetime


class WeatherService:
    """Fetch weather data to enrich product recommendations."""

    # Simulated weather data when API is unavailable
    SIMULATED_WEATHER = {
        "summer": {"temp_c": 32, "condition": "Sunny", "humidity": 45, "season": "summer"},
        "winter": {"temp_c": 8, "condition": "Cloudy", "humidity": 70, "season": "winter"},
        "spring": {"temp_c": 20, "condition": "Partly Cloudy", "humidity": 55, "season": "spring"},
        "autumn": {"temp_c": 15, "condition": "Windy", "humidity": 60, "season": "autumn"},
    }

    @staticmethod
    def _get_season() -> str:
        month = datetime.now().month
        if month in [12, 1, 2]:
            return "summer"  # Southern hemisphere (AU store)
        elif month in [3, 4, 5]:
            return "autumn"
        elif month in [6, 7, 8]:
            return "winter"
        else:
            return "spring"

    def get_weather(self, location: str = "Melbourne, AU") -> Dict[str, Any]:
        """Get current weather for location.

        Tries a free API first, falls back to season-based simulation.
        """
        # Try wttr.in (free, no API key needed)
        try:
            resp = requests.get(
                f"https://wttr.in/{location}?format=j1",
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                current = data["current_condition"][0]
                temp_c = int(current["temp_C"])
                return {
                    "location": location,
                    "temp_c": temp_c,
                    "condition": current["weatherDesc"][0]["value"],
                    "humidity": int(current["humidity"]),
                    "season": self._get_season(),
                    "source": "wttr.in",
                }
        except Exception:
            pass

        # Fallback: season-based simulation
        season = self._get_season()
        weather = self.SIMULATED_WEATHER[season].copy()
        weather["location"] = location
        weather["source"] = "simulated"
        return weather


class SessionHistoryService:
    """Manage user session history (in-memory for hackathon)."""

    def __init__(self):
        self._sessions: Dict[str, list] = {}

    def add_interaction(self, session_id: str, interaction: Dict[str, Any]):
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        self._sessions[session_id].append({
            **interaction,
            "timestamp": datetime.now().isoformat(),
        })

    def get_history(self, session_id: str, limit: int = 5) -> list:
        return self._sessions.get(session_id, [])[-limit:]

    def get_preferences(self, session_id: str) -> Dict[str, Any]:
        """Derive preferences from session history."""
        history = self.get_history(session_id, limit=10)
        if not history:
            return {}

        categories = []
        brands = []
        price_range = []
        for item in history:
            if "category" in item:
                categories.append(item["category"])
            if "brand" in item:
                brands.append(item["brand"])
            if "price" in item:
                price_range.append(item["price"])

        prefs = {}
        if categories:
            prefs["preferred_categories"] = list(set(categories))
        if brands:
            prefs["preferred_brands"] = list(set(brands))
        if price_range:
            prefs["avg_price"] = sum(price_range) / len(price_range)
        return prefs


class ContextAgent:
    """Context Agent: enriches intent with weather, location, and session data.

    Architecture position: after Intent Agent, before Constraint Agent.
    """

    def __init__(self):
        self.weather_service = WeatherService()
        self.session_service = SessionHistoryService()
        print("✓ Context Agent initialized")

    def enrich(
        self,
        intent: Dict[str, Any],
        user_id: str = None,
        session_id: str = None,
        location: str = "Melbourne, AU",
    ) -> Dict[str, Any]:
        """Enrich intent with contextual information.

        Args:
            intent: Structured intent dict from Intent Agent
            user_id: User identifier
            session_id: Session identifier
            location: User location string

        Returns:
            Enriched intent with context block added
        """
        context = {}

        # 1. Weather / Location enrichment
        weather = self.weather_service.get_weather(location)
        context["weather"] = weather
        context["location"] = location

        # Derive weather-based suggestions
        weather_tags = self._weather_to_tags(weather)
        context["weather_suggested_tags"] = weather_tags

        # 2. Session history
        if session_id:
            context["session_history"] = self.session_service.get_history(session_id)
            context["user_preferences"] = self.session_service.get_preferences(session_id)

            # Log this interaction
            self.session_service.add_interaction(session_id, {
                "query_type": "search",
                "category": intent.get("primary_category"),
                "product_type": intent.get("product_type"),
            })

        # 3. Temporal context
        now = datetime.now()
        context["temporal"] = {
            "day_of_week": now.strftime("%A"),
            "hour": now.hour,
            "is_weekend": now.weekday() >= 5,
            "date": now.strftime("%Y-%m-%d"),
        }

        # Build enriched output
        enriched = {**intent, "context": context}
        return enriched

    def _weather_to_tags(self, weather: Dict[str, Any]) -> list:
        """Convert weather conditions to product recommendation tags."""
        tags = []
        temp = weather.get("temp_c", 20)
        condition = weather.get("condition", "").lower()

        if temp >= 30:
            tags.extend(["summer", "lightweight", "breathable", "cooling", "UV protection"])
        elif temp >= 20:
            tags.extend(["spring", "light layers", "comfortable"])
        elif temp >= 10:
            tags.extend(["autumn", "layering", "warm"])
        else:
            tags.extend(["winter", "insulated", "warm", "waterproof"])

        if "rain" in condition:
            tags.extend(["waterproof", "rain gear"])
        if "sun" in condition:
            tags.extend(["sun protection", "outdoor"])
        if "wind" in condition:
            tags.extend(["windproof"])

        return list(set(tags))


if __name__ == "__main__":
    agent = ContextAgent()

    sample_intent = {
        "primary_category": "Clothing & Accessories",
        "subcategory": "Athletic Wear",
        "product_type": "Running Shoes",
        "attributes": {"urgency": "high", "timeline_days": 7},
        "filters": {"color": "Blue", "brand": "Nike"},
        "intent_confidence": 0.92,
    }

    enriched = agent.enrich(sample_intent, user_id="user_1", session_id="sess_1")
    print(json.dumps(enriched, indent=2, default=str))
