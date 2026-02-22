"""Common text processing utilities."""

import re
from typing import List

# Comprehensive stop words set (union of both existing implementations)
STOP_WORDS = frozenset({
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'been', 'being', 'but',
    'by', 'can', 'cannot', 'could', 'did', 'do', 'does', 'for', 'from',
    'had', 'has', 'have', 'how', 'in', 'is', 'may', 'might', 'must',
    'of', 'on', 'or', 'should', 'that', 'the', 'these', 'this', 'those',
    'to', 'was', 'were', 'what', 'when', 'where', 'which', 'who', 'why',
    'will', 'with', 'would'
})


def extract_key_terms(query: str, max_terms: int = 5) -> List[str]:
    """Extract meaningful key terms from a query string.

    Filters out stop words and extracts significant terms for search enhancement.

    Args:
        query: Input query text
        max_terms: Maximum number of terms to return (default: 5)

    Returns:
        List of key terms, filtered for stop words and minimum length
    """
    # Extract words (alphanumeric, including hyphens)
    words = re.findall(
        r'\b[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]\b|\b[a-zA-Z0-9]\b',
        query.lower()
    )

    # Filter stop words and short terms
    filtered = [w for w in words if w not in STOP_WORDS and len(w) > 2]

    return filtered[:max_terms]
