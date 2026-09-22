"""Business policy: thresholds are BUSINESS decisions, not model decisions.

Pure function => property-based-testable, reviewable by risk officers.
"""

BLOCK_THRESHOLD_DEFAULT = 0.85
REVIEW_BAND = 0.15  # width of the manual-review band below the block threshold


def decide(fraud_probability: float, block_threshold: float = BLOCK_THRESHOLD_DEFAULT) -> str:
    if fraud_probability >= block_threshold:
        return "block"
    if fraud_probability >= block_threshold - REVIEW_BAND:
        return "review"
    return "allow"
