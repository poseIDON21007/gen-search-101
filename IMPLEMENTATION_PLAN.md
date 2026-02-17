# Multi-Agent Product Recommendation System - Implementation Plan

## Architecture Overview

This implementation uses Google's Agent Development Kit (ADK) and Vertex AI to create a multi-agent orchestration system for intelligent product recommendations.

## System Components

### 1. Intent Agent (NLU & Slot Filling)
- **Model**: Gemini 1.5 Pro
- **Purpose**: Convert natural language to structured JSON
- **Input**: Raw user query
- **Output**: Structured intent with slots

### 2. Context Agent
- **Purpose**: Enrich request with contextual data
- **Functions**: Weather API, Location, Session History (CRM)

### 3. Constraint Agent
- **Purpose**: Filter based on business rules
- **Functions**: Pricing limits, Inventory availability

### 4. Candidate Generation Agent
- **Service**: Vertex AI Search (Hybrid Vector + Keyword)
- **Purpose**: Retrieve relevant products from catalog

### 5. Ranking Agent
- **Model**: Vertex AI AutoML or XGBoost
- **Purpose**: Rank candidates by relevance/likelihood

### 6. Action Agent
- **Model**: Gemini 1.5 Flash
- **Purpose**: Generate natural language response

### 7. Governance Layer
- **Service**: Cloud Trace, Cloud Logging
- **Purpose**: Observability and monitoring

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Agent Framework | Google Agent Development Kit (ADK) |
| LLM | Gemini 1.5 Pro, Gemini 1.5 Flash |
| Vector Search | Vertex AI Vector Search |
| Feature Store | Vertex AI Feature Store |
| Database | BigQuery (Product Catalog) |
| Orchestration | Cloud Run (Python FastAPI) |
| Monitoring | Cloud Trace, Cloud Logging |
| Session Store | Firestore or Cloud SQL |

---

## Implementation Phases

### Phase 1: Setup & Infrastructure (Week 1)
1. Enable required GCP APIs
2. Set up BigQuery with product embeddings (✅ Complete)
3. Configure Vertex AI Search with BigQuery data source
4. Set up Vertex AI Feature Store
5. Initialize Cloud Run environment

### Phase 2: Intent Agent (Week 2)
1. Design product taxonomy mapping
2. Create intent extraction prompts
3. Implement slot-filling logic with Gemini 1.5 Pro
4. Build intent validation and normalization
5. Create unit tests for intent extraction

### Phase 3: Context & Constraint Agents (Week 2-3)
1. Integrate weather/location APIs
2. Build session history service (Firestore)
3. Implement inventory checker (BigQuery)
4. Create pricing constraint logic
5. Build context enrichment pipeline

### Phase 4: Candidate Generation (Week 3)
1. Configure Vertex AI Search
2. Deploy embeddings to Vertex AI Vector Search
3. Implement hybrid search (vector + keyword)
4. Create fallback strategies
5. Optimize retrieval performance

### Phase 5: Ranking Agent (Week 4)
1. Collect training data for ranking
2. Build feature pipeline
3. Train Vertex AI AutoML ranking model
4. Deploy ranking endpoint
5. A/B test ranking strategies

### Phase 6: Action Agent & Orchestration (Week 4-5)
1. Design response templates
2. Implement Gemini 1.5 Flash response generation
3. Build agent orchestration layer
4. Create FastAPI endpoints
5. Implement error handling & retries

### Phase 7: Governance & Deployment (Week 5)
1. Set up Cloud Trace integration
2. Implement logging pipeline
3. Create monitoring dashboards
4. Deploy to Cloud Run
5. Load testing & optimization

---

## Detailed Component Specifications

### Intent Agent Specification

#### Input Schema
```json
{
  "user_query": "I need cheap running shoes for a marathon next week",
  "user_id": "user_12345",
  "session_id": "session_abc",
  "timestamp": "2026-02-14T10:30:00Z"
}
```

