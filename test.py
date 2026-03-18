# test_search.py
import asyncio

from src.core import bootstrap
from src.db.connection import AsyncSessionLocal
from src.ingestion.embedder import embed_query
from src.retrieval.search import search_knowledge_base


async def test():
    bootstrap()
    embedding = await embed_query("What projects has Chitrank built?")

    async with AsyncSessionLocal() as db:
        chunks = await search_knowledge_base(embedding, db)
        for c in chunks:
            print(f"{c['similarity']} | {c['source']} | {c['content'][:80]}")


asyncio.run(test())
