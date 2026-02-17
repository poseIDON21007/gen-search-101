"""
Orchestration Layer - Python App / Cloud Run
Wires all agents together following the architecture:
  User → Intent Agent → Context Agent → Constraint Agent
    → Candidate Generation Agent → Ranking Agent → Action Agent
With Governance / Trace Logger wrapping everything.
"""

import os
import json
import time
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from agents.intent_agent import IntentAgent
from agents.intent_agent_fallback import IntentAgentFallback
from agents.context_agent import ContextAgent
from agents.constraint_agent import ConstraintAgent
from agents.candidate_agent import CandidateGenerationAgent
from agents.ranking_agent import RankingAgent
from agents.action_agent import ActionAgent
from agents.governance import TraceLogger, timed_agent_call


class Orchestrator:
    """Main orchestrator that chains all agents per the architecture diagram.

    Flow:
    1. Intent Agent (Gemini 2.5 Flash) → structured intent
    2. Context Agent (Function Call) → weather, location, session history
    3. Constraint Agent (Pricing / Inventory Check) → filtered constraints
    4. Candidate Generation Agent → Vertex AI Search (Vector + Keyword)
    5. Ranking Agent (Weighted scoring / AutoML) → Top 5 Products
    6. Action Agent (Gemini 2.5 Flash) → Natural language response
    """

    def __init__(self, use_gemini: bool = True):
        load_dotenv()
        self.project_id = os.getenv("GCP_PROJECT_ID")
        self.region = os.getenv("GCP_REGION", "us-central1")

        print("\n" + "=" * 60)
        print("  Initializing Multi-Agent Orchestrator")
        print("=" * 60 + "\n")

        # Governance layer
        self.trace_logger = TraceLogger()

        # Agent 1: Intent
        if use_gemini:
            try:
                self.intent_agent = IntentAgent(
                    project_id=self.project_id, region=self.region
                )
                self._intent_mode = "gemini"
            except Exception as e:
                print(f"⚠ Gemini Intent Agent failed ({e}), using fallback")
                self.intent_agent = IntentAgentFallback()
                self._intent_mode = "fallback"
        else:
            self.intent_agent = IntentAgentFallback()
            self._intent_mode = "fallback"

        # Agent 2: Context
        self.context_agent = ContextAgent()

        # Agent 3: Constraint
        self.constraint_agent = ConstraintAgent(project_id=self.project_id)

        # Agent 4: Candidate Generation
        self.candidate_agent = CandidateGenerationAgent(
            project_id=self.project_id, region=self.region
        )

        # Agent 5: Ranking
        self.ranking_agent = RankingAgent()

        # Agent 6: Action
        if use_gemini:
            try:
                self.action_agent = ActionAgent(
                    project_id=self.project_id, region=self.region
                )
                self._action_mode = "gemini"
            except Exception:
                self._action_mode = "template"
                self.action_agent = None
        else:
            self._action_mode = "template"
            self.action_agent = None

        print(f"\n✅ All agents initialized (intent={self._intent_mode}, action={self._action_mode})\n")

    def run(
        self,
        query: str,
        user_id: str = None,
        session_id: str = None,
        location: str = "Melbourne, AU",
        top_n: int = 5,
    ) -> Dict[str, Any]:
        """Run the full multi-agent pipeline.

        Args:
            query: Natural language user query
            user_id: User identifier
            session_id: Session identifier
            location: User location
            top_n: Number of top products to return

        Returns:
            Full pipeline result with response
        """
        # Start governance trace
        trace_id = self.trace_logger.start_trace(query, user_id, session_id)

        pipeline_data = {}

        try:
            # ─── Step 1: Intent Agent ────────────────────────────
            with timed_agent_call(self.trace_logger, "IntentAgent") as t:
                t.input_data = query
                intent = self.intent_agent.extract_intent(
                    user_query=query, user_id=user_id, session_id=session_id
                )
                intent_dict = self.intent_agent.intent_to_dict(intent)
                t.output_data = intent_dict
                pipeline_data = intent_dict

            # ─── Step 2: Context Agent ───────────────────────────
            with timed_agent_call(self.trace_logger, "ContextAgent") as t:
                t.input_data = pipeline_data
                pipeline_data = self.context_agent.enrich(
                    pipeline_data, user_id=user_id,
                    session_id=session_id, location=location,
                )
                t.output_data = pipeline_data

            # ─── Step 3: Constraint Agent ────────────────────────
            with timed_agent_call(self.trace_logger, "ConstraintAgent") as t:
                t.input_data = pipeline_data
                pipeline_data = self.constraint_agent.apply_constraints(pipeline_data)
                t.output_data = pipeline_data

            # ─── Step 4: Candidate Generation Agent ──────────────
            with timed_agent_call(self.trace_logger, "CandidateGenerationAgent") as t:
                t.input_data = pipeline_data
                pipeline_data = self.candidate_agent.generate_candidates(
                    pipeline_data, top_k=50
                )
                t.output_data = f"{pipeline_data['candidates']['total_candidates']} candidates"

            # ─── Step 5: Ranking Agent ───────────────────────────
            with timed_agent_call(self.trace_logger, "RankingAgent") as t:
                t.input_data = f"{len(pipeline_data.get('candidates', {}).get('products', []))} products"
                pipeline_data = self.ranking_agent.rank(pipeline_data, top_n=top_n)
                t.output_data = f"{len(pipeline_data.get('ranked_products', []))} top products"

            # ─── Step 6: Action Agent ────────────────────────────
            with timed_agent_call(self.trace_logger, "ActionAgent") as t:
                t.input_data = f"{len(pipeline_data.get('ranked_products', []))} products"
                if self.action_agent:
                    pipeline_data = self.action_agent.generate_response(pipeline_data)
                else:
                    pipeline_data["response"] = self._template_response(pipeline_data)
                t.output_data = pipeline_data.get("response", "")[:100]

        except Exception as e:
            self.trace_logger.log_step("Orchestrator", query, None, 0,
                                       status="error", error=str(e))
            pipeline_data["response"] = f"An error occurred: {str(e)}"
            pipeline_data["error"] = str(e)

        # End trace
        self.trace_logger.end_trace(pipeline_data.get("response"))

        # Add trace info
        pipeline_data["trace_id"] = trace_id
        pipeline_data["trace"] = self.trace_logger.get_last_trace()

        return pipeline_data

    def _template_response(self, data: Dict[str, Any]) -> str:
        """Simple template response when Action Agent is unavailable."""
        products = data.get("ranked_products", [])
        product_type = data.get("product_type", "products")

        if not products:
            return "Sorry, I couldn't find any matching products."

        lines = [f"Here are my top {len(products)} recommendations for {product_type}:\n"]
        for i, p in enumerate(products, 1):
            lines.append(
                f"{i}. {p.get('title', 'Unknown')} - ${p.get('price_aud', 0):.2f} AUD "
                f"({p.get('brand', 'N/A')})"
            )
        return "\n".join(lines)


