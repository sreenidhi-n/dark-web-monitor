import logging

from elasticsearch import AsyncElasticsearch

from app.config import settings

logger = logging.getLogger(__name__)

FINDINGS_INDEX = "dwm_findings"

INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "url": {"type": "keyword"},
            "title": {"type": "text", "analyzer": "standard"},
            "content": {"type": "text", "analyzer": "standard"},
            "matched_keywords": {"type": "keyword"},
            "source_id": {"type": "integer"},
            "first_seen": {"type": "date"},
            "last_seen": {"type": "date"},
        }
    }
}


def get_es_client() -> AsyncElasticsearch:
    return AsyncElasticsearch([settings.elasticsearch_url])


async def ensure_index(client: AsyncElasticsearch) -> None:
    exists = await client.indices.exists(index=FINDINGS_INDEX)
    if not exists:
        await client.indices.create(index=FINDINGS_INDEX, body=INDEX_MAPPING)
        logger.info("Created Elasticsearch index: %s", FINDINGS_INDEX)


async def index_finding(client: AsyncElasticsearch, finding: dict) -> None:
    await client.index(
        index=FINDINGS_INDEX,
        id=finding["content_hash"],  # deduplicate by content hash
        document={
            "url": finding.get("url"),
            "title": finding.get("title", ""),
            "content": finding.get("text", ""),
            "matched_keywords": finding.get("matched_keywords", []),
            "source_id": finding.get("source_id"),
            "first_seen": finding.get("first_seen"),
            "last_seen": finding.get("last_seen"),
        },
    )


async def search_findings(
    client: AsyncElasticsearch, query: str, size: int = 20, from_: int = 0
) -> dict:
    return await client.search(
        index=FINDINGS_INDEX,
        body={
            "from": from_,
            "size": size,
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title^2", "content", "matched_keywords^3"],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                }
            },
            "highlight": {
                "fields": {"content": {"fragment_size": 150, "number_of_fragments": 3}}
            },
        },
    )
