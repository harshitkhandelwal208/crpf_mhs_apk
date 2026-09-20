"""
Mental Health Clinical Knowledge Base & RAG Vector Search
Powered by 100% Local AI in the HK Neural Tensor (.hk) binary format.
Provides sub-millisecond vector search with lexical fallback for maximum resilience.
"""

import os
import re
import json
import math
from pathlib import Path
try:
    import numpy as np
except ImportError:
    np = None

from app.ai.hk_format import load_hk, HKModelPackage



class ClinicalKnowledgeBase:
    """
    Manages the RAG clinical protocol documents and semantic similarity matching
    using local .hk neural tensor binary weights.
    """

    def __init__(self, hk_path: Optional[str] = None):
        base_dir = Path(__file__).resolve().parent.parent.parent
        if hk_path is None:
            hk_path = str(base_dir / "data" / "sentinel_mental_health.hk")

        self.hk_path = hk_path
        self.fallback_json_path = str(base_dir / "data" / "rag_db.json")
        self.documents: List[Dict[str, Any]] = []
        self.embeddings_matrix: Optional[np.ndarray] = None
        self._encoder = None
        self._hk_package: Optional[HKModelPackage] = None
        self._load_database()

    def _load_database(self) -> None:
        # 1. Primary: Load from high-performance .hk binary file
        if os.path.exists(self.hk_path):
            try:
                self._hk_package = load_hk(self.hk_path)
                self.embeddings_matrix = self._hk_package["embeddings"]
                self.documents = self._hk_package.metadata.get("documents", [])
                print(f"[KnowledgeBase] Loaded {len(self.documents)} protocols from local HK format: {self.hk_path}")
                return
            except Exception as e:
                print(f"[KnowledgeBase] Warning: Failed to load HK format ({e}), falling back to JSON.")

        # 2. Fallback: Load from rag_db.json
        if os.path.exists(self.fallback_json_path):
            try:
                with open(self.fallback_json_path, "r", encoding="utf-8") as f:
                    raw_docs = json.load(f)
                self.documents = []
                vectors = []
                for idx, doc in enumerate(raw_docs):
                    self.documents.append({
                        "id": idx,
                        "title": doc.get("title", ""),
                        "content": doc.get("content", ""),
                    })
                    vectors.append(doc.get("vector", [0.0] * 384))
                self.embeddings_matrix = np.array(vectors, dtype=np.float32)
                # Normalize
                norms = np.linalg.norm(self.embeddings_matrix, axis=1, keepdims=True)
                norms[norms == 0] = 1.0
                self.embeddings_matrix = self.embeddings_matrix / norms
                print(f"[KnowledgeBase] Loaded {len(self.documents)} clinical protocols from JSON fallback.")
            except Exception as e:
                print(f"[KnowledgeBase] Error: Failed to load fallback JSON: {e}")
                self.documents = []
        else:
            print(f"[KnowledgeBase] Warning: No clinical database found at {self.hk_path} or {self.fallback_json_path}")
            self.documents = []

    def _get_encoder(self):
        if self._encoder is None:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    import os, sys
                    # Temporarily suppress stderr to avoid noisy PyTorch missing prints
                    orig_stderr = sys.stderr
                    with open(os.devnull, "w") as devnull:
                        sys.stderr = devnull
                        from sentence_transformers import SentenceTransformer
                        self._encoder = SentenceTransformer("all-MiniLM-L6-v2")
                except Exception:
                    self._encoder = False
                finally:
                    sys.stderr = orig_stderr
        return self._encoder if self._encoder is not False else None

    # Common clinical synonym mappings for uniformed personnel mental health
    SYNONYM_MAP = {
        "insomnia": {"sleep", "fatigue", "rest", "exhaustion", "nightmare", "shift"},
        "sleepless": {"sleep", "fatigue", "rest", "exhaustion"},
        "exhausted": {"burnout", "fatigue", "sleep", "tired", "overwork"},
        "burnout": {"exhaustion", "fatigue", "stress", "overwork", "operational"},
        "trauma": {"ptsd", "combat", "incident", "flashback", "nightmare"},
        "depressed": {"hopeless", "sad", "worthless", "isolation", "withdrawal"},
        "anxious": {"panic", "nervous", "agitation", "worry", "fear"},
        "suicide": {"harm", "crisis", "hopeless", "kill", "die", "emergency"},
    }

    def _lexical_similarity(self, query: str, doc: Dict[str, Any]) -> float:
        """Token overlap similarity with synonym expansion and proportional scoring."""
        raw_query_tokens = set(re.findall(r"\w+", query.lower()))
        if not raw_query_tokens:
            return 0.0

        query_tokens = set(raw_query_tokens)
        for token in raw_query_tokens:
            if token in self.SYNONYM_MAP:
                query_tokens.update(self.SYNONYM_MAP[token])

        title_text = doc.get("title", "").lower()
        title_tokens = set(re.findall(r"\w+", title_text))
        content_tokens = set(re.findall(r"\w+", doc.get("content", "").lower()[:1500]))

        # Exact phrase in title or content
        clean_query = query.strip().lower()
        if clean_query in title_text:
            return 0.95

        title_overlap = len(query_tokens.intersection(title_tokens))
        content_overlap = len(query_tokens.intersection(content_tokens))

        title_score = min(0.6, (title_overlap / max(1, len(title_tokens))) * 1.5 + (0.4 if title_overlap > 0 else 0.0))
        content_score = min(0.4, (content_overlap / max(1, len(query_tokens))) * 0.4)

        return min(1.0, title_score + content_score)

    def search(self, query: str, threshold: float = 0.35, max_length: int = 500) -> Optional[Dict[str, Any]]:
        """
        Finds the most relevant clinical protocol for a user query.
        Uses local HK embedding vectors or lexical keyword matching.
        """
        if not self.documents or not query.strip():
            return None

        best_score = -1.0
        best_doc = None

        encoder = self._get_encoder()
        query_vec = None
        if encoder is not None:
            try:
                q_emb = encoder.encode(query)
                q_norm = np.linalg.norm(q_emb)
                if q_norm > 0:
                    query_vec = (q_emb / q_norm).astype(np.float32)
            except Exception:
                query_vec = None

        # 1. Neural Vector Similarity via HK matrix multiplication if query vector exists
        if query_vec is not None and self.embeddings_matrix is not None:
            sims = np.dot(self.embeddings_matrix, query_vec)
            best_idx = int(np.argmax(sims))
            best_score = float(sims[best_idx])
            best_doc = self.documents[best_idx]

        # 2. Lexical Keyword Overlap Fallback / Booster
        for doc in self.documents:
            lex_score = self._lexical_similarity(query, doc)
            if lex_score > best_score:
                best_score = lex_score
                best_doc = doc

        if best_doc and best_score >= threshold:
            raw_content = best_doc.get("content", "")
            if raw_content.startswith("---"):
                parts = raw_content.split("---", 2)
                if len(parts) >= 3:
                    raw_content = parts[2].strip()

            snippet = raw_content[:max_length] + ("..." if len(raw_content) > max_length else "")
            return {
                "title": best_doc.get("title", "Clinical Protocol"),
                "content": snippet,
                "score": round(best_score, 3),
                "format": "HKNT-Binary" if self._hk_package is not None else "Lexical",
            }

        return None


# Global singleton instance
_kb_instance: Optional[ClinicalKnowledgeBase] = None

def get_knowledge_base() -> ClinicalKnowledgeBase:
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = ClinicalKnowledgeBase()
    return _kb_instance
