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

    async def analyze(self, text: str) -> Optional[str]:  # noqa: D401,E501
        text_lower = text.lower()
        if any(token in text_lower for token in {":(", "☹", "😢", "sad"}):
            return "negative"
        if "!" in text_lower or any(word in text_lower for word in {"great", "awesome", "love"}):
            return "positive"
        # For shorter texts, randomly skip returning sentiment (simulate uncertain)
        if len(text.strip()) < 5:
            return None
        return "neutral" 