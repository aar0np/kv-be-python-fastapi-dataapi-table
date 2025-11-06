"""
Embedding service for generating vector embeddings using IBM Granite model.

This service uses the IBM Granite-Embedding-30m-English model to generate
384-dimensional embeddings for text. The model is loaded once at startup
and cached in memory for fast inference.
"""

import logging
import re
from typing import List, Optional

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Singleton service for generating embeddings using IBM Granite model.

    The model is loaded once at initialization and cached for fast inference.
    """

    _instance: Optional["EmbeddingService"] = None
    _model: Optional[SentenceTransformer] = None

    MODEL_NAME = "ibm-granite/granite-embedding-30m-english"
    EMBEDDING_DIMENSION = 384
    MAX_TOKENS = 512

    def __new__(cls):
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the embedding service."""
        if self._model is None:
            logger.info(f"Loading embedding model: {self.MODEL_NAME}")
            self._model = SentenceTransformer(self.MODEL_NAME)
            logger.info(
                f"Embedding model loaded successfully. Dimension: {self.EMBEDDING_DIMENSION}"
            )

    def _clip_to_max_tokens(self, text: str) -> str:
        """
        Clip text to maximum token limit (512 tokens).

        Uses a simple tokenizer that matches the pattern used for NVIDIA embeddings.
        This is a conservative approximation - actual tokenization may differ slightly.

        Args:
            text: The input text to clip

        Returns:
            The clipped text if over limit, otherwise original text
        """
        # Simple tokenizer: matches word characters and punctuation
        token_re = re.compile(r"\w+|[^\w\s]", flags=re.UNICODE)
        tokens = token_re.findall(text)

        if len(tokens) <= self.MAX_TOKENS:
            return text

        # Clip to max tokens and rejoin
        clipped_tokens = tokens[: self.MAX_TOKENS]
        # Find the position in original text where we should cut
        # This is approximate but works well enough
        clipped_text = " ".join(clipped_tokens)

        logger.warning(f"Text clipped from {len(tokens)} to {self.MAX_TOKENS} tokens")

        return clipped_text

    def generate_embedding(self, text: str, clip_tokens: bool = True) -> List[float]:
        """
        Generate a 384-dimensional embedding vector for the given text.

        Args:
            text: The input text to embed
            clip_tokens: Whether to clip text to MAX_TOKENS (default: True)

        Returns:
            A list of 384 float values representing the embedding vector

        Raises:
            ValueError: If text is empty or model is not loaded
        """
        if not text or not text.strip():
            raise ValueError("Cannot generate embedding for empty text")

        if self._model is None:
            raise ValueError("Embedding model not loaded")

        # Clip to token limit if requested
        if clip_tokens:
            text = self._clip_to_max_tokens(text)

        # Generate embedding
        # encode() returns numpy array, convert to list of floats
        embedding = self._model.encode(text, convert_to_numpy=True)

        return embedding.tolist()

    def generate_embeddings_batch(
        self, texts: List[str], clip_tokens: bool = True
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in a batch.

        This is more efficient than calling generate_embedding() multiple times
        as the model can process multiple texts in parallel.

        Args:
            texts: List of input texts to embed
            clip_tokens: Whether to clip texts to MAX_TOKENS (default: True)

        Returns:
            List of embedding vectors, one for each input text

        Raises:
            ValueError: If any text is empty or model is not loaded
        """
        if not texts:
            raise ValueError("Cannot generate embeddings for empty list")

        if self._model is None:
            raise ValueError("Embedding model not loaded")

        # Validate and clip texts
        processed_texts = []
        for text in texts:
            if not text or not text.strip():
                raise ValueError("Cannot generate embedding for empty text")

            if clip_tokens:
                text = self._clip_to_max_tokens(text)

            processed_texts.append(text)

        # Generate embeddings in batch
        embeddings = self._model.encode(
            processed_texts, convert_to_numpy=True, show_progress_bar=False
        )

        return [emb.tolist() for emb in embeddings]


# Global instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """
    Get the global embedding service instance.

    This function initializes the service on first call and returns
    the cached instance on subsequent calls.

    Returns:
        The global EmbeddingService instance
    """
    global _embedding_service

    if _embedding_service is None:
        _embedding_service = EmbeddingService()

    return _embedding_service
