#!/usr/bin/env python3
"""
Ollama Embeddings Generator
Generates embeddings using local Ollama instance
Supports both Mac (M4) and Fedora server deployment
"""

import json
import logging
import requests
import numpy as np
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import pickle
from pathlib import Path
import time

logger = logging.getLogger(__name__)

@dataclass
class EmbeddingConfig:
    """Configuration for Ollama embeddings"""
    model: str = "nomic-embed-text"  # 768-dimensional embeddings
    ollama_host: str = "http://localhost:11434"
    fedora_host: str = "http://192.168.1.100:11434"  # Fedora server as fallback
    batch_size: int = 32
    max_retries: int = 3
    retry_delay: float = 1.0
    cache_dir: Path = Path("/tmp/mind-base-embeddings-cache")
    use_cache: bool = True
    dimensions: int = 768  # nomic-embed-text dimensions

@dataclass
class EmbeddingResult:
    """Result of embedding generation"""
    text: str
    embedding: List[float]
    model: str
    dimensions: int
    processing_time: float
    cached: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

class OllamaEmbeddings:
    """Generate embeddings using Ollama"""
    
    def __init__(self, config: Optional[EmbeddingConfig] = None):
        self.config = config or EmbeddingConfig()
        self.session = requests.Session()
        
        # Create cache directory
        if self.config.use_cache:
            self.config.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Test connection
        self.current_host = self._test_connection()
        logger.info(f"Using Ollama at: {self.current_host}")
    
    def _test_connection(self) -> str:
        """Test connection to Ollama instances"""
        # Try local first
        try:
            response = requests.get(f"{self.config.ollama_host}/api/tags", timeout=2)
            if response.status_code == 200:
                return self.config.ollama_host
        except:
            pass
        
        # Try Fedora server
        try:
            response = requests.get(f"{self.config.fedora_host}/api/tags", timeout=2)
            if response.status_code == 200:
                logger.info("Using Fedora server for Ollama")
                return self.config.fedora_host
        except:
            pass
        
        # Default to localhost
        logger.warning("Could not connect to Ollama, defaulting to localhost")
        return self.config.ollama_host
    
    def generate_embedding(self, text: str, 
                          use_cache: Optional[bool] = None) -> EmbeddingResult:
        """
        Generate embedding for a single text
        
        Args:
            text: Text to embed
            use_cache: Override cache setting
            
        Returns:
            EmbeddingResult with embedding vector
        """
        start_time = time.time()
        use_cache = use_cache if use_cache is not None else self.config.use_cache
        
        # Check cache
        if use_cache:
            cached_result = self._get_cached_embedding(text)
            if cached_result:
                cached_result.cached = True
                return cached_result
        
        # Generate embedding
        embedding = self._call_ollama_api(text)
        
        if not embedding:
            raise ValueError(f"Failed to generate embedding for text: {text[:100]}...")
        
        processing_time = time.time() - start_time
        
        result = EmbeddingResult(
            text=text,
            embedding=embedding,
            model=self.config.model,
            dimensions=len(embedding),
            processing_time=processing_time
        )
        
        # Cache result
        if use_cache:
            self._cache_embedding(text, result)
        
        return result
    
    def generate_embeddings_batch(self, texts: List[str], 
                                 show_progress: bool = True) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
            show_progress: Show progress bar
            
        Returns:
            List of EmbeddingResults
        """
        results = []
        total = len(texts)
        
        for i, text in enumerate(texts):
            if show_progress and i % 10 == 0:
                logger.info(f"Processing {i}/{total} embeddings...")
            
            try:
                result = self.generate_embedding(text)
                results.append(result)
            except Exception as e:
                logger.error(f"Error embedding text {i}: {e}")
                # Create empty embedding on error
                results.append(EmbeddingResult(
                    text=text,
                    embedding=[0.0] * self.config.dimensions,
                    model=self.config.model,
                    dimensions=self.config.dimensions,
                    processing_time=0.0,
                    metadata={"error": str(e)}
                ))
        
        if show_progress:
            logger.info(f"Completed {total} embeddings")
        
        return results
    
    def _call_ollama_api(self, text: str) -> Optional[List[float]]:
        """Call Ollama embedding API"""
        url = f"{self.current_host}/api/embeddings"
        
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.post(
                    url,
                    json={
                        "model": self.config.model,
                        "prompt": text
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("embedding")
                else:
                    logger.warning(f"Ollama API error: {response.status_code}")
            
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request error (attempt {attempt + 1}): {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay * (attempt + 1))
            
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                return None
        
        return None
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        # Include model name in cache key
        key_string = f"{self.config.model}:{text}"
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def _get_cached_embedding(self, text: str) -> Optional[EmbeddingResult]:
        """Get cached embedding if exists"""
        cache_key = self._get_cache_key(text)
        cache_file = self.config.cache_dir / f"{cache_key}.pkl"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                logger.debug(f"Cache read error: {e}")
        
        return None
    
    def _cache_embedding(self, text: str, result: EmbeddingResult):
        """Cache embedding result"""
        cache_key = self._get_cache_key(text)
        cache_file = self.config.cache_dir / f"{cache_key}.pkl"
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(result, f)
        except Exception as e:
            logger.debug(f"Cache write error: {e}")
    
    def compute_similarity(self, embedding1: List[float], 
                         embedding2: List[float]) -> float:
        """
        Compute cosine similarity between two embeddings
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score (0-1)
        """
        # Convert to numpy arrays
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Compute cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        
        # Clamp to [0, 1]
        return max(0.0, min(1.0, similarity))
    
    def find_similar(self, query_embedding: List[float], 
                    embeddings: List[List[float]], 
                    top_k: int = 10,
                    threshold: float = 0.7) -> List[Tuple[int, float]]:
        """
        Find similar embeddings
        
        Args:
            query_embedding: Query embedding vector
            embeddings: List of embeddings to search
            top_k: Number of top results to return
            threshold: Minimum similarity threshold
            
        Returns:
            List of (index, similarity) tuples
        """
        similarities = []
        
        for i, embedding in enumerate(embeddings):
            similarity = self.compute_similarity(query_embedding, embedding)
            if similarity >= threshold:
                similarities.append((i, similarity))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    def cluster_embeddings(self, embeddings: List[List[float]], 
                          n_clusters: int = 5) -> Dict[int, List[int]]:
        """
        Cluster embeddings using K-means
        
        Args:
            embeddings: List of embedding vectors
            n_clusters: Number of clusters
            
        Returns:
            Dictionary mapping cluster ID to list of embedding indices
        """
        try:
            from sklearn.cluster import KMeans
            
            # Convert to numpy array
            X = np.array(embeddings)
            
            # Perform clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            labels = kmeans.fit_predict(X)
            
            # Group by cluster
            clusters = {}
            for i, label in enumerate(labels):
                if label not in clusters:
                    clusters[label] = []
                clusters[label].append(i)
            
            return clusters
        
        except ImportError:
            logger.warning("scikit-learn not installed, clustering unavailable")
            return {0: list(range(len(embeddings)))}
    
    def reduce_dimensions(self, embeddings: List[List[float]], 
                        target_dim: int = 2) -> np.ndarray:
        """
        Reduce embedding dimensions for visualization
        
        Args:
            embeddings: List of embedding vectors
            target_dim: Target dimensions (2 or 3 for visualization)
            
        Returns:
            Reduced dimension array
        """
        try:
            from sklearn.decomposition import PCA
            
            # Convert to numpy array
            X = np.array(embeddings)
            
            # Perform PCA
            pca = PCA(n_components=target_dim)
            X_reduced = pca.fit_transform(X)
            
            return X_reduced
        
        except ImportError:
            logger.warning("scikit-learn not installed, dimension reduction unavailable")
            return np.array(embeddings)[:, :target_dim]
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model"""
        url = f"{self.current_host}/api/show"
        
        try:
            response = self.session.post(
                url,
                json={"name": self.config.model},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Error getting model info: {e}")
        
        return {
            "model": self.config.model,
            "dimensions": self.config.dimensions,
            "host": self.current_host
        }
    
    def switch_to_fedora(self):
        """Switch to Fedora server for processing"""
        self.current_host = self.config.fedora_host
        logger.info(f"Switched to Fedora server: {self.current_host}")
    
    def switch_to_local(self):
        """Switch to local Ollama instance"""
        self.current_host = self.config.ollama_host
        logger.info(f"Switched to local Ollama: {self.current_host}")
    
    def clear_cache(self):
        """Clear embedding cache"""
        if self.config.cache_dir.exists():
            for cache_file in self.config.cache_dir.glob("*.pkl"):
                cache_file.unlink()
            logger.info("Embedding cache cleared")


# Utility functions
def test_ollama_connection():
    """Test Ollama connection and model availability"""
    embedder = OllamaEmbeddings()
    
    # Test embedding generation
    test_text = "This is a test message for embedding generation."
    result = embedder.generate_embedding(test_text)
    
    print(f"Model: {result.model}")
    print(f"Dimensions: {result.dimensions}")
    print(f"Processing time: {result.processing_time:.3f}s")
    print(f"Embedding sample: {result.embedding[:5]}...")
    
    return embedder


def batch_embed_conversations(conversations: List[str], 
                             config: Optional[EmbeddingConfig] = None) -> List[EmbeddingResult]:
    """
    Batch embed conversations
    
    Args:
        conversations: List of conversation texts
        config: Optional embedding configuration
        
    Returns:
        List of embedding results
    """
    embedder = OllamaEmbeddings(config)
    return embedder.generate_embeddings_batch(conversations)


if __name__ == "__main__":
    # Test the embedding system
    logging.basicConfig(level=logging.INFO)
    
    print("Testing Ollama Embeddings...")
    embedder = test_ollama_connection()
    
    # Test similarity
    texts = [
        "Machine learning is a subset of artificial intelligence.",
        "AI and ML are closely related fields.",
        "The weather is nice today.",
        "Deep learning uses neural networks."
    ]
    
    print("\nGenerating embeddings for test texts...")
    results = embedder.generate_embeddings_batch(texts)
    
    print("\nSimilarity matrix:")
    for i, text1 in enumerate(texts):
        similarities = []
        for j, text2 in enumerate(texts):
            sim = embedder.compute_similarity(
                results[i].embedding, 
                results[j].embedding
            )
            similarities.append(f"{sim:.2f}")
        print(f"{i}: {' '.join(similarities)}")
    
    print("\nEmbedding system ready!")