def main():
    """Interactive demo of the full pipeline."""
    print("\n🚀 Multi-Agent Product Recommendation System")
    print("=" * 50)

    # Initialize (use Gemini by default)
    orchestrator = Orchestrator(use_gemini=True)

    test_queries = [
        "I need cheap running shoes for a marathon next week",
        "Looking for premium skincare products for sensitive skin",
        "Show me blue Nike sneakers under $100",
        "Date night with my partner",
    ]

    for query in test_queries:
        print(f"\n{'─' * 60}")
        print(f"🔍 Query: \"{query}\"")
        print(f"{'─' * 60}")

        result = orchestrator.run(
            query=query,
            user_id="demo_user",
            session_id="demo_session",
            location="Melbourne, AU",
            top_n=5,
        )

        # Print response
        print(f"\n💬 Response:\n{result.get('response', 'No response')}")

        # Print trace summary
        trace = result.get("trace", {})
        if trace:
            print(f"\n📊 Trace: {trace.get('total_duration_ms', 0):.0f}ms total")
            for step in trace.get("steps", []):
                print(f"   {step['agent']:30s} {step['duration_ms']:>8.0f}ms  {step['status']}")

        # Print top products
        ranked = result.get("ranked_products", [])
        if ranked:
            print(f"\n🏆 Top {len(ranked)} Products:")
            for i, p in enumerate(ranked, 1):
                print(
                    f"   {i}. {p.get('title', '?')[:45]:45s} "
                    f"${p.get('price_aud', 0):>7.2f}  "
                    f"score={p.get('ranking_score', 0):.4f}"
                )


if __name__ == "__main__":
    main()
