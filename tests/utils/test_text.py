import re

import pytest

from app.utils.text import clip_to_512_tokens

TOKEN_RE = re.compile(r"\w+|[^\w\s]", flags=re.UNICODE)


def _count_tokens(s: str) -> int:
    return len(TOKEN_RE.findall(s))


@pytest.mark.parametrize("token_count", [600, 513, 512, 100])
def test_clip_to_512_tokens(token_count: int):
    """Ensure text is clipped to 512 tokens when necessary."""

    input_text = " ".join(f"tok{i}" for i in range(token_count))
    result = clip_to_512_tokens(input_text)

    if token_count <= 512:
        assert result == input_text
        assert _count_tokens(result) == token_count
    else:
        assert _count_tokens(result) == 512
        assert result.split()[0] == "tok0"
        assert result.split()[-1] == "tok511"


def test_unicode_and_whitespace():
    """Function should leave short text with Unicode punctuation unchanged."""

    text = "你好，   世界！  Hello — world…"
    clipped = clip_to_512_tokens(text)
    assert clipped == text
    assert _count_tokens(clipped) < 512
