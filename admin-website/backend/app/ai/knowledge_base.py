"""
Mental Health Clinical Knowledge Base & RAG Vector Search
Integrates the 21 clinical skills and pre-computed vector database from Mental_Health_Ui.
Provides cosine vector search with lexical fallback for maximum resilience.
"""

import os
import re
import json
import math
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple


class ClinicalKnowledgeBase:
    """
    Manages the RAG clinical protocol documents and semantic similarity matching.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Default to backend/data/rag_db.json
            base_dir = Path(__file__).resolve().parent.parent.parent
            db_path = str(base_dir / "data" / "rag_db.json")

        self.db_path = db_path
        self.documents: List[Dict[str, Any]] = []
        self._encoder = None
        self._load_database()

    def _load_database(self) -> None:
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    self.documents = json.load(f)
                print(f"[KnowledgeBase] Loaded {len(self.documents)} clinical protocols from {self.db_path}")
            except Exception as e:
                print(f"[KnowledgeBase] Warning: Failed to load {self.db_path}: {e}")
                self.documents = []
        else:
            print(f"[KnowledgeBase] Warning: Vector database not found at {self.db_path}")
            self.documents = []

    def _get_encoder(self):
        if self._encoder is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._encoder = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception as e:
                # Encoder not available on this python env or offline
                self._encoder = False
        return self._encoder if self._encoder is not False else None

    @staticmethod
    def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _lexical_similarity(self, query: str, doc: Dict[str, Any]) -> float:
        """Token overlap similarity between query and title/content."""
        query_tokens = set(re.findall(r"\w+", query.lower()))
        if not query_tokens:
            return 0.0

        title_tokens = set(re.findall(r"\w+", doc.get("title", "").lower()))
        content_tokens = set(re.findall(r"\w+", doc.get("content", "").lower()[:600]))

        # High weight for title matches, moderate weight for content matches
        title_overlap = len(query_tokens.intersection(title_tokens))
        content_overlap = len(query_tokens.intersection(content_tokens))

        score = (title_overlap * 0.4) + min(0.6, content_overlap * 0.08)
        return min(1.0, score)

    def search(self, query: str, threshold: float = 0.35, max_length: int = 500) -> Optional[Dict[str, Any]]:
        """
        Finds the most relevant clinical protocol for a user query.
        Uses neural embedding cosine similarity if SentenceTransformer is available,
        with robust lexical fallback.
        """
        if not self.documents or not query.strip():
            return None

        best_score = -1.0
        best_doc = None

        encoder = self._get_encoder()
        query_vec = None
        if encoder is not None:
            try:
                query_vec = encoder.encode(query).tolist()
            except Exception:
                query_vec = None

        for doc in self.documents:
            score = 0.0
            if query_vec is not None and "vector" in doc and doc["vector"]:
                # 1. Neural Vector Similarity
                score = self._cosine_similarity(query_vec, doc["vector"])
            else:
                # 2. Lexical Keyword Overlap
                score = self._lexical_similarity(query, doc)

            if score > best_score:
                best_score = score
                best_doc = doc

        if best_doc and best_score >= threshold:
            raw_content = best_doc.get("content", "")
            # Clean markdown header metadata (--- frontmatter ---)
            if raw_content.startswith("---"):
                parts = raw_content.split("---", 2)
                if len(parts) >= 3:
                    raw_content = parts[2].strip()

            snippet = raw_content[:max_length] + ("..." if len(raw_content) > max_length else "")
            return {
                "title": best_doc.get("title", "Clinical Protocol"),
                "content": snippet,
                "score": round(best_score, 3),
            }

        return None


# Global singleton instance
_kb_instance: Optional[ClinicalKnowledgeBase] = None

def get_knowledge_base() -> ClinicalKnowledgeBase:
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = ClinicalKnowledgeBase()
    return _kb_instance
