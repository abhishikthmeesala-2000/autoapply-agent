from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol

from qdrant_client import QdrantClient
from qdrant_client.http import models


class ResumeVectorStore(Protocol):
    def upsert_resume_evidence(
        self,
        *,
        profile_id: str,
        master_resume_id: str,
        evidence: list[tuple[str, str, str]],
    ) -> None: ...


def _hash_embedding(text: str, dimensions: int = 16) -> list[float]:
    values = [0.0] * dimensions
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    for index, byte in enumerate(digest):
        values[index % dimensions] += (byte / 255.0) - 0.5
    return values


@dataclass
class QdrantResumeVectorStore:
    client: QdrantClient
    collection_name: str = "resume_evidence"

    def ensure_collection(self, vector_size: int = 16) -> None:
        collections = self.client.get_collections().collections
        exists = any(collection.name == self.collection_name for collection in collections)
        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE,
                ),
            )

    def upsert_resume_evidence(
        self,
        *,
        profile_id: str,
        master_resume_id: str,
        evidence: list[tuple[str, str, str]],
    ) -> None:
        if not evidence:
            return

        self.ensure_collection()
        points = []
        for evidence_id, claim_text, source_ref in evidence:
            points.append(
                models.PointStruct(
                    id=evidence_id,
                    vector=_hash_embedding(claim_text),
                    payload={
                        "profile_id": profile_id,
                        "master_resume_id": master_resume_id,
                        "evidence_id": evidence_id,
                        "claim_text": claim_text,
                        "source_ref": source_ref,
                    },
                )
            )

        self.client.upsert(collection_name=self.collection_name, points=points)


class NoopResumeVectorStore:
    def upsert_resume_evidence(
        self,
        *,
        profile_id: str,
        master_resume_id: str,
        evidence: list[tuple[str, str, str]],
    ) -> None:
        return
