import pytest

from app.external_services.sentiment_mock import MockSentimentAnalyzer


@pytest.mark.asyncio
async def test_sentiment_positive():
    analyzer = MockSentimentAnalyzer()
    result = await analyzer.analyze_score("I love this video!")
    assert isinstance(result, float)
    assert result > 0


@pytest.mark.asyncio
async def test_sentiment_negative():
    analyzer = MockSentimentAnalyzer()
    result = await analyzer.analyze_score("This made me :( sad")
    assert isinstance(result, float)
    assert result < 0


@pytest.mark.asyncio
async def test_sentiment_neutral():
    analyzer = MockSentimentAnalyzer()
    result = await analyzer.analyze_score("Just an ordinary comment")
    assert isinstance(result, float)
