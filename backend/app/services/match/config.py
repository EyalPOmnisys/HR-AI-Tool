"""
Match configuration - simplified for new clean architecture.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class MatchConfig:
    """Configuration for matching algorithm."""
    
    # Cosine similarity threshold for RAG matching
    min_cosine_for_evidence: float = 0.35
    
    # RAG vs LLM score weights (for final combination)
    rag_weight: float = 0.5
    llm_weight: float = 0.5


CFG = MatchConfig()
