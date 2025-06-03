import pytest

from app.external_services.sentiment_mock import MockSentimentAnalyzer


@pytest.mark.asyncio
async def test_sentiment_positive():
    analyzer = MockSentimentAnalyzer()
    result = await analyzer.analyze("I love this video!")
    assert result == "positive"


@pytest.mark.asyncio
async def test_sentiment_negative():
    analyzer = MockSentimentAnalyzer()
    result = await analyzer.analyze("This made me :( sad")
    assert result == "negative"


@pytest.mark.asyncio
async def test_sentiment_neutral():
    analyzer = MockSentimentAnalyzer()
    result = await analyzer.analyze("Just an ordinary comment")
    assert result == "neutral" 