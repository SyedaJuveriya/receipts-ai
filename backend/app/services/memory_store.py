from pathlib import Path
from qdrant_client import QdrantClient, models
from fastembed import TextEmbedding

from app.models.memory import MemoryRecord


COLLECTION_NAME = "receipts_memories"
VECTOR_SIZE = 384


class MemoryStore:
    def __init__(self) -> None:
        storage_path = Path(__file__).resolve().parents[2] / "data" / "qdrant"
        storage_path.mkdir(parents=True, exist_ok=True)
        self.client = QdrantClient(path=str(storage_path))
        self.embedding_model = TextEmbedding("sentence-transformers/all-MiniLM-L6-v2")

        if not self.client.collection_exists(COLLECTION_NAME):
            self.client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=VECTOR_SIZE,
            distance=models.Distance.COSINE,
        ),
    )

    def save(self, memory: MemoryRecord) -> None:
        vector = list(self.embedding_model.embed([memory.content]))[0].tolist()

        self.client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                models.PointStruct(
                    id=memory.id,
                    vector=vector,
                    payload=memory.model_dump(mode="json"),
                )
            ],
        )

    def search(self, query: str, limit: int = 5) -> list[dict]:
        vector = list(self.embedding_model.embed([query]))[0].tolist()

        results = self.client.query_points(
            collection_name=COLLECTION_NAME,
            query=vector,
            limit=limit,
        ).points

        return [
            {
                "score": point.score,
                **point.payload,
            }
            for point in results
        ]

    def close(self) -> None:
        self.client.close()