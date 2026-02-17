# Gen-Search-101: Complete Project Deep Dive

> **For:** Vivek (and anyone on the team who wants to understand every moving part)
> **What this is:** A Kmart Australia AI-powered product recommendation system built for a GCP hackathon

---

## Table of Contents

1. [The Big Picture — What Are We Building?](#1-the-big-picture)
2. [AI Terminology — Plain English](#2-ai-terminology)
3. [Every GCP Service We Use (and Why)](#3-gcp-services)
4. [Architecture Walkthrough — Step by Step](#4-architecture-walkthrough)
5. [The Code — File by File](#5-the-code)
6. [Data — What's in BigQuery](#6-the-data)
7. [What Vivek's Branch Added (and Why It Matters)](#7-vivek-branch-changes)
8. [How to Give a Live Demo](#8-live-demo-guide)
9. [Common Errors & Fixes](#9-troubleshooting)

---

## 1. The Big Picture

### The Problem

Imagine you walk into a Kmart store and say:

> *"I need cheap running shoes for a marathon next week"*

A smart salesperson would:
1. **Understand** you need running shoes (not dress shoes)
2. **Know** "cheap" means under $50
3. **Check** what's in stock right now
4. **Pick** the 5 best options for you
5. **Explain** why those are great choices

**This project does exactly that — but as software.**

Instead of a salesperson, we have **6 AI agents** that each do one job, passing results to the next like a relay race.

### The One-Liner

> A multi-agent AI system that takes a natural language query like *"Date night outfit under $80"* and returns the best matching products from a 4,000-product Kmart catalog, with a human-like explanation — all powered by Google Cloud.

---

## 2. AI Terminology

### Embeddings (The Core Concept)

**Layman:** An embedding is a way to convert words into a list of numbers so a computer can understand meaning.

**Example:**
```
"running shoes"  → [0.23, -0.45, 0.67, 0.12, ... 768 numbers total]
"sneakers"       → [0.22, -0.44, 0.66, 0.13, ... 768 numbers total]
"refrigerator"   → [0.91, 0.33, -0.78, 0.54, ... 768 numbers total]
```

Notice how "running shoes" and "sneakers" have very similar numbers (because they mean almost the same thing), but "refrigerator" has completely different numbers. This is how the system knows sneakers are related to running shoes even if you don't type the exact word.

**We create a 768-dimensional embedding** for every single product using Google's `text-embedding-004` model. These are stored in BigQuery alongside the product data.

### Vector Search (How We Find Similar Products)

**Layman:** Once every product is a list of numbers, we can find similar products by measuring the "distance" between number lists.

**Real-world analogy:** Imagine every product is a dot on a map. When you search for "running shoes", your query also becomes a dot. The system finds the closest dots (products) to your dot (query). This is called **cosine similarity**.

**The math (simplified):**
```
Your query:     [0.23, -0.45, 0.67]
Product A:      [0.22, -0.44, 0.66]  → Distance: 0.001 (VERY close! Good match!)
Product B:      [0.91, 0.33, -0.78]  → Distance: 0.89  (FAR away! Bad match.)
```

### LLM (Large Language Model)

**Layman:** A giant AI brain trained on billions of pages of text. It can understand language and write responses like a human.

**In our project:** We use **Gemini 2.5 Flash** — Google's LLM. It does two things:
1. **Reads** your query and figures out what you want (Intent Agent)
2. **Writes** a friendly response explaining the product recommendations (Action Agent)

### Slot Filling

**Layman:** Extracting specific details from a sentence.

**Example:**
```
Query: "I need cheap blue Nike running shoes for men"

Slots extracted:
  - product_type: "running shoes"
  - price:        "cheap" → $0-$50
  - color:        "blue"
  - brand:        "Nike"
  - gender:       "Men"
```

### NLU (Natural Language Understanding)

**Layman:** Teaching a computer to understand what humans mean, not just what they say.

**Example:** When you say "something for date night", the system understands you probably want:
- Clothing or accessories (not kitchen appliances)
- Something stylish (not work boots)
- Maybe a mid-range price (not the cheapest option)

### Agents (Multi-Agent System)

**Layman:** Breaking a complex task into smaller tasks and giving each to a specialist.

**Analogy:** A hospital doesn't have ONE doctor do everything. The receptionist books you in, the nurse takes vitals, the specialist diagnoses, the pharmacist gives medicine. Each is an "agent" that does one job well.

Our 6 agents:
| Agent | Job | Real-World Analogy |
|-------|-----|--------------------|
| Intent Agent | Understand what you want | The receptionist who listens |
| Context Agent | Add weather, location info | The nurse who takes your temperature |
| Constraint Agent | Check price limits, inventory | The insurance verifier |
| Candidate Agent | Find matching products | The specialist who runs tests |
| Ranking Agent | Pick the best matches | The doctor who diagnoses |
| Action Agent | Explain in plain English | The doctor who explains results |

### Cosine Similarity

**Layman:** A number between 0 and 1 that measures how similar two things are. 1.0 = identical, 0.0 = completely different.

**In our system:** Every search result has a similarity score. A product with 0.85 similarity is a much better match than one with 0.60.

### Hybrid Search

**Layman:** We search in TWO ways at the same time:
1. **Vector search** — "What products have similar meaning to your query?" (semantic)
2. **Keyword filtering** — "Does the product match your category, brand, price range?" (exact)

Combining both gives way better results than either alone.

---

## 3. GCP Services

### Every Google Cloud Service We Use

| # | GCP Service | What It Is | How We Use It | Where In Code |
|---|------------|------------|---------------|---------------|
| 1 | **Vertex AI** | Google's AI/ML platform | Hosts the embedding model and Gemini LLM | `create_embeddings_pipeline.py`, `intent_agent.py`, `action_agent.py`, `candidate_agent.py` |
| 2 | **Gemini 2.5 Flash** | Google's latest LLM (via Vertex AI) | Intent extraction + response generation | `intent_agent.py` (line 196), `action_agent.py` (line 29) |
| 3 | **Text Embedding API** (`text-embedding-004`) | Converts text to 768-dim number vectors | Creates embeddings for all 4,000 products + user queries | `create_embeddings_pipeline.py` (line 53), `candidate_agent.py` (line 38) |
| 4 | **BigQuery** | Google's serverless data warehouse | Stores all products + embeddings + runs vector search SQL | `constraint_agent.py`, `candidate_agent.py`, `vector_search.py` |
| 5 | **Cloud Run** (planned) | Serverless container hosting | Will host the FastAPI web server for production | `IMPLEMENTATION_PLAN.md` |
| 6 | **Cloud Trace** (planned) | Distributed tracing | Will track request flow across agents in production | `governance.py` (logs locally for now) |
| 7 | **Cloud Logging** (planned) | Centralized logs | Will collect all agent logs in production | `governance.py` |
| 8 | **IAM & Auth** | Identity & access management | `gcloud auth` used for local authentication | `quickstart.sh`, `enable_gemini_apis.sh` |
| 9 | **Compute Engine API** | Required dependency | Needed by Vertex AI (enabled in `enable_gemini_apis.sh`) | `enable_gemini_apis.sh` |

### GCP APIs Enabled (from `enable_gemini_apis.sh`)

```bash
aiplatform.googleapis.com          # Vertex AI (embeddings + Gemini)
generativelanguage.googleapis.com  # Generative AI models
bigquery.googleapis.com            # BigQuery data warehouse
compute.googleapis.com             # Compute Engine (Vertex AI dependency)
```

### GCP Project Details

| Setting | Value |
|---------|-------|
| Project ID | `cloud-comrades-0120692` |
| Region | `us-central1` |
| BigQuery Dataset | `product_embeddings` |
| BigQuery Table | `products_with_vectors` |
| Auth Method | `gcloud auth application-default login` |

### Rough Cost Breakdown (Hackathon Scale)

| Service | Estimated Cost | Why |
|---------|---------------|-----|
| Vertex AI Embeddings (4,000 products) | ~$0.10 | One-time, already done |
| BigQuery Storage (4K rows + embeddings) | ~$0.02/month | Very small dataset |
| Gemini 2.5 Flash (per query) | ~$0.001 | Two calls per query (intent + response) |
| BigQuery Queries | ~$0.005/query | Scans ~50MB per query |
| **Total for demo day** | **< $1** | |

---

## 4. Architecture Walkthrough

### The Full Flow (What Happens When You Search)

```
User types: "I need cheap running shoes for a marathon next week"
                            │
                            ▼
            ┌───────────────────────────────┐
            │   1. INTENT AGENT             │ ← Gemini 2.5 Flash
            │   "What does the user want?"   │
            │                               │
            │   Output:                     │
            │   category: Clothing          │
            │   product: Running Shoes      │
            │   budget: cheap ($0-$50)      │
            │   urgency: high (7 days)      │
            └───────────┬───────────────────┘
                        │
                        ▼
            ┌───────────────────────────────┐
            │   2. CONTEXT AGENT            │ ← Weather API (wttr.in)
            │   "What else is relevant?"     │
            │                               │
            │   Adds:                       │
            │   weather: 32°C, Sunny        │
            │   tags: summer, breathable    │
            │   session: first-time user    │
            └───────────┬───────────────────┘
                        │
                        ▼
            ┌───────────────────────────────┐
            │   3. CONSTRAINT AGENT         │ ← BigQuery (inventory check)
            │   "What's available & valid?"  │
            │                               │
            │   Checks:                     │
            │   - 850 clothing items exist  │
            │   - 823 in stock              │
            │   - Price range: $6-$270      │
            │   Builds SQL WHERE clause     │
            └───────────┬───────────────────┘
                        │
                        ▼
            ┌───────────────────────────────┐
            │   4. CANDIDATE AGENT          │ ← Vertex AI Embeddings
            │   "Find matching products"     │      + BigQuery
            │                               │
            │   Steps:                      │
            │   a) Convert query to vector  │
            │   b) Run cosine similarity    │
            │      in BigQuery              │
            │   c) Apply constraint filters │
            │   d) Return top 50 matches    │
            └───────────┬───────────────────┘
                        │
                        ▼
            ┌───────────────────────────────┐
            │   5. RANKING AGENT            │ ← Weighted scoring
            │   "Which 5 are THE BEST?"      │
            │                               │
            │   Scores by:                  │
            │   - Similarity: 45%           │
            │   - Price fit: 20%            │
            │   - Stock level: 10%          │
            │   - Filter match: 15%         │
            │   - Popularity: 10%           │
            │   Returns Top 5              │
            └───────────┬───────────────────┘
                        │
                        ▼
            ┌───────────────────────────────┐
            │   6. ACTION AGENT             │ ← Gemini 2.5 Flash
            │   "Explain like a salesperson" │
            │                               │
            │   "Great news! I found some   │
            │    affordable running shoes   │
            │    perfect for your marathon. │
            │    The Active Core Sneakers   │
            │    at $39.16 are a top pick…" │
            └───────────────────────────────┘
                        │
                        ▼
                  User sees response
                  + Top 5 products
```

### What the Governance Layer Does

The **TraceLogger** wraps the entire flow above. It records:
- How long each agent took (in milliseconds)
- What data went in and came out of each agent
- Whether each step succeeded or failed
- A unique trace ID for debugging

**Example trace output:**
```
IntentAgent                    3200ms  success
ContextAgent                    450ms  success
ConstraintAgent                2100ms  success
CandidateGenerationAgent       8500ms  success
RankingAgent                      5ms  success
ActionAgent                    5200ms  success
─────────────────────────────────────
Total:                        19455ms
```

---

## 5. The Code

### File Map

```
gen-search-101/
│
├── orchestrator.py              ← THE MAIN FILE. Chains all 6 agents together.
│
├── agents/
│   ├── __init__.py              ← Package init, version tracking
│   ├── intent_agent.py          ← Agent 1: Gemini-powered intent extraction
│   ├── intent_agent_fallback.py ← Agent 1 backup: rule-based (no AI needed)
│   ├── context_agent.py         ← Agent 2: Weather, session history enrichment
│   ├── constraint_agent.py      ← Agent 3: Price limits, inventory check via BQ
│   ├── candidate_agent.py       ← Agent 4: Vector search + keyword filtering
│   ├── ranking_agent.py         ← Agent 5: Weighted scoring to pick Top 5
│   ├── action_agent.py          ← Agent 6: Gemini-powered response writer
│   └── governance.py            ← Trace logger (observability)
│
├── create_embeddings_pipeline.py ← ONE-TIME SETUP: Creates embeddings, loads to BQ
├── vector_search.py              ← Standalone vector search utility
├── test_intent_agent.py          ← Tests for the intent agent
│
├── Data files (already loaded into BigQuery):
│   ├── beauty_personal_care_500.json      (500 products)
│   ├── gifts_photo_products_500.json      (500 products)
│   ├── kmart_clothing_accessories_structured.json  (850 products)
│   ├── kmart_home_living_products_structured.json  (1,650 products)
│   └── nursery_kids_500.json              (500 products)
│   Total: 4,000 products
│
├── Configuration & docs:
│   ├── requirements.txt         ← Python dependencies
│   ├── quickstart.sh            ← Quick setup script
│   ├── enable_gemini_apis.sh    ← GCP API enablement script
│   ├── bigquery_queries.sql     ← 15 sample BigQuery queries
│   ├── README.md                ← Original setup guide
│   ├── QUICKSTART.md            ← Quick start instructions
│   ├── IMPLEMENTATION_PLAN.md   ← Full architecture plan
│   └── INTENT_AGENT_README.md   ← Intent agent documentation
│
└── .env                         ← Environment variables (GCP project, region)
```

### How Each Agent Works (With Code Examples)

#### Agent 1: Intent Agent (`intent_agent.py`)

**What it does:** Sends your query to Gemini 2.5 Flash with a carefully crafted prompt. Gemini returns structured JSON.

**The key prompt (simplified):**
```
You are a product intent extraction agent.

USER QUERY: "I need cheap running shoes for a marathon next week"

Extract:
- Product category → "Clothing & Accessories"
- Product type → "Running Shoes"
- Budget → "cheap" ($0-$50)
- Urgency → "high" (7 days)
- Filters: gender, size, color, brand

Return as JSON.
```

**What comes out:**
```json
{
  "primary_category": "Clothing & Accessories",
  "subcategory": "Athletic Wear",
  "product_type": "Running Shoes",
  "attributes": {
    "price_range": {"min": 0, "max": 50, "label": "budget"},
    "urgency": "high",
    "timeline_days": 7
  },
  "filters": {"brand": null, "color": null},
  "intent_confidence": 0.92
}
```

**Fallback:** If Gemini is unavailable, `intent_agent_fallback.py` uses regex/pattern matching — no AI needed.

#### Agent 2: Context Agent (`context_agent.py`)

**What it does:** Adds real-world context that helps narrow down results.

1. **Weather:** Calls `wttr.in` (free weather API). If it's 35°C and sunny, it adds tags like "summer", "breathable", "UV protection". If it's 8°C and rainy, it adds "waterproof", "warm", "insulated".

2. **Session history:** Remembers what you searched for earlier in this session. If you previously searched for skincare, it knows your preferences.

3. **Temporal:** Knows it's Saturday vs Monday, morning vs evening (useful for context).

#### Agent 3: Constraint Agent (`constraint_agent.py`)

**What it does:** Runs SQL queries against BigQuery to check real inventory.

**Example BigQuery query it runs:**
```sql
SELECT COUNT(*) as total_products,
       SUM(CASE WHEN stock_quantity > 0 THEN 1 ELSE 0 END) as in_stock,
       MIN(price_aud) as min_price,
       MAX(price_aud) as max_price
FROM `cloud-comrades-0120692.product_embeddings.products_with_vectors`
WHERE category LIKE '%Clothing & Accessories%'
```

**Output:** A WHERE clause for downstream agents:
```sql
stock_quantity >= 1 AND price_aud <= 50 AND category LIKE '%Clothing & Accessories%'
```

#### Agent 4: Candidate Agent (`candidate_agent.py`)

**What it does:** The core search engine. Two-step process:

1. **Convert query to a vector** using `text-embedding-004`
2. **Run a SQL query** that computes cosine similarity on all 4,000 products AND applies constraint filters at the same time

**The actual BigQuery query (simplified):**
```sql
WITH query_embedding AS (
  SELECT [0.23, -0.45, 0.67, ...] AS embedding  -- your query as numbers
)
SELECT
  p.title, p.price_aud, p.brand,
  -- Cosine similarity: how close is this product to your query?
  SUM(p_elem * q_elem) / (SQRT(SUM(p_elem²)) * SQRT(SUM(q_elem²)))
    AS similarity_score
FROM products p
CROSS JOIN query_embedding q
WHERE stock_quantity >= 1 AND price_aud <= 50  -- constraint filters
ORDER BY similarity_score DESC
LIMIT 50
```

Returns ~50 candidate products sorted by relevance.

#### Agent 5: Ranking Agent (`ranking_agent.py`)

**What it does:** Takes 50 candidates and picks the Top 5 using a scoring formula:

```
Final Score = (0.45 × similarity)       -- How semantically relevant
            + (0.20 × price_fit)        -- Is it in budget?
            + (0.10 × stock_level)      -- Is it well-stocked?
            + (0.15 × filter_match)     -- Does it match brand/color?
            + (0.10 × popularity)       -- Stock-as-popularity proxy
```

**Example scoring:**
```
Product A: Similarity 0.85, Price $39 (in budget) → Score: 0.72
Product B: Similarity 0.90, Price $120 (over budget) → Score: 0.58
Product C: Similarity 0.78, Price $25 (in budget) → Score: 0.68

Winner: Product A (best overall fit)
```

#### Agent 6: Action Agent (`action_agent.py`)

**What it does:** Takes the Top 5 products and asks Gemini to write a friendly response.

**The prompt (simplified):**
```
You are a helpful shopping assistant for an Australian retail store.
The customer asked about: Running Shoes
Budget: cheap
Weather: 32°C, Sunny

Top products:
1. Active Core Sneakers - $39.16
2. Coastal Wear Sneakers - $19.76
3. ...

Write a friendly 3-5 sentence response recommending these.
```

**Gemini's output:**
```
Great news! I've found some fantastic budget-friendly running shoes
perfect for your marathon prep. The Active Core Sneakers at $39.16
are an excellent choice — they're lightweight and breathable, ideal
for the warm weather. For an even more affordable option, check out
the Coastal Wear Sneakers at just $19.76. All options are currently
in stock and ready to ship!
```

---

## 6. The Data

### What's in BigQuery

The table `product_embeddings.products_with_vectors` has 4,000 rows with this schema:

| Column | Type | Example |
|--------|------|---------|
| `sku_id` | STRING | `SKU-BEA-0001` |
| `title` | STRING | `UrbanCare Premium Haircare Product 1` |
| `description` | STRING | `This premium haircare product is carefully designed...` |
| `category` | STRING | `Beauty & Personal Care` |
| `subcategory` | STRING | `Haircare` |
| `brand` | STRING | `UrbanCare` |
| `gender` | STRING | `Boys` |
| `color` | STRING | `White` |
| `size` | STRING | `One Size` |
| `price_aud` | FLOAT | `41.35` |
| `margin_percent` | INTEGER | `26` |
| `stock_quantity` | INTEGER | `481` |
| `fulfillment_eta_days` | INTEGER | `5` |
| `discount_percent` | INTEGER | `15` |
| `warranty_information` | STRING | `12 months manufacturer warranty` |
| `return_policy` | STRING | `60 days change of mind policy` |
| `store_availability` | JSON | `{"Kmart Melbourne CBD": true, ...}` |
| `tags` | REPEATED STRING | `["haircare", "urbancare", "kmart"]` |
| `embedding` | REPEATED FLOAT | `[0.23, -0.45, ... 768 numbers]` |

### Product Categories (with counts)

| Category | Products | Source File |
|----------|----------|-------------|
| Beauty & Personal Care | 500 | `beauty_personal_care_500.json` |
| Gifts & Photo Products | 500 | `gifts_photo_products_500.json` |
| Clothing & Accessories | 850 | `kmart_clothing_accessories_structured.json` |
| Home & Living | 1,650 | `kmart_home_living_products_structured.json` |
| Nursery & Kids | 500 | `nursery_kids_500.json` |
| **Total** | **4,000** | |

### How Data Got Into BigQuery

`create_embeddings_pipeline.py` was run once (by Dikshyanta). It:

1. Loaded all 5 JSON files (4,000 products)
2. For each product, combined title + description + category + brand + tags into one text block
3. Sent that text to Google's `text-embedding-004` model → got back a 768-number vector
4. Inserted the product + its vector into BigQuery

**This is already done. You don't need to run it again.**

---

## 7. What Vivek's Branch Added

### Branch: `vivek-contrib`

The original repo only had:
- Intent Agent (Gemini + fallback)
- Embeddings pipeline (one-time data loader)
- Vector search utility
- Documentation

**Vivek's branch completed the architecture** by adding:

| New File | Agent | What It Does | Lines |
|----------|-------|-------------|-------|
| `agents/context_agent.py` | Context Agent | Weather API, session history, temporal context | 219 |
| `agents/constraint_agent.py` | Constraint Agent | BigQuery inventory checks, price filtering, builds SQL WHERE | 250 |
| `agents/candidate_agent.py` | Candidate Agent | Hybrid vector + keyword search in BigQuery | 240 |
| `agents/ranking_agent.py` | Ranking Agent | Weighted multi-signal scoring, Top N selection | 200 |
| `agents/action_agent.py` | Action Agent | Gemini 2.5 Flash response generation | 200 |
| `agents/governance.py` | Governance Layer | Trace logging, timing, observability | 141 |
| `orchestrator.py` | Orchestrator | Chains all 6 agents in sequence | 252 |

### Bug Fixes

1. **`vector_search.py`**: Fixed broken import (`import aiplatform` → `from google.cloud import aiplatform`)
2. **Category matching**: Changed exact `=` to `LIKE '%...%'` because BigQuery categories are hierarchical (e.g., `Clothing & Accessories > Footwear & Accessories > Sneakers`)

### Updated Files

- **`requirements.txt`**: Added `requests`, `fastapi`, `uvicorn`
- **`agents/__init__.py`**: Updated to v0.2.0, added imports for all new agents

### Are These Changes Relevant?

**Yes — they complete the core architecture.** Before this branch:
- You could extract intent (Agent 1) ✓
- You could embed products (data pipeline) ✓
- Agents 2-6 were **not implemented** ✗
- There was **no orchestrator** to run the full pipeline ✗

After this branch: **The full pipeline works end-to-end.** You can type a query and get a ranked product list with a Gemini-generated response.

---

## 8. Live Demo Guide

### Prerequisites (One-Time Setup)

```bash
# 1. Clone and enter project
cd /Users/rvivek/playground/gen-search-101

# 2. Activate virtual environment
source venv/bin/activate

# 3. Make sure gcloud is available
export CLOUDSDK_PYTHON=/opt/homebrew/opt/python@3.13/libexec/bin/python3
export PATH="/opt/homebrew/share/google-cloud-sdk/bin:$PATH"

# 4. Set GCP project
gcloud config set project cloud-comrades-0120692

# 5. Verify auth works (should show your email)
gcloud auth list
```

### Running the Demo

#### Option 1: Full Pipeline Demo (Recommended for Hackathon)

```bash
# This runs 4 test queries through all 6 agents
python3 orchestrator.py
```

**What you'll see for each query:**
```
─────────────────────────────────────────────────────
🔍 Query: "I need cheap running shoes for a marathon next week"
─────────────────────────────────────────────────────

💬 Response:
Great news! I've found some fantastic budget-friendly running shoes...

📊 Trace: 26400ms total
   IntentAgent                     3200ms  success
   ContextAgent                     450ms  success
   ConstraintAgent                 2100ms  success
   CandidateGenerationAgent        8500ms  success
   RankingAgent                       5ms  success
   ActionAgent                     5200ms  success

🏆 Top 5 Products:
   1. Active Core Sneakers             $  39.16  score=0.7234
   2. Coastal Wear Sneakers            $  19.76  score=0.6891
   3. FreshSkin Sports Shoes           $  45.99  score=0.6544
   4. UrbanCare Athletic Runner        $  32.50  score=0.6321
   5. Outdoor Pro Trail Sneaker        $  48.00  score=0.6100
```

**Demo talking points:**
- "Notice how the system understood 'cheap' means under $50"
- "It checked real inventory in BigQuery — all products are in stock"
- "The weather is factored in — summer-appropriate recommendations"
- "Gemini wrote that response — not a template"
- "Total time ~20 seconds; each agent's contribution is traced"

#### Option 2: Just Intent Agent

```bash
python3 -m agents.intent_agent
```

Shows how Gemini extracts structured data from natural language.

#### Option 3: Just Vector Search

```bash
python3 vector_search.py
```

Shows semantic search: finds products similar to a text query.

#### Option 4: Run Tests

```bash
python3 test_intent_agent.py
```

Runs 6 test cases against the intent agent (should show 6/6 pass).

### Demo Script for Hackathon Presentation

**Slide 1:** "We built an AI shopping assistant that understands natural language"

**Live Demo:**
1. Open terminal, run `python3 orchestrator.py`
2. Show the first query running through all 6 agents
3. Point out the trace (timing of each agent)
4. Point out that it used real BigQuery data (4,000 products)
5. Point out Gemini wrote the response

**Slide 2:** "Here's how it works" (show the architecture diagram)

**Key talking points for judges:**
- *"We use 4 GCP services: Vertex AI, Gemini, BigQuery, and the Text Embeddings API"*
- *"6 specialized AI agents, each doing one job well"*
- *"Real product data — 4,000 Kmart products with vector embeddings"*
- *"Semantic search — you don't need exact keywords, the system understands meaning"*
- *"Governance layer tracks every step for observability"*

### Custom Queries (Interactive Demo)

If you want to run your own queries, add them to the `test_queries` list in `orchestrator.py`:

```python
test_queries = [
    "I need cheap running shoes for a marathon next week",
    "Looking for premium skincare products for sensitive skin",
    "Show me blue Nike sneakers under $100",
    "Date night with my partner",
    # Add your own:
    "Birthday gift for a 5 year old boy",
    "Home office furniture under $200",
    "Waterproof jacket for camping",
]
```

---

## 9. Troubleshooting

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `gcloud: command not found` | gcloud not in PATH | `export PATH="/opt/homebrew/share/google-cloud-sdk/bin:$PATH"` |
| `Permission denied` on git push | Not a collaborator on the repo | Ask Dikshyanta to add you, or fork |
| `JSONDecodeError` from Intent Agent | Gemini sometimes truncates long JSON | The code has automatic fallback handling |
| `No results found` | Category filter too strict | Already fixed — uses `LIKE '%...%'` for fuzzy matching |
| `ModuleNotFoundError` | Venv not activated | `source venv/bin/activate` |
| BigQuery timeout | Large embedding query | Normal — vector search over 4K rows takes 5-10 seconds |

### Quick Health Check

```bash
# 1. Python OK?
python3 --version
# Expected: Python 3.13.x

# 2. Deps installed?
python3 -c "import vertexai; import google.cloud.bigquery; print('OK')"

# 3. GCP auth OK?
gcloud auth list

# 4. BigQuery accessible?
python3 -c "
from google.cloud import bigquery
client = bigquery.Client(project='cloud-comrades-0120692')
r = list(client.query('SELECT COUNT(*) c FROM product_embeddings.products_with_vectors').result())
print(f'Products in BQ: {r[0].c}')
"
# Expected: Products in BQ: 4000

# 5. Full pipeline OK?
python3 orchestrator.py
```

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────┐
│                  GEN-SEARCH-101                         │
│           AI Product Recommendation System               │
├─────────────────────────────────────────────────────────┤
│ GCP Project:    cloud-comrades-0120692                   │
│ Region:         us-central1                             │
│ BigQuery Table: product_embeddings.products_with_vectors│
│ Products:       4,000 (5 categories)                    │
│ Embedding Dim:  768 (text-embedding-004)                │
│ LLM:            Gemini 2.5 Flash (Vertex AI)            │
│ Agents:         6 (Intent→Context→Constraint→           │
│                    Candidate→Ranking→Action)             │
│ Branch:         vivek-contrib                           │
│ Main entry:     python3 orchestrator.py                 │
├─────────────────────────────────────────────────────────┤
│ GCP Services Used:                                      │
│   ✅ Vertex AI (AI platform)                            │
│   ✅ Gemini 2.5 Flash (LLM)                             │
│   ✅ Text Embeddings API (text-embedding-004)            │
│   ✅ BigQuery (data warehouse + vector search)           │
│   ✅ IAM / gcloud auth                                   │
│   ✅ Compute Engine API (Vertex AI dependency)           │
│   📋 Cloud Run (planned - deployment)                   │
│   📋 Cloud Trace (planned - production tracing)         │
│   📋 Cloud Logging (planned - production logs)          │
└─────────────────────────────────────────────────────────┘
```
