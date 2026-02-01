# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Embedding service for generating vector embeddings using Vertex AI.

Uses Google's text-embedding-004 model (768 dimensions) for semantic search.
"""

import os
# from vertexai.language_models import TextEmbeddingModel

# Initialize Vertex AI
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "my-project-pk-484623")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")

# Model configuration
EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_DIMENSION = 768

# Cache the model instance
_model = None


def _get_model():
    """Get or create the embedding model instance."""
    global _model
    if _model is None:
        try:
            from vertexai.language_models import TextEmbeddingModel
            _model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL)
        except Exception as e:
            print(f"Warning: Failed to load TextEmbeddingModel: {e}")
            _model = None
    return _model


def generate_embedding(text: str) -> list[float]:
    """Generate a vector embedding for the given text.
    
    Args:
        text: The text to generate an embedding for.
        
    Returns:
        A list of floats representing the 768-dimensional embedding vector.
    """
    if not text or not text.strip():
        # Return zero vector for empty text
        return [0.0] * EMBEDDING_DIMENSION
    
    model = _get_model()
    embeddings = model.get_embeddings([text])
    
    if embeddings and len(embeddings) > 0:
        return list(embeddings[0].values)
    
    return [0.0] * EMBEDDING_DIMENSION


def generate_embeddings_batch(texts: list[str], batch_size: int = 5) -> list[list[float]]:
    """Generate embeddings for multiple texts in batches.
    
    Args:
        texts: List of texts to generate embeddings for.
        batch_size: Number of texts to process per API call (max 5 for Vertex AI).
        
    Returns:
        List of embedding vectors, one per input text.
    """
    if not texts:
        return []
    
    model = _get_model()
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        # Handle empty strings in batch
        batch = [t if t and t.strip() else " " for t in batch]
        
        embeddings = model.get_embeddings(batch)
        all_embeddings.extend([list(e.values) for e in embeddings])
    
    return all_embeddings
