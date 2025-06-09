from __future__ import annotations

"""A simple mocked sentiment analysis service for development and testing.

The service does not perform any real natural-language processing. Instead, it
returns a deterministic sentiment *based on the input text* to make unit tests
repeatable while still providing variation.

Rules (very naive):
1. If text contains an exclamation mark `!` → "positive".
2. If text contains any sad emoji like ":(" or "☹" → "negative".
3. Otherwise → "neutral".
"""

from typing import Optional


class MockSentimentAnalyzer:
    """Very naive deterministic sentiment inference for tests."""

    async def analyze_score(self, text: str) -> Optional[float]:  # noqa: D401,E501
        """Return a sentiment score between -1.0 (negative) and 1.0 (positive)."""
        text_lower = text.lower()
        if any(
            token in text_lower for token in {":(", "☹", "😢", "sad", "bad", "terrible"}
        ):
            return -0.8
        if "!" in text_lower or any(
            word in text_lower for word in {"great", "awesome", "love", "excellent"}
        ):
            return 0.9
        # For shorter texts, randomly skip returning sentiment (simulate uncertain)
        if len(text.strip()) < 10:
            return None
        return 0.1  # Default to slightly positive/neutral
