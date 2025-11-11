"""
Utility functions for matching.
Simplified - most logic moved to specialized modules.
"""

def format_experience_years(years: float | None) -> str | None:
    """Format experience years for display."""
    if years is None:
        return None
    if years < 1:
        return "<1 yr"
    if years % 1 == 0:
        return f"{int(years)} yrs"
    return f"{years:.1f} yrs"