#### Output Schema
```json
{
  "intent": {
    "primary_category": "Footwear",
    "subcategory": "Athletic Shoes",
    "product_type": "Running Shoes",
    "attributes": {
      "use_case": "Marathon/Long-distance",
      "price_range": {
        "min": 0,
        "max": 80,
        "label": "budget"
      },
      "urgency": "high",
      "timeline_days": 7
    },
    "filters": {
      "gender": null,
      "size": null,
      "color": null,
      "brand": null
    },
    "intent_confidence": 0.92
  },
  "extracted_slots": [
    {"slot": "product_type", "value": "running shoes", "normalized": "Running Shoes"},
    {"slot": "budget", "value": "cheap", "normalized": {"max": 80}},
    {"slot": "timeline", "value": "next week", "normalized": 7}
  ]
}
```

#### Taxonomy Mapping
```json
{
  "categories": {
    "footwear": {
      "id": "CAT_FOOT_001",
      "subcategories": {
        "athletic_shoes": {
          "id": "SUBCAT_ATH_001",
          "keywords": ["running shoes", "sneakers", "trainers", "athletic footwear"]
        }
      }
    }
  },
  "price_ranges": {
    "budget": {"max": 80},
    "mid_range": {"min": 80, "max": 150},
    "premium": {"min": 150}
  }
}
```

---

## Agent Development Kit (ADK) Integration

### ADK Agent Pattern

```python
from google.cloud.aiplatform import adk

# Define Intent Agent
intent_agent = adk.Agent(
    name="intent_agent",
    model="gemini-1.5-pro",
    instructions="""You are an intent extraction agent...""",
    tools=[taxonomy_mapper, slot_validator]
)

# Define orchestration flow
orchestrator = adk.Orchestrator([
    intent_agent,
    context_agent,
    constraint_agent,
    candidate_agent,
    ranking_agent,
    action_agent
])
```

---

## Data Flow Diagram

```
User Query
    ↓
[Intent Agent] → Structured Intent JSON
    ↓
[Context Agent] → Enriched with weather, location, history
    ↓
[Constraint Agent] → Filtered by inventory, pricing
    ↓
[Candidate Agent] → Query Vertex AI Search → Get 50 candidates
    ↓
[Ranking Agent] → Score & Rank → Top 5 products
    ↓
[Action Agent] → Generate Natural Response
    ↓
User Response
```

---

## Key Design Decisions

### 1. Why Gemini 1.5 Pro for Intent?
- Superior NLU capabilities
- Better at structured output (JSON mode)
- Handles ambiguous language well

### 2. Why Gemini 1.5 Flash for Action?
- Faster inference
- Cost-effective for template generation
- Sufficient for response synthesis

### 3. Hybrid Search Strategy
- Vector search: Semantic understanding
- Keyword search: Exact match fallback
- Combination ensures coverage

### 4. Feature Store for Ranking
- Real-time feature serving
- Historical behavior features
- Product popularity metrics

---

## API Endpoints

### Main Orchestration Endpoint
```
POST /api/v1/recommend
```

### Debug Endpoints
```
POST /api/v1/debug/intent      # Test intent extraction
POST /api/v1/debug/candidates  # Test candidate generation
POST /api/v1/debug/ranking     # Test ranking
```

---

## Monitoring & Observability

### Metrics to Track
1. **Latency**: End-to-end response time
2. **Intent Accuracy**: Manual labeling sample
3. **Search Recall**: Relevant products in candidates
4. **Ranking Performance**: Click-through rate
5. **User Satisfaction**: Feedback ratings

### Logging Strategy
- Log all agent inputs/outputs
- Track agent transition times
- Capture errors with context
- Store user feedback

---

## Cost Optimization

1. **Model Selection**: Use Flash for simple tasks
2. **Caching**: Cache taxonomy mappings
3. **Batch Processing**: Group similar requests
4. **Rate Limiting**: Prevent abuse
5. **Result Caching**: Cache popular queries

---

## Next Steps

1. Review and approve this plan
2. Set up development environment
3. Begin Phase 1 implementation
4. Schedule weekly checkpoints
