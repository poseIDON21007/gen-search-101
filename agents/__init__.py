"""
Multi-Agent Recommendation System
"""

__version__ = "0.2.0"

from agents.intent_agent_fallback import IntentAgentFallback
from agents.context_agent import ContextAgent
from agents.constraint_agent import ConstraintAgent
from agents.candidate_agent import CandidateGenerationAgent
from agents.ranking_agent import RankingAgent
from agents.action_agent import ActionAgent
from agents.governance import TraceLogger
