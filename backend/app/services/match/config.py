# app/services/match/config.py
"""
Match Configuration - Defines thresholds for the matching algorithm.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class MatchConfig:
    """Configuration for matching algorithm."""
    
    # Cosine similarity threshold for RAG vector search
    min_cosine_for_evidence: float = 0.35


CFG = MatchConfig()
