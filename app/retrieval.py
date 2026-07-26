"""Local and Databricks Vector Search retrieval providers."""

from __future__ import annotations

from typing import Protocol

from app.retrieval_models import RetrievalHit, RetrievalQuery, terms


class Retriever(Protocol):
    def search(self, query: RetrievalQuery) -> list[RetrievalHit]: ...


class LocalRetriever:
    def __init__(self, hits: list[RetrievalHit]) -> None:
        self._hits = hits

    def search(self, query: RetrievalQuery) -> list[RetrievalHit]:
        query_terms = terms(query.text)
        results = []
        for hit in self._hits:
            if hit.series_id != query.series_id or hit.version_id != query.version_id:
                continue
            if hit.language != query.language or not hit.permitted:
                continue
            if query.allowed_source_ids and hit.source_id not in query.allowed_source_ids:
                continue
            overlap = len(query_terms & terms(hit.text))
            if not overlap:
                continue
            results.append(hit.model_copy(update={"score": max(hit.score, overlap / len(query_terms))}))
        return sorted(results, key=lambda hit: (-hit.score, hit.source_id))[: query.limit]


class VectorSearchClient(Protocol):
    def search(self, *, index_name: str, query: str, filters: dict[str, object], limit: int) -> list[dict]: ...


class DatabricksVectorSearchRetriever:
    def __init__(self, client: VectorSearchClient, index_name: str) -> None:
        self._client = client
        self._index_name = index_name

    def search(self, query: RetrievalQuery) -> list[RetrievalHit]:
        rows = self._client.search(
            index_name=self._index_name,
            query=query.text,
            filters={"series_id": query.series_id, "version_id": query.version_id, "language": query.language, "allowed_source_ids": query.allowed_source_ids},
            limit=query.limit,
        )
        return [
            RetrievalHit.model_validate({**row, "permitted": row.get("permitted", True)})
            for row in rows
            if row.get("series_id") == query.series_id
            and row.get("version_id") == query.version_id
            and row.get("language") == query.language
            and row.get("permitted", True)
            and (not query.allowed_source_ids or row.get("source_id") in query.allowed_source_ids)
        ][: query.limit]
