from __future__ import annotations

"""Text processing helpers used across the KillrVideo backend."""

import re

__all__ = ["clip_to_512_tokens"]

# ---------------------------------------------------------------------------
# Basic tokenizer
# ---------------------------------------------------------------------------
# The NV-Embed provider enforces a hard limit of **512 tokens** for both
# `$vectorize` requests and vector-enabled queries.  We approximate token
# boundaries using a lightweight regex that splits on standard *word* chunks
# while treating punctuation and symbols as individual tokens.  This is **not**
# an exact match of the provider's internal SentencePiece model but is
# sufficiently close for defensive clipping.
#
#   • Consecutive whitespace is ignored (no empty tokens).
#   • Unicode punctuation characters are captured as standalone tokens.
#   • The pattern is Unicode-aware through the `re.UNICODE` flag (default in
#     Python 3 but kept explicit).
# ---------------------------------------------------------------------------
TOKEN_RE = re.compile(r"\w+|[^\w\s]", flags=re.UNICODE)
MAX_TOKENS_NV_EMBED = 512


def clip_to_512_tokens(text: str) -> str:  # noqa: D401
    """Return *text* truncated to **≤512** tokens.

    If the input already fits under the limit it is returned unchanged.  For
    longer inputs the first 512 tokens are kept and re-joined using a single
    space so downstream code works with a valid plain-text string.

    Parameters
    ----------
    text:
        Arbitrary input string (may contain newlines, tabs, or Unicode
        punctuation).

    Returns
    -------
    str
        The (possibly) truncated string, guaranteed to be ≤512 tokens when
        tokenised via :pydata:`TOKEN_RE`.
    """

    if not text:
        return text  # Early-exit for empty or ``None``‐like strings

    tokens = TOKEN_RE.findall(text)

    if len(tokens) <= MAX_TOKENS_NV_EMBED:
        # No truncation needed – preserve original spacing to avoid surprising
        # callers that might rely on exact text equality (e.g., hashing).
        return text

    clipped_tokens = tokens[:MAX_TOKENS_NV_EMBED]

    # Re-join tokens with a single space.  This canonical form is sufficient
    # for embedding purposes and avoids the complexity of reconstructing the
    # original whitespace layout.
    return " ".join(clipped_tokens)
