"""
Common Questions Service

Clusters student chat questions by embedding similarity to surface
the most frequently asked question topics on the advisor dashboard.
"""

from typing import List, Dict, Any
from core.config import get_firestore_client


class CommonQuestionsService:
    """Service for clustering and retrieving common student questions."""

    COLLECTION_NAME = "question_embeddings"

    def __init__(self):
        self.db = get_firestore_client()

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = sum(x * x for x in a) ** 0.5
        mag_b = sum(x * x for x in b) ** 0.5
        return dot / (mag_a * mag_b) if mag_a and mag_b else 0.0

    def get_common_questions(
        self, limit: int = 5, similarity_threshold: float = 0.85
    ) -> List[Dict[str, Any]]:
        """
        Cluster stored question embeddings and return the most common topics.

        1. Loads all question embeddings from Firestore
        2. Greedy clustering: pick question with most similar neighbors,
           group them, remove from pool, repeat
        3. Returns top N clusters sorted by count

        Returns:
            List of dicts: { text, count, conversationIds }
        """
        docs = list(self.db.collection(self.COLLECTION_NAME).stream())

        if not docs:
            return []

        # Extract questions with embeddings
        questions = []
        for doc in docs:
            data = doc.to_dict()
            embedding = data.get("embedding")
            if embedding is None:
                continue
            # Firestore Vector objects have a .value property
            if hasattr(embedding, "value"):
                embedding = list(embedding.value)
            elif isinstance(embedding, (list, tuple)):
                embedding = list(embedding)
            else:
                continue

            questions.append({
                "text": data.get("text", ""),
                "embedding": embedding,
                "conversationId": data.get("conversationId", ""),
                "studentId": data.get("studentId", ""),
            })

        if not questions:
            return []

        n = len(questions)
        assigned = [False] * n

        # Precompute neighbor lists above threshold
        neighbors: Dict[int, List[int]] = {i: [] for i in range(n)}
        for i in range(n):
            for j in range(i + 1, n):
                sim = self._cosine_similarity(
                    questions[i]["embedding"], questions[j]["embedding"]
                )
                if sim >= similarity_threshold:
                    neighbors[i].append(j)
                    neighbors[j].append(i)

        clusters = []
        while len(clusters) < limit:
            # Find unassigned question with most unassigned neighbors
            best_idx = -1
            best_count = -1
            for i in range(n):
                if assigned[i]:
                    continue
                unassigned_neighbors = sum(
                    1 for j in neighbors[i] if not assigned[j]
                )
                if unassigned_neighbors > best_count:
                    best_count = unassigned_neighbors
                    best_idx = i

            if best_idx == -1:
                break

            # Build cluster from this seed
            cluster_indices = [best_idx]
            assigned[best_idx] = True
            for j in neighbors[best_idx]:
                if not assigned[j]:
                    cluster_indices.append(j)
                    assigned[j] = True

            # Representative question = the seed (most connected)
            conversation_ids = list(set(
                questions[i]["conversationId"] for i in cluster_indices
                if questions[i]["conversationId"]
            ))

            clusters.append({
                "text": questions[best_idx]["text"],
                "count": len(cluster_indices),
                "conversationIds": conversation_ids,
            })

        # Sort by count descending
        clusters.sort(key=lambda c: c["count"], reverse=True)
        return clusters


# Singleton
_common_questions_service = None


def get_common_questions_service() -> CommonQuestionsService:
    """Get or create the CommonQuestionsService singleton."""
    global _common_questions_service
    if _common_questions_service is None:
        _common_questions_service = CommonQuestionsService()
    return _common_questions_service
